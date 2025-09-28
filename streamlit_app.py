# app/streamlit_app.py
import os
import base64
import io
from typing import Optional
import streamlit as st
import openai
import requests

# Uwaga: biblioteka openai może mieć różne interfejsy w zależności od wersji.
# Poniżej używamy klasycznego podejścia `openai` z metodą Image.create.
# Jeśli używasz nowej biblioteki klienta OpenAI, dopasuj wywołanie zgodnie z dokumentacją.

# ====== Konfiguracja ======
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
st.secrets.get("OPENAI_API_KEY", None)
if not OPENAI_API_KEY:
    st.error("Brakuje klucza API OpenAI. Ustaw zmienną środowiskową OPENAI_API_KEY lub użyj Streamlit secrets.")
    st.stop()
openai.api_key = OPENAI_API_KEY

# ====== Helpers ======
def make_prompt(fields: dict, modification: Optional[str] = None) -> str:
    """
    Skleja pełny prompt z pól zgodnie z szablonem.
    fields: dict z kluczami:
        subject, attributes, style, environment, composition, extra, negative
    modification: opcjonalny tekst z prośbą o poprawkę
    """
    parts = []
    parts.append(f"Subject: {fields.get('subject','')}")
    parts.append(f"Attributes: {fields.get('attributes','')}")
    parts.append(f"Style & Aesthetics: {fields.get('style','')}")
    parts.append(f"Environment / Setting: {fields.get('environment','')}")
    parts.append(f"Composition / Camera: {fields.get('composition','')}")
    parts.append(f"Extra details / Atmosphere: {fields.get('extra','')}")
    negative = fields.get('negative','')
    if negative:
        parts.append(f"Negative prompt (avoid): {negative}")
    if modification:
        parts.append(f"Modification request: {modification}")
    # Zwracamy scalony, ale czytelny prompt.
    return "\n".join(parts)

def generate_image_from_openai(prompt: str, size: str = "1024x1024", n: int = 1) -> bytes:
    """
    Wywołanie OpenAI Image API. Zwraca bajty pierwszego obrazu.
    Obsługujemy zarówno `b64_json` jak i `url` w odpowiedzi.
    """
    # Wywołanie – dostosuj do wersji biblioteki jeśli trzeba.
    try:
        response = openai.Image.create(prompt=prompt, n=n, size=size)
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}")

    data0 = response['data'][0]
    # Jeśli mamy base64 w 'b64_json'
    if 'b64_json' in data0:
        image_bytes = base64.b64decode(data0['b64_json'])
        return image_bytes
    # Jeśli API zwróciło URL
    if 'url' in data0:
        url = data0['url']
        r = requests.get(url)
        if r.status_code == 200:
            return r.content
        else:
            raise RuntimeError(f"Error downloading image from URL: {r.status_code}")
    raise RuntimeError("Nieznany format odpowiedzi od OpenAI Image API")

# ====== UI ======
st.set_page_config(page_title="Generator obrazów AI (DALL·E)", layout="centered")
st.title("Generator obrazów AI — szkic promptu + poprawki")

st.markdown("""
Wypełnij pola opisujące co chcesz zobaczyć na obrazie. Pole '**Negative prompt**' to co *unikać*.
Naciśnij **Generuj**, aby utworzyć pierwszą wersję obrazu. Po wygenerowaniu możesz dopisać uwagi i kliknąć **Generuj poprawkę**.
""")

with st.form(key="prompt_form"):
    st.subheader("1) Szablon promptu (wypełnij pola)")
    subject = st.text_input("1. Temat główny (subject)", placeholder="np. młoda kobieta na rowerze")
    attributes = st.text_area("2. Cechy szczegółowe (attributes)", placeholder="np. krótkie włosy, czerwony płaszcz, uśmiech")
    style = st.text_area("3. Styl artystyczny / estetyka (style & aesthetics)", placeholder="np. realizm, fotografia, film noir, cyberpunk")
    environment = st.text_area("4. Otoczenie / tło (environment / setting)", placeholder="np. brukowana uliczka, mgła, jesienny park")
    composition = st.text_area("5. Kompozycja i perspektywa (composition / camera setup)", placeholder="np. zbliżenie 3/4, szeroki kąt, ISO 200")
    extra = st.text_area("6. Dodatkowe efekty / atmosfera (extra details)", placeholder="np. światło złotej godziny, lekki bokeh")
    negative = st.text_area("7. Negative prompt (czego unikać)", placeholder="np. zniekształcenia, artefakty, watermark")
    submitted = st.form_submit_button("Generuj")

# sekcja ustawień rozdzielczości / pobierania
st.sidebar.header("Ustawienia obrazu / pobierania")
size = st.sidebar.selectbox("Rozdzielczość (size)", options=["1024x1024","1792x1024","1024x1792"], index=0)
file_format = st.sidebar.selectbox("Format pobrania", options=["png","jpg"], index=0)
n_images = st.sidebar.slider("Ilość wariantów (n)", 1, 4, 1)

# Przechowujemy w session_state ostatni prompt i obraz
if "last_prompt" not in st.session_state:
    st.session_state.last_prompt = ""
if "last_image_bytes" not in st.session_state:
    st.session_state.last_image_bytes = None

# Generowanie pierwszej wersji
if submitted:
    fields = {
        "subject": subject.strip(),
        "attributes": attributes.strip(),
        "style": style.strip(),
        "environment": environment.strip(),
        "composition": composition.strip(),
        "extra": extra.strip(),
        "negative": negative.strip()
    }
    prompt = make_prompt(fields)
    st.session_state.last_prompt = prompt
    st.info("Wysyłam zapytanie do OpenAI...")
    try:
        image_bytes = generate_image_from_openai(prompt=prompt, size=size, n=n_images)
        st.session_state.last_image_bytes = image_bytes
        st.success("Obraz wygenerowany.")
    except Exception as e:
        st.error(f"Błąd podczas generowania obrazu: {e}")
        st.stop()

# Wyświetlenie obrazu i pole do modyfikacji
if st.session_state.last_image_bytes:
    st.subheader("Wynik (podgląd)")
    st.image(st.session_state.last_image_bytes, use_column_width=True)
    st.write("Oryginalny prompt (możesz go edytować):")
    st.code(st.session_state.last_prompt, language="text")

    # Pobieranie obrazu
    if file_format == "png":
        download_label = "Pobierz PNG"
        mime = "image/png"
    else:
        download_label = "Pobierz JPG"
        mime = "image/jpeg"

    st.download_button(
        label=download_label,
        data=st.session_state.last_image_bytes,
        file_name=f"ai_image.{file_format}",
        mime=mime
    )

    # Pole na poprawki/opisy do kolejnego wygenerowania
    st.subheader("Poprawki / uwagi do kolejnej wersji")
    modification = st.text_area("Napisz co zmienić (dodatkowe instrukcje dla modelu)", "")
    if st.button("Generuj poprawkę"):
        # Scal prompt z modyfikacją i generuj ponownie
        new_prompt = st.session_state.last_prompt + "\nModification request: " + modification
        st.session_state.last_prompt = new_prompt
        st.info("Wysyłam poprawiony prompt do OpenAI...")
        try:
            image_bytes = generate_image_from_openai(prompt=new_prompt, size=size, n=1)
            st.session_state.last_image_bytes = image_bytes
            st.success("Nowa wersja wygenerowana.")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Błąd podczas generowania poprawki: {e}")
