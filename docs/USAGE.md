# Guide d'utilisation - MCP Tri Automatique avec Docker

Ce guide vous montre comment utiliser le système de tri automatique avec Docker.

---

## 🎯 Cas d'usage pratiques

### 1. Premier tri - Simulation

**Objectif** : Voir comment vos fichiers seront organisés sans les déplacer.

```bash
# 1. Construire l'image Docker
docker build -t mcp-file-classifier .

# 2. Lancer en mode dry-run (simulation)
docker run --network="host" \
  -v "${PWD}/mon_dossier:/files" \
  -e OLLAMA_MODEL_NAME=llama3:latest \
  mcp-file-classifier python main.py --folder /files --dry-run
```

Le script affichera la structure proposée sans déplacer aucun fichier.

---

### 2. Tri réel d'un dossier

**Objectif** : Trier automatiquement vos fichiers.

```bash
# Lancer le tri réel
docker run --name mcp-sorting --network="host" \
  -v "${PWD}/mes_documents:/files" \
  -e OLLAMA_MODEL_NAME=llama3:latest \
  mcp-file-classifier python main.py --folder /files

# Voir les logs
docker logs mcp-sorting

# Nettoyer après
docker rm mcp-sorting
```

---

### 3. Trier avec un meilleur modèle

**Objectif** : Obtenir une classification plus précise avec un modèle cloud.

```bash
# 1. Se connecter à Ollama Cloud
ollama signin

# 2. Lancer avec le modèle performant
docker run --name mcp-sorting --network="host" \
  -v "${PWD}/data:/files" \
  -e OLLAMA_MODEL_NAME=deepseek-v3.1:671b-cloud \
  mcp-file-classifier python main.py --folder /files
```

---

### 4. Trier uniquement certains types de fichiers

**Objectif** : Trier seulement les PDFs ou DOCXs.

```bash
# Uniquement les PDFs
docker run --network="host" \
  -v "${PWD}/documents:/files" \
  -e OLLAMA_MODEL_NAME=llama3:latest \
  mcp-file-classifier python main.py --folder /files --extensions .pdf

# PDFs et DOCXs
docker run --network="host" \
  -v "${PWD}/documents:/files" \
  -e OLLAMA_MODEL_NAME=llama3:latest \
  mcp-file-classifier python main.py --folder /files --extensions .pdf .docx
```

---

## 🚀 Workflow complet recommandé

### Étape 1 : Préparation

```bash
# S'assurer qu'Ollama tourne
ollama serve

# Télécharger le modèle si nécessaire
ollama pull llama3:latest

# Construire l'image Docker (une seule fois)
docker build -t mcp-file-classifier .
```

### Étape 2 : Simulation

```bash
# Tester sans déplacer les fichiers
docker run --network="host" \
  -v "${PWD}/mon_dossier:/files" \
  -e OLLAMA_MODEL_NAME=llama3:latest \
  mcp-file-classifier python main.py --folder /files --dry-run
```

### Étape 3 : Tri réel

```bash
# Lancer le tri
docker run --name mcp-sorting --network="host" \
  -v "${PWD}/mon_dossier:/files" \
  -e OLLAMA_MODEL_NAME=llama3:latest \
  mcp-file-classifier python main.py --folder /files
```

### Étape 4 : Vérification

```bash
# Consulter les logs
docker logs mcp-sorting

# Vérifier la structure créée
ls -R mon_dossier/

# Nettoyer
docker rm mcp-sorting
```

---

## 📁 Exemples par type de documents

### Trier des CVs

```bash
docker run --network="host" \
  -v "${PWD}/CVs_recus:/files" \
  -e OLLAMA_MODEL_NAME=llama3:latest \
  mcp-file-classifier python main.py --folder /files --extensions .pdf .docx
```

**Résultat attendu** :
```
CVs_recus/
├── cv/
│   ├── developpeurs/
│   ├── designers/
│   └── managers/
```

---

### Trier des articles scientifiques

```bash
docker run --network="host" \
  -v "${PWD}/Papers:/files" \
  -e OLLAMA_MODEL_NAME=deepseek-v3.1:671b-cloud \
  mcp-file-classifier python main.py --folder /files --extensions .pdf
```

**Résultat attendu** :
```
Papers/
├── article/
│   ├── intelligence-artificielle/
│   ├── medical/
│   ├── reseaux/
│   └── mathematiques/
```

---

### Trier un dossier de téléchargements Windows

```bash
docker run --network="host" \
  -v "C:/Users/VotreNom/Downloads:/files" \
  -e OLLAMA_MODEL_NAME=llama3:latest \
  mcp-file-classifier python main.py --folder /files
```

---

## 🔧 Options avancées

### Utiliser docker-compose

Créez ou modifiez `docker-compose.yml` :

```yaml
services:
  mcp:
    build: .
    network_mode: "host"
    environment:
      - OLLAMA_MODEL_NAME=llama3:latest
    volumes:
      - ./mon_dossier:/files
    command: python main.py --folder /files
```

Puis lancez :
```bash
docker-compose up --build
```

---

### Automatiser le tri quotidien

Créez un script batch Windows (`trier_quotidien.bat`) :

