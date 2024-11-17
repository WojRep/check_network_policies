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
import uvicorn  # Dodane

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

# Skonfiguruj serwer statyczny do serwowania plików
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")

# Dodanie CORS middleware z bardziej szczegółową konfiguracją
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

@app.get("/download/{file_id}")
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

def create_zip_file(source_file: str, zip_filename: str, client_name: str, os_type: str) -> str:
    """
    Tworzy plik ZIP zawierający plik wykonywalny i dodatkowe informacje
    """
    zip_path = os.path.join("output", zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Dodaj plik wykonywalny
        zipf.write(source_file, os.path.basename(source_file))
        
        # Dodaj plik README z informacjami
        readme_content = """Network Policy Checker ({os_type})
Generated for: {client_name}
Generation date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
System: {os_type}

Instructions:
1. Extract the executable file
2. Run the program to check network policies
   {"- Windows: Double click the .exe file" if os_type == "Windows" else "- Linux: Make the file executable with 'chmod +x' and run it from terminal"}
3. Review the results

For support contact your system administrator.
"""
        zipf.writestr('README.txt', readme_content)
    
    return zip_path

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

        # Generowanie dla Windows
        cmd_windows = 'docker run -v "$(pwd):/src/" --rm -it --entrypoint /bin/bash cdrx/pyinstaller-windows:python3 -c "python -m pip install --upgrade pip && /entrypoint.sh"'
        process_windows = subprocess.run(cmd_windows, shell=True, check=True, capture_output=True, text=True)

        # Sprawdzenie czy plik exe został wygenerowany
        exe_path = "dist/windows/client_x86.exe"
        if not os.path.exists(exe_path):
            raise HTTPException(status_code=500, detail="Nie udało się wygenerować pliku wykonywalnego dla Windows")

        # Przygotowanie nazw plików dla Windows
        output_filename_windows = f"check_network_policies_{safe_client_name}.exe"
        zip_filename_windows = f"check_network_policies_{safe_client_name}_windows.zip"
        
        # Utworzenie katalogu output jeśli nie istnieje
        os.makedirs("output", exist_ok=True)
        
        # Skopiuj plik exe do katalogu output
        output_exe_path_windows = os.path.join("output", output_filename_windows)
        shutil.copy2(exe_path, output_exe_path_windows)
        
        # Utwórz plik ZIP dla Windows
        zip_path_windows = create_zip_file(output_exe_path_windows, zip_filename_windows, client_name, "Windows")
        
        # Generowanie dla Linux
        cmd_linux = 'docker run -v "$(pwd):/src/" --rm -it --entrypoint /bin/bash cdrx/pyinstaller-linux:python3 -c "python -m pip install --upgrade pip && /entrypoint.sh"'
        process_linux = subprocess.run(cmd_linux, shell=True, check=True, capture_output=True, text=True)

        # Sprawdzenie czy plik dla Linuxa został wygenerowany
        linux_path = "dist/linux/client"
        if not os.path.exists(linux_path):
            raise HTTPException(status_code=500, detail="Nie udało się wygenerować pliku wykonywalnego dla Linux")

        # Przygotowanie nazw plików dla Linux
        output_filename_linux = f"check_network_policies_{safe_client_name}"
        zip_filename_linux = f"check_network_policies_{safe_client_name}_linux.zip"
        
        # Skopiuj plik dla Linux do katalogu output
        output_linux_path = os.path.join("output", output_filename_linux)
        shutil.copy2(linux_path, output_linux_path)
        
        # Utwórz plik ZIP dla Linux
        zip_path_linux = create_zip_file(output_linux_path, zip_filename_linux, client_name, "Linux")
        
        # Usuń tymczasowe pliki
        os.remove(output_exe_path_windows)
        os.remove(output_linux_path)
        
        # Zwróć stronę z linkami do pobrania
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "download_link_windows": f"/download/{zip_filename_windows}",
                "filename_windows": zip_filename_windows,
                "download_link_linux": f"/download/{zip_filename_linux}",
                "filename_linux": zip_filename_linux
            }
        )

    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Wystąpił błąd: {str(e)}")

    finally:
        # Czyszczenie plików tymczasowych
        if os.path.exists('temp'):
            shutil.rmtree('temp')