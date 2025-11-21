---

# 📁 MCP – Système de Tri Automatique de Dossiers (File Manager)

Ce projet utilise un pipeline basé sur un **LLM (Ollama / Llama 3)** pour analyser, classer et organiser automatiquement des fichiers dans une arborescence logique.
Il fonctionne intégralement en local via Docker, ou peut se connecter à Ollama Cloud si nécessaire.

---

## 🚀 Lancement rapide

### 1️⃣ Exécuter le script PowerShell

```bash
.\run_file_manager.ps1 <chemin_du_dossier_a_trier>
```

Si vous avez une erreur liée à l'exécution des scripts, activez les droits :

```bash
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Voir les politiques actuelles :

```bash
Get-ExecutionPolicy -List
```

---

## 🧠 Installation de Ollama

### ✔ Installer Ollama (local)

Suivez l’installation pour votre OS :
[https://ollama.com/download](https://ollama.com/download)

### ✔ Télécharger un modèle local

Par exemple Llama 3 :

```bash
ollama pull llama3
```

### ✔ Utiliser le modèle automatiquement avec le MCP

Aucun changement à faire : le script utilisera automatiquement Ollama.

---

## ☁️ (OPTIONNEL) Utiliser Ollama Cloud

Si vous souhaitez exécuter les analyses côté cloud :

```bash
ollama signin
ollama serve
```

Puis sélectionnez un modèle cloud dans votre configuration. Ajouter ce model à la ligne 76 du main.py.

---

# 🛠 Fonctionnement du pipeline

Le système suit 4 étapes principales :

---

## **1. Récupération des fichiers**

Le script récupère :

* les noms de fichiers
* leurs chemins
* un extrait de leur contenu (prévisualisation)

Cela permet au modèle de comprendre le type du document.

---

## **2. Analyse des fichiers**

Un premier traitement est effectué :

* extraction de mots-clés
* tentative d’identification du type de fichier (CV, ordonnance, article, etc.)
* extraction de métadonnées (dates, titres, noms)
* détection de langue

Ces informations servent de base au LLM pour proposer un classement intelligent.

---

## **3. Classification via LLM**

Un prompt spécialisé est envoyé au LLM afin :

* de déterminer la catégorie exacte du fichier
* de proposer une **structure hiérarchique** cohérente
* de nommer les dossiers de manière propre
* d’indiquer où chaque fichier doit être déplacé

Le LLM retourne un **JSON strict**, par exemple :

```json
{
  "target_folder": "Documents/Articles/Réseaux/2023",
  "keywords": ["network slicing", "VSR", "architecture"],
  "type": "article",
  "date": "2023-05-12"
}
```

---

## **4. Déplacement et création des dossiers**

À partir du JSON :

* les dossiers nécessaires sont créés automatiquement
* les fichiers sont déplacés vers leur emplacement final
* les collisions de noms sont gérées
* les chemins sont sécurisés

Le tri entier est **automatique**, reproductible, et piloté par le LLM.

---

# 📌 Résumé du workflow

```
[Fichiers brut]
       ↓
[Extraction keywords + métadonnées]
       ↓
[LLM → propose une hiérarchie complète]
       ↓
[Création dossiers + tri automatique]
       ↓
[Dossier final organisé proprement]
```

---

# 📝 Notes

* Aucun fichier n’est supprimé automatiquement.
* Le système fonctionne en local : vos documents ne quittent jamais votre machine.
* Le modèle recommandé est **Llama 3 (via Ollama)**, performant pour classification.
* Le script fonctionne sous Windows, Linux et macOS via Docker.


erreur ajouter des outils 
serveur definit des outils 
clients choisit ce quil veut faire  
api chat => in formation serveur => besoin d'appeler => appeler telle fonction