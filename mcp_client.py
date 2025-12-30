import time
import json
import requests
import traceback
from typing import Any, List

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
# PROMPTS — DOCUMENT ANALYSIS
# ==========================
DOC_SYSTEM_PROMPT = """
Tu es un classificateur de documents.

À partir du texte fourni, tu dois identifier :
- le TYPE du document
- la DATE si elle est présente
- des MOTS-CLÉS représentatifs

Tu dois répondre STRICTEMENT en JSON valide, sans texte autour.

Champs obligatoires :
{ "type": "...", "date": "...", "keywords": [...] }
"""

DOC_USER_TEMPLATE = """
Nom du fichier : {filename}

Texte extrait du document :
<<<
{preview}
>>>
"""

# ==========================
# PROMPTS — THEME GENERATION
# ==========================
THEME_SYSTEM_PROMPT = """
Tu génères des noms de sous-dossiers pour organiser des documents.

À partir d’un TYPE de document et d’une liste de mots-clés, tu dois proposer
un nom de thème GÉNÉRAL et ABSTRAIT.

Règles importantes :
- Maximum 2 mots.
- Résumer le sujet général, pas le document exact.
- Éviter les noms trop spécifiques ou uniques.
- Le thème doit pouvoir regrouper plusieurs documents.

Réponds STRICTEMENT en JSON :
{ "folder_name": "..." }
"""

THEME_USER_TEMPLATE = """
Type de document :
{doc_type}

Mots-clés :
{keywords}
"""

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    print("\n--- MCP CLIENT STARTED ---")
    start = time.perf_counter()

    try:
        files = list_files("")
        print(f"[DEBUG] Fichiers trouvés: {files}")

        for filename in files:
            preview = extract_preview(filename)

            # ---- Analyse document ----
            messages = [
                SystemMessage(content=DOC_SYSTEM_PROMPT),
                HumanMessage(
                    content=DOC_USER_TEMPLATE.format(
                        filename=filename,
                        preview=preview
                    )
                )
            ]

            response = llm.invoke(messages)
            data = json.loads(response.content)

            doc_type = data.get("type", "autre")
            keywords = data.get("keywords", [])

            # ---- Génération thème ----
            messages = [
                SystemMessage(content=THEME_SYSTEM_PROMPT),
                HumanMessage(
                    content=THEME_USER_TEMPLATE.format(
                        doc_type=doc_type,
                        keywords=", ".join(keywords)
                    )
                )
            ]

            response = llm.invoke(messages)
            theme_data = json.loads(response.content)
            theme = theme_data.get("folder_name", "divers")

            target_dir = f"{doc_type}/{theme}"
            create_directory(target_dir)
            move_file(filename, f"{target_dir}/{filename}")

        end = time.perf_counter()
        print("\n--- MCP TASK FINISHED ---")
        print(f"⏱️ Execution time: {end - start:.2f} seconds\n")

    except Exception:
        print("\n❌ ERREUR DÉTAILLÉE :")
        traceback.print_exc()
