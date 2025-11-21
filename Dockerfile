FROM python:3.12-slim AS base
  
  # System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
git curl nano && \
rm -rf /var/lib/apt/lists/*
  
  # App user
RUN useradd -m appuser
WORKDIR /app
USER appuser
  
  # Install dependencies via requirements
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
  
  # Copy app
COPY --chown=appuser:appuser . .
  
  # Hot reload for dev
RUN pip install --no-cache-dir watchgod

CMD ["python", "-m", "watchgod", "main"]
