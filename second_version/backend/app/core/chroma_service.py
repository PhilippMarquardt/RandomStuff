import os
from typing import List, Tuple
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import logging
import shutil

if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] =

logger = logging.getLogger(__name__)

class ChromaService:
    """Service for handling ChromaDB vector store operations."""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        self.persist_directory = "./chroma_data"
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        os.makedirs(self.persist_directory, exist_ok=True)
    
    def _get_collection_path(self, collection_name: str) -> str:
        """Get the persistence path for a specific collection."""
        return os.path.join(self.persist_directory, collection_name)
    
    async def embed_text(
        self, 
        text_content: str, 
        filename: str, 
        content_type: str,
        collection_name: str
    ) -> Tuple[bool, str, int]:
        """
        Process text content and store embeddings in ChromaDB.
        
        Args:
            text_content: The text content of the file.
            filename: Name of the original file.
            content_type: MIME type of the original file.
            collection_name: Name of the ChromaDB collection.
            
        Returns:
            Tuple of (success, message, document_count)
        """
        try:
            if not text_content:
                return False, "No content provided to embed", 0

            # Create a single Document object from the text content
            doc = Document(page_content=text_content, metadata={"source": filename})

            # Split document into chunks
            text_chunks = self.text_splitter.split_documents([doc])
            
            if not text_chunks:
                return False, "No text chunks could be created from the document", 0
            
            # Add metadata to chunks
            for chunk in text_chunks:
                chunk.metadata.update({
                    "source_file": filename,
                    "content_type": content_type,
                    "collection": collection_name
                })
            
            collection_path = self._get_collection_path(collection_name)
            
            if os.path.exists(collection_path):
                vector_store = Chroma(
                    persist_directory=collection_path,
                    embedding_function=self.embeddings,
                    collection_name=collection_name
                )
                vector_store.add_documents(documents=text_chunks)
            else:
                vector_store = Chroma.from_documents(
                    documents=text_chunks,
                    embedding=self.embeddings,
                    persist_directory=collection_path,
                    collection_name=collection_name
                )
            
            logger.info(f"Successfully uploaded {len(text_chunks)} chunks from {filename} to collection {collection_name}")
            return True, f"Successfully processed and stored {len(text_chunks)} chunks", len(text_chunks)
                
        except Exception as e:
            logger.error(f"Error processing text from {filename}: {str(e)}")
            return False, f"Error processing text: {str(e)}", 0
    
    def list_collections(self) -> List[str]:
        """List all available ChromaDB collections."""
        try:
            collections = []
            
            # Check for existing collection directories
            if os.path.exists(self.persist_directory):
                for item in os.listdir(self.persist_directory):
                    item_path = os.path.join(self.persist_directory, item)
                    if os.path.isdir(item_path):
                        collections.append(item)
            
            # Always ensure we have a default collection
            if "default" not in collections:
                collections.append("default")
            
            return sorted(collections)
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            return ["default"]
    
    def delete_collection(self, collection_name: str) -> Tuple[bool, str]:
        """Delete a ChromaDB collection."""
        try:
            if collection_name == "default":
                return False, "Cannot delete the default collection"
            
            collection_path = self._get_collection_path(collection_name)
            
            if os.path.exists(collection_path):
                shutil.rmtree(collection_path)
                return True, f"Collection '{collection_name}' deleted successfully"
            else:
                return False, f"Collection '{collection_name}' does not exist"
                
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {str(e)}")
            return False, f"Error deleting collection: {str(e)}"
    
    def search_documents(
        self, 
        query: str, 
        collection_name: str, 
        k: int = 5
    ) -> List[Document]:
        """Search for similar documents in a collection."""
        try:
            collection_path = self._get_collection_path(collection_name)
            
            if not os.path.exists(collection_path):
                logger.warning(f"Collection '{collection_name}' does not exist")
                return []
            
            vector_store = Chroma(
                persist_directory=collection_path,
                embedding_function=self.embeddings,
                collection_name=collection_name
            )
            
            results = vector_store.similarity_search(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Error searching in collection {collection_name}: {str(e)}")
            return []

# Keep the old class name for backward compatibility
class MilvusService(ChromaService):
    """Backward compatibility alias for ChromaService."""
    pass 