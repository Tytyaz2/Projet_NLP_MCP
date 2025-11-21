import sys
import json
import shutil
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader
from docx import Document
import ollama   # client Python Ollama

# ─────────────────────────────────────────
# Extraction d'un aperçu (1ère page / début)
# ─────────────────────────────────────────

def extract_first_page_pdf(path: str) -> str:
    try:
        reader = PdfReader(path)
        if len(reader.pages) == 0:
            return ""
        first_page = reader.pages[0]
        text = first_page.extract_text() or ""
        return text.strip()
    except Exception as e:
        return f"[ERREUR EXTRACTION PDF] {e}"


def extract_first_part_docx(path: str, max_chars: int = 4000) -> str:
    try:
        doc = Document(path)
        texts = []
        total = 0
        for para in doc.paragraphs:
            if para.text:
                texts.append(para.text)
                total += len(para.text)
                if total >= max_chars:
                    break
        return "\n".join(texts).strip()
    except Exception as e:
        return f"[ERREUR EXTRACTION DOCX] {e}"


def extract_first_part_txt(path: str, max_chars: int = 4000) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(max_chars)
        return content.strip()
    except Exception as e:
        return f"[ERREUR LECTURE TEXTE] {e}"


def extract_preview(path: str) -> str:
    """
    Retourne un aperçu textuel du fichier (1ère page / début).
    On choisit la méthode en fonction de l'extension.
    """
    ext = Path(path).suffix.lower()

    if ext == ".pdf":
        return extract_first_page_pdf(path)
    elif ext == ".docx":
        return extract_first_part_docx(path)
    elif ext in [".txt", ".md", ".log"]:
        return extract_first_part_txt(path)
    else:
        # Fallback : tentative de lecture texte simple
        return extract_first_part_txt(path)


# ─────────────────────────────────────────
# Appel LLM (Ollama) pour analyser le document
# ─────────────────────────────────────────

MODEL_NAME = "gemma3:4b"  # modèle Ollama utilisé


def analyze_with_llm(preview: str, filename: str) -> dict:
    """
    Appelle Ollama avec la 1ère page (preview) et renvoie un dict du type :
    {
      "type": "cv" | "article" | "ordonnance" | "autre",
      "date": "2024-01-15" ou "unknown",
      "keywords": ["...", "..."]
    }
    """

    system_instructions = (
        "Tu es un classificateur de documents. "
        "À partir du texte fourni, tu dois analyser le type de document, "
        "sa date d'émission si elle est présente, et des mots-clés représentatifs. "
        "Tu dois répondre STRICTEMENT en JSON, sans texte autour."
    )

    user_prompt = f"""
On te donne un extrait correspondant principalement à la première page d'un document.

Nom du fichier : {filename}

À partir de ce seul texte, tu dois :

1. Déterminer le TYPE du document parmi : "article", "cv", "ordonnance" ou autre si besoin.
   - "cv" : curriculum vitae, profil de personne, expériences, formations, compétences, etc.
   - "ordonnance" : document médical avec prescriptions, posologie, nom de médecin ou d'établissement de santé.
   - "article" : rapport, article, note, mémoire, documentation, texte explicatif structuré.
   - "autre" : à toi de déterminer le TYPE.

2. Déterminer la DATE DU DOCUMENT si elle est indiquée dans le texte (date de rédaction / émission).
   - Retourne-la au format YYYY-MM-DD si possible.
   - Sinon, mets "unknown".

3. Proposer entre 3 et 8 mots-clés représentatifs du contenu.

Réponds STRICTEMENT en JSON de la forme :

{{
  "type": "...",
  "date": "...",
  "keywords": ["...", "...", "..."]
}}

Texte du document :

<<<
{preview}
>>>
""".strip()

    # Appel à Ollama (chat)
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response["message"]["content"].strip()

    # Nettoyage éventuel (```json ... ```)
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "type": "autre",
            "date": "unknown",
            "keywords": [],
            "raw_response": raw,
        }

    data.setdefault("type", "autre")
    data.setdefault("date", "unknown")
    data.setdefault("keywords", [])

    return data


# ─────────────────────────────────────────
# Génération LLM du nom de sous-dossier (2 mots max)
# ─────────────────────────────────────────

