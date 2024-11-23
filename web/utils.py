# app/utils/sanitizer.py
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

# app/utils/zip_utils.py
import os
import zipfile
from datetime import datetime
from ..config import OUTPUT_DIR

def create_zip_file(source_file: str, zip_filename: str, client_name: str, os_type: str) -> str:
    """
    Tworzy plik ZIP zawierający plik wykonywalny i dodatkowe informacje
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    zip_path = os.path.join(OUTPUT_DIR, zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Dodaj plik wykonywalny
        zipf.write(source_file, os.path.basename(source_file))
        
        # Dodaj plik README z informacjami
        readme_content = f"""Network Policy Checker ({os_type})
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