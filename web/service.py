# app/services/file_service.py
import pandas as pd
import io
from fastapi import HTTPException
from fastapi.responses import FileResponse
from ..utils.sanitizer import sanitize_client_name
from ..utils.zip_utils import create_zip_file
from ..dependencies import templates
from ..config import OUTPUT_DIR
from .build_service import build_executables
import os

async def process_upload_file(request, client_name, file):
    try:
        # Read and validate CSV
        content = await file.read()
        csv_data = io.StringIO(content.decode('utf-8'))
        df = pd.read_csv(csv_data)
        
        # Save CSV file
        csv_path = os.path.join('/src', 'network_policy.csv')
        df.to_csv(csv_path, index=False)
        
        # Sanitize client name
        safe_client_name = sanitize_client_name(client_name)
        
        # Build executables
        windows_path, linux_path = build_executables(safe_client_name)
        
        # Create ZIP files
        zip_filename_windows = f"check_network_policies_{safe_client_name}_windows.zip"
        zip_filename_linux = f"check_network_policies_{safe_client_name}_linux.zip"
        
        zip_path_windows = create_zip_file(windows_path, zip_filename_windows, client_name, "Windows")
        zip_path_linux = create_zip_file(linux_path, zip_filename_linux, client_name, "Linux")
        
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
        raise HTTPException(status_code=500, detail=str(e))

# app/services/build_service.py
import subprocess
import os
from fastapi import HTTPException

def build_executables(safe_client_name):
    try:
        # Build Windows executable
        cmd_windows = 'docker run -v /var/run/docker.sock:/var/run/docker.sock --volumes-from network_policies_container --privileged  --network host --rm --entrypoint /bin/bash cdrx/pyinstaller-windows:python3 -c "python -m pip install --upgrade pip && /entrypoint.sh"'
        subprocess.run(cmd_windows, shell=True, check=True, capture_output=True, text=True)
        
        # Build Linux executable
        cmd_linux = 'docker run -v /var/run/docker.sock:/var/run/docker.sock --volumes-from network_policies_container --privileged --network host --rm cdrx/pyinstaller-linux:python3'
        subprocess.run(cmd_linux, shell=True, check=True, capture_output=True, text=True)
        
        # Verify and return paths
        windows_path = os.path.join("dist", "windows", "client_x86.exe")
        linux_path = os.path.join("dist", "linux", "client_x86")
        
        if not os.path.exists(windows_path) or not os.path.exists(linux_path):
            raise HTTPException(status_code=500, detail="Błąd podczas generowania plików wykonywalnych")
            
        return windows_path, linux_path
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Błąd podczas budowania: {str(e)}")
    