# MCP - Tri Automatique de Documents

Système de tri automatique de documents utilisant IA (Ollama) pour organiser vos fichiers intelligemment.

**100% local via Docker** - Vos documents restent sur votre machine.

---

## Démarrage rapide

### Prérequis

- **Docker Desktop** installé
- **Ollama** en cours d'exécution

```bash
# Lancer Ollama
ollama serve

# Télécharger un modèle
ollama pull llama3:latest
```

### Lancement

```bash
# Depuis le dossier docker/
cd docker
docker-compose up --build
```

**C'est tout !** Vos fichiers dans `files_to_sort` seront automatiquement triés.

---

## Comment ça marche ?

### Processus

```
[Fichiers bruts] 
    → [Extraction contenu]
    → [Analyse LLM]
    → [Classification]
    → [Organisation automatique]
```

### Résultat

**Avant :**
```
files_to_sort/
├── article1.pdf
├── article2.pdf
├── CV_Martin.pdf
└── rapport.pdf
```

**Après :**
```
files_to_sort/
├── article/
│   └── medical-retine/ (2 fichiers)
├── cv/ (1 fichier)
└── rapport/ (1 fichier)
```

---

## Architecture du projet

```
Projet_NLP_MCP/
├── docker/              # Configuration Docker + .env
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env            # Configuration (modèle, dossiers)
├── src/                 # Code source
│   ├── mcp/            # Serveur MCP
│   ├── classifier/     # Analyse et organisation
│   └── tools/          # Outils MCP
├── docs/                # Documentation
│   ├── USAGE.md        # Guide d'utilisation détaillé
│   └── QUICKSTART.md   # Démarrage rapide
├── files_to_sort/       # Dossier à trier
├── main.py              # Point d'entrée
└── requirements.txt     # Dépendances Python
```

---

## Configuration

### Choisir un modèle

Éditez `docker/.env` :

```bash
# Modèle local (rapide, gratuit)
OLLAMA_MODEL_NAME=llama3:latest

# Modèle cloud (meilleure classification)
OLLAMA_MODEL_NAME=deepseek-v3.1:671b-cloud
```

### Mode simulation

```bash
cd docker
docker run --network="host" \
  -v "../files_to_sort:/files" \
  docker-mcp python main.py --folder /files --dry-run
```

---

## Formats supportés

- PDF (.pdf)
- Word (.docx, .doc)
- Texte (.txt)
- OpenDocument (.odt)

---

## Documentation complète

- **[Guide d'utilisation](./docs/USAGE.md)** - Exemples et cas d'usage
- **[Démarrage rapide](./docs/QUICKSTART.md)** - Guide installation

---

## Dépannage

### Ollama non connecté

```bash
# Vérifier qu'Ollama tourne
ollama serve
ollama list
```

### Erreur "model not found"

```bash
# Télécharger le modèle
ollama pull llama3:latest
```

### Classification imprécise

- Essayer un modèle plus puissant : `deepseek-v3.1:671b-cloud`
- Vérifier que vos fichiers ont du contenu textuel

---

## Sécurité & Confidentialité

- 100% local - Vos fichiers restent sur votre machine
- Pas de cloud avec llama3:latest
- Aucune suppression - Les fichiers sont déplacés
- Open source - Code auditable

---

## Technologies

- **MCP (Model Context Protocol)** - Architecture outils
- **Ollama** - Exécution locale LLMs
- **Docker** - Portabilité
- **Python 3.11** - Backend

