from fastapi import APIRouter, UploadFile, File, HTTPException
from langchain_community.document_loaders import PyPDFLoader, TextLoader
import tempfile
import os

router = APIRouter()

@router.post("/")
async def convert_file_to_text(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in [".pdf", ".txt"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        documents = []
        if file_extension == ".pdf":
            loader = PyPDFLoader(tmp_path)
            async for page in loader.alazy_load():
                documents.append(page)
        elif file_extension == ".txt":
            loader = TextLoader(tmp_path, autodetect_encoding=True)
            async for doc in loader.alazy_load():
                documents.append(doc)
        
        text = " ".join(doc.page_content for doc in documents)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    return {"text": text} 