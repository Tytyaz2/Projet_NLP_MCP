import json
import os
import time
from pathlib import Path
from pypdf import PdfReader
from docx import Document
import ollama
import httpx
import logging

from src.classifier.preprocessor import preprocess

# Configuration du modèle depuis les variables d'environnement
MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:20b-cloud")

# Configuration du client Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ollama_client = ollama.Client(host=OLLAMA_HOST)

# Configuration retry
MAX_RETRIES = 3
RETRY_DELAY = 2  # secondes entre chaque tentative

logger = logging.getLogger(__name__)


def check_ollama_available() -> bool:
    """Vérifie si le serveur Ollama est accessible."""
    try:
        httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        return True
    except (httpx.ConnectError, httpx.TimeoutException, Exception):
        return False


def call_ollama_with_retry(messages: list[dict], context: str = "") -> str:
    """
    Appelle Ollama avec retry automatique.

    Args:
        messages: Messages à envoyer au modèle
        context: Description du contexte pour les logs (ex: nom du fichier)

    Returns:
        Le contenu de la réponse brute du modèle

    Raises:
        ConnectionError: Si Ollama est inaccessible après toutes les tentatives
        RuntimeError: Si le modèle ne répond pas correctement après toutes les tentatives
    """
    if not check_ollama_available():
        raise ConnectionError(
            f"Ollama n'est pas accessible sur {OLLAMA_HOST}. "
            "Vérifiez qu'Ollama est lancé avec 'ollama serve'."
        )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = ollama_client.chat(model=MODEL_NAME, messages=messages)
            raw = resp["message"]["content"].strip()
            if raw:
                return raw
            last_error = RuntimeError("Réponse vide du modèle")
            logger.warning(f"[RETRY {attempt}/{MAX_RETRIES}] {context}: réponse vide, nouvelle tentative...")
        except ollama.ResponseError as e:
            if "model" in str(e).lower() and "not found" in str(e).lower():
                raise RuntimeError(
                    f"Le modèle '{MODEL_NAME}' n'est pas installé. "
                    f"Installez-le avec : ollama pull {MODEL_NAME}"
                ) from e
            last_error = e
            logger.warning(f"[RETRY {attempt}/{MAX_RETRIES}] {context}: erreur Ollama ({e}), nouvelle tentative...")
        except (httpx.ConnectError, httpx.TimeoutException, ConnectionError) as e:
            last_error = ConnectionError(
                f"Ollama a perdu la connexion sur {OLLAMA_HOST}. "
                "Vérifiez qu'Ollama est toujours en cours d'exécution."
            )
            logger.warning(f"[RETRY {attempt}/{MAX_RETRIES}] {context}: connexion perdue ({e}), nouvelle tentative...")
        except Exception as e:
            last_error = e
            logger.warning(f"[RETRY {attempt}/{MAX_RETRIES}] {context}: erreur ({e}), nouvelle tentative...")

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    raise last_error or RuntimeError(f"Échec après {MAX_RETRIES} tentatives")

# -------------------------------------------------
# Extraction previews
# -------------------------------------------------
def extract_pdf(path):
    try:
        reader = PdfReader(path)
        if not reader.pages:
            return ""
        return reader.pages[0].extract_text() or ""
    except:
        return ""

def extract_docx(path):
    try:
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs[:20])
        return text.strip()
    except:
        return ""

def extract_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(4000).strip()
    except:
        return ""

def extract_preview(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf(path)
    if ext == ".docx":
        return extract_docx(path)
    return extract_text(path)

# -------------------------------------------------
# LLM analyze (Cloud)
# -------------------------------------------------
def analyze_document(path: Path) -> dict:
    preview = extract_preview(path)
    filename = path.name

    # Prétraitement NLP
    processed = preprocess(preview)
    cleaned_text = processed['text']
    detected_lang = processed['lang']
    token_count = processed['token_count']

    logger.info(f"[PREPROCESS] {filename}: lang={detected_lang}, tokens={token_count}")

    system_prompt = (
        "Tu es un expert en classification de fichiers. "
        "Analyse le CONTENU réel du fichier, pas juste son extension. "
        "Sois précis et descriptif dans ta classification. "
        "Utilise des catégories qui reflètent vraiment la NATURE du contenu."
    )

    user_prompt = f"""
Fichier: {filename}
Langue détectée: {detected_lang}

CONTENU (prétraité, {token_count} tokens):
<<<
{cleaned_text[:2000]}
>>>

INSTRUCTIONS STRICTES:

1. TYPE - Identifie la VRAIE nature du contenu (1-2 mots):
   
   DOCUMENTS ACADÉMIQUES/PROFESSIONNELS:
   - "article" : article scientifique, recherche, publication
   - "cv" : curriculum vitae, resume
   - "rapport" : rapport de projet, compte-rendu
   - "cours" : support de cours, slides, correction d'exercices
   - "these" : thèse, mémoire
   
   DOCUMENTS PERSONNELS:
   - "facture" : factures, devis
   - "administratif" : documents officiels, formulaires
   - "note" : notes personnelles, brouillons
   
   AUTRES TYPES:
   - "tableur" : Excel, données tabulaires
   - "presentation" : PowerPoint, slides
   - "image" : photos, schémas, dessins
   - "code" : fichiers de programmation
   - "autre" : si vraiment inclassable

2. KEYWORDS - 2 mots-clés maximum sur le SUJET/THÈME principal:
   - Sois SPÉCIFIQUE et DESCRIPTIF
   - Exemple bon: "segmentation-retine", "reseaux-5g", "optimisation-edge"
   - Exemple mauvais: "ai", "document", "file"
   - Évite les termes trop génériques

3. DATE - Format YYYY ou YYYY-MM si présent, sinon "unknown"

RETOURNE EXACTEMENT CE JSON:
{{
  "type": "...",
  "date": "...",
  "keywords": ["...", "..."]
}}
"""

    try:
        raw = call_ollama_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            context=filename
        )

        # Nettoyage si le modèle ajoute des ```json
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        data = json.loads(raw)
        return {
            "path": str(path),
            "type": data.get("type", "autre"),
            "date": data.get("date", "unknown"),
            "keywords": data.get("keywords", [])
        }

    except ConnectionError as e:
        logger.error(f"[OLLAMA INDISPONIBLE] {path}: {e}")
        return {
            "path": str(path),
            "type": "autre",
            "date": "unknown",
            "keywords": [],
            "error": str(e)
        }

    except RuntimeError as e:
        logger.error(f"[ERREUR MODÈLE] {path}: {e}")
        return {
            "path": str(path),
            "type": "autre",
            "date": "unknown",
            "keywords": [],
            "error": str(e)
        }

    except json.JSONDecodeError as e:
        logger.error(f"[ERREUR JSON] {path}: réponse non-JSON du modèle")
        return {
            "path": str(path),
            "type": "autre",
            "date": "unknown",
            "keywords": [],
            "error": f"Le modèle n'a pas retourné un JSON valide: {e}"
        }

    except Exception as e:
        logger.error(f"[ERREUR] {path}: {e}")
        return {
            "path": str(path),
            "type": "autre",
            "date": "unknown",
            "keywords": [],
            "error": str(e)
        }
