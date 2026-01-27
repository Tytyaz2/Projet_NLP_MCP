# --- Base Python ---
FROM python:3.11-slim

# --- Réduire les warnings et améliorer l'exécution ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# --- Installer dépendances système ---
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Ajouter le code du serveur MCP ---
WORKDIR /app
COPY . /app

# --- Installer les dépendances Python ---
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# --- Exposer le port MCP (généralement 3000 mais libre) ---
EXPOSE 3000

# --- Commande d'exécution du serveur MCP ---
CMD ["python", "src/tools/server.py"]
