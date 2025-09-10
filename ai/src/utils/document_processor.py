"""
Document Processing Service using LangChain
Handles various document types with extensible architecture
"""
import os
import tempfile
import base64
from pathlib import Path
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod

try:
    # LangChain document loaders
    from langchain_community.document_loaders import (
        PyPDFLoader,
        Docx2txtLoader,
        UnstructuredPowerPointLoader,
        UnstructuredExcelLoader,
        TextLoader,
        UnstructuredMarkdownLoader,
        CSVLoader,
        UnstructuredHTMLLoader,
        UnstructuredXMLLoader,
        JSONLoader
    )
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("LangChain document loaders not available. Install required dependencies.")

try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not available for image processing. Install with: pip install Pillow")


class DocumentProcessorBase(ABC):
    """Base class for document processors"""
    
    @abstractmethod
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        """Check if this processor can handle the file"""
        pass
    
    @abstractmethod
    def process(self, file_path: str) -> List[Document]:
        """Process the document and return LangChain Documents"""
        pass


class PDFProcessor(DocumentProcessorBase):
    """PDF document processor"""
    
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        return file_path.lower().endswith('.pdf') or mime_type == 'application/pdf'
    
    def process(self, file_path: str) -> List[Document]:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available for PDF processing")
        
        loader = PyPDFLoader(file_path)
        return loader.load()


class DocxProcessor(DocumentProcessorBase):
    """Word document processor"""
    
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        return (file_path.lower().endswith('.docx') or 
                mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'])
    
    def process(self, file_path: str) -> List[Document]:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available for DOCX processing")
        
        loader = Docx2txtLoader(file_path)
        return loader.load()


class PowerPointProcessor(DocumentProcessorBase):
    """PowerPoint document processor"""
    
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        return (file_path.lower().endswith(('.ppt', '.pptx')) or 
                mime_type in ['application/vnd.ms-powerpoint', 
                             'application/vnd.openxmlformats-officedocument.presentationml.presentation'])
    
    def process(self, file_path: str) -> List[Document]:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available for PowerPoint processing")
        
        loader = UnstructuredPowerPointLoader(file_path)
        return loader.load()


class ExcelProcessor(DocumentProcessorBase):
    """Excel document processor"""
    
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        return (file_path.lower().endswith(('.xls', '.xlsx')) or 
                mime_type in ['application/vnd.ms-excel',
                             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'])
    
    def process(self, file_path: str) -> List[Document]:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available for Excel processing")
        
        loader = UnstructuredExcelLoader(file_path)
        return loader.load()


class TextProcessor(DocumentProcessorBase):
    """Text file processor"""
    
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        return (file_path.lower().endswith('.txt') or 
                mime_type == 'text/plain')
    
    def process(self, file_path: str) -> List[Document]:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available for text processing")
        
        loader = TextLoader(file_path)
        return loader.load()


class MarkdownProcessor(DocumentProcessorBase):
    """Markdown file processor"""
    
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        return (file_path.lower().endswith(('.md', '.markdown')) or 
                mime_type == 'text/markdown')
    
    def process(self, file_path: str) -> List[Document]:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available for Markdown processing")
        
        loader = UnstructuredMarkdownLoader(file_path)
        return loader.load()


class CSVProcessor(DocumentProcessorBase):
    """CSV file processor"""
    
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        return (file_path.lower().endswith('.csv') or 
                mime_type == 'text/csv')
    
    def process(self, file_path: str) -> List[Document]:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available for CSV processing")
        
        loader = CSVLoader(file_path)
        return loader.load()


class HTMLProcessor(DocumentProcessorBase):
    """HTML file processor"""
    
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        return (file_path.lower().endswith(('.html', '.htm')) or 
                mime_type == 'text/html')
    
    def process(self, file_path: str) -> List[Document]:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available for HTML processing")
        
        loader = UnstructuredHTMLLoader(file_path)
        return loader.load()


class JSONProcessor(DocumentProcessorBase):
    """JSON file processor"""
    
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        return (file_path.lower().endswith('.json') or 
                mime_type == 'application/json')
    
    def process(self, file_path: str) -> List[Document]:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available for JSON processing")
        
        loader = JSONLoader(file_path, jq_schema='.')
        return loader.load()


class ImageProcessor(DocumentProcessorBase):
    """Image file processor"""
    
    def can_process(self, file_path: str, mime_type: str = None) -> bool:
        image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')
        image_mime_types = ('image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp')
        
        return (file_path.lower().endswith(image_extensions) or 
                mime_type in image_mime_types)
    
    def process(self, file_path: str) -> List[Document]:
        if not PIL_AVAILABLE:
            raise ImportError("PIL not available for image processing")
        
        try:
            # Open and analyze the image
            with Image.open(file_path) as img:
                # Get image metadata
                width, height = img.size
                mode = img.mode
                format = img.format or 'Unknown'
                
                # Convert image to base64 for embedding
                with open(file_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                
                # Create document content with image description and data
                content = f"""Image File: {os.path.basename(file_path)}
Dimensions: {width} x {height} pixels
Color Mode: {mode}
Format: {format}

This is an image file that has been uploaded. The image data is available for analysis.
[Image data: data:image/{format.lower() if format != 'Unknown' else 'png'};base64,{image_data}]"""
                
                # Create metadata
                metadata = {
                    'source': file_path,
                    'filename': os.path.basename(file_path),
                    'image_width': width,
                    'image_height': height,
                    'image_mode': mode,
                    'image_format': format,
                    'file_type': 'image',
                    'base64_data': image_data
                }
                
                return [Document(page_content=content, metadata=metadata)]
                
        except Exception as e:
            # If image processing fails, create a basic document
            content = f"Image file: {os.path.basename(file_path)} (Error reading image: {str(e)})"
            metadata = {'source': file_path, 'filename': os.path.basename(file_path), 'file_type': 'image', 'error': str(e)}
            return [Document(page_content=content, metadata=metadata)]


class DocumentProcessingService:
    """Main service for processing various document types"""
    
    def __init__(self):
        # Register all available processors
        self.processors = [
            PDFProcessor(),
            DocxProcessor(),
            PowerPointProcessor(),
            ExcelProcessor(),
            TextProcessor(),
            MarkdownProcessor(),
            CSVProcessor(),
            HTMLProcessor(),
            JSONProcessor(),
            ImageProcessor()
        ]
        
        # Text splitter for chunking large documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        ) if LANGCHAIN_AVAILABLE else None
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        extensions = []
        test_files = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.csv': 'text/csv',
            '.html': 'text/html',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        
        for ext, mime_type in test_files.items():
            for processor in self.processors:
                if processor.can_process(f"test{ext}", mime_type):
                    extensions.append(ext)
                    break
        
        return extensions
    
    def can_process_file(self, file_path: str, mime_type: str = None) -> bool:
        """Check if the file can be processed"""
        for processor in self.processors:
            if processor.can_process(file_path, mime_type):
                return True
        return False
    
    def process_file(self, file_path: str, mime_type: str = None, 
                     chunk_documents: bool = True) -> Dict[str, Any]:
        """
        Process a file and return structured document data
        
        Args:
            file_path: Path to the file
            mime_type: MIME type of the file (optional)
            chunk_documents: Whether to split large documents into chunks
            
        Returns:
            Dict containing processed document information
        """
        if not LANGCHAIN_AVAILABLE:
            return {
                'success': False,
                'error': 'LangChain document processing not available',
                'documents': [],
                'metadata': {}
            }
        
        # Find appropriate processor
        processor = None
        for proc in self.processors:
            if proc.can_process(file_path, mime_type):
                processor = proc
                break
        
        if not processor:
            return {
                'success': False,
                'error': f'No processor found for file: {file_path}',
                'documents': [],
                'metadata': {}
            }
        
        try:
            # Process the document
            documents = processor.process(file_path)
            
            # Chunk documents if requested and they're large
            if chunk_documents and self.text_splitter:
                chunked_docs = []
                for doc in documents:
                    if len(doc.page_content) > 1000:
                        chunks = self.text_splitter.split_documents([doc])
                        chunked_docs.extend(chunks)
                    else:
                        chunked_docs.append(doc)
                documents = chunked_docs
            
            # Clean document content to handle encoding issues
            cleaned_documents = []
            for doc in documents:
                # Aggressively clean the content to handle all encoding issues
                try:
                    content = doc.page_content
                    # Remove all non-ASCII characters that might cause issues
                    content = content.encode('ascii', errors='ignore').decode('ascii')
                    # If content becomes too short, try a gentler approach
                    if len(content) < len(doc.page_content) * 0.8:  # Lost more than 20% of content
                        # Use UTF-8 with replacement
                        content = doc.page_content.encode('utf-8', errors='replace').decode('utf-8')
                        # Replace specific problematic Unicode characters
                        content = content.replace('\u2640', 'female').replace('\u2642', 'male')
                        content = content.replace('\u2013', '-').replace('\u2014', '-')  # en/em dashes
                        content = content.replace('\u201c', '"').replace('\u201d', '"')  # smart quotes
                        content = content.replace('\u2018', "'").replace('\u2019', "'")  # smart apostrophes
                    
                    doc.page_content = content
                    cleaned_documents.append(doc)
                except Exception as e:
                    # If cleaning fails, create a simple fallback content
                    fallback_content = f"Document content could not be processed due to encoding issues: {str(e)}"
                    doc.page_content = fallback_content
                    cleaned_documents.append(doc)
            
            documents = cleaned_documents
            
            # Extract metadata
            file_info = {
                'filename': os.path.basename(file_path),
                'file_size': os.path.getsize(file_path),
                'processor_type': processor.__class__.__name__,
                'num_documents': len(documents),
                'total_characters': sum(len(doc.page_content) for doc in documents)
            }
            
            return {
                'success': True,
                'error': None,
                'documents': documents,
                'metadata': file_info
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing file: {str(e)}',
                'documents': [],
                'metadata': {}
            }
    
    def save_uploaded_file(self, uploaded_file_content: bytes, filename: str) -> str:
        """Save uploaded file to temporary location"""
        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(tempfile.gettempdir(), 'coreai_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate unique filename
        file_path = os.path.join(temp_dir, filename)
        counter = 1
        while os.path.exists(file_path):
            name, ext = os.path.splitext(filename)
            file_path = os.path.join(temp_dir, f"{name}_{counter}{ext}")
            counter += 1
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(uploaded_file_content)
        
        return file_path
    
    def cleanup_file(self, file_path: str):
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning up file {file_path}: {e}")
    
    def get_document_summary(self, documents: List[Document]) -> str:
        """Generate a summary of the processed documents"""
        if not documents:
            return "No content found in the document."
        
        total_chars = sum(len(doc.page_content) for doc in documents)
        num_pages = len(documents)
        
        # Sample content from first few documents
        sample_content = ""
        for i, doc in enumerate(documents[:3]):  # First 3 chunks/pages
            content = doc.page_content.strip()
            if content:
                sample_content += f"Section {i+1}: {content[:200]}...\n\n"
        
        summary = f"""Document processed successfully:
- Number of sections/pages: {num_pages}
- Total characters: {total_chars:,}
- Sample content:

{sample_content}

This document is now available for analysis and questions."""
        
        return summary


# Global service instance
document_service = DocumentProcessingService()