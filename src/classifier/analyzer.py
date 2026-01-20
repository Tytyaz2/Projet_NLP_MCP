import json
import os
from pathlib import Path
from pypdf import PdfReader
from docx import Document
import ollama
import logging

from src.classifier.preprocessor import preprocess

# Configuration du modèle depuis les variables d'environnement
MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3:latest")

# Configuration du client Ollama
ollama_client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

logger = logging.getLogger(__name__)

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
        resp = ollama_client.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        raw = resp["message"]["content"].strip()

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

    except Exception as e:
        logger.error(f"[ERREUR LLM] {path}: {e}")
        return {
            "path": str(path),
            "type": "autre",
            "date": "unknown",
            "keywords": []
        }