def generate_topic_folder_name_llm(doc_type: str, keywords: list[str]) -> str:
    """
    Utilise Ollama pour générer un nom de sous-dossier court (2 mots max)
    à partir du type de document et de la liste de mots-clés.
    Retourne un nom déjà slugifié, prêt à être utilisé comme nom de dossier.
    """
    if not keywords:
        return "sans-theme"

    system_instructions = (
        "Tu génères des noms de dossiers courts et parlants pour organiser des documents. "
        "Tu dois proposer un nom de sous-dossier basé sur le type de document et une liste de mots-clés. "
        "Le nom doit faire au maximum 2 mots (par exemple: 'network slicing', 'retinal images', 'cv', 'ordonnances'). "
        "Réponds STRICTEMENT en JSON sans texte autour, au format : "
        '{ "folder_name": "..." }'
    )

    keywords_str = ", ".join(keywords)

    user_prompt = f"""
Type de document : {doc_type}

Mots-clés associés :
{keywords_str}

Tâche :
- Proposer un nom de sous-dossier qui résume le thème.
- Le nom doit contenir au maximum 2 mots (séparés par des espaces).
- Pas d'explication, pas de phrase, seulement un nom court.

Réponds STRICTEMENT en JSON :

{{
  "folder_name": "..."
}}
""".strip()

    folder_name = ""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw = response["message"]["content"].strip()

        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        data = json.loads(raw)
        folder_name = (data.get("folder_name") or "").strip()
    except Exception:
        # Fallback si l'appel LLM se passe mal
        folder_name = keywords[0].strip() if keywords else "sans theme"

    if not folder_name:
        folder_name = keywords[0].strip() if keywords else "sans theme"

    # Limiter à 2 mots max
    words = folder_name.split()
    words = words[:2]
    trimmed = " ".join(words)

    # Slugify pour en faire un vrai nom de dossier
    return slugify(trimmed) or "sans-theme"


# ─────────────────────────────────────────
# Analyse d'un seul fichier
# ─────────────────────────────────────────

def analyze_single_file(path: Path) -> dict:
    preview = extract_preview(str(path))
    result = analyze_with_llm(preview, path.name)
    return {
        "path": str(path),
        "type": result["type"],
        "date": result["date"],
        "keywords": result["keywords"],
    }


# ─────────────────────────────────────────
# Utilitaires pour noms de dossiers et déplacement
# ─────────────────────────────────────────

def slugify(text: str) -> str:
    """Transforme un texte en nom de dossier safe."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "misc"


def safe_move(src: Path, dest_dir: Path) -> Path:
    """
    Déplace un fichier dans dest_dir.
    Si un fichier du même nom existe déjà, ajoute un suffixe _1, _2, etc.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / src.name
    if not dest.exists():
        shutil.move(str(src), str(dest))
        return dest

    stem = src.stem
    suffix = src.suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            shutil.move(str(src), str(candidate))
            return candidate
        counter += 1


# ─────────────────────────────────────────
# Organisation d'un dossier entier
# ─────────────────────────────────────────

def organize_directory(root: Path) -> None:
    """
    1. Liste les fichiers du dossier (non récursif pour l'instant).
    2. Analyse chaque fichier avec le LLM (type, keywords, date).
    3. Crée une arborescence:
       <root>/<type>/<sous-dossier-theme basé sur keywords>/,
       où le nom du sous-dossier est généré par le LLM (2 mots max).
    4. Déplace les fichiers dedans.
    """

    # 1. Récupérer les fichiers
    files = [p for p in root.iterdir() if p.is_file()]
    if not files:
        print(f"Aucun fichier à traiter dans : {root}")
        return

    print(f"Analyse de {len(files)} fichier(s) dans : {root}")

    analyzed: list[dict] = []
    for f in files:
        print(f"  → Analyse : {f.name}")
        info = analyze_single_file(f)
        analyzed.append(info)

    # 2. Grouper par (type, ensemble complet de keywords)
    #    → le groupement utilise tous les keywords normalisés
    groups = defaultdict(list)

    for info in analyzed:
        doc_type = info.get("type") or "autre"
        keywords = info.get("keywords") or []

        normalized_keywords = tuple(sorted(k.strip().lower() for k in keywords if k.strip()))
        group_key = (doc_type, normalized_keywords)
        groups[group_key].append(info)

    # 3. Appliquer le plan : créer dossiers et déplacer les fichiers
    for (doc_type, keywords_tuple), files_infos in groups.items():
        type_folder = slugify(doc_type)
        keywords_list = list(keywords_tuple)

        # Nom de sous-dossier généré par LLM (2 mots max)
        topic_folder = generate_topic_folder_name_llm(doc_type, keywords_list)
        target_dir = root / type_folder / topic_folder

        print(f"\nGroupe type='{doc_type}', keywords={keywords_list or ['(aucun)']}")
        print(f"  → Dossier cible : {target_dir}")

        for info in files_infos:
            src = Path(info["path"])
            if not src.exists():
                print(f"    ! Fichier introuvable, ignoré : {src}")
                continue
            try:
                new_path = safe_move(src, target_dir)
                print(f"    Déplacé : {src.name} -> {new_path.relative_to(root)}")
            except PermissionError as e:
                print(f"    ! Permission refusée pour déplacer {src} : {e}")
            except Exception as e:
                print(f"    ! Erreur lors du déplacement de {src} : {e}")

    print("\nClassification terminée.")


# ─────────────────────────────────────────
# Entrée principale
# ─────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <fichier_ou_dossier>")
        sys.exit(1)

    target = Path(sys.argv[1])

    if not target.exists():
        print(f"Chemin introuvable : {target}")
        sys.exit(1)

    # CAS 1 : un seul fichier → test
    if target.is_file():
        info = analyze_single_file(target)
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return

    # CAS 2 : dossier → on organise tout
    if target.is_dir():
        organize_directory(target)
        return


if __name__ == "__main__":
    main()
