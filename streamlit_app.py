"""
Application Streamlit pour tester le système de classification de fichiers.
Utilise Gemini (Google AI) avec function calling pour les outils MCP.
Permet de basculer entre le mode Baseline (sans outils) et le mode MCP (avec outils).

GRATUIT : Gemini a un tier gratuit (15 req/min, 1500 req/jour)
"""

import streamlit as st
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Charger les variables d'environnement (.env à la racine du projet)
load_dotenv()

# Configuration Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Import des outils MCP (pour le mode MCP)
from src.classifier import analyze_document, group_documents, apply_plan


# ─────────────────────────────────────────────────────────────────────────────
# Configuration de la page
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="File Classifier - NLP MCP",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# Styles CSS personnalisés
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .tool-call {
        background-color: #1e3a5f;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 3px solid #4CAF50;
    }
    .tool-result {
        background-color: #2d2d2d;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        font-family: monospace;
        font-size: 0.85rem;
        max-height: 300px;
        overflow-y: auto;
    }
    .mcp-badge {
        background-color: #4CAF50;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .baseline-badge {
        background-color: #ff9800;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# État de session
# ─────────────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mcp_enabled" not in st.session_state:
    st.session_state.mcp_enabled = False
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = 0
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None


# ─────────────────────────────────────────────────────────────────────────────
# Définition des outils MCP pour Gemini
# ─────────────────────────────────────────────────────────────────────────────

def list_files_to_sort(folder: str, extensions: list = None) -> dict:
    """Liste tous les fichiers à trier dans un dossier."""
    if not folder or not isinstance(folder, str) or not folder.strip():
        return {"error": "Le chemin du dossier doit être une chaîne non vide"}

    if extensions is not None:
        if not isinstance(extensions, list):
            return {"error": "extensions doit être une liste de chaînes (ex: [\".pdf\", \".docx\"])"}
        extensions = [e.strip() if e.startswith(".") else f".{e.strip()}" for e in extensions if isinstance(e, str)]
    else:
        extensions = [".pdf", ".docx", ".txt", ".doc", ".odt"]

    folder_path = Path(folder.strip())
    if not folder_path.exists():
        return {"error": f"Le dossier {folder} n'existe pas"}
    if not folder_path.is_dir():
        return {"error": f"{folder} n'est pas un dossier"}

    files = []
    for ext in extensions:
        files.extend(folder_path.rglob(f"*{ext}"))

    file_list = [str(f.absolute()) for f in files if f.is_file()]
    return {"files": file_list, "count": len(file_list)}


def analyze_file(path: str) -> dict:
    """Analyse un fichier et retourne ses métadonnées."""
    if not path or not isinstance(path, str) or not path.strip():
        return {"error": "Le chemin doit être une chaîne non vide"}

    supported = [".pdf", ".docx", ".txt", ".doc", ".odt"]
    try:
        p = Path(path.strip())
        if not p.exists():
            return {"error": f"Le fichier {path} n'existe pas"}
        if not p.is_file():
            return {"error": f"{path} n'est pas un fichier"}
        if p.suffix.lower() not in supported:
            return {"error": f"Extension non supportée : {p.suffix}. Extensions supportées : {', '.join(supported)}"}
        info = analyze_document(p)
        return info
    except Exception as e:
        return {"error": str(e)}


def sort_folder(folder: str, dry_run: bool = False) -> dict:
    """Trie automatiquement tous les documents d'un dossier."""
    if not folder or not isinstance(folder, str) or not folder.strip():
        return {"error": "Le chemin du dossier doit être une chaîne non vide"}
    if not isinstance(dry_run, bool):
        return {"error": "dry_run doit être un booléen (true ou false)"}

    folder_path = Path(folder.strip())

    if not folder_path.exists():
        return {"error": f"Le dossier {folder} n'existe pas"}
    if not folder_path.is_dir():
        return {"error": f"{folder} n'est pas un dossier"}

    extensions = [".pdf", ".docx", ".txt", ".doc", ".odt"]

    result = {
        "folder": folder,
        "dry_run": dry_run,
        "files_found": 0,
        "files_analyzed": 0,
        "groups": [],
        "moved": [],
        "errors": []
    }

    # Lister les fichiers
    files = []
    for ext in extensions:
        files.extend(folder_path.rglob(f"*{ext}"))
    files = [f for f in files if f.is_file()]
    result["files_found"] = len(files)

    if not files:
        return {"message": "Aucun fichier à trier", **result}

    # Analyser chaque fichier
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

    # Regrouper les fichiers
    groups = group_documents(files_info)
    result["groups"] = groups.get("groups", [])

    if not result["groups"]:
        return {"message": "Aucun groupe créé", **result}

    # Appliquer le plan (sauf si dry_run)
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


# Mapping des fonctions pour Gemini
TOOL_FUNCTIONS = {
    "list_files_to_sort": list_files_to_sort,
    "analyze_file": analyze_file,
    "sort_folder": sort_folder,
}

# Liste des fonctions Python à passer directement à Gemini
# Gemini introspèque automatiquement les fonctions Python
MCP_TOOLS_FUNCTIONS = [list_files_to_sort, analyze_file, sort_folder]

# Descriptions pour la sidebar
MCP_TOOLS_DESCRIPTIONS = [
    {"name": "list_files_to_sort", "description": "Liste tous les fichiers à trier dans un dossier (.pdf, .docx, .txt, .doc, .odt)."},
    {"name": "analyze_file", "description": "Analyse un fichier et retourne son type, sa date et ses mots-clés."},
    {"name": "sort_folder", "description": "Trie automatiquement un dossier complet (analyse + regroupement + déplacement)."},
]


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Gemini
# ─────────────────────────────────────────────────────────────────────────────
def init_gemini(mcp_enabled: bool):
    """Initialise le modèle Gemini avec ou sans outils."""
    if not GEMINI_API_KEY:
        return None

    genai.configure(api_key=GEMINI_API_KEY)

    if mcp_enabled:
        # Mode MCP : avec les outils de classification
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            tools=MCP_TOOLS_FUNCTIONS,
            system_instruction="""Tu es un assistant IA spécialisé dans la classification et l'organisation de fichiers.

Tu as accès à des outils pour:
- Lister les fichiers d'un dossier (list_files_to_sort)
- Analyser un fichier pour obtenir son type et ses mots-clés (analyze_file)
- Trier automatiquement un dossier complet (sort_folder)

Quand l'utilisateur te demande d'analyser ou trier des fichiers, utilise ces outils.
Explique clairement ce que tu fais et les résultats obtenus.
Sois précis et professionnel dans tes réponses."""
        )
    else:
        # Mode Baseline : chat simple sans outils
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction="""Tu es un assistant IA généraliste, similaire à ChatGPT.
Tu réponds aux questions de l'utilisateur de manière utile et précise.
Tu n'as PAS accès à des outils pour analyser ou trier des fichiers.
Si l'utilisateur te demande de trier des fichiers, explique-lui qu'il doit activer le mode MCP dans la barre latérale pour avoir accès à ces fonctionnalités."""
        )

    return model