```batch
@echo off
echo Démarrage d'Ollama...
start /B ollama serve

echo Attente démarrage Ollama...
timeout /t 5

echo Lancement du tri...
docker run --name mcp-sorting-%date:~-4%%date:~-7,2%%date:~-10,2% ^
  --network="host" ^
  -v "%USERPROFILE%\Downloads:/files" ^
  -e OLLAMA_MODEL_NAME=llama3:latest ^
  mcp-file-classifier python main.py --folder /files

echo Tri terminé !
pause
```

---

## 📊 Interpréter les logs

### Logs de succès

```
11:36:24 - INFO - ============================================
11:36:24 - INFO - 🚀 MCP - Système de Tri Automatique
11:36:24 - INFO - ============================================
11:36:24 - INFO - 📂 Dossier à trier: /files
11:36:25 - INFO - 📁 11 fichier(s) trouvé(s)
11:36:25 - INFO - 🔍 Début de l'analyse des fichiers...
11:36:26 - INFO -   [1/11] Analyse de: document1.pdf
11:36:27 - INFO -     ✓ Type: article, Keywords: AI, ML
...
11:36:45 - INFO - ✅ Analyse terminée : 11/11 fichiers
11:36:45 - INFO - 📊 Regroupement des documents...
11:36:46 - INFO - ✅ 3 groupe(s) créé(s)
11:36:46 - INFO - 📦 Application du plan...
11:36:47 - INFO - ✅ 11 fichier(s) déplacé(s)
11:36:47 - INFO - ============================================
11:36:47 - INFO - ✅ Tri terminé : 11 fichiers organisés
11:36:47 - INFO - ============================================
```

### Logs d'erreur commune

**"Connection refused"** → Ollama n'est pas démarré
```bash
# Solution :
ollama serve
```

**"model not found"** → Le modèle n'est pas téléchargé
```bash
# Solution :
ollama pull llama3:latest
```

---

## 💡 Conseils pour de meilleurs résultats

### 1. Noms de fichiers descriptifs

❌ **Mauvais** : `document.pdf`, `scan.pdf`  
✅ **Bon** : `CV_Jean_Dupont.pdf`, `Facture_Janvier_2024.pdf`

### 2. Fichiers avec contenu lisible

- Les PDFs scannés sans OCR sont difficiles à analyser
- Les fichiers vides seront classés dans "autre"
- Privilégiez les PDF avec texte sélectionnable

### 3. Choix du modèle

| Modèle | Vitesse | Précision | Utilisation |
|--------|---------|-----------|-------------|
| `llama3:latest` | ⚡⚡⚡ Rapide | 🎯 Basique | Usage quotidien |
| `deepseek-v3.1:671b-cloud` | ⚡⚡ Moyen | 🎯🎯🎯 Excellent | Classification précise |

---

## 🐛 Résolution de problèmes

### Tous les fichiers dans "autre/sans-theme"

**Causes possibles** :
- Modèle trop basique (llama3:latest)
- Fichiers sans contenu exploitable
- PDFs scannés sans texte

**Solutions** :
```bash
# 1. Essayer un modèle plus puissant
ollama signin
docker run --network="host" \
  -v "${PWD}/data:/files" \
  -e OLLAMA_MODEL_NAME=deepseek-v3.1:671b-cloud \
  mcp-file-classifier python main.py --folder /files

# 2. Vérifier le contenu des fichiers
# Ouvrir quelques PDFs pour s'assurer qu'ils ont du texte sélectionnable
```

### Docker lent ou freeze

**Solutions** :
```bash
# Augmenter les ressources Docker Desktop
# Settings → Resources → Advanced
# - CPU: 4+ cores
# - Memory: 8+ GB

# Redémarrer Docker
# Settings → Restart Docker Desktop
```

### Erreur de permissions (Linux/Mac)

```bash
# Ajouter --user pour les permissions
docker run --network="host" --user $(id -u):$(id -g) \
  -v "${PWD}/data:/files" \
  -e OLLAMA_MODEL_NAME=llama3:latest \
  mcp-file-classifier python main.py --folder /files
```

---

## 🎓 Exemples réels testés

### Exemple 1 : Dossier académique

**Contenu initial** : 11 PDFs (articles, CVs, cours)

```bash
docker run --name mcp-sorting --network="host" \
  -v "${PWD}/data:/files" \
  -e OLLAMA_MODEL_NAME=llama3:latest \
  mcp-file-classifier python main.py --folder /files
```

**Résultat** : Tous classés dans `data/autre/sans-theme/` (modèle basique)

**Amélioration** :
```bash
ollama signin
docker run --network="host" \
  -v "${PWD}/data:/files" \
  -e OLLAMA_MODEL_NAME=deepseek-v3.1:671b-cloud \
  mcp-file-classifier python main.py --folder /files
```

---

## 📞 Aide supplémentaire

- **README principal** : [readme.md](./readme.md)
- **Démarrage rapide** : [QUICKSTART.md](./QUICKSTART.md)
- **Tests effectués** : Consultez les logs Docker

---

## ✅ Checklist avant de lancer

- [ ] Docker Desktop est démarré
- [ ] Ollama est en cours d'exécution (`ollama serve`)
- [ ] Le modèle est téléchargé (`ollama list`)
- [ ] L'image Docker est construite (`docker build -t mcp-file-classifier .`)
- [ ] Vos fichiers sont dans le dossier à trier
- [ ] Vous avez testé en mode `--dry-run`

**Vous êtes prêt !** 🚀
