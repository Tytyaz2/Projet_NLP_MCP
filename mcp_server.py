import os
import shutil
from pathlib import Path
from fastapi import FastAPI, Request
from fastmcp import FastMCP
from pypdf import PdfReader
from docx import Document
import uvicorn

# --- Setup ---
app = FastAPI(title="MCP Hybrid Server")
mcp = FastMCP("File Organizer")

CONTAINER_ROOT = os.path.abspath(os.environ.get("CONTAINER_ROOT", "/data_mount"))
LLM_SANDBOX_LIMIT = None

# --- Path validation ---
def _validate_path(user_input_path: str) -> str | None:
    global LLM_SANDBOX_LIMIT
    if not user_input_path: user_input_path = ""
    if user_input_path.startswith("/home"): user_input_path = ""

    combined_path = os.path.join(CONTAINER_ROOT, user_input_path.lstrip(os.path.sep))
    absolute_resolved_path = os.path.realpath(combined_path)

    is_root = (absolute_resolved_path == CONTAINER_ROOT)
    is_child = absolute_resolved_path.startswith(os.path.join(CONTAINER_ROOT, ""))

    if not (is_root or is_child):
        print(f"[SEC] Rejet physique: {absolute_resolved_path} n'est pas dans {CONTAINER_ROOT}")
        return None

    if LLM_SANDBOX_LIMIT:
        is_limit_root = (absolute_resolved_path == LLM_SANDBOX_LIMIT)
        is_limit_child = absolute_resolved_path.startswith(os.path.join(LLM_SANDBOX_LIMIT, ""))
        if not (is_limit_root or is_limit_child):
            print(f"[SEC] Rejet logique: {absolute_resolved_path} hors limite {LLM_SANDBOX_LIMIT}")
            return None

    return absolute_resolved_path

# --- Logic tools ---
def _logic_set_limit(limit_path: str) -> str:
    global LLM_SANDBOX_LIMIT
    current = LLM_SANDBOX_LIMIT
    LLM_SANDBOX_LIMIT = None
    safe = _validate_path(limit_path)
    if not safe:
        LLM_SANDBOX_LIMIT = current
        return "ERREUR: Chemin invalide."
    LLM_SANDBOX_LIMIT = safe
    return f"SUCCÈS: Limite fixée à {limit_path}"

def _logic_list_files(path: str = "") -> list[str]:
    safe = _validate_path(path)
    if not safe: return ["ERREUR: Accès refusé ou hors limite."]
    try:
        if os.path.isfile(safe): return [os.path.basename(safe)]
        items = os.listdir(safe)
        return items if items else ["(Dossier vide)"]
    except Exception as e: return [f"ERREUR: {e}"]

def _logic_create_dir(path: str) -> str:
    safe = _validate_path(path)
    if not safe: return "ERREUR: Chemin invalide."
    try:
        os.makedirs(safe, exist_ok=True)
        return "SUCCÈS"
    except Exception as e:
        return f"ERREUR: {e}"

def _logic_move_file(source_path: str, destination_path: str) -> str:
    safe_src = _validate_path(source_path)
    safe_dst = _validate_path(destination_path)
    if not safe_src or not safe_dst: return "ERREUR: Chemins invalides."
    try:
        shutil.move(safe_src, safe_dst)
        return "SUCCÈS: Déplacé."
    except Exception as e:
        return f"ERREUR: {e}"

def _logic_extract_preview(path: str) -> str:
    safe = _validate_path(path)
    if not safe:
        return "ERREUR: chemin invalide."

    ext = Path(safe).suffix.lower()
    try:
        if ext == ".pdf":
            reader = PdfReader(safe)
            return (reader.pages[0].extract_text() or "").strip() if reader.pages else ""
        elif ext == ".docx":
            doc = Document(safe)
            text = ""
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"
                    if len(text) >= 4000:
                        break
            return text.strip()
        elif ext in [".txt", ".md", ".log"]:
            with open(safe, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(4000).strip()
        else:
            return f"[EXTENSION NON SUPPORTÉE] {ext}"
    except Exception as e:
        return f"[ERREUR LECTURE FICHIER] {e}"

# --- MCP tools ---
@mcp.tool()
def set_sandbox_limit(limit_path: str) -> str: return _logic_set_limit(limit_path)

@mcp.tool()
def list_files(path: str = "") -> list[str]: return _logic_list_files(path)

@mcp.tool()
def create_directory(path: str) -> str: return _logic_create_dir(path)

@mcp.tool()
def move_file(source_path: str, destination_path: str) -> str: return _logic_move_file(source_path, destination_path)

@mcp.tool()
def extract_preview(path: str) -> str: return _logic_extract_preview(path)

# --- API ---
@app.post("/tools/{tool_name}/execute")
async def handle_tool_execution(tool_name: str, request: Request):
    kwargs = await request.json()
    try:
        if tool_name == "set_sandbox_limit": return _logic_set_limit(**kwargs)
        elif tool_name == "list_files": return _logic_list_files(path=kwargs.get("path", ""))
        elif tool_name == "create_directory": return _logic_create_dir(**kwargs)
        elif tool_name == "move_file": return _logic_move_file(**kwargs)
        elif tool_name == "extract_preview": return _logic_extract_preview(**kwargs)
        else: return f"ERREUR: Outil inconnu"
    except Exception as e:
        return f"INTERNAL ERROR: {e}"

# --- Launch server ---
if __name__ == "__main__":
    print(f"--- SERVER READY ---")
    print(f"Montage: {CONTAINER_ROOT}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
