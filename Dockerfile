FROM python:3.11-slim

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copier le serveur
COPY . .

# Définir la racine accessible
ENV CONTAINER_ROOT=/data_mount

# Exposer le port
EXPOSE 8000

# Lancer le serveur MCP
CMD ["python", "mcp_server.py"]
