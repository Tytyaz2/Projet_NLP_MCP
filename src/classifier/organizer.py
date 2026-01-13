import json
import os
import shutil
from pathlib import Path
from collections import defaultdict
import unicodedata
import re
import ollama
import logging

# Configuration du modèle depuis les variables d'environnement
MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3:latest")

# Configuration du client Ollama
ollama_client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

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
# Détection de thèmes similaires
# -------------------------------------------------
def get_main_theme(keywords: list[str]) -> str:
    """Extrait le thème principal des keywords pour regrouper les sujets similaires."""
    if not keywords:
        return "general"
    
    # Mapping de termes similaires vers un thème commun
    theme_mapping = {
        # Médical/Santé
        'retina': 'medical-retine',
        'retinal': 'medical-retine',
        'vessel': 'medical-retine',
        'segmentation': 'medical-retine',
        'medical': 'medical-retine',
        'imaging': 'medical-retine',
        
        # Réseaux/5G
        '5g': 'reseaux-5g',
        '5G': 'reseaux-5g',
        'network': 'reseaux-5g',
        'traffic': 'reseaux-5g',
        'slicing': 'reseaux-5g',
        'resource': 'reseaux-5g',
        
        # Optimisation
        'optimization': 'optimisation',
        'optimisation': 'optimisation',
        'resource': 'optimisation',
        'edge': 'optimisation',
        'scheduling': 'optimisation',
        
        # IA/ML
        'ai': 'ia-ml',
        'AI': 'ia-ml',
        'machine': 'ia-ml',
        'learning': 'ia-ml',
        'deep': 'ia-ml',
        'neural': 'ia-ml',
        
        # Quantique
        'quantum': 'quantique',
        'correction': 'quantique',
        
        # RH/Sociologie
        'rh': 'rh-social',
        'RH': 'rh-social',
        'sociologie': 'rh-social',
        'relations': 'rh-social',
        'organisations': 'rh-social',
    }
    
    # Chercher le premier keyword qui match un thème connu
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        # Chercher une correspondance exacte ou partielle
        for term, theme in theme_mapping.items():
            if term.lower() in keyword_lower or keyword_lower in term.lower():
                return theme
    
    # Si aucun thème trouvé, utiliser le premier keyword
    return slugify(keywords[0])

# -------------------------------------------------
# GROUPING (TOOL 2) - Regroupement intelligent
# -------------------------------------------------
def group_documents(files_info: list[dict]) -> dict:
    groups = defaultdict(list)
    for info in files_info:
        # Normaliser le type de document
        doc_type = normalize_doc_type(info["type"])
        
        # Obtenir le thème principal au lieu d'utiliser tous les keywords
        keywords_list = info.get("keywords", [])[:2]
        main_theme = get_main_theme(keywords_list)
        
        # Grouper par (type, thème)
        groups[(doc_type, main_theme)].append(info)

    result = []
    for (doc_type, theme), files in groups.items():
        # Récupérer les keywords du premier fichier pour l'affichage
        first_file_keywords = files[0].get("keywords", [])
        result.append({
            "type": doc_type,
            "keywords": [theme],  # Utiliser le thème comme keyword unique
            "files": [f["path"] for f in files]
        })
    return {"groups": result}

# -------------------------------------------------
# Generate short folder name (2 words max)
# -------------------------------------------------
def generate_topic_folder(doc_type: str, keywords: list[str]) -> str:
    if not keywords:
        return "sans-theme"

    system_prompt = (
        "Génère un nom de dossier court (max 2 mots) "
        "basé sur le type de document et les mots-clés. "
        "Répond STRICTEMENT en JSON : {\"name\": \"...\"}."
    )
    user_prompt = f"Type: {doc_type}\nKeywords: {', '.join(keywords)}"

    try:
        resp = ollama_client.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        raw = resp["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        name = json.loads(raw)["name"]
        return slugify(name)

    except Exception:
        # Fallback si LLM échoue
        return slugify(keywords[0])

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
        topic_folder = generate_topic_folder(doc_type, keywords)

        target_dir = root / type_folder / topic_folder

        for file_path in files:
            src = Path(file_path)
            new_path = safe_move(src, target_dir)
            moves.append({"from": file_path, "to": new_path})

    return {"moved": moves}
