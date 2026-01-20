import os
import requests
from typing import List
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

# ==========================
# CONFIGURATION
# ==========================
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = "llama3.1"

print(f"--- MODE AGENT AUTONOME ---")
print(f"Server MCP : {MCP_SERVER_URL}")
print(f"Ollama URL : {OLLAMA_HOST}")

# ==========================
# DÉFINITION DES OUTILS (Côté Client)
# ==========================
# Ici, on "wrap" les appels API dans des fonctions que LangChain peut comprendre

@tool
def list_files_tool(path: str = "") -> List[str]:
    """Liste les fichiers présents dans le dossier racine ou un sous-dossier."""
    try:
        resp = requests.post(f"{MCP_SERVER_URL}/tools/list_files/execute", json={"path": path})
        return resp.json()
    except Exception as e:
        return [f"Erreur: {e}"]

@tool
def read_file_tool(filename: str) -> str:
    """Lit le contenu (début) d'un fichier pour comprendre de quoi il parle."""
    try:
        resp = requests.post(f"{MCP_SERVER_URL}/tools/extract_preview/execute", json={"path": filename})
        # On coupe pour ne pas saturer la mémoire du LLM
        return str(resp.json())[:1000]
    except Exception as e:
        return f"Erreur de lecture: {e}"

@tool
def move_file_tool(filename: str, target_folder: str) -> str:
    """
    Déplace un fichier dans un dossier thématique.
    Crée le dossier s'il n'existe pas.
    Exemple: move_file_tool("facture.pdf", "Comptabilite")
    """
    try:
        # 1. Création du dossier
        requests.post(f"{MCP_SERVER_URL}/tools/create_directory/execute", json={"path": target_folder})
        # 2. Déplacement
        full_dest = f"{target_folder}/{filename}"
        requests.post(f"{MCP_SERVER_URL}/tools/move_file/execute", 
                      json={"source_path": filename, "destination_path": full_dest})
        return f"Succès: {filename} déplacé dans {target_folder}"
    except Exception as e:
        return f"Erreur déplacement: {e}"

# Liste des outils donnés à l'IA
tools = [list_files_tool, read_file_tool, move_file_tool]

# ==========================
# CRÉATION DE L'AGENT
# ==========================

# 1. Le Cerveau
llm = ChatOllama(model=MODEL_NAME, base_url=OLLAMA_HOST, temperature=0)

# 2. Le Prompt (Les instructions de comportement)
prompt = ChatPromptTemplate.from_messages([
    ("system", """
    Tu es un Expert en Organisation Autonome.

    TA MISSION : 
    Ranger le dossier racine. Chaque fichier qui s'y trouve doit être déplacé dans un dossier thématique approprié (ex: 'Administratif', 'Tech', 'Rapports', etc.).

    CONTRAINTES DE VÉRITÉ :
    - Utilise `list_files_tool` pour connaitre la réalité du terrain. N'invente aucun fichier.

    IMPÉRATIF D'ACTION (TRÈS IMPORTANT) :
    Il est inutile de me raconter ton plan ("Je vais déplacer ce fichier...").
    JE VEUX DES ACTES.
    Pour considérer qu'un fichier est traité, tu DOIS obligatoirement avoir déclenché l'outil `move_file_tool` avec succès.
    
    Tant que les fichiers sont encore à la racine, ta mission n'est pas finie.
    Agis.
    """),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# 3. Assemblage de l'Agent (LangChain Magic)
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True, # IMPORTANT : Met True pour voir l'IA "penser" et appeler les outils
    handle_parsing_errors=True
)

# ==========================
# LANCEMENT
# ==========================
if __name__ == "__main__":
    print("🚀 L'Agent se réveille...")
    try:
        # On donne juste l'ordre général. L'Agent se débrouille pour le reste.
        agent_executor.invoke({"input": "Organise tous les fichiers qui sont dans le dossier racine."})
    except Exception as e:
        print(f"Erreur Agent : {e}")