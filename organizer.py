import json
import shutil
from pathlib import Path
from collections import defaultdict
import unicodedata
import re
import ollama

MODEL_NAME = "deepseek-v3.1:671b-cloud"  # Ollama Cloud, pas besoin de :latest

# -------------------------------------------------
# Slugify : noms de dossiers sûrs
# -------------------------------------------------
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "misc"

# -------------------------------------------------
# GROUPING (TOOL 2)
# -------------------------------------------------
def group_documents(files_info: list[dict]) -> dict:
    groups = defaultdict(list)
    for info in files_info:
        doc_type = info["type"]
        keywords = tuple(sorted(info.get("keywords", [])))
        groups[(doc_type, keywords)].append(info)

    result = []
    for (doc_type, keywords), files in groups.items():
        result.append({
            "type": doc_type,
            "keywords": list(keywords),
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
        resp = ollama.chat(
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
