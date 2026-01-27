# src/tools/server.py
"""
Outils MCP pour le tri automatique de fichiers.
Ces outils sont exposés à Claude Desktop via le protocole MCP.
"""

from pathlib import Path
from src.mcp import mcp
from src.classifier import analyze_document
from src.classifier import group_documents, apply_plan

SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".doc", ".odt"]


# ────────────────────────────────────────────
# Validation des paramètres
# ────────────────────────────────────────────
def validate_path(path: str) -> Path:
    """Valide un chemin de fichier et retourne un objet Path."""
    if not path or not isinstance(path, str):
        raise ValueError("Le chemin doit être une chaîne non vide")
    path = path.strip()
    if not path:
        raise ValueError("Le chemin ne peut pas être vide ou composé uniquement d'espaces")
    return Path(path)


def validate_extensions(extensions: list[str] | None) -> list[str]:
    """Valide et retourne la liste d'extensions."""
    if extensions is None:
        return SUPPORTED_EXTENSIONS
    if not isinstance(extensions, list):
        raise ValueError("extensions doit être une liste de chaînes (ex: [\".pdf\", \".docx\"])")
    validated = []
    for ext in extensions:
        if not isinstance(ext, str):
            raise ValueError(f"Extension invalide : {ext} (doit être une chaîne)")
        ext = ext.strip()
        if not ext.startswith("."):
            ext = f".{ext}"
        validated.append(ext.lower())
    return validated


# ────────────────────────────────────────────
# TOOL 1 : analyse d'un fichier
# ────────────────────────────────────────────
@mcp.tool()
def analyze_file(path: str) -> dict:
    """
    Analyse un fichier et retourne ses métadonnées.

    Args:
        path: Chemin absolu vers le fichier à analyser

    Returns:
        Un dictionnaire contenant:
        - path: chemin du fichier
        - type: type de document (article, cv, rapport, etc.)
        - date: date détectée dans le document
        - keywords: liste de mots-clés décrivant le contenu
    """
    try:
        p = validate_path(path)
    except ValueError as e:
        return {"error": str(e)}

    if not p.exists():
        return {"error": f"Le fichier {path} n'existe pas"}
    if not p.is_file():
        return {"error": f"{path} n'est pas un fichier"}
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return {"error": f"Extension non supportée : {p.suffix}. Extensions supportées : {', '.join(SUPPORTED_EXTENSIONS)}"}

    info = analyze_document(p)
    return info


# ────────────────────────────────────────────
# TOOL 2 : regroupement des documents
# ────────────────────────────────────────────
@mcp.tool()
def group_files(files_info: list[dict]) -> list[dict]:
    """
    Regroupe les documents analysés par type et thème.

    Args:
        files_info: Liste de dictionnaires retournés par analyze_file

    Returns:
        Liste de groupes, chaque groupe contenant:
        - type: type de document
        - keywords: mots-clés communs au groupe
        - files: liste des chemins de fichiers dans ce groupe
    """
    if not files_info or not isinstance(files_info, list):
        return {"error": "files_info doit être une liste non vide de dictionnaires"}
    for i, info in enumerate(files_info):
        if not isinstance(info, dict):
            return {"error": f"L'élément {i} n'est pas un dictionnaire valide"}
        if "path" not in info or "type" not in info:
            return {"error": f"L'élément {i} doit contenir au minimum 'path' et 'type'"}
    return group_documents(files_info)


# ────────────────────────────────────────────
# TOOL 3 : appliquer le plan d'organisation
# ────────────────────────────────────────────
@mcp.tool()
def apply_file_plan(root: str, groups: list[dict]) -> dict:
    """
    Crée les dossiers et déplace les fichiers selon le plan généré.

    Args:
        root: Dossier racine où organiser les fichiers
        groups: Liste de groupes retournée par group_files

    Returns:
        Résultat de l'opération avec les fichiers déplacés
    """
    try:
        root_path = validate_path(root)
    except ValueError as e:
        return {"error": str(e)}

    if not root_path.exists():
        return {"error": f"Le dossier {root} n'existe pas"}
    if not root_path.is_dir():
        return {"error": f"{root} n'est pas un dossier"}

    if not groups or not isinstance(groups, list):
        return {"error": "groups doit être une liste non vide de groupes"}
    for i, g in enumerate(groups):
        if not isinstance(g, dict):
            return {"error": f"Le groupe {i} n'est pas un dictionnaire valide"}
        if "type" not in g or "files" not in g:
            return {"error": f"Le groupe {i} doit contenir 'type' et 'files'"}

    result = apply_plan(root_path, groups)
    return result


