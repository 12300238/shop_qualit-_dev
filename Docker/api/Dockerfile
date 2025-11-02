FROM python:3.11-slim

WORKDIR /app

# Installation de dépendances système si besoin
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de l'API
COPY api-shop.py .
COPY shop.py .
COPY requirements.txt .
COPY test_data.json .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port FastAPI
EXPOSE 8000

# Lancement de l'API
CMD ["uvicorn", "api-shop:app", "--host", "0.0.0.0", "--port", "8000"]