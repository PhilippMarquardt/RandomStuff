from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from services.pymupdf_service import PyMuPDFService
from schemas.pdf import ImageRegionRequest
import tempfile
import os
import json
from starlette.responses import StreamingResponse
import io
from pathlib import Path
import fitz

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


@router.post("/extract-text-with-layout")
async def extract_text_with_layout(
    file: UploadFile = File(...),
    page_num: int = Form(...),
    bbox: str = Form(...)
):
    """
    Extract text with layout from a specific region of a PDF page.
    """
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="A PDF file is required.")
    
    try:
        # Parse bbox
        bbox_list = json.loads(bbox)
        if len(bbox_list) != 4:
            raise ValueError("Bbox must contain exactly 4 values")
        
        pdf_bytes = await file.read()
        service = PyMuPDFService()
        
        # Extract text with layout
        text = service.extract_text_with_layout(
            pdf_bytes=pdf_bytes,
            page_num=page_num - 1,  # Convert to 0-based index
            bbox=tuple(bbox_list)
        )
        
        return {"text": text}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid bbox format.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")

@router.post("/extract-image-region")
async def extract_image_from_region(
    file: UploadFile = File(...),
    region_data_str: str = Form(...)
):
    """
    Extract a specific region from a PDF page as a base64 encoded image.
    The file is uploaded as multipart/form-data, and the region data is a JSON string.
    """
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="A PDF file is required.")

    try:
        # Parse the JSON string for region data
        region_data = ImageRegionRequest.parse_raw(region_data_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid region data format.")

    try:
        pdf_bytes = await file.read()
        
        service = PyMuPDFService()
        base64_image = service.extract_image_from_region(
            pdf_bytes=pdf_bytes,
            page_number=region_data.page_number,
            bbox=region_data.bbox
        )
        
        return {"image": base64_image}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting image: {str(e)}")

@router.get("/thumbnail", response_class=StreamingResponse)
async def get_pdf_thumbnail(file_path: str):
    """
    Generates a thumbnail for the first page of a PDF.
    """
    if not os.path.isabs(file_path):
        # Prevent directory traversal attacks
        base_path = Path(".").resolve()
        full_path = (base_path / file_path).resolve()
        if base_path not in full_path.parents:
            raise HTTPException(status_code=400, detail="Invalid file path")
    else:
        full_path = Path(file_path)

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="PDF file not found")
        
    try:
        doc = fitz.open(full_path)
        page = doc.load_page(0)  # Load the first page
        
        # Create a pixmap (thumbnail)
        pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2)) # Scale down to 20%
        doc.close()
        
        img_bytes = pix.tobytes("png")
        
        return StreamingResponse(io.BytesIO(img_bytes), media_type="image/png")

    except Exception as e:
        logger.error(f"Failed to generate thumbnail for {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate thumbnail") 