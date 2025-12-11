import os
import shutil
import uvicorn
from fastapi import FastAPI, Request
from fastmcp import FastMCP

# 1. SETUP
app = FastAPI(title="MCP Hybrid Server")
mcp = FastMCP("File Organizer")

# --- CORRECTION SÉCURITÉ ---
# On s'assure que la racine est propre et absolue, SANS slash de fin pour la comparaison
CONTAINER_ROOT = os.path.abspath(os.environ.get("CONTAINER_ROOT", "/data_mount"))
LLM_SANDBOX_LIMIT = None

# 2. LOGIQUE PURE
def _validate_path(user_input_path: str) -> str | None:
    global LLM_SANDBOX_LIMIT
    if not user_input_path: user_input_path = ""
    if user_input_path.startswith("/home"): user_input_path = "" 
    
    # Construction du chemin cible
    # lstrip permet d'éviter que "/dossier" soit vu comme une racine absolue
    combined_path = os.path.join(CONTAINER_ROOT, user_input_path.lstrip(os.path.sep))
    absolute_resolved_path = os.path.realpath(combined_path)
    
    # --- CORRECTION DU SLASH ---
    # On vérifie si c'est la racine EXACTE ou un sous-dossier
    # 1. Est-ce que c'est le dossier racine tout court ?
    is_root = (absolute_resolved_path == CONTAINER_ROOT)
    # 2. Est-ce que c'est un enfant (doit commencer par RACINE + SLASH)
    is_child = absolute_resolved_path.startswith(os.path.join(CONTAINER_ROOT, ""))
    
    if not (is_root or is_child):
        print(f"[SEC] Rejet physique: {absolute_resolved_path} n'est pas dans {CONTAINER_ROOT}")
        return None
        
    # Vérification de la limite logique (Sandboxing dynamique)
    if LLM_SANDBOX_LIMIT:
        is_limit_root = (absolute_resolved_path == LLM_SANDBOX_LIMIT)
        is_limit_child = absolute_resolved_path.startswith(os.path.join(LLM_SANDBOX_LIMIT, ""))
        if not (is_limit_root or is_limit_child):
            print(f"[SEC] Rejet logique: {absolute_resolved_path} hors limite {LLM_SANDBOX_LIMIT}")
            return None
            
    return absolute_resolved_path

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

def _logic_move_file(source_path: str, destination_path: str) -> str:
    safe_src = _validate_path(source_path)
    safe_dst = _validate_path(destination_path)
    if not safe_src or not safe_dst: return "ERREUR: Chemins invalides."
    try:
        shutil.move(safe_src, safe_dst)
        return f"SUCCÈS: Déplacé."
    except Exception as e: return f"ERREUR: {e}"

def _logic_create_dir(path: str) -> str:
    safe = _validate_path(path)
    if not safe: return "ERREUR: Chemin invalide."
    try:
        os.makedirs(safe, exist_ok=True)
        return "SUCCÈS"
    except Exception as e: return f"ERREUR: {e}"

# 3. TOOLS MCP
@mcp.tool()
def set_sandbox_limit(limit_path: str) -> str: return _logic_set_limit(limit_path)
@mcp.tool()
def list_files(path: str = "") -> list[str]: return _logic_list_files(path)
@mcp.tool()
def move_file(source_path: str, destination_path: str) -> str: return _logic_move_file(source_path, destination_path)
@mcp.tool()
def create_directory(path: str) -> str: return _logic_create_dir(path)

# 4. ROUTAGE API
@app.post("/tools/{tool_name}/execute")
async def handle_tool_execution(tool_name: str, request: Request):
    kwargs = await request.json()
    print(f"[SERVER] Appel {tool_name} args={kwargs}")
    try:
        if tool_name == "set_sandbox_limit": return _logic_set_limit(**kwargs)
        elif tool_name == "list_files": return _logic_list_files(path=kwargs.get("path", ""))
        elif tool_name == "move_file": return _logic_move_file(**kwargs)
        elif tool_name == "create_directory": return _logic_create_dir(**kwargs)
        else: return f"ERREUR: Outil inconnu"
    except Exception as e: return f"INTERNAL ERROR: {e}"

# 5. LANCEMENT
if __name__ == "__main__":
    print(f"--- SERVER READY ---")
    print(f"Montage: {CONTAINER_ROOT}")
    uvicorn.run(app, host="0.0.0.0", port=8000)