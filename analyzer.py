import json
from pathlib import Path
from pypdf import PdfReader
from docx import Document
import ollama

MODEL_NAME = "deepseek-v3.1:671b-cloud"  # nom du modèle dans le cloud (sans :latest)

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

    system_prompt = (
        "Tu es un classificateur de documents. "
        "Retourne strictement un JSON contenant {type,date,keywords}."
    )

    user_prompt = f"""
Analyse ce document :

<<<
{preview}
>>>

Retourne exactement ce JSON :

{{
  "type": "...",
  "date": "...",
  "keywords": ["...", "..."]
}}
"""

    try:
        resp = ollama.chat(
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
        print(f"[ERREUR LLM] {path}: {e}")
        return {
            "path": str(path),
            "type": "autre",
            "date": "unknown",
            "keywords": []
        }
