# app/routes/file_routes.py
from fastapi import APIRouter, Request, UploadFile, HTTPException, Form, File
from fastapi.responses import FileResponse, HTMLResponse
from ..dependencies import templates
from ..services.file_service import process_upload_file
from ..logging_config import setup_logging

router = APIRouter()
logger = setup_logging()

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        logger.info("Próba wyświetlenia strony głównej")
        return templates.TemplateResponse("upload.html", {"request": request})
    except Exception as e:
        logger.error(f"Błąd podczas renderowania strony głównej: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_file(filename: str):
    return await process_download_file(filename)

@router.post("/upload/")
async def upload_policy(
    request: Request,
    client_name: str = Form(...),
    file: UploadFile = File(...)
):
    return await process_upload_file(request, client_name, file)