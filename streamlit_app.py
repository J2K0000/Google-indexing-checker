import streamlit as st
import httpx  # Remplacement de requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from urllib.parse import quote

# --- Configuration de la page Streamlit ---
st.set_page_config(
    page_title="Vérificateur d'Indexation Google",
    page_icon="🔎",
    layout="centered"
)

# --- Logique de vérification (Corrigée v7) ---
# Utilisation de httpx avec HTTP/2 et des headers réalistes
CLIENT = httpx.Client(
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5.37.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/5.37.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
    },
    follow_redirects=True,
    http2=True,  # Important pour éviter le blocage
    timeout=20.0
)

def _execute_search(query: str, url: str) -> str:
    """
    Fonction d'aide : Exécute UNE requête Google et vérifie la présence de l'URL.
    Utilise la logique v5 (recoller les <cite>) qui est la plus fiable.
    Utilise httpx (v7) pour la requête réseau.
    Retourne "Indexed", "Not Found", ou "Blocked".
    """
    # quote() est nécessaire pour encoder correctement les requêtes (ex: " ")
    google_search_url = f"https://www.google.com/search?q={quote(query)}&hl=fr&cr=countryFR"
    
    try:
        # Remplacement de requests.get par client.get
        response = CLIENT.get(google_search_url)
        
        # Gestion des codes d'erreur (429 = Rate Limit)
        if response.status_code == 429:
            return "Blocked"
        
        response.raise_for_status() # Lève une erreur pour 4xx/5xx (sauf 429 déjà géré)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()

        # 1. Vérification du blocage ou CAPTCHA
        if "CAPTCHA" in response.text or "nos systèmes ont détecté un trafic inhabituel" in page_text:
            return "Blocked"
        
        # 2. Vérification des phrases claires de "non-indexation"
        if "Aucun document ne correspond" in page_text or "Il se peut qu'aucun bon résultat ne corresponde" in page_text:
            return "Not Found"

        # 3. Vérification de la preuve (logique v5/v6)
        cite_tags = soup.find_all('cite')
        url_with_protocol = url.rstrip('/') 
        url_without_protocol = url_with_protocol.replace("https://", "").replace("http://", "")

        for cite in cite_tags:
            cite_text = cite.get_text(separator="") # Recolle les morceaux
            
            if url_with_protocol in cite_text or url_without_protocol in cite_text:
                return "Indexed" # TROUVÉ !
        
        # 4. Si non bloqué, pas de "aucun doc", et pas dans les <cite> -> non trouvé
        return "Not Found"

    except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException):
        return "Blocked" # Gère les erreurs HTTP, de connexion, et les timeouts
    except Exception:
        return "Blocked" # Erreur inattendue
    finally:
        # Pause obligatoire pour ne pas se faire bloquer
        time.sleep(1.0)

def check_google_indexing(url: str) -> dict:
    """
    Vérifie si une URL est indexée sur Google en suivant la logique
    multi-étapes (v6) mais avec le client réseau httpx (v7).
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

st.title("🔎 Vérificateur d'Indexation Google (Version Corrigée v7)")
st.write("Collez une ou plusieurs URLs (une par ligne) pour vérifier si elles sont *réellement* indexées par Google.")
st.write("Cette version utilise `httpx` (HTTP/2) et une vérification en 2 étapes (`site:URL` puis `\"URL\"`) pour une fiabilité maximale.")

# Zone de texte pour les URLs
urls_text = st.text_area("Liste d'URLs à vérifier", height=200, placeholder="https://www.example.com/page1\nhttps://www.example.com/page2")

# Bouton pour lancer la vérification
if st.button("🚀 Lancer la vérification"):
    urls_to_check = [url.strip() for url in urls_text.splitlines() if url.strip()]
    
    if not urls_to_check:
        st.warning("Veuillez entrer au moins une URL.")
    else:
        progress_bar = st.progress(0)
        results = []
        status_text = st.empty()
        
        for i, url in enumerate(urls_to_check):
            status_text.text(f"Vérification de {i+1}/{len(urls_to_check)} : {url}")
            results.append(check_google_indexing(url))
            progress_bar.progress((i + 1) / len(urls_to_check))
        
        status_text.success("Vérification terminée !")
        
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)

        st.info(
            "**Note :** Cet outil utilise le 'scraping' de Google. "
            "Si vous voyez beaucoup d'erreurs '🚫 CAPTCHA/Blocage', "
            "cela signifie que Google a temporairement bloqué votre adresse IP. "
            "Réessayez plus tard."
        )

