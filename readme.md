# MCP TRiE DE DOSSIER

### Lancement

````bash
.\run_file_manager.ps1 <votre dossier>
````
````bash
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
````
````bash
Get-ExecutionPolicy -List
````

### Fonctionalité

#### 1 Recupérer les fichiers -> prendre les noms des fichiers a trier et les envoyer au llm [nom du fichier/chemin] 

#### 2 analyser les fichiers -> création des mots cles [type de fichier, mots clés du contenu, dates de l'écrit]

#### 3 LLm qui trie -> renvoie une hierarchie de dossier sous un format choisie [créer le prompt et ajoute 1 2  ]

#### 4 Déplacement/création de fichier -> lit le format de fichier envoyer depuis le llm [ deplacer/créer selon le format ]



