FROM python:3.11-slim

WORKDIR /app

# Copier les sources du frontend
COPY site_marchand.py .
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

# Lancement Streamlit
CMD ["streamlit", "run", "site_marchand.py", "--server.port=8501", "--server.address=0.0.0.0"]