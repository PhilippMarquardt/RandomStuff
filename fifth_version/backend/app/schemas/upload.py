from pydantic import BaseModel
from typing import Optional, List, Any


class UploadResponse(BaseModel):
    """Response model for file upload."""
    success: bool
    message: str
    filename: str
    collection_name: str
    document_count: int


class CollectionResponse(BaseModel):
    """Response model for collection operations."""
    collections: List[str]


class DeleteCollectionResponse(BaseModel):
    """Response model for collection deletion."""
    success: bool
    message: str


class SearchResult(BaseModel):
    """Individual search result."""
    content: str
    metadata: dict
    score: float = 0.0


class SearchResponse(BaseModel):
    """Response model for document search."""
    query: str
    collection_name: str
    results: List[SearchResult]
    total_results: int 