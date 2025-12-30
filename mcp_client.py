import time
import json
import requests
import traceback
from typing import Any, List

from langchain_ollama import ChatOllama
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage

# ----------------------------
# MCP SERVER CONFIG
# ----------------------------
MCP_SERVER_URL = "http://localhost:8000"

# ----------------------------
# LLM
# ----------------------------
llm = ChatOllama(model="llama3.2:1b", temperature=0)

# ----------------------------
# MCP TOOL EXECUTION WRAPPER
# ----------------------------
def execute_mcp_tool(tool_name: str, **kwargs: Any) -> str:
    """Exécute l'appel API vers le serveur MCP Docker"""
    print(f"\n[DEBUG] 📞 Tentative d'appel de l'outil : {tool_name} avec {kwargs}")
    url = f"{MCP_SERVER_URL}/tools/{tool_name}/execute"
    try:
        response = requests.post(url, json=kwargs)
        response.raise_for_status()
        return response.text
    except requests.exceptions.ConnectionError:
        return f"ERROR: Impossible de se connecter au serveur MCP sur {MCP_SERVER_URL}. Vérifiez que le Docker tourne."
    except Exception as e:
        return f"ERROR executing {tool_name}: {str(e)}"

# ----------------------------
# TOOL DEFINITIONS
# ----------------------------
def set_sandbox_limit(limit_path: str) -> str:
    return execute_mcp_tool("set_sandbox_limit", limit_path=limit_path)

def list_files(path: str = "") -> List[str]:
    result = execute_mcp_tool("list_files", path=path)
    try:
        return json.loads(result) if result.startswith("[") else result.splitlines()
    except Exception:
        return result.splitlines()

def move_file(source_path: str, destination_path: str) -> str:
    return execute_mcp_tool("move_file", source_path=source_path, destination_path=destination_path)

def create_directory(path: str) -> str:
    return execute_mcp_tool("create_directory", path=path)

def extract_preview(path: str) -> str:
    return execute_mcp_tool("extract_preview", path=path)

mcp_tools = [
    StructuredTool.from_function(
        func=set_sandbox_limit,
        name="set_sandbox_limit",
        description="Sets a safety boundary. Call this FIRST if the user mentions a specific folder (e.g. 'Photos'). The path is relative to the root."
    ),
    StructuredTool.from_function(
        func=extract_preview,
        name="extract_preview",
        description="Returns a textual preview of a file (PDF, DOCX, TXT)."
    ),
    StructuredTool.from_function(
        func=move_file,
        name="move_file",
        description="Moves a file. Args: source_path, destination_path. Both paths relative to root."
    ),
    StructuredTool.from_function(
        func=create_directory,
        name="create_directory",
        description="Creates a NEW directory. Arg: 'path'."
    ),
]

# ----------------------------
# SYSTEM PROMPT
# ----------------------------
SYSTEM_PROMPT = """
You are an intelligent MCP-based document organizer.

You have access ONLY to the provided MCP tools.
You MUST use the tools to act.
You MUST NOT generate scripts, code, or invent paths.

ROOT DIRECTORY RULE:
- The root directory is an empty string: "".

WORKFLOW RULES:
1. Process ALL files.
2. For each file:
   - Infer the document TYPE among:
     ["cv", "ordonnance", "article", "facture", "contrat", "email",
      "lettre", "relevé bancaire", "document juridique", "cours", "autre"]
   - Infer a short THEMATIC folder name (1–2 words max).
3. Organize files using:
   /<type>/<theme>/<filename>
4. Create directories only if necessary.
5. Use ONLY MCP tools to act.
"""

USER_PROMPT_TEMPLATE = """
Filename: {filename}

Document preview:
<<<
{preview}
>>>

Return ONLY valid JSON with fields:
  {{ "type": "...", "keywords": [...] }}
"""

# ----------------------------
# MAIN EXECUTION
# ----------------------------
if __name__ == "__main__":
    print("\n--- MCP CLIENT STARTED ---")
    start_time = time.perf_counter()

    try:
        files = list_files()
        print(f"[DEBUG] Fichiers trouvés: {files}")

        for filename in files:
            if filename.startswith("("):
                continue

            preview = extract_preview(filename)

            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=USER_PROMPT_TEMPLATE.format(
                        filename=filename,
                        preview=preview
                    )
                )
            ]

            response = llm.invoke(messages)
            try:
                data = json.loads(response.content)
            except Exception:
                print(f"❌ ERREUR : Le LLM n'a pas renvoyé de JSON valide pour {filename}. Contenu reçu : {response.content}")
                continue

            doc_type = data.get("type", "autre")
            keywords = data.get("keywords", [])
            theme = keywords[0] if keywords else "sans-theme"

            target_dir = f"{doc_type}/{theme}"
            create_directory(target_dir)
            move_file(filename, f"{target_dir}/{filename}")

        end_time = time.perf_counter()
        print("\n--- MCP TASK FINISHED ---")
        print(f"⏱️ Execution time: {end_time - start_time:.2f} seconds\n")

    except Exception:
        print("\n❌ ERREUR DÉTAILLÉE :")
        traceback.print_exc()
