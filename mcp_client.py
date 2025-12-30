import time
import json
import requests
import traceback
from typing import Any, List, Dict
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

# ==========================
# MCP SERVER CONFIG
# ==========================
MCP_SERVER_URL = "http://localhost:8000"

# ==========================
# LLM
# ==========================
llm = ChatOllama(model="llama3.2:1b", temperature=0)

# ==========================
# MCP TOOL CALLER
# ==========================
def call_mcp(tool: str, **kwargs) -> Any:
    url = f"{MCP_SERVER_URL}/tools/{tool}/execute"
    r = requests.post(url, json=kwargs)
    r.raise_for_status()
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text

# ==========================
# MCP TOOLS
# ==========================
def list_files(path: str = "") -> List[str]:
    return call_mcp("list_files", path=path)

def extract_preview(path: str) -> str:
    return call_mcp("extract_preview", path=path)

def create_directory(path: str) -> str:
    return call_mcp("create_directory", path=path)

def move_file(source_path: str, destination_path: str) -> str:
    return call_mcp("move_file", source_path=source_path, destination_path=destination_path)

# ==========================
# PROMPTS
# ==========================
DOC_SYSTEM_PROMPT = """
Tu es un classificateur de documents.

À partir du texte fourni, tu dois identifier :
- le TYPE du document
- la DATE si elle est présente
- des MOTS-CLÉS représentatifs

Réponds STRICTEMENT en JSON valide :
{ "type": "...", "date": "...", "keywords": [...] }
"""

DOC_USER_TEMPLATE = """
Nom du fichier : {filename}

Texte extrait du document :
<<<
{preview}
>>>
"""

THEME_SYSTEM_PROMPT = """
Tu génères des noms de sous-dossiers courts et cohérents pour organiser des documents.

Règles :
- Maximum 2 mots
- Nom abstrait, général, pouvant regrouper plusieurs fichiers
- Pas de dossiers vagues ou génériques comme 'PDF', 'document', 'Document'
- Réponds STRICTEMENT en JSON : { "folder_name": "..." }
"""

THEME_USER_TEMPLATE = """
Type de document :
{doc_type}

Mots-clés :
{keywords}
"""

# ==========================
# HELPER FUNCTIONS
# ==========================
def safe_json_loads(s: str) -> Dict:
    """Parse JSON robustly; fallback to empty dict"""
    try:
        s_clean = s.strip().strip("```")
        return json.loads(s_clean)
    except Exception:
        return {}

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    print("\n--- MCP CLIENT STARTED ---")
    start_time = time.perf_counter()

    try:
        # ---- Step 1: Collect all files ----
        files = list_files("")
        print(f"[DEBUG] Fichiers trouvés: {files}")

        all_docs = []

        for filename in files:
            preview = extract_preview(filename)

            # ---- Document Analysis ----
            messages = [
                SystemMessage(content=DOC_SYSTEM_PROMPT),
                HumanMessage(content=DOC_USER_TEMPLATE.format(filename=filename, preview=preview))
            ]
            response = llm.invoke(messages)
            data = safe_json_loads(response.content)

            doc_type = data.get("type", "autre")
            keywords = data.get("keywords", [])
            date = data.get("date", "unknown")

            all_docs.append({
                "filename": filename,
                "type": doc_type,
                "keywords": keywords,
                "date": date
            })

        # ---- Step 2: Group by type and generate themes ----
        type_to_keywords = {}
        for doc in all_docs:
            type_to_keywords.setdefault(doc["type"], []).extend(doc["keywords"])

        type_to_themes = {}
        for doc_type, kws in type_to_keywords.items():
            messages = [
                SystemMessage(content=THEME_SYSTEM_PROMPT),
                HumanMessage(content=THEME_USER_TEMPLATE.format(doc_type=doc_type, keywords=", ".join(kws)))
            ]
            response = llm.invoke(messages)
            theme_data = safe_json_loads(response.content)
            folder_name = theme_data.get("folder_name", "divers")
            type_to_themes[doc_type] = folder_name

        # ---- Step 3 & 4: Create folders and move files ----
        for doc in all_docs:
            doc_type = doc["type"]
            theme = type_to_themes.get(doc_type, "divers")
            target_dir = f"{doc_type}/{theme}"
            create_directory(target_dir)
            move_file(doc["filename"], f"{target_dir}/{doc['filename']}")

        end_time = time.perf_counter()
        print("\n--- MCP TASK FINISHED ---")
        print(f"⏱️ Execution time: {end_time - start_time:.2f} seconds\n")

    except Exception:
        print("\n❌ ERREUR DÉTAILLÉE :")
        traceback.print_exc()
