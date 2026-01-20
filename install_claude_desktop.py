#!/usr/bin/env python3
"""
Script d'installation pour configurer Claude Desktop avec le serveur MCP file-classifier.
Fonctionne sur n'importe quel PC Windows.

Usage: python install_claude_desktop.py
"""

import json
import os
import shutil
from pathlib import Path


def get_claude_config_path() -> Path:
    """Retourne le chemin du fichier de config Claude Desktop."""
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        raise EnvironmentError("Variable APPDATA non trouvée")
    return Path(appdata) / "Claude" / "claude_desktop_config.json"


def get_user_home() -> str:
    """Retourne le dossier utilisateur (ex: C:\\Users\\NomUtilisateur)."""
    return str(Path.home())


def get_project_root() -> Path:
    """Retourne le dossier racine du projet."""
    return Path(__file__).parent


def load_env_file() -> dict:
    """Charge les variables depuis docker/.env"""
    env_path = get_project_root() / "docker" / ".env"
    env_vars = {}

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Ignorer les commentaires et lignes vides
                if not line or line.startswith("#"):
                    continue
                # Parser KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

    return env_vars


def create_config() -> dict:
    """Crée la configuration MCP pour Claude Desktop."""
    user_home = get_user_home()

    # Charger les variables depuis .env
    env_vars = load_env_file()

    # Valeurs par défaut si non définies dans .env
    ollama_model = env_vars.get("OLLAMA_MODEL_NAME", "llama3:latest")
    ollama_port = env_vars.get("OLLAMA_PORT", "11434")

    return {
        "mcpServers": {
            "file-classifier": {
                "command": "docker",
                "args": [
                    "run", "-i", "--rm",
                    "-e", f"OLLAMA_HOST=http://host.docker.internal:{ollama_port}",
                    "-e", f"OLLAMA_MODEL_NAME={ollama_model}",
                    "-v", f"{user_home}:/home/user",
                    "docker-mcp"
                ]
            }
        }
    }


def install():
    """Installe la configuration Claude Desktop."""
    config_path = get_claude_config_path()
    env_vars = load_env_file()

    print("=" * 60)
    print(" Installation MCP file-classifier pour Claude Desktop")
    print("=" * 60)
    print()

    # Afficher les valeurs du .env
    print("Configuration depuis docker/.env:")
    print(f"  OLLAMA_MODEL_NAME = {env_vars.get('OLLAMA_MODEL_NAME', 'llama3:latest (défaut)')}")
    print(f"  OLLAMA_PORT       = {env_vars.get('OLLAMA_PORT', '11434 (défaut)')}")
    print()

    # Vérifier si le dossier Claude existe
    config_dir = config_path.parent
    if not config_dir.exists():
        print(f"Création du dossier: {config_dir}")
        config_dir.mkdir(parents=True, exist_ok=True)

    # Sauvegarder l'ancienne config si elle existe
    if config_path.exists():
        backup_path = config_path.with_suffix(".json.backup")
        print(f"Sauvegarde de l'ancienne config: {backup_path}")
        shutil.copy(config_path, backup_path)

        # Charger la config existante pour fusionner
        with open(config_path, "r", encoding="utf-8") as f:
            existing_config = json.load(f)
    else:
        existing_config = {"mcpServers": {}}

    # Créer la nouvelle config
    new_config = create_config()

    # Fusionner avec la config existante
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}

    existing_config["mcpServers"]["file-classifier"] = new_config["mcpServers"]["file-classifier"]

    # Écrire la config
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(existing_config, f, indent=2)

    print()
    print(f"Configuration écrite dans: {config_path}")
    print()
    print("Correspondance des chemins:")
    print(f"  {get_user_home()}  -->  /home/user")
    print()
    print("Exemples de chemins à utiliser dans Claude Desktop:")
    print("  - /home/user/Downloads")
    print("  - /home/user/Documents")
    print("  - /home/user/Desktop")
    print()
    print("=" * 60)
    print(" IMPORTANT: Redémarrez Claude Desktop pour appliquer!")
    print("=" * 60)
    print()
    print("Prérequis:")
    print("  1. Docker Desktop doit être installé et lancé")
    print("  2. Ollama doit tourner (ollama serve)")
    print("  3. L'image docker-mcp doit être construite:")
    print("     cd docker && docker-compose build")
    print()


if __name__ == "__main__":
    try:
        install()
    except Exception as e:
        print(f"Erreur: {e}")
        input("Appuyez sur Entrée pour fermer...")
