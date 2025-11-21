FROM python:3.12-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl nano && \
    rm -rf /var/lib/apt/lists/*

# App user
RUN useradd -m appuser
WORKDIR /app
USER appuser

# Install deps
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY --chown=appuser:appuser . .

# (optionnel) watchgod si tu veux, mais pas nécessaire pour un script one-shot
# RUN pip install --no-cache-dir watchgod

# 🔹 Ne lance plus main.py automatiquement
CMD ["bash"]
