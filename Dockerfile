FROM python:3.11-slim

# Instalacja dockera
RUN apt-get update && \
    apt-get install -y docker.io curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Ustawienie katalogu roboczego
WORKDIR /src

# Kopiowanie plików projektu
COPY ./web/requirements-web.txt .
COPY ./web/main.py .
COPY ./web/templates/ templates/

COPY ./src/client_x86.spec .
COPY ./src/client.py .
COPY ./src/requirements.txt .

# Instalacja zależności
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements-web.txt

# Port na którym działa aplikacja
EXPOSE 8945

# Uruchomienie aplikacji
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8945"]