# ────────────────────────────────────────────
# TOOL 4 : lister les fichiers à trier
# ────────────────────────────────────────────
@mcp.tool()
def list_files_to_sort(folder: str, extensions: list[str] = None) -> list[str]:
    """
    Liste tous les fichiers à trier dans un dossier.

    Args:
        folder: Chemin du dossier à scanner
        extensions: Liste d'extensions à inclure (ex: [".pdf", ".docx"])
                   Si non spécifié, utilise: .pdf, .docx, .txt, .doc, .odt

    Returns:
        Liste des chemins absolus des fichiers trouvés
    """
    try:
        folder_path = validate_path(folder)
    except ValueError as e:
        return {"error": str(e)}

    if not folder_path.exists():
        return {"error": f"Le dossier {folder} n'existe pas"}
    if not folder_path.is_dir():
        return {"error": f"{folder} n'est pas un dossier"}

    try:
        exts = validate_extensions(extensions)
    except ValueError as e:
        return {"error": str(e)}

    files = []
    for ext in exts:
        files.extend(folder_path.rglob(f"*{ext}"))

    return [str(f.absolute()) for f in files if f.is_file()]


# ────────────────────────────────────────────
# TOOL 5 : tri automatique complet
# ────────────────────────────────────────────
@mcp.tool()
def sort_folder(folder: str, dry_run: bool = False, extensions: list[str] = None) -> dict:
    """
    Trie automatiquement tous les documents d'un dossier.

    C'est l'outil principal qui exécute le pipeline complet:
    1. Liste tous les fichiers du dossier
    2. Analyse chaque fichier avec l'IA (type, date, keywords)
    3. Regroupe les fichiers par type et thème
    4. Déplace les fichiers dans des sous-dossiers organisés

    Args:
        folder: Chemin du dossier à trier (ex: "/files")
        dry_run: Si True, simule sans déplacer les fichiers
        extensions: Extensions à inclure (défaut: .pdf, .docx, .txt, .doc, .odt)

    Returns:
        Rapport complet du tri effectué avec:
        - files_found: nombre de fichiers trouvés
        - files_analyzed: nombre de fichiers analysés
        - groups: groupes créés avec leurs fichiers
        - moved: fichiers déplacés (vide si dry_run)
    """
    try:
        folder_path = validate_path(folder)
    except ValueError as e:
        return {"error": str(e)}

    try:
        extensions = validate_extensions(extensions)
    except ValueError as e:
        return {"error": str(e)}

    if not isinstance(dry_run, bool):
        return {"error": "dry_run doit être un booléen (true ou false)"}

    # Vérifications
    if not folder_path.exists():
        return {"error": f"Le dossier {folder} n'existe pas"}
    if not folder_path.is_dir():
        return {"error": f"{folder} n'est pas un dossier"}

    result = {
        "folder": folder,
        "dry_run": dry_run,
        "files_found": 0,
        "files_analyzed": 0,
        "groups": [],
        "moved": [],
        "errors": []
    }

    # Étape 1 : Lister les fichiers
    files = []
    for ext in extensions:
        files.extend(folder_path.rglob(f"*{ext}"))
    files = [f for f in files if f.is_file()]
    result["files_found"] = len(files)

    if not files:
        return {"message": "Aucun fichier à trier", **result}

    # Étape 2 : Analyser chaque fichier
    files_info = []
    for file_path in files:
        try:
            info = analyze_document(file_path)
            files_info.append(info)
        except Exception as e:
            result["errors"].append(f"Erreur analyse {file_path.name}: {str(e)}")

    result["files_analyzed"] = len(files_info)

    if not files_info:
        return {"message": "Aucun fichier n'a pu être analysé", **result}

    # Étape 3 : Regrouper les fichiers
    groups = group_documents(files_info)
    result["groups"] = groups.get("groups", [])

    if not result["groups"]:
        return {"message": "Aucun groupe créé", **result}

    # Étape 4 : Appliquer le plan (sauf si dry_run)
    if dry_run:
        result["message"] = f"Simulation terminée: {len(files_info)} fichiers seraient organisés en {len(result['groups'])} groupes"
    else:
        try:
            move_result = apply_plan(folder_path, result["groups"])
            result["moved"] = move_result.get("moved", [])
            result["message"] = f"Tri terminé: {len(result['moved'])} fichiers organisés en {len(result['groups'])} groupes"
        except Exception as e:
            result["errors"].append(f"Erreur déplacement: {str(e)}")

    return result


# ────────────────────────────────────────────
# Point d'entrée du serveur MCP
# ────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
