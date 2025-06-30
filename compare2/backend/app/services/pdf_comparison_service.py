import os
import fitz  # PyMuPDF
import json
import pymupdf4llm
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from app.services.chat_models import chat_model_registry
from langchain_core.messages import HumanMessage, SystemMessage
import base64
import logging
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

def get_first_headline(markdown_text: str) -> str | None:
    """
    Returns the first line that is either:
      - a markdown heading (starts with '#'), or
      - a standalone bold line (starts and ends with '**').
    Strips away the markdown syntax and returns just the inner text.
    """
    for line in markdown_text.splitlines():
        # Look for a standard MD heading
        m = re.match(r'^\s*#+\s*(.+)$', line)
        if m:
            return m.group(1).strip()

        # Look for a standalone bold line like **Headline**
        m2 = re.match(r'^\s*\*\*(.+?)\*\*\s*$', line)
        if m2:
            return m2.group(1).strip()

    return None  # no headline found

def clean_headline_for_matching(headline: str) -> str:
    """Remove markdown formatting characters from headline for matching"""
    if not headline:
        return ""
    
    # Remove strikethrough markers (~~)
    cleaned = headline.replace("~~", "")
    
    # Remove bold markers (**)
    cleaned = cleaned.replace("**", "")
    
    # Remove any multiple spaces and normalize
    cleaned = " ".join(cleaned.split())
    
    return cleaned.strip().lower()

@dataclass
class ComparisonResult:
    """Represents the result of comparing a single annotation box"""
    box_id: str
    box_type: str
    comparison_type: str
    status: str  # 'match', 'mismatch', 'error', 'not_found'
    details: Dict[str, Any]
    llm_response: Optional[str] = None
    error_message: Optional[str] = None

