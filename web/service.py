# service.py
import pandas as pd
import io
from fastapi import HTTPException
from fastapi.responses import FileResponse
import utils
from config import OUTPUT_DIR, BASE_DIR
from config import templates
import os
import routes
import logging
from build_binary import build_executables

logger = logging.getLogger(__name__)

async def validate_csv_structure(df: pd.DataFrame) -> bool:
    """
    Sprawdza poprawność struktury pliku CSV.
    Zwraca True jeśli struktura jest prawidłowa, w przeciwnym razie rzuca wyjątek.
    """
    required_columns = ['src_ip', 'src_fqdn', 'src_port', 'protocol', 'dst_ip', 'dst_fqdn', 'dst_port']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        error_msg = f"Brakujące wymagane kolumny: {', '.join(missing_columns)}"
        logger.error(f"Błąd walidacji struktury CSV: {error_msg}")
        raise ValueError(error_msg)
    
    # Sprawdzanie czy są puste wartości
    null_counts = df.isnull().sum()
    if null_counts.any():
        null_columns = [f"{col}: {count}" for col, count in null_counts.items() if count > 0]
        error_msg = f"Znaleziono puste wartości w kolumnach: {', '.join(null_columns)}"
        logger.warning(f"Ostrzeżenie podczas walidacji CSV: {error_msg}")
    
    logger.info("Pomyślnie zwalidowano strukturę CSV")
    return True


async def process_upload_file(request, client_name, file):
    """
    Przetwarza przesłany plik CSV i generuje pliki wykonywalne.
    """
    logger.info(f"Rozpoczęto przetwarzanie pliku dla klienta: {client_name}")
    
    try:
        # Walidacja nazwy klienta
        if not client_name or len(client_name.strip()) == 0:
            error_msg = "Nazwa klienta nie może być pusta"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        logger.debug(f"Rozpoczęto odczyt pliku: {file.filename}")
        
        try:
            content = await file.read()
            logger.debug(f"Odczytano {len(content)} bajtów")
        except Exception as e:
            logger.error(f"Błąd podczas odczytu pliku: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Błąd odczytu pliku: {str(e)}")

        try:
            csv_data = io.StringIO(content.decode('utf-8'))
        except UnicodeDecodeError as e:
            logger.error(f"Błąd dekodowania pliku CSV: {str(e)}")
            raise HTTPException(status_code=400, detail="Plik musi być zakodowany w UTF-8")

        try:
            df = pd.read_csv(csv_data)
            logger.info(f"Wczytano CSV z {len(df)} wierszami i {len(df.columns)} kolumnami")
        except pd.errors.EmptyDataError:
            logger.error("Przesłano pusty plik CSV")
            raise HTTPException(status_code=400, detail="Przesłany plik CSV jest pusty")
        except pd.errors.ParserError as e:
            logger.error(f"Błąd parsowania CSV: {str(e)}")
            raise HTTPException(status_code=400, detail="Nieprawidłowy format pliku CSV")

        # Walidacja struktury CSV
        try:
            await validate_csv_structure(df)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Zapis CSV
        csv_path = os.path.join(BASE_DIR, 'network_policy.csv')
        try:
            df.to_csv(csv_path, index=False)
            logger.info(f"Zapisano plik CSV do {csv_path}")
        except Exception as e:
            logger.error(f"Błąd podczas zapisu CSV: {str(e)}")
            raise HTTPException(status_code=500, detail="Nie udało się zapisać pliku CSV")

        # Sanityzacja nazwy klienta
        safe_client_name = utils.sanitize_client_name(client_name)
        logger.debug(f"Nazwa klienta po sanityzacji: {safe_client_name}")

        # Budowanie plików wykonywalnych
        try:
            logger.info("Rozpoczęto budowanie plików wykonywalnych")
            windows_client_path, windows_server_path, linux_client_path, linux_server_path = build_executables(safe_client_name)
            logger.info(f"Pomyślnie zbudowano pliki wykonywalne: Windows: {windows_client_path}, {windows_server_path}, Linux: {linux_client_path}, {linux_server_path}.")
        except Exception as e:
            logger.error(f"Błąd podczas budowania plików wykonywalnych: {str(e)}")
            raise HTTPException(status_code=500, detail="Błąd podczas generowania plików wykonywalnych")

        # Tworzenie plików ZIP
        try:
            zip_filename_windows = f"check_network_policies_{safe_client_name}_windows.zip"
            zip_filename_linux = f"check_network_policies_{safe_client_name}_linux.zip"
                    
            windows_files = {
                'client': windows_client_path,
                'server': windows_server_path
            }
            zip_path_windows = utils.create_zip_file(
                files=windows_files,
                zip_filename=zip_filename_windows,
                client_name=client_name,
                os_type="Windows"
            )
            
            # Create Linux ZIP with both client and server files
            linux_files = {
                'client': linux_client_path,
                'server': linux_server_path
            }
            zip_path_linux = utils.create_zip_file(
                files=linux_files,
                zip_filename=zip_filename_linux,
                client_name=client_name,
                os_type="Linux"
            )
            
            logger.info(f"Utworzono pliki ZIP: {zip_path_windows}, {zip_path_linux}")
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia plików ZIP: {str(e)}")
            raise HTTPException(status_code=500, detail="Błąd podczas pakowania plików")

        # Przygotowanie odpowiedzi
        logger.info("Zakończono przetwarzanie pliku pomyślnie")
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd podczas przetwarzania pliku: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Wystąpił nieoczekiwany błąd: {str(e)}")


async def process_download_file(filename: str):
    """Endpoint do pobierania wygenerowanego pliku"""
    file_path = os.path.join("output", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Plik nie został znaleziony")
    return FileResponse(
        file_path,
        media_type='application/zip',
        filename=filename
    )