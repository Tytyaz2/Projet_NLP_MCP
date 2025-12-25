from langchain_ollama import ChatOllama
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

import requests
import traceback
from typing import Any


# ----------------------------
# MCP SERVER CONFIG
# ----------------------------
MCP_SERVER_URL = "http://localhost:8000"


# ----------------------------
# LLM (Correct modern import)
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
    """Sets the safety boundary. MUST be called first for sub-folder tasks."""
    return execute_mcp_tool("set_sandbox_limit", limit_path=limit_path)

def list_files(path: str = "") -> str:
    """Lists files in the current path or specified path."""
    return execute_mcp_tool("list_files", path=path)

def move_file(source_path: str, destination_path: str) -> str:
    """Moves a file from source to destination."""
    return execute_mcp_tool("move_file", source_path=source_path, destination_path=destination_path)

def create_directory(path: str) -> str:
    """Creates a folder at the specified path."""
    return execute_mcp_tool("create_directory", path=path)

mcp_tools = [
    StructuredTool.from_function(
        func=set_sandbox_limit,
        name="set_sandbox_limit",
        description="Sets a safety boundary. Call this FIRST if the user mentions a specific folder (e.g. 'Photos'). The path is relative to the root."
    ),
    StructuredTool.from_function(
        func=list_files,
        name="list_files",
        # INSTRUCTION CRITIQUE ICI :
        description="Lists files in a directory. IMPORTANT: To list the ROOT directory, you MUST use an empty string '' as the path. DO NOT use '/' or '/home'. If the user does not specify a folder, assume path=''."
    ),
    StructuredTool.from_function(
        func=move_file,
        name="move_file",
        description="Moves a file. Args: source_path, destination_path. Both paths are relative to the current root. Example: source_path='file.txt', destination_path='Folder/file.txt'."
    ),
    StructuredTool.from_function(
        func=create_directory,
        name="create_directory",
        description="Creates a NEW directory. REQUIRED ARGUMENT: 'path' (the string name of the folder to create). Example: if user says 'create test', path='test'."
    ),
]

# ----------------------------
# PROMPT WITH MESSAGE HISTORY
# ----------------------------
SYSTEM_PROMPT = """
You are a highly capable File Management Agent (MCP) specialized in organizing files on a user's system.
Your goal is to fulfill user requests efficiently by choosing the right tool at the right time.

CRITICAL SECURITY RULE:
1.  **DYNAMIC SANDBOXING:** If the user asks you to operate *within a specific subdirectory* (e.g., "Sort the 'Photos/Vacances' folder"), you MUST first call the 'set_sandbox_limit' tool with that path (e.g., "Photos/Vacances") before performing any file operations (list_files, move_file, etc.). This ensures operations are restricted to that safe zone.
2.  If the user asks for a general operation on the entire mounted volume, DO NOT call 'set_sandbox_limit'.
3.  Always check the contents of a directory using 'list_files' before attempting to move or delete files.

CRITICAL RULES FOR PATHS:
1. THE ROOT DIRECTORY IS AN EMPTY STRING: "".
2. NEVER assume Linux paths like '/home/user', '/etc', or '/var'. They do NOT exist here.
3. If the user asks something without specifying a folder, you MUST call the correct tool with path="".

LOGIC RULES:
1. If the user targets a specific subfolder (e.g., "Sort the 'Invoices' folder"), call 'set_sandbox_limit' with that folder name FIRST.
2. Always list files using 'list_files' to see what exists before moving anything.

Response format: Just perform the action and report the result concisely.
"""

agent_executor = create_agent(
    model=llm,
    tools=mcp_tools,
    system_prompt=SYSTEM_PROMPT
)

if __name__ == "__main__":
    print("\n--- Agent Démarré ---")
    
    user_input = "I want you to move '2020_Retinal Image Segmentation with a Structure-Texture Demixing Network_Zhang.pdf' to the '2020_Artcile' directory"
    print(f"\nUser: {user_input}")
    
    try:
        # Appel de l'agent
        events = agent_executor.invoke({"messages": [HumanMessage(content=user_input)]})
        
        # Récupération de la réponse
        last_message = events["messages"][-1]
        print(f"\n🤖 Agent: {last_message.content}")
        
    except Exception:
        # Affiche l'erreur complète pour le débogage
        print("\n❌ Erreur d'exécution détaillée :")
        traceback.print_exc()