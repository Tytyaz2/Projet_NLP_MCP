from mcp import Server, tool
from pathlib import Path

from analyzer import analyze_document
from organizer import (
    group_documents,
    apply_plan
)

server = Server(name="file-classifier")


# ────────────────────────────────────────────
# TOOL 1 : analyse d’un fichier
# ────────────────────────────────────────────
@tool()
def analyze_file(path: str) -> dict:
    """
    Analyse un fichier et retourne :
    {
      "path": "...",
      "type": "...",
      "date": "...",
      "keywords": [...],
    }
    """
    p = Path(path)
    info = analyze_document(p)
    return info


# ────────────────────────────────────────────
# TOOL 2 : regroupement des documents
# ────────────────────────────────────────────
@tool()
def group_files(files_info: list[dict]) -> dict:
    """
    Regroupe les documents par type + keywords.
    """
    return group_documents(files_info)


# ────────────────────────────────────────────
# TOOL 3 : appliquer le plan
# ────────────────────────────────────────────
@tool()
def apply_file_plan(root: str, groups: list[dict]) -> dict:
    """
    Crée les dossiers et déplace les fichiers selon le plan généré.
    """
    root_path = Path(root)
    result = apply_plan(root_path, groups)
    return result


if __name__ == "__main__":
    server.run()
