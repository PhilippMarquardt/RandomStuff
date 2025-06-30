from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# This should be the same directory as in your other API files
DATA_DIR = Path("data").resolve()

@router.get("/{filename}")
async def get_data_file(filename: str):
    """
    Serves a file from the data directory, with security checks.
    """
    # Sanitize filename to prevent directory traversal
    safe_filename = Path(filename).name
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = DATA_DIR / safe_filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    # Security check: Ensure the resolved path is within the DATA_DIR
    if not file_path.resolve().is_relative_to(DATA_DIR):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(file_path) 