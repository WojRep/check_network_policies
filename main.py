from fastapi import FastAPI, UploadFile, HTTPException, Request, Form, File
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd
import os
import re
import subprocess
import shutil
import io
import logging
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import zipfile
from datetime import datetime

# Ustawienie ścieżki bazowej
BASE_DIR = Path(__file__).resolve().parent

# Konfiguracja logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Konfiguracja szablonów z absolutną ścieżką
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Dodanie CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sanitize_client_name(client_name: str) -> str:
    """Oczyszcza nazwę klienta z niedozwolonych znaków."""
    logger.debug(f"Sanityzacja nazwy klienta: {client_name}")
    sanitized = re.sub(r'[^\w\s-]', '', client_name)
    sanitized = sanitized.replace(' ', '_')
    sanitized = sanitized.strip('_')
    logger.debug(f"Nazwa po sanityzacji: {sanitized}")
    return sanitized

def create_zip_file(source_file: str, zip_filename: str, client_name: str) -> str:
    """Tworzy plik ZIP zawierający plik wykonywalny i dodatkowe informacje"""
    zip_path = os.path.join("output", zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Dodaj plik wykonywalny
        zipf.write(source_file, os.path.basename(source_file))
        
        # Dodaj plik README z informacjami
        readme_content = """Network Policy Checker
Generated for: {client_name}
Generation date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Instructions:
1. Extract the executable file
2. Run the program to check network policies
3. Review the results

For support contact your system administrator.
"""
        zipf.writestr('README.txt', readme_content)
    
    return zip_path

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        logger.info("Próba wyświetlenia strony głównej")
        logger.debug(f"Ścieżka do szablonów: {str(BASE_DIR / 'templates')}")
        response = templates.TemplateResponse(
            "upload.html",
            {"request": request}
        )
        logger.info("Strona główna wygenerowana pomyślnie")
        return response
    except Exception as e:
        logger.error(f"Błąd podczas renderowania strony głównej: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"/download/{file_id}")
async def download_file(file_id: str):
    """Endpoint do pobierania wygenerowanego pliku"""
    file_path = os.path.join("output", file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Plik nie został znaleziony")
    return FileResponse(
        file_path,
        media_type='application/zip',
        filename=file_id
    )

@app.post("/upload/")
async def upload_policy(
    request: Request,
    client_name: str = Form(...),
    file: UploadFile = File(...)
):
    logger.info(f"Rozpoczęcie przetwarzania dla klienta: {client_name}")
    
    try:
        content = await file.read()
        csv_data = io.StringIO(content.decode('utf-8'))
        df = pd.read_csv(csv_data)

        # Zapisanie pliku CSV
        os.makedirs('temp', exist_ok=True)
        csv_path = os.path.join('temp', 'network_policy.csv')
        df.to_csv(csv_path, index=False)

        # Sanityzacja nazwy klienta
        safe_client_name = sanitize_client_name(client_name)

        # Uruchomienie kontenera Docker
        cmd = 'docker run -v "$(pwd):/src/" --rm -it --entrypoint /bin/bash cdrx/pyinstaller-windows:python3 -c "python -m pip install --upgrade pip && /entrypoint.sh"'
        
        process = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)

        # Sprawdzenie czy plik exe został wygenerowany
        exe_path = "dist/windows/client_x86.exe"
        if not os.path.exists(exe_path):
            raise HTTPException(status_code=500, detail="Nie udało się wygenerować pliku wykonywalnego")

        # Przygotowanie nazw plików
        output_filename = f"check_network_policies_{safe_client_name}.exe"
        zip_filename = f"check_network_policies_{safe_client_name}.zip"
        
        # Utworzenie katalogu output jeśli nie istnieje
        os.makedirs("output", exist_ok=True)
        
        # Skopiuj plik exe do katalogu output
        output_exe_path = os.path.join("output", output_filename)
        shutil.copy2(exe_path, output_exe_path)
        
        # Utwórz plik ZIP
        zip_path = create_zip_file(output_exe_path, zip_filename, client_name)
        
        # Usuń tymczasowy plik exe
        os.remove(output_exe_path)
        
        # Zwróć stronę z linkiem do pobrania
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "download_link": f"/download/{zip_filename}",
                "filename": zip_filename
            }
        )

    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Wystąpił błąd: {str(e)}")

    finally:
        # Czyszczenie plików tymczasowych
        if os.path.exists('temp'):
            shutil.rmtree('temp')