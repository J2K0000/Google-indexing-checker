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

# --- Logique de vérification (Corrigée v6) ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
}

def _execute_search(query: str, url: str) -> str:
    """
    Fonction d'aide : Exécute UNE requête Google et vérifie la présence de l'URL.
    Utilise la logique v5 (recoller les <cite>) qui est la plus fiable.
    Retourne "Indexed", "Not Found", ou "Blocked".
    """
    google_search_url = f"https://www.google.com/search?q={query}&hl=fr&cr=countryFR"
    
    try:
        response = requests.get(google_search_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()

        # 1. Vérification du blocage ou CAPTCHA
        if "CAPTCHA" in response.text or "nos systèmes ont détecté un trafic inhabituel" in page_text:
            return "Blocked"
        
        # 2. Vérification des phrases claires de "non-indexation"
        if "Aucun document ne correspond" in page_text or "Il se peut qu'aucun bon résultat ne corresponde" in page_text:
            return "Not Found"

        # 3. Vérification de la preuve (logique v5)
        cite_tags = soup.find_all('cite')
        url_with_protocol = url.rstrip('/') 
        url_without_protocol = url_with_protocol.replace("https://", "").replace("http://", "")

        for cite in cite_tags:
            # Correction v5 : recolle les morceaux de texte dans les <cite>
            cite_text = cite.get_text(separator="")
            
            if url_with_protocol in cite_text or url_without_protocol in cite_text:
                return "Indexed" # TROUVÉ !
        
        # 4. Si non bloqué, pas de "aucun doc", et pas dans les <cite> -> non trouvé
        return "Not Found"

    except requests.exceptions.HTTPError:
        return "Blocked" # Erreur 429, 503, etc.
    except requests.exceptions.RequestException:
        return "Blocked" # Erreur de connexion
    except Exception:
        return "Blocked" # Erreur inattendue
    finally:
        # Pause obligatoire pour ne pas se faire bloquer
        time.sleep(1.0)

def check_google_indexing(url: str) -> dict:
    """
    Vérifie si une URL est indexée sur Google en suivant la logique
    multi-étapes fournie par l'utilisateur.
    Version 6 : Implémente Étape 1 (site:) PUIS Étape 2 (URL exacte).
    """
    result = {"URL": url, "Statut": ""}

    # --- ÉTAPE 1 : Recherche avec 'site:' ---
    status1 = _execute_search(query=f"site:{url}", url=url)
    
    if status1 == "Indexed":
        result["Statut"] = "✅ Indexée (via 'site:')"
        return result
    
    if status1 == "Blocked":
        result["Statut"] = "🚫 CAPTCHA/Blocage (Étape 1)"
        return result

    # --- ÉTAPE 2 : Recherche avec URL exacte (si Étape 1 a échoué) ---
    # (status1 doit être "Not Found" pour arriver ici)
    
    # On cherche l'URL exacte, entre guillemets
    status2 = _execute_search(query=f'"{url}"', url=url)

    if status2 == "Indexed":
        result["Statut"] = "✅ Indexée (via URL exacte)"
        return result
    
    if status2 == "Blocked":
        result["Statut"] = "🚫 CAPTCHA/Blocage (Étape 2)"
        return result

    # --- ÉTAPE 3 : Non trouvée après les 2 étapes ---
    result["Statut"] = "❌ Non Indexée"
    return result

# --- Interface de l'application Streamlit (inchangée) ---

st.title("🔎 Vérificateur d'Indexation Google (Version Corrigée v6)")
st.write("Collez une ou plusieurs URLs (une par ligne) pour vérifier si elles sont *réellement* indexées par Google.")
st.write("Cette version utilise une vérification en 2 étapes (`site:URL` puis `\"URL\"`) pour plus de fiabilité.")

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
            # Chaque URL peut prendre ~2 secondes (1s par étape)
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

