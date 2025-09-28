import streamlit as st
import openai
from openai import OpenAI
import requests
from PIL import Image
import io
import base64
from datetime import datetime
import os

# Konfiguracja strony
st.set_page_config(
    page_title="DALL-E Image Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicjalizacja sesji
if "generated_images" not in st.session_state:
    st.session_state.generated_images = []
if "current_image_url" not in st.session_state:
    st.session_state.current_image_url = None
if "image_history" not in st.session_state:
    st.session_state.image_history = []


def initialize_openai_client():
    """Inicjalizacja klienta OpenAI"""
    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not api_key:
        st.error("⚠️ Brak klucza API OpenAI. Dodaj OPENAI_API_KEY do secrets.toml lub zmiennych środowiskowych.")
        st.stop()

    return OpenAI(api_key=api_key)


def construct_prompt(subject, attributes, style, environment, composition, effects, negative_prompt):
    """Konstruowanie promptu na podstawie pól formularza"""
    prompt_parts = []

    if subject:
        prompt_parts.append(f"Subject: {subject}")
    if attributes:
        prompt_parts.append(f"Details: {attributes}")
    if style:
        prompt_parts.append(f"Style: {style}")
    if environment:
        prompt_parts.append(f"Setting: {environment}")
    if composition:
        prompt_parts.append(f"Composition: {composition}")
    if effects:
        prompt_parts.append(f"Additional effects: {effects}")

    main_prompt = ". ".join(prompt_parts)

    if negative_prompt:
        main_prompt += f". Avoid: {negative_prompt}"

    return main_prompt


def generate_image(client, prompt, size="1024x1024", quality="standard"):
    """Generowanie obrazu za pomocą DALL-E"""
    try:
        with st.spinner("🎨 Generowanie obrazu..."):
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )

            return response.data[0].url, response.data[0].revised_prompt
    except Exception as e:
        st.error(f"Błąd podczas generowania obrazu: {str(e)}")
        return None, None


# def edit_image(client, image_url, modification_prompt, size="1024x1024"):
#     """Modyfikacja obrazu (używa variation, ponieważ edit wymaga przezroczystości)"""
#     try:
#         with st.spinner("🔄 Modyfikowanie obrazu..."):
#             # Konstruujemy nowy prompt łączący poprzedni z modyfikacją
#             new_prompt = f"Based on the previous image, make the following changes: {modification_prompt}"
#
#             response = client.images.generate(
#                 model="dall-e-3",
#                 prompt=new_prompt,
#                 size=size,
#                 quality="standard",
#                 n=1,
#             )
#
#             return response.data[0].url, response.data[0].revised_prompt
#     except Exception as e:
#         st.error(f"Błąd podczas modyfikacji obrazu: {str(e)}")
#         return None, None


def download_image(image_url, quality_suffix=""):
    """Pobieranie obrazu z URL"""
    try:
        response = requests.get(image_url)
        response.raise_for_status()

        # Tworzenie nazwy pliku z timestampem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dalle_image_{timestamp}{quality_suffix}.png"

        return response.content, filename
    except Exception as e:
        st.error(f"Błąd podczas pobierania obrazu: {str(e)}")
        return None, None


# Interfejs użytkownika
st.title("🎨 DALL-E Image Generator")
st.markdown("Generuj i modyfikuj obrazy za pomocą sztucznej inteligencji OpenAI")

# Sidebar z ustawieniami
with st.sidebar:
    st.header("⚙️ Ustawienia generacji")

    # Rozmiar obrazu
    size_options = {
        "1024x1024": "Kwadratowy (1024x1024)",
        "1792x1024": "Poziomy (1792x1024)",
        "1024x1792": "Pionowy (1024x1792)"
    }
    selected_size = st.selectbox(
        "Rozmiar obrazu:",
        options=list(size_options.keys()),
        format_func=lambda x: size_options[x]
    )

    # Jakość obrazu
    quality_options = {
        "standard": "Standardowa",
        "hd": "Wysoka (HD)"
    }
    selected_quality = st.selectbox(
        "Jakość obrazu:",
        options=list(quality_options.keys()),
        format_func=lambda x: quality_options[x]
    )

# Inicjalizacja klienta OpenAI
client = initialize_openai_client()

# Główny interfejs
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📝 Opis obrazu")

    with st.form("image_prompt_form"):
        st.subheader("1. Temat główny (Subject)")
        subject = st.text_area(
            "Opisz główny obiekt/podmiot obrazu:",
            placeholder="np. piękna kobieta, futurystyczne miasto, kot...",
            height=80
        )

        st.subheader("2. Cechy szczegółowe (Attributes)")
        attributes = st.text_area(
            "Dodaj szczegółowe cechy i charakterystyki:",
            placeholder="np. długie ciemne włosy, niebieskie oczy, elegancka sukienka...",
            height=80
        )

        st.subheader("3. Styl artystyczny / estetyka (Style & Aesthetics)")
        style = st.text_area(
            "Określ styl artystyczny:",
            placeholder="np. fotorealistyczny, malarstwo olejne, anime, cyberpunk...",
            height=80
        )

        st.subheader("4. Otoczenie / tło (Environment / Setting)")
        environment = st.text_area(
            "Opisz otoczenie i tło:",
            placeholder="np. górski krajobraz, nowoczesne wnętrze, ulica miasta...",
            height=80
        )

        st.subheader("5. Kompozycja i perspektywa (Composition / Camera Setup)")
        composition = st.text_area(
            "Określ kompozycję i ujęcie:",
            placeholder="np. portret, pełna postać, widok z lotu ptaka, makro...",
            height=80
        )

        st.subheader("6. Dodatkowe efekty / atmosfera (Extra Details)")
        effects = st.text_area(
            "Dodaj efekty i atmosferę:",
            placeholder="np. złote światło, mgła, deszcz, magiczne światło...",
            height=80
        )

        st.subheader("7. Negative prompt (czego unikać)")
        negative_prompt = st.text_area(
            "Co ma być unikane na obrazie:",
            placeholder="np. rozmazane, zniekształcone, złej jakości...",
            height=80
        )

        generate_button = st.form_submit_button("🎨 Generuj obraz", type="primary")

