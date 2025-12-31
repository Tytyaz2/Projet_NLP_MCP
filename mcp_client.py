import os
import json
import time
import requests
from typing import List
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

# ==========================
# CONFIGURATION
# ==========================
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = "llama3" 

print(f"--- CONFIG CLIENT ---")
print(f"Server MCP : {MCP_SERVER_URL}")
print(f"Ollama URL : {OLLAMA_HOST}")
print(f"Modèle     : {MODEL_NAME}")

llm = ChatOllama(
    model=MODEL_NAME, 
    base_url=OLLAMA_HOST,
    temperature=0, 
    num_ctx=8192
)

# ==========================
# FONCTIONS API
# ==========================
def api_list_files(path: str = "") -> List[str]:
    try:
        resp = requests.post(f"{MCP_SERVER_URL}/tools/list_files/execute", json={"path": path})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"⚠️ Erreur connexion MCP (list_files): {e}")
        return []

def api_extract_preview(path: str) -> str:
    try:
        resp = requests.post(f"{MCP_SERVER_URL}/tools/extract_preview/execute", json={"path": path})
        return str(resp.json())[:1000] 
    except:
        return ""

def api_move_file(source: str, dest_folder: str):
    requests.post(f"{MCP_SERVER_URL}/tools/create_directory/execute", json={"path": dest_folder})
    full_dest = f"{dest_folder}/{source}"
    requests.post(f"{MCP_SERVER_URL}/tools/move_file/execute", 
                  json={"source_path": source, "destination_path": full_dest})

# ==========================
# UTILITAIRE DE NETTOYAGE JSON
# ==========================
def clean_and_parse_json(text: str):
    """Extrait le JSON valide même s'il y a du texte autour."""
    try:
        # On cherche la première accolade ouvrante et la dernière fermante
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx == -1 or end_idx == -1:
            return None

        # On extrait juste ce qu'il y a entre les accolades
        json_str = text[start_idx : end_idx + 1]
        return json.loads(json_str)
    except Exception:
        return None

# ==========================
# LOGIQUE PRINCIPALE
# ==========================
def run_architect():
    # Démarrage du Chronomètre
    start_time = time.perf_counter()
    
    print("⏳ Attente du démarrage des services (5s)...")
    time.sleep(5) 
    
    print(f"\n🚀 Démarrage de l'Architecte IA...")

    # 1. SCAN
    files = api_list_files("")
    files = [f for f in files if "." in f and not f.startswith(".")]

    if not files:
        print("📂 Aucun fichier à traiter.")
        return

    print(f"📂 Fichiers détectés : {len(files)}")
    
    summaries = []
    print("  Lecture des contenus...")
    for f in files:
        content = api_extract_preview(f).replace("\n", " ")[:300]
        summaries.append(f"- Fichier: '{f}' | Contenu: {content}")

    global_context = "\n".join(summaries)

    # 2. RÉFLEXION
    print("\n🧠 L'IA analyse et crée l'architecture...")
    
    sys_prompt = """
    Tu es un Expert en Organisation Documentaire.
    Ta mission : Classer une liste de fichiers en vrac dans des dossiers thématiques.
    
    Règles :
    1. Crée des noms de dossiers courts (ex: 'Factures', 'Medical', 'CVs').
    2. Réponds UNIQUEMENT avec le JSON (pas de phrase d'introduction).
    Format attendu :
    {
        "plan": [
            {"filename": "doc.pdf", "target_folder": "Dossier"}
        ]
    }
    """
    
    user_msg = f"Voici les fichiers :\n{global_context}\n\nPropose le JSON de classement."

    messages = [SystemMessage(content=sys_prompt), HumanMessage(content=user_msg)]
    
    try:
        resp = llm.invoke(messages)
        raw_content = resp.content
        
        # --- NETTOYAGE CORRIGÉ ---
        data = clean_and_parse_json(raw_content)
        
        if not data or "plan" not in data:
            print("❌ Erreur : Impossible d'extraire le JSON de la réponse.")
            print(f"Réponse brute IA : \n{raw_content}")
            return

        plan = data["plan"]
        print(f"\n🏗️ Exécution du plan ({len(plan)} fichiers)...")
        
        for item in plan:
            fname = item['filename']
            folder = item['target_folder']
            # Nettoyage nom dossier
            folder = folder.strip().replace("/", "-").replace(" ", "_")
            
            print(f"  Move : {fname} -> 📁 {folder}")
            api_move_file(fname, folder)
            
        print("\n✅ Terminé ! Organisation complète.")
        
    except Exception as e:
        print(f"❌ Erreur critique : {e}")

    # Arrêt du Chronomètre
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    
    print(f"\n⏱️ Temps d'exécution total : {minutes} min {seconds} s ({duration:.2f} s)")

if __name__ == "__main__":
    run_architect()