import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd

# --- Configuration de la page Streamlit ---
# st.set_page_config doit être la première commande Streamlit exécutée
st.set_page_config(
    page_title="Vérificateur d'Indexation Google",
    page_icon="🔎",
    layout="centered"
)

# --- Logique de vérification (inchangée) ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def check_google_indexing(url: str) -> dict:
    """
    Vérifie si une URL est indexée sur Google et retourne un dictionnaire avec les détails.
    """
    query = f"site:{url}"
    google_search_url = f"https://www.google.com/search?q={query}&hl=fr"
    
    result = {"URL": url, "Statut": ""}

    try:
        response = requests.get(google_search_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()

        if "Aucun document ne correspond" in page_text:
            result["Statut"] = "❌ Non Indexée"
        elif "CAPTCHA" in response.text:
            result["Statut"] = "🚫 CAPTCHA détecté"
        else:
            result["Statut"] = "✅ Indexée"

    except requests.exceptions.HTTPError as http_err:
        result["Statut"] = f"🚫 Erreur HTTP : {http_err.response.status_code}"
    except requests.exceptions.RequestException:
        result["Statut"] = "🚫 Erreur de connexion"
    except Exception:
        result["Statut"] = "🚫 Erreur inattendue"
    
    # Petite pause pour ne pas surcharger Google
    time.sleep(0.5)
    return result

# --- Interface de l'application Streamlit ---

st.title("🔎 Vérificateur d'Indexation Google")
st.write("Collez une ou plusieurs URLs (une par ligne) pour vérifier si elles sont indexées par Google.")

# Zone de texte pour les URLs
urls_text = st.text_area("Liste d'URLs à vérifier", height=200, placeholder="https://www.example.com/page1\nhttps://www.example.com/page2")

# Bouton pour lancer la vérification
if st.button("🚀 Lancer la vérification"):
    urls_to_check = [url.strip() for url in urls_text.splitlines() if url.strip()]
    
    if not urls_to_check:
        st.warning("Veuillez entrer au moins une URL.")
    else:
        # Barre de progression
        progress_bar = st.progress(0)
        results = []
        
        # Affiche un message pendant le traitement
        with st.spinner(f"Vérification de {len(urls_to_check)} URL(s) en cours..."):
            for i, url in enumerate(urls_to_check):
                results.append(check_google_indexing(url))
                # Met à jour la barre de progression
                progress_bar.progress((i + 1) / len(urls_to_check))
        
        st.success("Vérification terminée !")
        
        # Affiche les résultats dans un tableau propre
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)

