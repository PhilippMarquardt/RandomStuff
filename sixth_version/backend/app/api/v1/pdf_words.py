from fastapi import APIRouter, UploadFile, File, HTTPException
from services.pymupdf_service import PyMuPDFService
import tempfile
import os

router = APIRouter()

@router.post("/extract-words")
async def extract_pdf_words(file: UploadFile = File(...)):
    """
    Extract word-level bounding boxes from PDF using PyMuPDF.
    Returns structured data with word positions for each page.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # Read file content as bytes
        pdf_bytes = await file.read()
        
        # Use PyMuPDF service to extract words with bounding boxes
        service = PyMuPDFService()
        result = service.extract_words_with_bbox(pdf_bytes)
        
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}") 