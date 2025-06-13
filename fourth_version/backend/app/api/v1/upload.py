from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging
from pathlib import Path
from pydantic import BaseModel
from schemas.upload import UploadResponse, CollectionResponse, DeleteCollectionResponse
from core.chroma_service import ChromaService
from .convert import convert_file_to_text

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize the ChromaDB service
chroma_service = ChromaService()

class SearchRequest(BaseModel):
    query: str
    collection_name: str = "default"
    k: int = 5

@router.get("/collections", response_model=List[str])
async def list_collections():
    """List all available collections."""
    try:
        collections = chroma_service.list_collections()
        return collections
    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing collections: {str(e)}")

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    collection_name: str = Form(default="default")
):
    """Upload a file, convert it to text, and store its embeddings in ChromaDB."""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # 1. Convert file to text using the converter function
        conversion_result = await convert_file_to_text(file)
        text_content = conversion_result.get("text")

        if not text_content:
            raise HTTPException(status_code=400, detail="Could not extract text from file.")

        # Ensure the file pointer is at the beginning if we need to re-read it.
        # This is important because convert_file_to_text has already read the stream.
        await file.seek(0)
        
        # 2. Embed the extracted text using the refactored chroma_service
        success, message, doc_count = await chroma_service.embed_text(
            text_content=text_content,
            filename=file.filename,
            content_type=file.content_type or "text/plain",
            collection_name=collection_name
        )
        
        if success:
            return UploadResponse(
                success=True,
                message=message,
                filename=file.filename,
                collection_name=collection_name,
                document_count=doc_count
            )
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """Delete a collection."""
    try:
        success, message = chroma_service.delete_collection(collection_name)
        if success:
            return DeleteCollectionResponse(success=True, message=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting collection {collection_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting collection: {str(e)}")

@router.post("/search")
async def search_documents(request: SearchRequest):
    """Search for similar documents in a collection."""
    try:
        results = chroma_service.search_documents(
            query=request.query,
            collection_name=request.collection_name,
            k=request.k
        )
        
        # Convert results to JSON-serializable format
        search_results = []
        for doc in results:
            search_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": getattr(doc, 'score', 0.0)  # Some vector stores include scores
            })
        
        return {
            "query": request.query,
            "collection_name": request.collection_name,
            "results": search_results,
            "total_results": len(search_results)
        }
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}") 