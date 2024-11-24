FROM python:3.11-slim

# Instalacja dockera
RUN apt-get update && \
    apt-get install -y docker.io curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Ustawienie katalogu roboczego
WORKDIR /web

# Aktualizacja pip
RUN pip install --upgrade pip

# Instalowanie zależności
COPY web/requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Kopiowanie plików projektu WEB
COPY web/main.py .
COPY web/config.py .
COPY web/utils.py .
COPY web/build_binary.py .
COPY web/service.py .
COPY web/routes.py .
COPY web/templates/ templates/

EXPOSE 8945



CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8945"]