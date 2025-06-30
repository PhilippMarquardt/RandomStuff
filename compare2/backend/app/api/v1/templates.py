from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any, List
import json
import os
import logging
from pathlib import Path
import shutil
import fitz  # PyMuPDF
import pymupdf4llm
from services.pdf_comparison_service import get_first_headline

router = APIRouter()
logger = logging.getLogger(__name__)

# Define the directory to save templates and PDFs
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

@router.post("/save-template")
async def save_template(
    template_file: UploadFile = File(...), 
    pdf_file: UploadFile = File(...)
):
    """
    Receives a workflow template as a file and its corresponding PDF, 
    saves both to the server, and links the PDF inside the template file.
    """
    try:
        template_content = await template_file.read()
        template = json.loads(template_content)
        document_name = pdf_file.filename
        
        if not document_name or not template:
            raise HTTPException(status_code=400, detail="Missing document name or template data")

        # Sanitize the document name to create a valid filename
        safe_doc_name = "".join(c for c in document_name if c.isalnum() or c in ('.', '_')).rstrip()
        pdf_savename = f"SRC-{Path(safe_doc_name).stem}.pdf"
        template_filename = f"workflow-{Path(safe_doc_name).stem}.json"
        
        pdf_save_path = DATA_DIR / pdf_savename
        template_save_path = DATA_DIR / template_filename
        
        # Save the PDF file
        logger.info(f"Saving PDF to: {pdf_save_path}")
        with pdf_save_path.open("wb") as buffer:
            shutil.copyfileobj(pdf_file.file, buffer)
            
        # Add a link to the PDF in the template data
        template['source_pdf'] = str(pdf_save_path)
        
        # --- Inject headline extraction logic ---
        try:
            logger.info(f"Extracting page headlines from {pdf_save_path}...")
            doc = fitz.open(pdf_save_path)
            
            page_markdown_cache = {}
            updated_annotation_boxes = []

            for box in template.get("annotationBoxes", []):
                page_num = box.get('page')
                if page_num is None:
                    updated_annotation_boxes.append(box)
                    continue
                
                page_index = page_num - 1
                
                if page_index not in page_markdown_cache:
                    try:
                        markdown_text = pymupdf4llm.to_markdown(doc, pages=[page_index])
                        page_markdown_cache[page_index] = markdown_text
                    except Exception as e:
                        logger.error(f"Could not extract markdown for page {page_num}: {e}")
                        page_markdown_cache[page_index] = ""

                headline = get_first_headline(page_markdown_cache[page_index])
                
                if headline:
                    if 'settings' not in box:
                        box['settings'] = {}
                    box['settings']['pageHeadline'] = headline
                    logger.info(f"Found and saved headline for page {page_num}: '{headline}'")
                
                updated_annotation_boxes.append(box)

            # Replace the old list with the new one containing headlines
            template['annotationBoxes'] = updated_annotation_boxes
            doc.close()
        except Exception as e:
            logger.error(f"Failed to process PDF for headline extraction: {e}", exc_info=True)
            # We can choose to continue without headlines or raise an error
            # For now, we log the error and save the template without headlines
       
        # Save the template file (now with headlines)
        logger.info(f"Saving template to: {template_save_path}")
        with open(template_save_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
            
        return {
            "message": "Template and PDF saved successfully", 
            "template_path": str(template_save_path),
            "pdf_path": str(pdf_save_path)
        }

    except json.JSONDecodeError:
        logger.error("Invalid JSON format for template data")
        raise HTTPException(status_code=400, detail="Invalid JSON format for template data")
    except Exception as e:
        logger.error(f"Error saving template and PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save template and PDF: {str(e)}")

@router.get("/list-templates")
async def list_templates():
    """
    Scans the data directory for workflow templates and returns a list of them
    with their metadata.
    """
    templates = []
    for file_path in DATA_DIR.glob("workflow-*.json"):
        try:
            with file_path.open('r', encoding='utf-8') as f:
                template_data = json.load(f)
                
                # Get headline from the first annotation box for preview if available
                first_box_headline = None
                first_box = template_data.get("annotationBoxes", [])
                if first_box:
                    first_box_headline = first_box[0].get("settings", {}).get("pageHeadline")

                templates.append({
                    "filename": file_path.name,
                    "document": template_data.get("document"),
                    "export_date": template_data.get("exportDate"),
                    "source_pdf": template_data.get("source_pdf"),
                    "box_count": len(template_data.get("annotationBoxes", [])),
                    "headline_preview": first_box_headline
                })
        except Exception as e:
            logger.error(f"Error reading template file {file_path.name}: {e}")
            continue # Skip corrupted files
    
    return templates 

@router.get("/{template_name}")
async def get_template(template_name: str):
    """
    Retrieves a specific workflow template by its filename.
    """
    # Sanitize filename to prevent directory traversal
    safe_name = Path(template_name).name
    if not safe_name == template_name or not safe_name.startswith("workflow-"):
        raise HTTPException(status_code=400, detail="Invalid filename format")

    file_path = DATA_DIR / safe_name
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
        
    try:
        with file_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading template file {file_path.name}: {e}")
        raise HTTPException(status_code=500, detail="Could not read template file") 