class PDFComparisonEngine:
    """Main engine for comparing PDFs based on annotation templates"""
    
    def __init__(self, workflow_path: str, pdf1_path: str, pdf2_path: str, debug_mode: bool = False, include_reference_image: bool = False, use_headline: bool = False, parallel_boxes: int = 1):
        self.workflow_path = workflow_path
        self.pdf1_path = pdf1_path
        self.pdf2_path = pdf2_path
        self.workflow = None
        self.doc1 = None
        self.doc2 = None
        self.results: List[ComparisonResult] = []
        self.debug_mode = debug_mode
        self.include_reference_image = include_reference_image
        self.use_headline = use_headline
        self.parallel_boxes = max(1, parallel_boxes)  # Ensure at least 1
        self.debug_dir = None
        
        # Thread lock for results list
        self.results_lock = threading.Lock()
        
        # Thread locks for cache operations
        self.page_cache_lock = threading.Lock()
        self.headline_cache_lock = threading.Lock()
        
        # Cache for full document markdown text
        self.full_text_doc1_md: Optional[str] = None
        self.full_text_doc2_md: Optional[str] = None
        
        # Cache for individual page markdown text
        self.page_cache_doc1: Dict[int, str] = {}  # page_num -> markdown text
        self.page_cache_doc2: Dict[int, str] = {}  # page_num -> markdown text
        
        # Cache for page headlines
        self.headline_cache_doc1: Dict[int, Optional[str]] = {}  # page_num -> headline
        self.headline_cache_doc2: Dict[int, Optional[str]] = {}  # page_num -> headline
        
        if self.debug_mode:
            # Create debug directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.debug_dir = f"debug_comparison_{timestamp}"
            os.makedirs(self.debug_dir, exist_ok=True)
            logger.info(f"Debug mode enabled. Images will be saved to: {self.debug_dir}")

    def load_resources(self):
        """Load workflow JSON and open PDF documents"""
        logger.info(f"Loading workflow from: {self.workflow_path}")
        with open(self.workflow_path, 'r') as f:
            self.workflow = json.load(f)
            
        logger.info(f"Opening PDF 1: {self.pdf1_path}")
        self.doc1 = fitz.open(self.pdf1_path)
        
        logger.info(f"Opening PDF 2: {self.pdf2_path}")
        self.doc2 = fitz.open(self.pdf2_path)
        
    def close_resources(self):
        """Close PDF documents"""
        if self.doc1:
            self.doc1.close()
        if self.doc2:
            self.doc2.close()
            
    def _cache_all_pages(self):
        """Cache markdown text for all pages of both documents"""
        logger.info("Caching all pages from both documents...")
        
        if self.doc1:
            logger.info(f"Caching {len(self.doc1)} pages from Document 1...")
            for page_num in range(len(self.doc1)):
                with self.page_cache_lock:
                    if page_num not in self.page_cache_doc1:
                        try:
                            page_text = pymupdf4llm.to_markdown(self.doc1, pages=[page_num])
                            self.page_cache_doc1[page_num] = page_text.strip() if page_text else ""
                        except Exception as e:
                            logger.error(f"Error caching page {page_num + 1} from Document 1: {e}")
                            self.page_cache_doc1[page_num] = ""
        
        if self.doc2:
            logger.info(f"Caching {len(self.doc2)} pages from Document 2...")
            for page_num in range(len(self.doc2)):
                with self.page_cache_lock:
                    if page_num not in self.page_cache_doc2:
                        try:
                            page_text = pymupdf4llm.to_markdown(self.doc2, pages=[page_num])
                            self.page_cache_doc2[page_num] = page_text.strip() if page_text else ""
                        except Exception as e:
                            logger.error(f"Error caching page {page_num + 1} from Document 2: {e}")
                            self.page_cache_doc2[page_num] = ""
        
        # Cache headlines after pages are cached
        logger.info("Caching headlines from both documents...")
        
        if self.doc1:
            for page_num in range(len(self.doc1)):
                with self.headline_cache_lock:
                    if page_num not in self.headline_cache_doc1:
                        with self.page_cache_lock:
                            page_text = self.page_cache_doc1.get(page_num, "")
                        headline = get_first_headline(page_text) if page_text else None
                        self.headline_cache_doc1[page_num] = headline
                        if headline:
                            logger.debug(f"Doc1 page {page_num + 1} headline: '{headline}'")
        
        if self.doc2:
            for page_num in range(len(self.doc2)):
                with self.headline_cache_lock:
                    if page_num not in self.headline_cache_doc2:
                        with self.page_cache_lock:
                            page_text = self.page_cache_doc2.get(page_num, "")
                        headline = get_first_headline(page_text) if page_text else None
                        self.headline_cache_doc2[page_num] = headline
                        if headline:
                            logger.debug(f"Doc2 page {page_num + 1} headline: '{headline}'")
            
        logger.info("Page and headline caching complete")
    
    def get_cached_page_text(self, doc_num: int, page_num: int) -> str:
        """Get cached markdown text for a specific page"""
        with self.page_cache_lock:
            if doc_num == 1:
                return self.page_cache_doc1.get(page_num, "")
            elif doc_num == 2:
                return self.page_cache_doc2.get(page_num, "")
            else:
                logger.error(f"Invalid document number: {doc_num}")
                return ""
    
    def get_cached_page_headline(self, doc_num: int, page_num: int) -> Optional[str]:
        """Get cached headline for a specific page"""
        with self.headline_cache_lock:
            if doc_num == 1:
                return self.headline_cache_doc1.get(page_num)
            elif doc_num == 2:
                return self.headline_cache_doc2.get(page_num)
            else:
                logger.error(f"Invalid document number: {doc_num}")
                return None
            
    def extract_text_from_region(self, doc: fitz.Document, page_num: int, bbox: Tuple[float, float, float, float]) -> str:
        """Extract text from a specific region using PyMuPDF"""
        page = doc[page_num]
        rect = fitz.Rect(bbox)
        
        # Get words in the rectangle
        words = page.get_text("words")
        text_in_rect = []
        
        for word in words:
            word_rect = fitz.Rect(word[:4])
            if rect.contains(word_rect):
                text_in_rect.append(word[4])
                
        return " ".join(text_in_rect)
    
    def extract_text_with_layout(self, doc: fitz.Document, page_num: int, bbox: Tuple[float, float, float, float]) -> str:
        """Extract text with layout preservation using pymupdf4llm"""
        page = doc[page_num]
        page_height = page.rect.height
        page_width = page.rect.width
        
        # Calculate margins to isolate the bbox region
        margins = (
            bbox[0],  # left margin
            bbox[1],  # top margin
            page_width - bbox[2],  # right margin
            page_height - bbox[3]  # bottom margin
        )
        
        # Extract markdown with layout preserved
        try:
            markdown_text = pymupdf4llm.to_markdown(
                doc, 
                pages=[page_num], 
                margins=margins,
                page_chunks=True
            )
            # When page_chunks=True, pymupdf4llm returns a list of page chunks
            # Since we're only processing one page, get the first element
            if isinstance(markdown_text, list) and len(markdown_text) > 0:
                return markdown_text[0]['text'].strip()
            else:
                return str(markdown_text).strip()
        except Exception as e:
            logger.error(f"Error extracting text with layout: {e}")
            return self.extract_text_from_region(doc, page_num, bbox)
    
    def extract_image_from_region(self, doc: fitz.Document, page_num: int, bbox: Tuple[float, float, float, float]) -> str:
        """Extract image from region as base64"""
        page = doc[page_num]
        clip_rect = fitz.Rect(bbox)
        
        # Get pixmap of the region
        pix = page.get_pixmap(clip=clip_rect, matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def compare_exact_match(self, box: Dict[str, Any]) -> ComparisonResult:
        """Scenario 1: Must match exactly with guaranteed position"""
        logger.info(f"Comparing exact match for box {box['id']}")
        
        page_num = box['page'] - 1
        bbox = (box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
        
        try:
            text1 = self.extract_text_from_region(self.doc1, page_num, bbox)
            text2 = self.extract_text_from_region(self.doc2, page_num, bbox)
            
            if text1 == text2:
                return ComparisonResult(
                    box_id=box['id'],
                    box_type=box['type'],
                    comparison_type='exact_match',
                    status='match',
                    details={
                        'text1': text1,
                        'text2': text2,
                        'page': box['page']
                    }
                )
            else:
                return ComparisonResult(
                    box_id=box['id'],
                    box_type=box['type'],
                    comparison_type='exact_match',
                    status='mismatch',
                    details={
                        'text1': text1,
                        'text2': text2,
                        'page': box['page']
                    }
                )
        except Exception as e:
            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='exact_match',
                status='error',
                details={'page': box['page']},
                error_message=str(e)
            )
    
    def compare_exact_match_position_not_guaranteed(self, box: Dict[str, Any]) -> ComparisonResult:
        """Scenario 2: Must match exactly but position not guaranteed (placeholder)"""
        logger.info(f"Placeholder for exact match with position not guaranteed: box {box['id']}")
        
        return ComparisonResult(
            box_id=box['id'],
            box_type=box['type'],
            comparison_type='exact_match_position_not_guaranteed',
            status='error',
            details={},
            error_message="Not implemented: Exact match with position not guaranteed"
        )
    
    def compare_with_llm(self, box: Dict[str, Any], model_name: str) -> ComparisonResult:
        """Scenario 3: Position guaranteed, no vision model"""
        logger.info(f"Comparing with LLM for box {box['id']}")
        
        page_num = box['page'] - 1
        bbox = (box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
        settings = box.get('settings', {})
        
        try:
            # Extract text with layout
            text1 = self.extract_text_with_layout(self.doc1, page_num, bbox)
            text2 = self.extract_text_with_layout(self.doc2, page_num, bbox)
            
            # Get comparison instruction
            comparison_instruction = settings.get('chatTaskDescription', 
                                                'Compare these two text regions and describe any differences.')
            
            # Initialize LLM
            llm = chat_model_registry.get_model(model_name)
            
            messages = [
                SystemMessage(content=comparison_instruction),
                HumanMessage(content=f"""
Text from Document 1:
```
{text1}
```

Text from Document 2:
```
{text2}
```

Please provide a detailed comparison based on the instructions.""")
            ]
            
            response = llm.invoke(messages)
            
            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='llm_text_only',
                status='match',  # LLM comparisons always "match" - the response contains the analysis
                details={
                    'text1': text1,
                    'text2': text2,
                    'page': box['page'],
                    'model': model_name
                },
                llm_response=response.content
            )
            
        except Exception as e:
            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='llm_text_only',
                status='error',
                details={'page': box['page']},
                error_message=str(e)
            )
    
    def compare_with_vision(self, box: Dict[str, Any], vision_model_name: str) -> ComparisonResult:
        """Scenario 4: Position guaranteed with vision model"""
        logger.info(f"Comparing with vision model for box {box['id']}")
        
        page_num = box['page'] - 1
        bbox = (box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
        settings = box.get('settings', {})
        
        try:
            # Extract both text and images
            text1 = self.extract_text_with_layout(self.doc1, page_num, bbox)
            text2 = self.extract_text_with_layout(self.doc2, page_num, bbox)
            
            image1_b64 = self.extract_image_from_region(self.doc1, page_num, bbox)
            image2_b64 = self.extract_image_from_region(self.doc2, page_num, bbox)
            
            # Get comparison instruction
            comparison_instruction = settings.get('visionTaskDescription', 
                                                'Compare these two regions visually and describe any differences.')
            
            # Check if text guidance is enabled
            guide_with_text = settings.get('guideWithTextIfAvailable', False)
            
            # Initialize vision LLM
            llm = chat_model_registry.get_model(vision_model_name)
            
            # Build message with both text and images
            content = [
                {"type": "text", "text": comparison_instruction},
            ]
            
            # Add text content if guide with text is enabled
            if guide_with_text:
                content.extend([
                    {"type": "text", "text": f"\n\nText from Document 1:\n```\n{text1}\n```"},
                    {"type": "text", "text": f"\n\nText from Document 2:\n```\n{text2}\n```"}
                ])
            
            # Add images
            content.extend([
                {"type": "text", "text": "\n\nDocument 1 region:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image1_b64}"}},
                {"type": "text", "text": "\n\nDocument 2 region:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image2_b64}"}}
            ])
            
            messages = [
                SystemMessage(content="You are a visual document analysis assistant."),
                HumanMessage(content=content)
            ]
            
            response = llm.invoke(messages)
            
            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='vision_model',
                status='match',
                details={
                    'text1': text1,
                    'text2': text2,
                    'page': box['page'],
                    'model': vision_model_name,
                    'guide_with_text': guide_with_text
                },
                llm_response=response.content
            )
            
        except Exception as e:
            logger.error(f"Error checking page {page_num + 1}: {e}")
            return False
    
    def _get_full_text_markdown(self, doc: fitz.Document, doc_id: int) -> str:
        """Helper to generate the full markdown text for a document with page markers using cached page text."""
        text = f"---DOCUMENT {doc_id}---\n"
        for i in range(len(doc)):
            # Get cached markdown for each page and add the marker
            page_text = self.get_cached_page_text(doc_id, i)
            text += f"----PAGE {i + 1}----\n"
            text += page_text + "\n\n"
        return text

    def _prepare_full_text_cache(self):
        """
        Extracts the full markdown text of both documents and caches it
        to avoid redundant processing for multiple annotation boxes.
        """
        # First ensure all pages are cached
        self._cache_all_pages()
        
        if self.doc1 and self.full_text_doc1_md is None:
            logger.info("Preparing full text cache for Document 1...")
            self.full_text_doc1_md = self._get_full_text_markdown(self.doc1, 1)

        if self.doc2 and self.full_text_doc2_md is None:
            logger.info("Preparing full text cache for Document 2...")
            self.full_text_doc2_md = self._get_full_text_markdown(self.doc2, 2)

    def find_pages_via_full_text_prompt(self, reference_text: str, search_model_name: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Finds the page numbers for a reference text in two documents using a single LLM call
        with the pre-cached, full-text markdown of both PDFs.
        """
        logger.info(f"Searching for reference text in cached full PDF content using model {search_model_name}.")

        if not self.full_text_doc1_md or not self.full_text_doc2_md:
            logger.error("Full text cache is not available. This should have been prepared by the run_comparison method.")
            # This should not happen in the normal flow, but as a fallback, we can generate it on the fly.
            self._prepare_full_text_cache()
            
        full_text_doc1 = self.full_text_doc1_md
        full_text_doc2 = self.full_text_doc2_md

        llm = chat_model_registry.get_model(search_model_name)

        system_message = """
You are an expert at finding specific content within large documents.
The user will provide the full text of two PDFs, with each document and page clearly marked.
Your task is to identify which page in EACH document contains the reference text provided by the user.
Its not about the direct match. Its about finding the graph behind this text.
The reference text might not be an exact match, but it should be semantically similar or refer to the same element (like a table or chart with a specific title).
You must respond with the page numbers for both documents in the format: "Doc1: <page_number>, Doc2: <page_number>".
For example: "Doc1: 5, Doc2: 12".
If you cannot find the content in a document, use '0' for that document's page number. For example: "Doc1: 5, Doc2: 0".
"""

        human_message = f"""
Reference Text to find:
'''
{reference_text}
'''

Full Text of Documents:
{full_text_doc1}
{full_text_doc2}

Which pages contain the reference text? Respond in the format: "Doc1: <page_number>, Doc2: <page_number>".
"""

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=human_message),
        ]

        try:
            response = llm.invoke(messages)
            content = response.content.strip()
            
            doc1_match = re.search(r"Doc1:\s*(\d+)", content, re.IGNORECASE)
            doc2_match = re.search(r"Doc2:\s*(\d+)", content, re.IGNORECASE)

            page1 = int(doc1_match.group(1)) if doc1_match and int(doc1_match.group(1)) > 0 else None
            page2 = int(doc2_match.group(1)) if doc2_match and int(doc2_match.group(1)) > 0 else None
            
            page1_0_indexed = page1 - 1 if page1 and page1 <= len(self.doc1) else None
            page2_0_indexed = page2 - 1 if page2 and page2 <= len(self.doc2) else None

            logger.info(f"LLM identified page matches: Doc1 -> {page1}, Doc2 -> {page2}")
            return page1_0_indexed, page2_0_indexed

        except Exception as e:
            logger.error(f"Error parsing page numbers from LLM response: {e}. Response was: {content}")
            return None, None

    def compare_found_pages(self, box: Dict[str, Any], page1: int, page2: int) -> ComparisonResult:
        """Compares two full pages (image and text) using a vision model, guided by reference text."""
        settings = box.get('settings', {})
        
        comparison_model = settings.get('visionModel', 'gpt-4o-mini')
        comparison_instruction = settings.get('comparisonTaskDescription', 
                                            'Compare the specified element on these two pages and describe any differences.')
        # The referenceGuidingText is crucial to focus the model's attention
        reference_text = settings.get('referenceGuidingText', '')

        try:
            # Doc 1 Data
            page_doc1 = self.doc1[page1]
            pix1 = page_doc1.get_pixmap(matrix=fitz.Matrix(2, 2))
            img1_b64 = base64.b64encode(pix1.tobytes("png")).decode('utf-8')
            text1 = self.get_cached_page_text(1, page1)

            # Doc 2 Data
            page_doc2 = self.doc2[page2]
            pix2 = page_doc2.get_pixmap(matrix=fitz.Matrix(2, 2))
            img2_b64 = base64.b64encode(pix2.tobytes("png")).decode('utf-8')
            text2 = self.get_cached_page_text(2, page2)

            llm = chat_model_registry.get_model(comparison_model)

            system_message = "You are a visual document analysis assistant. Your task is to compare a specific element (like a graph or table) across two different document pages. The user will provide images and text for both pages, along with a reference text to help you identify the specific element to focus on."

            human_content = [
                {"type": "text", "text": comparison_instruction},
                {"type": "text", "text": f"\n**Reference text to identify the element for comparison:**\n'''\n{reference_text}\n'''"},
            ]
            
            # Add reference image if enabled and available
            if self.include_reference_image:
                reference_image = settings.get('base64Image')
                if reference_image:
                    human_content.extend([
                        {"type": "text", "text": "\n\n**Reference image from workflow:**"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{reference_image}"}},
                    ])
            
            human_content.extend([
                {"type": "text", "text": f"\n\n--- Start of Document 1, Page {page1 + 1} ---"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img1_b64}"}},
                {"type": "text", "text": f"**Full text from Document 1, Page {page1 + 1}:**\n{text1}"},
                {"type": "text", "text": f"--- End of Document 1, Page {page1 + 1} ---"},
                {"type": "text", "text": f"\n\n--- Start of Document 2, Page {page2 + 1} ---"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img2_b64}"}},
                {"type": "text", "text": f"**Full text from Document 2, Page {page2 + 1}:**\n{text2}"},
                {"type": "text", "text": f"--- End of Document 2, Page {page2 + 1} ---"},
            ])

            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=human_content)
            ]

            response = llm.invoke(messages)

            # Get headlines for the found pages if headline mode is enabled
            headlines = {}
            if self.use_headline:
                headline1 = self.get_cached_page_headline(1, page1)
                headline2 = self.get_cached_page_headline(2, page2)
                if headline1:
                    headlines['doc1_headline'] = headline1
                if headline2:
                    headlines['doc2_headline'] = headline2

            details = {
                'doc1_page': page1 + 1,
                'doc2_page': page2 + 1,
                'comparison_model': comparison_model,
            }
            details.update(headlines)  # Add headlines if available

            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='position_not_guaranteed_single_call',
                status='match',
                details=details,
                llm_response=response.content
            )

        except Exception as e:
            logger.error(f"Error in single-call full page comparison for box {box['id']}: {e}")
            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='position_not_guaranteed_single_call',
                status='error',
                details={},
                error_message=str(e)
            )
            
    def find_pages_by_headline_match(self, target_headline: str) -> Tuple[Optional[int], Optional[int]]:
        """Find pages in both documents that have the same headline"""
        logger.info(f"Searching for headline match: '{target_headline}'")
        
        # Clean the target headline for matching
        target_cleaned = clean_headline_for_matching(target_headline)
        logger.info(f"Cleaned target headline: '{target_cleaned}'")
        
        page1 = None
        page2 = None
        
        # Search in document 1
        for page_num in range(len(self.doc1)):
            headline = self.get_cached_page_headline(1, page_num)
            if headline:
                headline_cleaned = clean_headline_for_matching(headline)
                if headline_cleaned == target_cleaned:
                    page1 = page_num
                    logger.info(f"Found matching headline in Doc1 on page {page_num + 1}")
                    break
        
        # Search in document 2  
        for page_num in range(len(self.doc2)):
            headline = self.get_cached_page_headline(2, page_num)
            if headline:
                headline_cleaned = clean_headline_for_matching(headline)
                if headline_cleaned == target_cleaned:
                    page2 = page_num
                    logger.info(f"Found matching headline in Doc2 on page {page_num + 1}")
                    break
                
        return page1, page2

    def compare_position_not_guaranteed(self, box: Dict[str, Any]) -> ComparisonResult:
        """Scenario 5: Position not guaranteed. Find page via headline matching or full text, then perform a single comparison call."""
        logger.info(f"Comparing with position not guaranteed for box {box['id']}")
        
        settings = box.get('settings', {})
        
        try:
            if self.use_headline:
                # Strict: Use headline from the workflow JSON. No fallbacks.
                target_headline = settings.get('pageHeadline')

                if not target_headline:
                    # Fail immediately if headline is missing in the workflow.
                    logger.error(f"Strict mode failure for box {box['id']}: --use-headline is active, but 'pageHeadline' is missing in the workflow.")
                    return ComparisonResult(
                        box_id=box['id'],
                        box_type=box['type'],
                        comparison_type='position_not_guaranteed',
                        status='error',
                        details={'search_method': 'headline_match'},
                        error_message="--use-headline is active, but 'pageHeadline' is missing in the workflow for this annotation box."
                    )
                
                logger.info(f"Step 1: Searching for pages with matching headline from workflow: '{target_headline}'")
                page1, page2 = self.find_pages_by_headline_match(target_headline)
                search_method = 'headline_match'
                search_text = target_headline
            else:
                # Use standard reference text approach
                reference_text = settings.get('referenceGuidingText', '')
                if not reference_text:
                    page_num = box['page'] - 1
                    bbox = (box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
                    reference_text = self.extract_text_with_layout(self.doc1, page_num, bbox)
                    logger.info("No referenceGuidingText, extracted from doc1 original position.")

                if not reference_text:
                    return ComparisonResult(
                        box_id=box['id'],
                        box_type=box['type'],
                        comparison_type='position_not_guaranteed',
                        status='error',
                        details={},
                        error_message="Reference text is required for position-not-guaranteed search, but none was provided or could be extracted."
                    )

                search_model = settings.get('chatModel', 'gpt-4o-mini')
                logger.info("Step 1: Searching for element in both documents using full-text prompt...")
                page1, page2 = self.find_pages_via_full_text_prompt(reference_text, search_model)
                search_method = 'full_text'
                search_text = reference_text

            # Handle cases where pages are not found
            if page1 is None or page2 is None:
                status = 'not_found'
                details = {
                    'doc1_found': page1 is not None, 
                    'doc1_page': page1 + 1 if page1 is not None else None,
                    'doc2_found': page2 is not None, 
                    'doc2_page': page2 + 1 if page2 is not None else None,
                    'search_method': search_method,
                    'search_text': search_text
                }
                error_msg = "Element not found in either document." if page1 is None and page2 is None else \
                            "Element not found in Document 1." if page1 is None else \
                            "Element not found in Document 2."
                return ComparisonResult(
                    box_id=box['id'], 
                    box_type=box['type'], 
                    comparison_type='position_not_guaranteed',
                    status=status, 
                    details=details, 
                    error_message=error_msg
                )

            # Step 2: Perform the single, context-rich comparison call
            logger.info(f"Step 2: Performing single-call comparison for pages {page1+1} and {page2+1}...")
            result = self.compare_found_pages(box, page1, page2)
            
            # Add search method info to the result details
            if hasattr(result, 'details') and result.details:
                result.details['search_method'] = search_method
                result.details['search_text'] = search_text
                
            return result

        except Exception as e:
            logger.error(f"Error in position-not-guaranteed comparison for box {box['id']}: {e}")
            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='position_not_guaranteed',
                status='error',
                details={},
                error_message=str(e)
            )
    
    def process_annotation_box(self, box: Dict[str, Any]) -> ComparisonResult:
        """Process a single annotation box based on its settings"""
        settings = box.get('settings', {})
        
        # Determine which comparison method to use
        must_match_exactly = settings.get('mustMatchExactly', False)
        position_not_guaranteed = settings.get('positionIsNotGuaranteed', False)
        use_vision_model = settings.get('useVisionModel', False)
        
        logger.info(f"\nProcessing box {box['id']} - Type: {box['type']}")
        logger.info(f"Settings: mustMatchExactly={must_match_exactly}, "
                   f"positionNotGuaranteed={position_not_guaranteed}, "
                   f"useVisionModel={use_vision_model}")
        
        if must_match_exactly and not position_not_guaranteed:
            # Scenario 1: Exact match with guaranteed position
            return self.compare_exact_match(box)
            
        elif must_match_exactly and position_not_guaranteed:
            # Scenario 2: Exact match but position not guaranteed (placeholder)
            return self.compare_exact_match_position_not_guaranteed(box)
            
        elif not position_not_guaranteed and not use_vision_model:
            # Scenario 3: LLM comparison without vision
            model_name = settings.get('chatModel', 'gpt-4o-mini')
            return self.compare_with_llm(box, model_name)
            
        elif not position_not_guaranteed and use_vision_model:
            # Scenario 4: Vision model comparison
            model_name = settings.get('visionModel', 'gpt-4o-mini')
            return self.compare_with_vision(box, model_name)
            
        elif position_not_guaranteed:
            # Scenario 5: Position not guaranteed (requires finding element)
            return self.compare_position_not_guaranteed(box)
            
        else:
            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='unknown',
                status='error',
                details={},
                error_message="Unknown comparison configuration"
            )
    
    def run_comparison(self) -> Dict[str, Any]:
        """Run the complete comparison process"""
        try:
            self.load_resources()
            
            # Prepare the full-text cache once for the entire run
            self._prepare_full_text_cache()
            
            annotation_boxes = self.workflow.get('annotationBoxes', [])
            logger.info(f"Found {len(annotation_boxes)} annotation boxes to process")
            
            if self.parallel_boxes > 1:
                logger.info(f"Processing boxes in parallel with {self.parallel_boxes} workers")
                
                # Process boxes in parallel
                with ThreadPoolExecutor(max_workers=self.parallel_boxes) as executor:
                    # Submit all tasks
                    future_to_box = {
                        executor.submit(self.process_annotation_box, box): box 
                        for box in annotation_boxes
                    }
                    
                    # Collect results as they complete
                    for future in as_completed(future_to_box):
                        box = future_to_box[future]
                        try:
                            result = future.result()
                            # Thread-safe append to results
                            with self.results_lock:
                                self.results.append(result)
                        except Exception as e:
                            logger.error(f"Error processing box {box['id']}: {e}", exc_info=True)
                            # Create error result
                            error_result = ComparisonResult(
                                box_id=box['id'],
                                box_type=box['type'],
                                comparison_type='unknown',
                                status='error',
                                details={},
                                error_message=f"Processing error: {str(e)}"
                            )
                            with self.results_lock:
                                self.results.append(error_result)
            else:
                # Sequential processing (original behavior)
                logger.info("Processing boxes sequentially")
                for box in annotation_boxes:
                    result = self.process_annotation_box(box)
                    self.results.append(result)
            
            # Sort results by box_id to maintain consistent ordering
            self.results.sort(key=lambda r: r.box_id)
            
            # Generate summary
            summary = self.generate_summary()
            
            return {
                'summary': summary,
                'results': [self._result_to_dict(r) for r in self.results],
                'metadata': {
                    'workflow': self.workflow_path,
                    'document1': self.pdf1_path,
                    'document2': self.pdf2_path,
                    'timestamp': datetime.now().isoformat(),
                    'parallel_processing': self.parallel_boxes > 1,
                    'parallel_workers': self.parallel_boxes
                }
            }
            
        finally:
            # Ensure resources are closed only after all processing is complete
            self.close_resources()
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of the comparison results"""
        total = len(self.results)
        matches = sum(1 for r in self.results if r.status == 'match')
        mismatches = sum(1 for r in self.results if r.status == 'mismatch')
        errors = sum(1 for r in self.results if r.status == 'error')
        not_found = sum(1 for r in self.results if r.status == 'not_found')
        
        return {
            'total_comparisons': total,
            'matches': matches,
            'mismatches': mismatches,
            'errors': errors,
            'not_found': not_found,
            'success_rate': (matches / total * 100) if total > 0 else 0
        }
    
    def _result_to_dict(self, result: ComparisonResult) -> Dict[str, Any]:
        """Convert ComparisonResult to dictionary"""
        return {
            'box_id': result.box_id,
            'box_type': result.box_type,
            'comparison_type': result.comparison_type,
            'status': result.status,
            'details': result.details,
            'llm_response': result.llm_response,
            'error_message': result.error_message
        }
    
    def save_results(self, output_path: str):
        """Save results to JSON file"""
        results_dict = self.run_comparison()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Results saved to: {output_path}")

    def save_debug_image(self, image_b64: str, filename: str):
        """Save base64 image to debug directory"""
        if not self.debug_mode or not self.debug_dir:
            return
            
        try:
            # Decode base64 to bytes
            image_bytes = base64.b64decode(image_b64)
            
            # Save image
            image_path = os.path.join(self.debug_dir, filename)
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
                
            logger.info(f"Debug image saved: {image_path}")
        except Exception as e:
            logger.error(f"Failed to save debug image {filename}: {e}") 