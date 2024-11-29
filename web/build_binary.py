import os
import subprocess
import shutil
import logging
from fastapi import HTTPException
from config import BUILD_BASE_DIR

logger = logging.getLogger(__name__)

def build_windows(safe_client_name):
    """Generuje plik wykonywalny dla Windows."""
    logger.info(f"Rozpoczęcie generowania pliku wykonywalnego Windows dla klienta: {safe_client_name}")
    
    try:
        # Generowanie dla Windows
        cmd_windows = 'docker run -v /var/run/docker.sock:/var/run/docker.sock --volumes-from network_policies_container --privileged --network host --rm --entrypoint /bin/bash cdrx/pyinstaller-windows:python3 -c "python -m pip install --upgrade pip && /entrypoint.sh"'
        logger.debug(f"Wykonywanie komendy Docker dla Windows: {cmd_windows}")
        
        process_windows = subprocess.run(cmd_windows, shell=True, check=True, capture_output=True, text=True)
        logger.debug(f"Wynik procesu Windows - stdout: {process_windows.stdout}")
        logger.debug(f"Wynik procesu Windows - stderr: {process_windows.stderr}")
        
        # Sprawdzenie czy plik CLIENT exe został wygenerowany
        exe_client_path = os.path.join(BUILD_BASE_DIR, "dist/windows/client_x86.exe")
        logger.debug(f"Sprawdzanie istnienia pliku CLIENT exe pod ścieżką: {exe_client_path}")
        
        if not os.path.exists(exe_client_path):
            error_msg = "Nie udało się wygenerować pliku CLIENT wykonywalnego dla Windows"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # Sprawdzenie czy plik SERVER exe został wygenerowany
        exe_server_path = os.path.join(BUILD_BASE_DIR, "dist/windows/server_x86.exe")
        logger.debug(f"Sprawdzanie istnienia pliku SERVER exe pod ścieżką: {exe_server_path}")
        
        if not os.path.exists(exe_server_path):
            error_msg = "Nie udało się wygenerować pliku SERVER wykonywalnego dla Windows"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
                    
        # Przygotowanie nazw plików dla Windows
        output_client_filename_windows = f"check_network_policies_{safe_client_name}.exe"
        output_exe_client_path_windows = os.path.join("output", output_client_filename_windows)
        output_server_filename_windows = f"server_check_network_policies_{safe_client_name}.exe"
        output_exe_server_path_windows = os.path.join("output", output_server_filename_windows)
        
        try:
            shutil.copy2(exe_client_path, output_exe_client_path_windows)
            logger.info(f'Poprawnie skopiowano plik: {output_exe_client_path_windows}')
        except Exception as e:
            logger.error(f"Błąd podczas kopiowania pliku {output_exe_client_path_windows} : {str(e)}")

        try:
            shutil.copy2(exe_server_path, output_exe_server_path_windows)
            logger.info(f'Poprawnie skopiowano plik: {output_exe_server_path_windows}')
        except Exception as e:
            logger.error(f"Błąd podczas kopiowania pliku {output_exe_server_path_windows} : {str(e)}")
                    
        return output_exe_client_path_windows, output_exe_server_path_windows
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Błąd podczas wykonywania komendy Docker dla Windows: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Nieoczekiwany błąd podczas generowania pliku Windows: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

def build_linux(safe_client_name):
    """Generuje plik wykonywalny dla Linux."""
    logger.info(f"Rozpoczęcie generowania pliku wykonywalnego Linux dla klienta: {safe_client_name}")
    
    try:
        # Generowanie dla Linux
        cmd_linux = 'docker run -v /var/run/docker.sock:/var/run/docker.sock --volumes-from network_policies_container --privileged --network host --rm cdrx/pyinstaller-linux:python3'
        logger.debug(f"Wykonywanie komendy Docker dla Linux: {cmd_linux}")
        
        process_linux = subprocess.run(cmd_linux, shell=True, check=True, capture_output=True, text=True)
        logger.debug(f"Wynik procesu Linux - stdout: {process_linux.stdout}")
        logger.debug(f"Wynik procesu Linux - stderr: {process_linux.stderr}")
        
        # Sprawdzenie czy plik CLIENT dla Linuxa został wygenerowany
        linux_client_path = os.path.join(BUILD_BASE_DIR, "dist/linux/client_x86")
        logger.debug(f"Sprawdzanie istnienia pliku CLIENT Linux pod ścieżką: {linux_client_path}")
        
        if not os.path.exists(linux_client_path):
            error_msg = "Nie udało się wygenerować pliku CLIENT wykonywalnego dla Linux"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # Sprawdzenie czy plik SERVER dla Linuxa został wygenerowany
        linux_server_path = os.path.join(BUILD_BASE_DIR, "dist/linux/server_x86")
        logger.debug(f"Sprawdzanie istnienia pliku SERVER Linux pod ścieżką: {linux_server_path}")
        
        if not os.path.exists(linux_server_path):
            error_msg = "Nie udało się wygenerować pliku SERVER wykonywalnego dla Linux"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
        # Przygotowanie nazw plików dla Linux
        output_client_filename_linux = f"check_network_policies_{safe_client_name}"
        output_linux_client_path = os.path.join("output", output_client_filename_linux)
        output_server_filename_linux = f"server_check_network_policies_{safe_client_name}"
        output_linux_server_path = os.path.join("output", output_server_filename_linux)
        try:
            shutil.copy2(linux_client_path, output_linux_client_path)
            logger.info(f'Poprawnie skopiowano plik: {output_linux_client_path}')
        except Exception as e:
            logger.error(f"Błąd podczas kopiowania pliku {output_linux_client_path} : {str(e)}")
            
        try:
            shutil.copy2(linux_server_path, output_linux_server_path)
            logger.info(f'Poprawnie skopiowano plik: {output_linux_server_path}')
        except Exception as e:
            logger.error(f"Błąd podczas kopiowania pliku {output_linux_server_path} : {str(e)}")
        
        return output_linux_client_path, output_linux_server_path
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Błąd podczas wykonywania komendy Docker dla Linux: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Nieoczekiwany błąd podczas generowania pliku Linux: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

def build_executables(safe_client_name):
    """Generuje pliki wykonywalne dla obu systemów operacyjnych."""
    logger.info(f"Rozpoczęcie procesu generowania plików wykonywalnych dla klienta: {safe_client_name}")

    # Utworzenie katalogu output jeśli nie istnieje
    os.makedirs("output", exist_ok=True)    

    try:
        shutil.copy2("/web/network_policy.csv", "/src/network_policy.csv")
        logger.info(f'Poprawnie skopiowano plik: network_policy.csv')
    except Exception as e:
        logger.error(f"Błąd podczas kopiowania pliku network_policy.csv : {str(e)}")

    try:
        windows_client_file, windows_server_file = build_windows(safe_client_name)
        linux_client_file, linux_server_file = build_linux(safe_client_name)
        
        logger.info(f"Pomyślnie wygenerowano wszystkie pliki wykonywalne dla klienta: {safe_client_name}")
        return (windows_client_file, windows_server_file, linux_client_file, linux_server_file)
        
    except Exception as e:
        error_msg = f"Błąd podczas generowania plików wykonywalnych: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise