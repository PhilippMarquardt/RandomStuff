import os
import tempfile
from typing import List, Tuple
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader, 
    Docx2txtLoader
)
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
        # Use ChromaDB with local persistence
        self.persist_directory = "./chroma_data"
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        # Ensure persist directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
    
    def _get_document_loader(self, file_path: str, file_type: str):
        """Get appropriate document loader based on file type."""
        try:
            # Get file extension for better type detection
            file_extension = os.path.splitext(file_path)[1].lower()
            
            # Determine file type based on extension if content_type is unreliable
            if file_type == "text/plain" or file_type is None or file_extension in ['.txt', '.py', '.js', '.html', '.css', '.md', '.json', '.xml', '.csv']:
                # Try different encodings for text files
                return TextLoader(file_path, encoding='utf-8')
            elif file_type == "application/pdf" or file_extension == '.pdf':
                return PyPDFLoader(file_path)
            elif (file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                              "application/msword"] or file_extension in ['.docx', '.doc']):
                return Docx2txtLoader(file_path)
            else:
                # For unknown types, try text loader with utf-8 encoding
                return TextLoader(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            # If UTF-8 fails, try with different encodings
            try:
                return TextLoader(file_path, encoding='latin-1')
            except:
                # Last resort - try with error handling
                return TextLoader(file_path, encoding='utf-8', autodetect_encoding=True)
    
    def _get_collection_path(self, collection_name: str) -> str:
        """Get the persistence path for a specific collection."""
        return os.path.join(self.persist_directory, collection_name)
    
    async def upload_and_embed_file(
        self, 
        file_content: bytes, 
        filename: str, 
        content_type: str,
        collection_name: str
    ) -> Tuple[bool, str, int]:
        """
        Upload a file, process it, and store embeddings in ChromaDB.
        
        Args:
            file_content: The file content as bytes
            filename: Name of the uploaded file
            content_type: MIME type of the file
            collection_name: Name of the ChromaDB collection to store embeddings
            
        Returns:
            Tuple of (success, message, document_count)
        """
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            try:
                # Load the document
                loader = self._get_document_loader(temp_file_path, content_type)
                
                try:
                    documents = loader.load()
                except Exception as load_error:
                    # If loading fails, try with autodetect encoding
                    logger.warning(f"Initial load failed for {filename}: {str(load_error)}. Trying with autodetect encoding.")
                    try:
                        if content_type == "text/plain" or content_type is None:
                            loader = TextLoader(temp_file_path, autodetect_encoding=True)
                            documents = loader.load()
                        else:
                            raise load_error
                    except Exception as retry_error:
                        logger.error(f"Failed to load document {filename} even with autodetect: {str(retry_error)}")
                        return False, f"Error loading {filename}: Could not decode file. Please ensure it's a valid text file.", 0
                
                if not documents:
                    return False, "No content could be extracted from the file", 0
                
                # Split documents into chunks
                text_chunks = self.text_splitter.split_documents(documents)
                
                if not text_chunks:
                    return False, "No text chunks could be created from the document", 0
                
                # Add metadata to chunks
                for chunk in text_chunks:
                    chunk.metadata.update({
                        "source_file": filename,
                        "content_type": content_type,
                        "collection": collection_name
                    })
                
                # Get collection persistence path
                collection_path = self._get_collection_path(collection_name)
                
                # Check if collection already exists
                if os.path.exists(collection_path):
                    # Load existing collection and add documents
                    vector_store = Chroma(
                        persist_directory=collection_path,
                        embedding_function=self.embeddings,
                        collection_name=collection_name
                    )
                    vector_store.add_documents(documents=text_chunks)
                else:
                    # Create new collection
                    vector_store = Chroma.from_documents(
                        documents=text_chunks,
                        embedding=self.embeddings,
                        persist_directory=collection_path,
                        collection_name=collection_name
                    )
                
                
                logger.info(f"Successfully uploaded {len(text_chunks)} chunks from {filename} to collection {collection_name}")
                return True, f"Successfully processed and stored {len(text_chunks)} chunks", len(text_chunks)
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}")
            return False, f"Error processing file: {str(e)}", 0
    
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