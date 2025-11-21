param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

# Nom de l'image
$imageName = "mcp-file-manager"

# Résoudre le chemin passé en argument (fichier ou dossier)
$resolved = Resolve-Path $Path

# Dossier du projet (là où se trouve ce script)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectPath = Resolve-Path $scriptDir

# Déterminer si c'est un fichier ou un dossier
if (Test-Path $resolved -PathType Leaf) {
    # 👉 FICHIER
    $dir = Split-Path $resolved
    $fileName = Split-Path $resolved -Leaf

    $mountPath = $dir
    $targetInContainer = "/data/$fileName"
}
else {
    # 👉 DOSSIER
    $mountPath = $resolved
    $targetInContainer = "/data"
}

# Vérifier si l'image existe, sinon build
$imageId = docker images -q $imageName
if (-not $imageId) {
    Write-Host "Image '$imageName' introuvable. Build en cours..."
    docker build -t $imageName .
}

Write-Host "→ Projet monté : $projectPath -> /app"
Write-Host "→ Dossier de travail : $mountPath -> /data"
Write-Host "→ Argument main.py : $targetInContainer"

docker run --rm `
  -v "${projectPath}:/app" `
  -v "${mountPath}:/data" `
  -e OLLAMA_HOST="http://host.docker.internal:11434" `
  $imageName `
  python /app/main.py $targetInContainer
