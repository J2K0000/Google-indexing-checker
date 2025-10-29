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

# --- Logique de vérification (Corrigée) ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
}

def check_google_indexing(url: str) -> dict:
    """
    Vérifie si une URL est indexée sur Google et retourne un dictionnaire avec les détails.
    La logique est plus stricte pour différencier "Indexée" de "Résultats similaires".
    """
    query = f"site:{url}"
    # On force la langue (hl=fr) et le pays (cr=countryFR) pour des résultats stables
    google_search_url = f"https://www.google.com/search?q={query}&hl=fr&cr=countryFR"
    
    result = {"URL": url, "Statut": ""}

    try:
        response = requests.get(google_search_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text() # Pour les vérifications de texte génériques

        # --- LOGIQUE DE VÉRIFICATION CORRIGÉE ---

        # 1. Vérification du blocage ou CAPTCHA (prioritaire)
        # "nos systèmes ont détecté un trafic inhabituel" est le signe de blocage IP
        if "CAPTCHA" in response.text or "nos systèmes ont détecté un trafic inhabituel" in page_text:
            result["Statut"] = "🚫 CAPTCHA/Blocage"
        
        # 2. Vérification des phrases claires de "non-indexation"
        # C'est le cas où Google ne trouve absolument rien.
        elif "Aucun document ne correspond" in page_text:
            result["Statut"] = "❌ Non Indexée"
        
        # C'est le cas où Google ne trouve pas l'URL exacte, mais propose des alternatives.
        elif "Il se peut qu'aucun bon résultat ne corresponde" in page_text:
             result["Statut"] = "❌ Non Indexée"

        # 3. Si aucune phrase de "non-indexation" n'est trouvée,
        #    cela ne signifie pas que l'URL est indexée (c'était l'erreur).
        #    Google peut afficher des résultats *similaires* du même domaine.
        #    Nous devons donc chercher la *preuve* que notre URL exacte est présente.
        #    La balise <cite> est la plus fiable pour ça, car elle affiche l'URL du résultat.
        else:
            cite_tags = soup.find_all('cite')
            found_in_cite = False
            for cite in cite_tags:
                # On vérifie si l'URL exacte est dans le texte de la balise <cite>
                # (Google peut ajouter '...' ou couper, mais l'URL principale doit y être)
                if url in cite.get_text():
                    found_in_cite = True
                    break
            
            if found_in_cite:
                result["Statut"] = "✅ Indexée"
            else:
                # Si on est ici, c'est que Google n'a pas dit "aucun résultat",
                # mais notre URL n'est pas non plus dans les balises <cite>.
                # C'est le cas où il montre des pages du domaine, mais pas celle-ci.
                # C'est donc "Non Indexée" pour cette URL spécifique.
                result["Statut"] = "❌ Non Indexée (résultats similaires)"

    except requests.exceptions.HTTPError as http_err:
        # Gère les erreurs 403, 429 (trop de requêtes), 503, etc.
        result["Statut"] = f"🚫 Erreur HTTP : {http_err.response.status_code}"
    except requests.exceptions.RequestException:
        result["Statut"] = "🚫 Erreur de connexion"
    except Exception:
        result["Statut"] = "🚫 Erreur inattendue"
    
    # Petite pause pour ne pas surcharger Google et réduire le risque de blocage
    time.sleep(0.5)
    return result

# --- Interface de l'application Streamlit (inchangée) ---

st.title("🔎 Vérificateur d'Indexation Google (Version Corrigée)")
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
