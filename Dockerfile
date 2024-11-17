FROM python:3.11-slim

# Instalacja dockera
RUN apt-get update && \
    apt-get install -y docker.io && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Ustawienie katalogu roboczego
WORKDIR /app

# Kopiowanie plików projektu
COPY requirements-web.txt .
COPY main.py .
COPY templates/ templates/

COPY client_x86.spec .
COPY client.py .
COPY requirements.txt .

# Instalacja zależności
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements-web.txt

# Port na którym działa aplikacja
EXPOSE 8945

# Uruchomienie aplikacji
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8945"]