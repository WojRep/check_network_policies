# utils.py
import re
import logging

logger = logging.getLogger(__name__)

def sanitize_client_name(client_name: str) -> str:
    """Oczyszcza nazwę klienta z niedozwolonych znaków."""
    logger.debug(f"Sanityzacja nazwy klienta: {client_name}")
    sanitized = re.sub(r'[^\w\s-]', '', client_name)
    sanitized = sanitized.replace(' ', '_')
    sanitized = sanitized.strip('_')
    logger.debug(f"Nazwa po sanityzacji: {sanitized}")
    return sanitized


import os
import zipfile
from datetime import datetime
from config import OUTPUT_DIR
from typing import Union, Dict

def create_zip_file(
    files: Union[str, Dict[str, str]], 
    zip_filename: str, 
    client_name: str, 
    os_type: str
) -> str:
    """
    Tworzy plik ZIP zawierający jeden lub więcej plików wykonywalnych i dodatkowe informacje
    
    Args:
        source_file: Ścieżka do pliku lub słownik ścieżek {'client': path, 'server': path}
        zip_filename: Nazwa tworzonego pliku ZIP
        client_name: Nazwa klienta
        os_type: Typ systemu operacyjnego ('Windows' lub 'Linux')
        
    Returns:
        str: Ścieżka do utworzonego pliku ZIP
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    zip_path = os.path.join(OUTPUT_DIR, zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Dodawanie plików do archiwum
        if isinstance(files, dict):
            files_info = []
            for file_type, file_path in files.items():
                base_name = os.path.basename(file_path)
                zipf.write(file_path, base_name)
                files_info.append(f"- {file_type.capitalize()}: {base_name}")
        else:
            base_name = os.path.basename(files)
            zipf.write(files, base_name)
            files_info = [f"- Executable: {base_name}"]
            
        # Tworzenie zawartości README
        files_section = "\n".join(files_info)
        execution_instructions = {
            "Windows": "Double click the .exe file",
            "Linux": "Make the file executable with 'chmod +x' and run it from terminal"
        }
        
        readme_content = f"""Network Policy Checker ({os_type})
Generated for: {client_name}
Generation date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
System: {os_type}

Included files:
{files_section}

Instructions:
1. Extract all files from the archive
2. Run the program(s) to check network policies
- {execution_instructions[os_type]}
3. Review the results

For support contact your system administrator.
"""
        zipf.writestr('README.txt', readme_content)
        
    return zip_path