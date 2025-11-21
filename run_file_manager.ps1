param(
    [Parameter(Mandatory = $true)]
    [string]$Folder
)

# Nom de l'image
$imageName = "mcp-file-manager"

# Résoudre le chemin complet
$fullPath = Resolve-Path $Folder

# Vérifier si l'image existe
$imageId = docker images -q $imageName

if (-not $imageId) {
    Write-Host "Image '$imageName' introuvable. Build en cours..."
    docker build -t $imageName .
}

# Lancer le container en montant le dossier donné et en appelant main.py
docker run --rm `
  -v "$($fullPath):/data" `
  $imageName `
  python main.py /data
