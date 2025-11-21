# --- Base Python ---
FROM python:3.11-slim

# --- Réduire les warnings et améliorer l'exécution ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# --- Installer dépendances système ---
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Installer Ollama client (optionnel) ---
# ⚠ Si tu veux utiliser Ollama en local, il doit tourner dans un autre conteneur :
# docker run -d --gpus=all -p 11434:11434 ollama/ollama:latest
RUN curl -fsSL https://ollama.com/install.sh | sh || true

# --- Ajouter le code du serveur MCP ---
WORKDIR /app
COPY . /app

# --- Installer les dépendances Python ---
# Ajoute un fichier requirements.txt contenant :
# mcp
# fastapi
# uvicorn
# python-dotenv
# ollama
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# --- Exposer le port MCP (généralement 3000 mais libre) ---
EXPOSE 3000

# --- Commande d'exécution du serveur MCP ---
CMD ["python", "server.py"]
