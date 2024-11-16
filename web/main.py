from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import os
import re
import subprocess
import shutil
from typing import List
from pydantic import BaseModel
import logging

# Konfiguracja logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Model do walidacji struktury CSV
class NetworkPolicy(BaseModel):
    src_ip: str
    src_fqdn: str
    src_port: str
    protocol: str
    dst_ip: str
    dst_fqdn: str
    dst_port: str
    description: str

def sanitize_client_name(client_name: str) -> str:
    """Oczyszcza nazwę klienta z niedozwolonych znaków."""
    # Zamiana spacji na podkreślenia i usunięcie niedozwolonych znaków
    sanitized = re.sub(r'[^\w\s-]', '', client_name)
    return sanitized.replace(' ', '_')

def validate_csv_structure(df: pd.DataFrame) -> bool:
    """Sprawdza czy struktura CSV jest poprawna."""
    required_columns = [
        'src_ip', 'src_fqdn', 'src_port', 'protocol',
        'dst_ip', 'dst_fqdn', 'dst_port', 'description'
    ]
    return all(column in df.columns for column in required_columns)

def validate_protocols(df: pd.DataFrame) -> bool:
    """Sprawdza czy protokoły są poprawne (TCP/UDP)."""
    valid_protocols = ['TCP', 'UDP']
    return all(protocol.upper() in valid_protocols for protocol in df['protocol'])

@app.post("/upload/")
async def upload_policy(client_name: str, file: UploadFile):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Plik musi być w formacie CSV")

    # Sanityzacja nazwy klienta
    safe_client_name = sanitize_client_name(client_name)
    
    try:
        # Odczyt i walidacja CSV
        content = await file.read()
        df = pd.read_csv(content.decode('utf-8'))
        
        if not validate_csv_structure(df):
            raise HTTPException(
                status_code=400,
                detail="Nieprawidłowa struktura CSV. Wymagane kolumny: src_ip, src_fqdn, src_port, protocol, dst_ip, dst_fqdn, dst_port, description"
            )

        if not validate_protocols(df):
            raise HTTPException(
                status_code=400,
                detail="Nieprawidłowe protokoły. Dozwolone wartości: TCP, UDP"
            )

        # Zapisanie pliku CSV
        os.makedirs('temp', exist_ok=True)
        csv_path = os.path.join('temp', 'network_policy.csv')
        df.to_csv(csv_path, index=False)

        # Uruchomienie kontenera Docker
        cmd = 'docker run -v "$(pwd):/src/" --rm -it --entrypoint /bin/bash cdrx/pyinstaller-windows:python3 -c "python -m pip install --upgrade pip && /entrypoint.sh"'
        
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Błąd podczas budowania exe: {e}")
            raise HTTPException(status_code=500, detail="Błąd podczas generowania pliku wykonywalnego")

        # Sprawdzenie czy plik exe został wygenerowany
        exe_path = "dist/windows/client_x86.exe"
        if not os.path.exists(exe_path):
            raise HTTPException(status_code=500, detail="Nie udało się wygenerować pliku wykonywalnego")

        # Przygotowanie nazwy pliku wynikowego
        output_filename = f"check_network_policies_{safe_client_name}.exe"
        output_path = os.path.join("output", output_filename)
        
        # Utworzenie katalogu output jeśli nie istnieje
        os.makedirs("output", exist_ok=True)
        
        # Skopiowanie pliku do katalogu output z nową nazwą
        shutil.copy2(exe_path, output_path)

        return FileResponse(
            output_path,
            media_type='application/octet-stream',
            filename=output_filename
        )

    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Wystąpił błąd: {str(e)}")

    finally:
        # Czyszczenie plików tymczasowych
        if os.path.exists('temp'):
            shutil.rmtree('temp')