def process_tool_calls(response, chat_session):
    """Traite les appels d'outils de Gemini et retourne les résultats."""
    tool_calls_info = []

    # Vérifier s'il y a des appels de fonction
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                fc = part.function_call
                tool_name = fc.name
                tool_args = dict(fc.args) if fc.args else {}

                # Exécuter l'outil
                if tool_name in TOOL_FUNCTIONS:
                    result = TOOL_FUNCTIONS[tool_name](**tool_args)
                else:
                    result = {"error": f"Outil inconnu: {tool_name}"}

                tool_calls_info.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result
                })

                # Envoyer le résultat à Gemini
                response = chat_session.send_message(
                    genai.protos.Content(
                        parts=[genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={"result": result}
                            )
                        )]
                    )
                )

                # Vérifier s'il y a d'autres appels d'outils
                more_calls, more_info = process_tool_calls(response, chat_session)
                if more_info:
                    tool_calls_info.extend(more_info)
                    response = more_calls

    return response, tool_calls_info


def get_response_text(response):
    """Extrait le texte de la réponse Gemini."""
    text_parts = []
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if hasattr(part, 'text') and part.text:
                text_parts.append(part.text)
    return "\n".join(text_parts)


# ─────────────────────────────────────────────────────────────────────────────
# Interface utilisateur - Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")

    # Configuration API Key
    st.markdown("### 🔑 Clé API Gemini (GRATUIT)")
    api_key_input = st.text_input(
        "Clé API",
        value=GEMINI_API_KEY,
        type="password",
        help="Obtenez votre clé GRATUITE sur https://aistudio.google.com/apikey"
    )

    if api_key_input != GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = api_key_input
        GEMINI_API_KEY = api_key_input
        st.session_state.chat_session = None  # Reset session

    if not GEMINI_API_KEY:
        st.warning("⚠️ Entrez votre clé API Gemini")
        st.markdown("[🆓 Obtenir une clé GRATUITE](https://aistudio.google.com/apikey)")

    st.markdown("---")

    # Toggle MCP
    st.markdown("### Mode de fonctionnement")

    new_mcp_state = st.toggle(
        "Activer MCP (outils)",
        value=st.session_state.mcp_enabled,
        help="Activez pour donner accès aux outils de classification de fichiers"
    )

    # Détection du changement de mode
    if new_mcp_state != st.session_state.mcp_enabled:
        st.session_state.mcp_enabled = new_mcp_state
        st.session_state.messages = []  # Reset conversation
        st.session_state.chat_session = None  # Reset Gemini session
        st.session_state.conversation_id += 1
        st.rerun()

    # Affichage du mode actuel
    if st.session_state.mcp_enabled:
        st.markdown('<span class="mcp-badge">MCP ACTIVÉ</span>', unsafe_allow_html=True)
        st.info("L'IA a accès aux outils de classification et peut analyser/trier vos fichiers.")
    else:
        st.markdown('<span class="baseline-badge">BASELINE</span>', unsafe_allow_html=True)
        st.warning("Mode baseline - Chat simple sans outils MCP.")

    st.markdown("---")

    # Info modèle
    st.markdown("### 🤖 Modèle")
    st.text(f"Modèle: {GEMINI_MODEL}")
    st.caption("💚 Gratuit : 15 req/min")

    # Bouton nouvelle conversation
    if st.button("🔄 Nouvelle conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.session_state.conversation_id += 1
        st.rerun()

    st.markdown("---")

    # Outils disponibles (si MCP activé)
    if st.session_state.mcp_enabled:
        st.markdown("### 🛠️ Outils disponibles")
        for tool in MCP_TOOLS_DESCRIPTIONS:
            with st.expander(f"📌 {tool['name']}"):
                st.write(tool["description"])


# ─────────────────────────────────────────────────────────────────────────────
# Interface principale - Chat
# ─────────────────────────────────────────────────────────────────────────────
st.title("💬 File Classifier Chat")

if st.session_state.mcp_enabled:
    st.caption("Mode MCP activé - L'IA peut analyser et trier vos fichiers")
else:
    st.caption("Mode Baseline - Chat simple sans outils")

# Vérifier la clé API
if not GEMINI_API_KEY:
    st.error("⚠️ Veuillez entrer votre clé API Gemini dans la barre latérale pour commencer.")
    st.markdown("👉 [Obtenir une clé API GRATUITE](https://aistudio.google.com/apikey)")
    st.stop()

# Afficher l'historique des messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Afficher les appels d'outils s'il y en a
        if "tool_calls" in message and message["tool_calls"]:
            for tc in message["tool_calls"]:
                st.markdown(f'<div class="tool-call">🔧 Outil: <b>{tc["tool"]}</b></div>',
                           unsafe_allow_html=True)
                result_str = json.dumps(tc["result"], indent=2, ensure_ascii=False)
                display_result = result_str[:1000] + "..." if len(result_str) > 1000 else result_str
                st.markdown(f'<div class="tool-result"><pre>{display_result}</pre></div>',
                           unsafe_allow_html=True)

# Input utilisateur
if prompt := st.chat_input("Posez votre question..."):
    # Ajouter le message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Initialiser la session Gemini si nécessaire
    if st.session_state.chat_session is None:
        model = init_gemini(st.session_state.mcp_enabled)
        if model:
            st.session_state.chat_session = model.start_chat()

    # Obtenir la réponse
    with st.chat_message("assistant"):
        if st.session_state.chat_session is None:
            st.error("Erreur: Impossible d'initialiser Gemini. Vérifiez votre clé API.")
            st.stop()

        with st.spinner("Réflexion en cours..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)

                # Traiter les appels d'outils si MCP activé
                tool_calls_info = []
                if st.session_state.mcp_enabled:
                    # Afficher les appels d'outils en temps réel
                    response, tool_calls_info = process_tool_calls(
                        response, st.session_state.chat_session
                    )

                    # Afficher les outils appelés
                    for tc in tool_calls_info:
                        st.markdown(f'<div class="tool-call">🔧 Outil: <b>{tc["tool"]}</b></div>',
                                   unsafe_allow_html=True)
                        result_str = json.dumps(tc["result"], indent=2, ensure_ascii=False)
                        display_result = result_str[:1000] + "..." if len(result_str) > 1000 else result_str
                        st.markdown(f'<div class="tool-result"><pre>{display_result}</pre></div>',
                                   unsafe_allow_html=True)

                # Extraire et afficher le texte de la réponse
                response_text = get_response_text(response)
                st.markdown(response_text)

                # Sauvegarder le message assistant
                assistant_msg = {"role": "assistant", "content": response_text}
                if tool_calls_info:
                    assistant_msg["tool_calls"] = tool_calls_info
                st.session_state.messages.append(assistant_msg)

            except Exception as e:
                error_msg = f"Erreur: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})


# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "NLP MCP File Classifier | "
    f"Mode: {'MCP' if st.session_state.mcp_enabled else 'Baseline'} | "
    f"Modèle: {GEMINI_MODEL} | "
    "💚 Gratuit"
    "</div>",
    unsafe_allow_html=True
)
