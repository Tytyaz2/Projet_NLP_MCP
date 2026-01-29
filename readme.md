# MCP - Tri Automatique de Documents

Système de tri automatique de documents utilisant le **Tool Calling** et le **Model Context Protocol (MCP)** pour organiser vos fichiers intelligemment.

**Deux modes d'utilisation :**

| Mode | LLM | Protocole | Prérequis |
|------|-----|-----------|-----------|
| **Streamlit + Gemini** | Gemini (gratuit) | Function Calling | Python + Ollama |
| **Claude Desktop + MCP** | Claude (Anthropic) | MCP standard | Docker + Ollama + Claude Desktop |

---

## Option 1 : Streamlit + Gemini (gratuit)

Interface web avec Gemini (Google AI) et son function calling natif. Toggle baseline/MCP pour comparer.

### Prérequis

- **Python 3.10+** installé
- **Ollama** installé et en cours d'exécution
- **Clé API Gemini** (gratuite) : [Obtenir sur Google AI Studio](https://aistudio.google.com/apikey)

### Installation

```bash
# 1. Cloner le projet
git clone https://github.com/Tytyaz2/Projet_NLP_MCP.git
cd Projet_NLP_MCP

# 2. Créer un environnement virtuel
python -m venv venv

# Windows PowerShell :
.\venv\Scripts\Activate.ps1
# Windows CMD :
.\venv\Scripts\activate.bat
# Linux/Mac :
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements_streamlit.txt

# 4. Configurer l'environnement
cp .env.example .env
# Éditer .env et ajouter votre GEMINI_API_KEY
```

### Lancement

```bash
# Terminal 1 : Lancer Ollama
ollama serve

# Terminal 2 : Lancer l'application
.\venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

L'application s'ouvre sur `http://localhost:8501`

### Utilisation

1. **Coller votre clé API Gemini** dans la barre latérale
2. **Mode Baseline** (par défaut) : Posez des questions, l'IA répond sans outils (comme ChatGPT)
3. **Activer MCP** : Basculez le toggle pour donner accès aux outils de classification
4. **Trier des fichiers** (mode MCP activé) : Utilisez des **chemins Windows absolus** :
   - *"Analyse le fichier C:/Users/Utilisateur/Documents/rapport.pdf"*
   - *"Trie le dossier C:/Users/Utilisateur/Downloads"*
   - *"Trie C:/Users/Utilisateur/Desktop en mode dry-run"* (simulation sans déplacer)

> **Important** : En mode Streamlit, utilisez les **chemins Windows réels** (ex: `C:/Users/VotreNom/Documents`).

---

## Option 2 : Claude Desktop + MCP (protocole standard)

Architecture MCP-compliant avec un serveur FastMCP dans Docker, connecté à Claude Desktop via le protocole stdio.

### Prérequis

- **Docker Desktop** installé et lancé
- **Ollama** installé et en cours d'exécution
- **Claude Desktop** installé avec un compte connecté

### Installation

```bash
# 1. Construire l'image Docker
cd docker
docker-compose build

# 2. Installer la config Claude Desktop
cd ..
python install_claude_desktop.py

# 3. Redémarrer Claude Desktop (fermer complètement et relancer)
```

### Utilisation

Dans Claude Desktop, dites :

> **"Trie le dossier /home/user/Downloads"**

> **"Trie /home/user/Documents en mode dry-run"**

> **Rappel** : En mode Docker, utilisez les chemins `/home/user/...` (pas les chemins Windows).

### Correspondance des chemins (Docker)

| Votre PC (Windows) | Ce que vous dites à Claude |
|--------------------|----------------------------|
| `C:\Users\VotreNom\Downloads` | `/home/user/Downloads` |
| `C:\Users\VotreNom\Documents` | `/home/user/Documents` |
| `C:\Users\VotreNom\Desktop` | `/home/user/Desktop` |

---

## Architecture

### Mode Streamlit (Tool Calling)

```
┌────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Navigateur │ --> │   Streamlit     │ --> │ Gemini (Google)  │
│ :8501      │     │  streamlit_app  │     │ Function Calling │
└────────────┘     └───────┬─────────┘     └─────────────────┘
                           │
                    (mode MCP activé)
                           │
                   ┌───────▼─────────┐
                   │  Ollama (local) │
                   │ localhost:11434 │
                   └─────────────────┘
```

- **Gemini** : LLM cloud avec function calling natif (gratuit, 15 req/min)
- **Ollama** : Analyse le contenu des fichiers localement
- **Streamlit** : Interface web interactive

### Mode Claude Desktop (MCP standard)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Claude Desktop  │ --> │  Docker (MCP)   │ --> │ Ollama (local)  │
│  (client MCP)   │     │  FastMCP server │     │ localhost:11434 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
   protocole MCP           protocole stdio
   (JSON-RPC 2.0)         (stdin/stdout)
```

- **Claude Desktop** : Client MCP natif (envoie les requêtes JSON-RPC)
- **FastMCP** : Serveur MCP Python qui expose les outils via le protocole standard
- **Docker** : Isolation et portabilité du serveur MCP
- **Ollama** : Analyse locale des fichiers

---

## Modes de fonctionnement

| Mode | Outils | Description | Interface |
|------|--------|-------------|-----------|
| **Baseline** | Désactivés | Chat simple sans accès aux fichiers. Pas d'analyse ni de tri. | Streamlit (toggle off) |
| **Tool Calling** | Activés | Le LLM peut appeler les outils pour analyser et trier vos fichiers. | Streamlit (toggle on) + Claude Desktop |

- **Streamlit** : Basculez le toggle dans la sidebar. Le changement de mode **démarre automatiquement une nouvelle conversation**.
- **Claude Desktop** : Les outils sont toujours disponibles via le serveur MCP.

---

## Outils disponibles

| Outil | Description | Disponible dans |
|-------|-------------|-----------------|
| `list_files_to_sort` | Liste les fichiers d'un dossier | Streamlit + Claude Desktop |
| `analyze_file` | Analyse un fichier (type, date, mots-clés) | Streamlit + Claude Desktop |
| `sort_folder` | Trie automatiquement un dossier complet | Streamlit + Claude Desktop |
| `group_files` | Regroupe les documents par type et thème | Claude Desktop uniquement |
| `apply_file_plan` | Applique un plan d'organisation | Claude Desktop uniquement |

---

## Pipeline de traitement

```
[Fichiers bruts]
    → [Extraction contenu (PDF, DOCX, TXT)]
    → [Prétraitement NLP (nettoyage, tokenisation, stemming)]
    → [Analyse LLM (Ollama)]
    → [Classification par type et thème]
    → [Organisation automatique en dossiers]
```

### Exemple de résultat

**Avant :**
```
Downloads/
├── article_retine.pdf
├── article_ia.pdf
├── CV_Martin.pdf
├── facture_edf.pdf
└── rapport_stage.pdf
```

**Après :**
```
Downloads/
├── article/
│   ├── medical-retine/
│   │   └── article_retine.pdf
│   └── intelligence-artificielle/
│       └── article_ia.pdf
├── cv/
│   └── CV_Martin.pdf
├── facture/
│   └── facture_edf.pdf
└── rapport/
    └── rapport_stage.pdf
```

---

## Configuration

### Variables d'environnement (.env)

```bash
cp .env.example .env
```

| Variable | Description | Valeur par défaut | Utilisé par |
|----------|-------------|-------------------|-------------|
| `GEMINI_API_KEY` | Clé API Gemini | - | Streamlit |
| `GEMINI_MODEL` | Modèle Gemini | `gemini-2.0-flash` | Streamlit |
| `OLLAMA_HOST` | URL d'Ollama | `http://localhost:11434` | Les deux |
| `OLLAMA_MODEL_NAME` | Modèle Ollama | `gpt-oss:20b-cloud` | Les deux |

### Obtenir la clé API Gemini (gratuit)

1. Aller sur [Google AI Studio](https://aistudio.google.com/apikey)
2. Se connecter avec un compte Google
3. Cliquer sur **"Create API Key"**
4. Copier la clé (format : `AIzaSy...xxxxx`)
5. La coller dans `.env` ou directement dans la sidebar de l'app

**Limites du tier gratuit :**

| Limite | Valeur |
|--------|--------|
| Requêtes/minute | 15 |
| Requêtes/jour | 1500 |

### Configurer Ollama

```bash
# Installer un modèle (au choix)
ollama pull llama3:latest        # Recommandé pour débuter
ollama pull mistral:latest       # Alternative légère
```

---

## Structure du projet

```
Projet_NLP_MCP/
├── streamlit_app.py                # Interface web Streamlit (Gemini + function calling)
├── .env.example                    # Configuration (Gemini + Ollama)
├── requirements_streamlit.txt      # Dépendances Streamlit
├── requirements.txt                # Dépendances MCP (Docker)
├── src/
│   ├── classifier/
│   │   ├── analyzer.py             # Extraction + analyse LLM (Ollama)
│   │   ├── preprocessor.py         # Pipeline NLP (NLTK)
│   │   └── organizer.py            # Regroupement + déplacement
│   ├── mcp/
│   │   └── server.py               # Serveur FastMCP
│   └── tools/
│       └── server.py               # Outils MCP exposés (5 tools)
├── docker/
│   ├── Dockerfile                  # Image Docker du serveur MCP
│   └── docker-compose.yml          # Orchestration
├── install_claude_desktop.py       # Script d'installation Claude Desktop
├── claude_desktop_config.template.json
└── files_to_sort/                  # Dossier de test avec fichiers exemples
```

---

## Formats supportés

- PDF (.pdf)
- Word (.docx, .doc)
- Texte (.txt)
- OpenDocument (.odt)

---

## Comparaison Baseline vs Tool Calling

| Critère | Baseline (sans outils) | Avec Tool Calling |
|---------|----------------------|-------------------|
| **Accès aux fichiers** | Non | Oui |
| **Analyse de contenu** | Non | Oui (via Ollama) |
| **Tri automatique** | Non | Oui |
| **Qualité des réponses sur les fichiers** | Hallucinations possibles | Basé sur le contenu réel |
| **Cas d'usage** | Chat général | Classification et organisation de fichiers |

---

## Dépannage

### Erreur 429 "Quota exceeded" (Gemini)

Le quota gratuit de Gemini est épuisé.

- **Solution** : Attendre le lendemain (le quota se réinitialise chaque jour)
- **Alternative** : Créer un nouveau projet sur Google AI Studio avec une nouvelle clé

### Erreur "model not found" (Ollama)

```bash
ollama pull llama3:latest
```

### Ollama ne répond pas

```bash
# Vérifier qu'Ollama tourne
ollama serve

# Vérifier les modèles installés
ollama list
```

### Classification imprécise

- Utilisez un modèle Ollama plus puissant
- Vérifiez que vos fichiers contiennent du texte extractible

---

## Sécurité & Confidentialité

- **Fichiers analysés localement** - Ollama tourne sur votre machine
- **Aucune suppression** - Les fichiers sont déplacés, jamais supprimés
- **Open source** - Code auditable

---

## Technologies

- **Gemini (Google AI)** - LLM cloud avec function calling (gratuit)
- **Claude Desktop** - Client MCP natif (Anthropic)
- **FastMCP** - Framework Python pour serveurs MCP standard
- **MCP (Model Context Protocol)** - Protocole standardisé IA <-> outils (JSON-RPC 2.0)
- **Ollama** - Exécution locale de LLMs pour l'analyse de fichiers
- **Streamlit** - Interface web interactive
- **NLTK** - Pipeline NLP (tokenisation, stemming, stopwords)
- **Docker** - Isolation du serveur MCP
- **Python 3.10+** - Backend
