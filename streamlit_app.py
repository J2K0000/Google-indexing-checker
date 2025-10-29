import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd

# --- Configuration de la page Streamlit ---
st.set_page_config(
    page_title="Vérificateur d'Indexation Google",
    page_icon="🔎",
    layout="centered"
)

# --- Logique de vérification (Corrigée v5) ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
}

def check_google_indexing(url: str) -> dict:
    """
    Vérifie si une URL est indexée sur Google et retourne un dictionnaire avec les détails.
    Version 5 : Revient à la logique <cite> (v3), mais la corrige en "recollant"
    le texte des balises <span> internes (ex: <span>https:</span><span>//</span>...).
    C'est la cause d'échec identifiée grâce aux captures de code source.
    """
    query = f"site:{url}"
    google_search_url = f"https://www.google.com/search?q={query}&hl=fr&cr=countryFR"
    
    result = {"URL": url, "Statut": ""}

    try:
        response = requests.get(google_search_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text() # Pour les vérifications de texte génériques

        # --- LOGIQUE DE VÉRIFICATION CORRIGÉE (v5) ---

        # 1. Vérification du blocage ou CAPTCHA (prioritaire)
        if "CAPTCHA" in response.text or "nos systèmes ont détecté un trafic inhabituel" in page_text:
            result["Statut"] = "🚫 CAPTCHA/Blocage"
        
        # 2. Vérification des phrases claires de "non-indexation"
        elif "Aucun document ne correspond" in page_text:
            result["Statut"] = "❌ Non Indexée"
        
        elif "Il se peut qu'aucun bon résultat ne corresponde" in page_text:
             result["Statut"] = "❌ Non Indexée"

        # 3. NOUVELLE LOGIQUE DE DÉTECTION (v5) - Correction de la v3
        # On utilise les <cite> mais en recollant le texte.
        else:
            cite_tags = soup.find_all('cite')
            found_in_cite = False
            
            # Prépare les URLs à chercher (avec et sans protocole)
            url_with_protocol = url.rstrip('/') 
            url_without_protocol = url_with_protocol.replace("https://", "").replace("http://", "")

            for cite in cite_tags:
                # LA CORRECTION CLÉ EST ICI :
                # get_text(separator="") va coller "https:", "//", "domaine.com"
                # en "https://domaine.com" sans espaces.
                cite_text = cite.get_text(separator="")
                
                # On vérifie si le texte <cite> reconstruit contient
                # l'une OU l'autre des versions de notre URL.
                if url_with_protocol in cite_text or url_without_protocol in cite_text:
                    found_in_cite = True
                    break
            
            if found_in_cite:
                result["Statut"] = "✅ Indexée"
            else:
                # Cas où Google montre des résultats similaires mais pas l'URL exacte.
                result["Statut"] = "❌ Non Indexée (résultats similaires)"

    except requests.exceptions.HTTPError as http_err:
        result["Statut"] = f"🚫 Erreur HTTP : {http_err.response.status_code}"
    except requests.exceptions.RequestException:
        result["Statut"] = "🚫 Erreur de connexion"
    except Exception:
        result["Statut"] = "🚫 Erreur inattendue"
    
    # Pause pour réduire le risque de blocage
    time.sleep(1.0)
    return result

# --- Interface de l'application Streamlit (inchangée) ---

st.title("🔎 Vérificateur d'Indexation Google (Version Corrigée v5)")
st.write("Collez une ou plusieurs URLs (une par ligne) pour vérifier si elles sont *réellement* indexées par Google (via la commande site:).")

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
        status_text = st.empty()
        
        for i, url in enumerate(urls_to_check):
            status_text.text(f"Vérification de {i+1}/{len(urls_to_check)} : {url}")
            results.append(check_google_indexing(url))
            # Met à jour la barre de progression
            progress_bar.progress((i + 1) / len(urls_to_check))
        
        status_text.success("Vérification terminée !")
        
        # Affiche les résultats dans un tableau propre
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)

        # Ajoute une note d'avertissement sur la fiabilité
        st.info(
            "**Note :** Cet outil utilise le 'scraping' de Google. "
            "Si vous voyez beaucoup d'erreurs '🚫 CAPTCHA/Blocage', "
            "cela signifie que Google a temporairement bloqué votre adresse IP. "
            "Réessayez plus tard."
        )

