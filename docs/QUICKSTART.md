# 🚀 Démarrage Rapide MCP

## Installation et premier lancement

### 1. Prérequis

- Docker Desktop installé
- Ollama installé : https://ollama.com/download

### 2. Configuration

```bash
# Copier la configuration
cp .env.example .env

# (Optionnel) Éditer .env pour personnaliser
```

### 3. Premier test

```bash
# Démarrer avec Docker
docker-compose up --build

# OU tester en local
pip install -r requirements.txt
python main.py --folder ./files_to_sort --dry-run
```

## 🎯 Utilisation rapide

**Placer vos fichiers** dans `files_to_sort/` et lancer :

```bash
docker-compose up
```

Les fichiers seront automatiquement triés !

## 📚 Documentation complète

- **Guide d'utilisation** : [USAGE.md](./USAGE.md)
- **Documentation technique** : [readme.md](./readme.md)

## ⚙️ Configuration rapide

Dans `.env` :

```bash
# Pour utiliser Ollama en local (recommandé pour débuter)
OLLAMA_MODEL_NAME=llama3:latest

# Pour utiliser le cloud (plus performant)
OLLAMA_MODEL_NAME=deepseek-v3.1:671b-cloud
```

## 🐛 Problèmes fréquents

**"model not found"** → `ollama pull llama3:latest`

**Erreur connexion Ollama** → `ollama serve`

**Fichiers non triés** → Vérifier les logs : `docker-compose logs -f`

---

Pour plus de détails, consultez [USAGE.md](./USAGE.md) et [readme.md](./readme.md)