with col2:
    st.header("🖼️ Wygenerowany obraz")

    if generate_button:
        # Konstruowanie promptu
        full_prompt = construct_prompt(
            subject, attributes, style, environment,
            composition, effects, negative_prompt
        )

        if full_prompt.strip():
            st.info(f"**Skonstruowany prompt:** {full_prompt}")

            # Generowanie obrazu
            image_url, revised_prompt = generate_image(
                client, full_prompt, selected_size, selected_quality
            )

            if image_url:
                st.session_state.current_image_url = image_url
                st.session_state.image_history.append({
                    "url": image_url,
                    "prompt": full_prompt,
                    "revised_prompt": revised_prompt,
                    "timestamp": datetime.now()
                })

                st.success("✅ Obraz wygenerowany pomyślnie!")
                if revised_prompt:
                    st.info(f"**Zmodyfikowany prompt przez DALL-E:** {revised_prompt}")
        else:
            st.warning("⚠️ Wypełnij przynajmniej jedno pole opisu!")

    # Wyświetlanie aktualnego obrazu
    if st.session_state.current_image_url:
        try:
            st.image(st.session_state.current_image_url, caption="Wygenerowany obraz", use_container_width=True)

            # Sekcja pobierania
            st.subheader("📥 Pobierz obraz")

            download_col1, download_col2 = st.columns(2)

            with download_col1:
                if st.button("📱 Pobierz w jakości standardowej"):
                    image_data, filename = download_image(st.session_state.current_image_url, "_standard")
                    if image_data:
                        st.download_button(
                            label="💾 Zapisz plik",
                            data=image_data,
                            file_name=filename,
                            mime="image/png"
                        )

            with download_col2:
                if st.button("🖥️ Pobierz w jakości HD"):
                    # Dla uproszczenia używamy tego samego obrazu
                    # W rzeczywistości można by regenerować w wyższej jakości
                    image_data, filename = download_image(st.session_state.current_image_url, "_hd")
                    if image_data:
                        st.download_button(
                            label="💾 Zapisz plik HD",
                            data=image_data,
                            file_name=filename,
                            mime="image/png"
                        )

            # # Sekcja modyfikacji
            # st.subheader("✏️ Modyfikuj obraz")
            #
            # with st.form("modification_form"):
            #     modification_prompt = st.text_area(
            #         "Opisz jakie zmiany chcesz wprowadzić:",
            #         placeholder="np. zmień kolor włosów na blond, dodaj okulary, usuń tło...",
            #         height=100
            #     )
            #
            #     modify_button = st.form_submit_button("🔄 Modyfikuj obraz", type="secondary")
            #
            #     if modify_button and modification_prompt.strip():
            #         # Modyfikacja obrazu
            #         new_image_url, new_revised_prompt = edit_image(
            #             client, st.session_state.current_image_url,
            #             modification_prompt, selected_size
            #         )
            #
            #         if new_image_url:
            #             st.session_state.current_image_url = new_image_url
            #             st.session_state.image_history.append({
            #                 "url": new_image_url,
            #                 "prompt": modification_prompt,
            #                 "revised_prompt": new_revised_prompt,
            #                 "timestamp": datetime.now(),
            #                 "is_modification": True
            #             })
            #
            #             st.success("✅ Obraz zmodyfikowany pomyślnie!")
            #             st.rerun()
            #     elif modify_button:
            #         st.warning("⚠️ Opisz jakie zmiany chcesz wprowadzić!")

        except Exception as e:
            st.error(f"Błąd podczas wyświetlania obrazu: {str(e)}")

# Historia obrazów
if st.session_state.image_history:
    st.header("📚 Historia wygenerowanych obrazów")

    for i, img_data in enumerate(reversed(st.session_state.image_history[-5:])):  # Ostatnie 5 obrazów
        with st.expander(
                f"Obraz #{len(st.session_state.image_history) - i} - {img_data['timestamp'].strftime('%H:%M:%S')}"):
            col_hist1, col_hist2 = st.columns([1, 2])

            with col_hist1:
                try:
                    st.image(img_data["url"], use_container_width=True)
                except:
                    st.error("Nie można wyświetlić obrazu")

            with col_hist2:
                st.text(f"Typ: {'Modyfikacja' if img_data.get('is_modification') else 'Nowy obraz'}")
                st.text(f"Prompt: {img_data['prompt'][:200]}...")
                if img_data.get('revised_prompt'):
                    st.text(f"Zmodyfikowany: {img_data['revised_prompt'][:200]}...")

                if st.button(f"Użyj tego obrazu", key=f"use_img_{i}"):
                    st.session_state.current_image_url = img_data["url"]
                    st.rerun()

# Stopka
st.markdown("---")
st.markdown("💡 **Wskazówka:** Im bardziej szczegółowe opisy, tym lepszy efekt końcowy!")