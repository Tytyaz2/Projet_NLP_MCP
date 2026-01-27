import json
import shutil
from pathlib import Path
from collections import defaultdict
import unicodedata
import re
import logging

from src.classifier.analyzer import call_ollama_with_retry

logger = logging.getLogger(__name__)

# -------------------------------------------------
# Slugify : noms de dossiers sûrs
# -------------------------------------------------
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "misc"

# -------------------------------------------------
# Normalisation minimale des types
# -------------------------------------------------
def normalize_doc_type(doc_type: str) -> str:
    """Normalise légèrement les types pour éviter les doublons."""
    doc_type_clean = doc_type.lower().strip()

    # Normaliser les pluriels
    if doc_type_clean.endswith('s'):
        doc_type_clean = doc_type_clean[:-1]

    # Normaliser quelques synonymes courants
    synonyms = {
        'picture': 'image',
        'photo': 'image',
        'img': 'image',
        'txt': 'document',
        'text': 'document',
        'file': 'document',
        'pdf': 'document',
        'spreadsheet': 'tableur',
        'excel': 'tableur',
        'powerpoint': 'presentation',
        'slide': 'presentation',
        'vid': 'video',
        'movie': 'video',
        'music': 'audio',
        'sound': 'audio',
        'zip': 'archive',
    }

    return synonyms.get(doc_type_clean, doc_type_clean)

# -------------------------------------------------
# Génération des catégories via LLM (en une seule fois)
# -------------------------------------------------
def generate_categories(all_keywords: list[list[str]]) -> dict:
    """
    Génère des catégories cohérentes pour un ensemble de fichiers.

    Args:
        all_keywords: Liste des keywords de chaque fichier [[kw1, kw2], [kw3, kw4], ...]

    Returns:
        Dict mapping index du fichier -> nom de catégorie
    """
    if not all_keywords:
        return {}

    # Préparer la liste des fichiers avec leurs keywords
    files_desc = []
    for i, keywords in enumerate(all_keywords):
        kw_str = ", ".join(keywords) if keywords else "sans mots-clés"
        files_desc.append(f"Fichier {i}: {kw_str}")

    system_prompt = """Tu es un assistant qui organise des fichiers en catégories.
Tu reçois une liste de fichiers avec leurs mots-clés.
Tu dois créer des CATÉGORIES COHÉRENTES pour regrouper les fichiers similaires.

RÈGLES:
- Crée entre 1 et 10 catégories maximum
- Les noms de catégories doivent être courts (1-3 mots)
- Regroupe les fichiers qui parlent du même sujet
- Si des fichiers sont très similaires, mets-les dans la même catégorie

Réponds UNIQUEMENT en JSON avec ce format:
{
  "categories": {
    "0": "nom-categorie",
    "1": "nom-categorie",
    "2": "autre-categorie"
  }
}

où les clés sont les numéros des fichiers et les valeurs sont les noms de catégories."""

    user_prompt = "Voici les fichiers à catégoriser:\n\n" + "\n".join(files_desc)

    try:
        raw = call_ollama_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            context="generate_categories"
        )

        # Nettoyer la réponse (enlever les blocs de code markdown)
        if "```" in raw:
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw, re.DOTALL)
            if match:
                raw = match.group(1)

        data = json.loads(raw)
        categories = data.get("categories", {})

        # Convertir les clés en int et slugify les valeurs
        result = {}
        for key, value in categories.items():
            try:
                idx = int(key)
                result[idx] = slugify(value)
            except (ValueError, TypeError):
                continue

        return result

    except (ConnectionError, RuntimeError) as e:
        logger.warning(f"Ollama indisponible pour catégories: {e}")
        # Fallback : utiliser le premier keyword de chaque fichier
        result = {}
        for i, keywords in enumerate(all_keywords):
            if keywords:
                result[i] = slugify(keywords[0])
            else:
                result[i] = "general"
        return result

    except Exception as e:
        logger.warning(f"Erreur pour catégories: {e}")
        result = {}
        for i, keywords in enumerate(all_keywords):
            if keywords:
                result[i] = slugify(keywords[0])
            else:
                result[i] = "general"
        return result

# -------------------------------------------------
# GROUPING (TOOL 2) - Regroupement intelligent
# -------------------------------------------------
def group_documents(files_info: list[dict]) -> dict:
    """
    Regroupe les documents par type et catégorie thématique.
    Utilise le LLM pour créer des catégories cohérentes en une seule passe.
    """
    if not files_info:
        return {"groups": []}

    # Étape 1: Collecter tous les keywords
    all_keywords = []
    for info in files_info:
        keywords = info.get("keywords", [])[:3]  # Max 3 keywords par fichier
        all_keywords.append(keywords)

    # Étape 2: Générer les catégories via LLM (une seule fois pour tous les fichiers)
    categories = generate_categories(all_keywords)

    # Étape 3: Regrouper par (type normalisé, catégorie)
    groups = defaultdict(list)
    for i, info in enumerate(files_info):
        doc_type = normalize_doc_type(info["type"])
        category = categories.get(i, "general")
        groups[(doc_type, category)].append(info)

    # Étape 4: Construire le résultat
    result = []
    for (doc_type, category), files in groups.items():
        result.append({
            "type": doc_type,
            "keywords": [category],
            "files": [f["path"] for f in files]
        })

    return {"groups": result}

# -------------------------------------------------
# Generate short folder name (utilise directement la catégorie)
# -------------------------------------------------
def generate_topic_folder(keywords: list[str]) -> str:
    """Retourne le nom du dossier thématique."""
    if not keywords:
        return "general"
    # La catégorie est déjà slugifiée
    return keywords[0]

# -------------------------------------------------
# Moving files (TOOL 3)
# -------------------------------------------------
def safe_move(src: Path, dest_dir: Path) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    if not dest.exists():
        shutil.move(str(src), str(dest))
        return str(dest)

    base, ext = src.stem, src.suffix
    counter = 1
    while True:
        new = dest_dir / f"{base}_{counter}{ext}"
        if not new.exists():
            shutil.move(str(src), str(new))
            return str(new)
        counter += 1

def apply_plan(root: Path, groups: list[dict]) -> dict:
    moves = []
    for group in groups:
        doc_type = group["type"]
        keywords = group["keywords"]
        files = group["files"]

        type_folder = slugify(doc_type)
        topic_folder = generate_topic_folder(keywords)

        target_dir = root / type_folder / topic_folder

        for file_path in files:
            src = Path(file_path)
            new_path = safe_move(src, target_dir)
            moves.append({"from": file_path, "to": new_path})

    return {"moved": moves}
