# MCP - Tri Automatique de Documents

Système de tri automatique de documents contenant du texte utilisant IA locale (Ollama) pour organiser vos fichiers intelligemment.

**100% local** - Vos documents restent sur votre machine.

---

## Démarrage rapide avec Claude Desktop

### Prérequis

- **Docker Desktop** installé et lancé
- **Ollama** installé et en cours d'exécution sur votre PC
- **Claude Desktop** installé avec un compte connecté

```bash
# Lancer Ollama (si pas déjà fait)
ollama serve

# Télécharger un modèle (au choix)
ollama pull llama3:latest
# ou
ollama pull gpt-oss:20b-cloud
```

### Installation (3 étapes)

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

Dans Claude Desktop, dites simplement :

> **"Trie le dossier /home/user/Downloads"**

ou en mode simulation (sans déplacer les fichiers) :

> **"Trie /home/user/Documents en mode dry-run"**

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Claude Desktop  │ --> │  Docker (MCP)   │ --> │ Ollama (local)  │
│                 │     │  file-classifier│     │ localhost:11434 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

- **Claude Desktop** : Interface utilisateur, appelle les outils MCP
- **Docker** : Contient le serveur MCP avec les outils de tri
- **Ollama** : Tourne en local sur votre PC, analyse les documents

---

## Correspondance des chemins

Le script d'installation monte automatiquement votre dossier utilisateur dans Docker :

| Votre PC (Windows) | Ce que vous dites à Claude |
|--------------------|----------------------------|
| `C:\Users\VotreNom\Downloads` | `/home/user/Downloads` |
| `C:\Users\VotreNom\Documents` | `/home/user/Documents` |
| `C:\Users\VotreNom\Desktop` | `/home/user/Desktop` |

---

## Outils MCP disponibles

| Outil | Description |
|-------|-------------|
| `sort_folder` | **Recommandé** - Trie automatiquement un dossier complet |
| `list_files_to_sort` | Liste les fichiers d'un dossier |
| `analyze_file` | Analyse un fichier avec l'IA |
| `group_files` | Regroupe les fichiers analysés |
| `apply_file_plan` | Applique le plan de tri |

---

## Comment ça marche ?

### Pipeline de traitement

```
[Fichiers bruts]
    → [Extraction contenu (PDF, DOCX, TXT)]
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

## Structure du projet

```
Projet_NLP_MCP/
├── docker/
│   ├── Dockerfile               # Image Docker du serveur MCP
│   ├── docker-compose.yml       # Orchestration
│   └── .env                     # Configuration (modèle Ollama)
├── src/
│   ├── mcp/
│   │   └── server.py            # Serveur FastMCP
│   ├── classifier/
│   │   ├── analyzer.py          # Extraction + analyse LLM
│   │   └── organizer.py         # Regroupement + déplacement
│   └── tools/
│       └── server.py            # 5 outils MCP exposés
├── install_claude_desktop.py    # Script d'installation automatique
├── claude_desktop_config.template.json
├── main.py                      # CLI standalone (sans Claude)
└── requirements.txt
```

---

## Configuration

### Fichier d'environnement (.env)

Avant de lancer le projet, vous devez créer le fichier de configuration :

```bash
# Copier le fichier exemple
cd docker
cp .env.example .env
```

Puis éditez `docker/.env` selon vos besoins :

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `OLLAMA_MODEL_NAME` | Modèle Ollama à utiliser | `deepseek-v3.1:671b-cloud` |
| `OLLAMA_MODEL_PATH` | Chemin local vers les modèles Ollama | `${USERPROFILE}\.ollama` (Windows) |
| `FILES_TO_SORT` | Dossier à trier (monté dans `/files` dans Docker) | `./files_to_sort` |
| `MCP_PORT` | Port du serveur MCP | `3000` |
| `OLLAMA_PORT` | Port d'Ollama | `11434` |

### Changer le modèle Ollama

Dans `docker/.env`, modifiez `OLLAMA_MODEL_NAME` :

```bash
# Cloud (performant, nécessite connexion)
OLLAMA_MODEL_NAME=deepseek-v3.1:671b-cloud

# Local (recommandé pour débuter)
OLLAMA_MODEL_NAME=llama3:latest

# Local (alternative légère)
OLLAMA_MODEL_NAME=mistral:latest
```

Puis reconstruisez : `cd docker && docker-compose build`

---

## Formats supportés

- PDF (.pdf)
- Word (.docx, .doc)
- Texte (.txt)
- OpenDocument (.odt)

---

## Dépannage

### Claude Desktop : "Server disconnected"

1. Vérifiez que **Docker Desktop** est lancé
2. Vérifiez que l'image est construite :
   ```bash
   cd docker && docker-compose build
   ```
3. Vérifiez qu'**Ollama** tourne :
   ```bash
   ollama serve
   ollama list
   ```
4. Relancez le script d'installation :
   ```bash
   python install_claude_desktop.py
   ```
5. **Redémarrez complètement** Claude Desktop

### Erreur "model not found"

```bash
ollama pull llama3:latest
```

### Classification imprécise

- Utilisez un modèle plus puissant : `gpt-oss:20b-cloud`
- Vérifiez que vos fichiers contiennent du texte extractible

---

## Sécurité & Confidentialité

- **100% local** - Vos fichiers ne quittent jamais votre machine
- **Aucune suppression** - Les fichiers sont déplacés, jamais supprimés
- **Open source** - Code auditable

---

## Technologies

- **MCP (Model Context Protocol)** - Protocole de communication IA ↔ outils
- **FastMCP** - Framework Python pour serveurs MCP
- **Ollama** - Exécution locale de LLMs
- **Docker** - Portabilité et isolation
- **Python 3.11** - Backend
