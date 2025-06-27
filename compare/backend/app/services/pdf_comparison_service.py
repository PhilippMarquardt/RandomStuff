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

logger = logging.getLogger(__name__)

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
    
    def __init__(self, workflow_path: str, pdf1_path: str, pdf2_path: str, debug_mode: bool = False):
        self.workflow_path = workflow_path
        self.pdf1_path = pdf1_path
        self.pdf2_path = pdf2_path
        self.workflow = None
        self.doc1 = None
        self.doc2 = None
        self.results: List[ComparisonResult] = []
        self.debug_mode = debug_mode
        self.debug_dir = None
        
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
            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='vision_model',
                status='error',
                details={'page': box['page']},
                error_message=str(e)
            )
    
    def find_element_on_page(self, doc: fitz.Document, page_num: int, reference_image_b64: str, 
                           vision_model_name: str, reference_text: Optional[str] = None, 
                           guide_with_text: bool = False) -> bool:
        """Check if reference element exists on a specific page"""
        try:
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            page_img_b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
            
            llm = chat_model_registry.get_model(vision_model_name)
            
            # Build the prompt based on whether text guidance is enabled
            system_content = """You are a visual assistant. Determine if the reference chart/graph/table 
                appears on the page. It can also be a text block. Then you have to probably look at headline or similar. The reference might have different data/numbers but should be the same type 
                of visualization (e.g., same chart type, same table structure). Respond with only 'yes' or 'no'."""
            
            human_content = [
                {"type": "text", "text": "Does this page contain the reference element (possibly with different data)?"}
            ]
            
            # Add text guidance if enabled
            if guide_with_text and reference_text:
                # Extract text from current page
                page_text = self.extract_text_with_layout(doc, page_num, 
                    (0, 0, page.rect.width, page.rect.height))

                human_content.append({
                    "type": "text", 
                    "text": f"\n\nFor further guidance here is the extracted text from the reference image and the whole document to help you find whether the reference is on this page: Reference element contains this text:\n{reference_text}...\n\nCurrent page text:\n{page_text}..."
                })
            
            human_content.extend([
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_img_b64}"}},
                {"type": "text", "text": "Reference element:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{reference_image_b64}"}}
            ])
            
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=human_content)
            ]
            
            response = llm.invoke(messages)
            return 'yes' in response.content.lower()
            
        except Exception as e:
            logger.error(f"Error checking page {page_num + 1}: {e}")
            return False
    
    def find_element_on_page_text_only(self, doc: fitz.Document, page_num: int, 
                                      reference_text: str, search_model_name: str) -> bool:
        """Check if reference element exists on a page using only text search"""
        try:
            # Extract text from current page
            page = doc[page_num]
            page_text = self.extract_text_with_layout(doc, page_num, 
                (0, 0, page.rect.width, page.rect.height))
            
            llm = chat_model_registry.get_model(search_model_name)
            
            messages = [
                SystemMessage(content="""You are a text analysis assistant. Determine if the reference text element 
                    appears on this page. The element might have different data/numbers but should be the same type 
                    of content (e.g., same table structure, same section type). Respond with only 'yes' or 'no'."""),
                HumanMessage(content=f"""
Reference element text:
{reference_text}

Current page text:
{page_text}

Does this page contain the reference element (possibly with different data)?""")
            ]
            
            response = llm.invoke(messages)
            return 'yes' in response.content.lower()
            
        except Exception as e:
            logger.error(f"Error checking page {page_num + 1} with text search: {e}")
            return False
    
    def find_all_candidate_pages(self, doc: fitz.Document, reference_image_b64: str, 
                               search_model: str, reference_text: str, 
                               use_vision_model: bool, guide_with_text: bool) -> List[int]:
        """Find all candidate pages that might contain the reference element"""
        candidates = []
        
        for page_num in range(len(doc)):
            logger.info(f"  Checking page {page_num + 1}...")
            
            if use_vision_model:
                found = self.find_element_on_page(doc, page_num, reference_image_b64, search_model,
                                                reference_text if guide_with_text else None, guide_with_text)
            else:
                found = self.find_element_on_page_text_only(doc, page_num, reference_text, search_model)
                
            if found:
                candidates.append(page_num)
                logger.info(f"  Found potential match on page {page_num + 1}")
                
        return candidates
    
    def select_best_candidate(self, doc: fitz.Document, candidates: List[int], 
                            reference_text: str, search_model: str, 
                            use_vision_model: bool, reference_image_b64: str = None) -> Optional[int]:
        """Select the best candidate page from the list of potential matches"""
        if not candidates:
            return None
            
        if len(candidates) == 1:
            return candidates[0]
            
        logger.info(f"Multiple candidates found ({len(candidates)} pages). Selecting best match...")
        
        llm = chat_model_registry.get_model(search_model)
        
        # Prepare candidate information
        candidate_info = []
        for page_num in candidates:
            page = doc[page_num]
            page_text = self.extract_text_with_layout(doc, page_num, 
                (0, 0, page.rect.width, page.rect.height))
            
            if use_vision_model:
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))  # Lower resolution for comparison
                page_img_b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
                candidate_info.append({
                    'page': page_num,
                    'text': page_text,
                    'image': page_img_b64
                })
            else:
                candidate_info.append({
                    'page': page_num,
                    'text': page_text
                })
        
        # Build prompt for selection
        if use_vision_model:
            system_content = """You are analyzing multiple pages to find the best match for a reference element. 
                The reference element appears in one of these pages. Select the page that contains the most 
                relevant and complete version of the element. Consider both visual similarity and content relevance.
                Respond with only the page number (1-indexed)."""
            
            human_content = [
                {"type": "text", "text": "Reference element:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{reference_image_b64}"}},
                {"type": "text", "text": f"\nReference text:\n{reference_text[:500]}...\n\nCandidate pages:"}
            ]
            
            for i, info in enumerate(candidate_info):
                human_content.extend([
                    {"type": "text", "text": f"\n\nPage {info['page'] + 1}:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{info['image']}"}},
                    {"type": "text", "text": f"Text preview: {info['text']}"}
                ])
                
        else:
            system_content = """You are analyzing multiple pages to find the best match for a reference text element. 
                Select the page that contains the most relevant and complete version of the element.
                Respond with only the page number (1-indexed)."""
            
            candidates_text = ""
            for info in candidate_info:
                candidates_text += f"\n\nPage {info['page'] + 1}:\n{info['text']}\n"
            
            human_content = f"""Reference element text:
{reference_text}

Candidate pages:
{candidates_text}

Which page contains the best match for the reference element?"""
        
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=human_content)
        ]
        
        try:
            response = llm.invoke(messages)
            # Extract page number from response
            match = re.search(r'\b(\d+)\b', response.content)
            if match:
                selected_page = int(match.group(1)) - 1  # Convert to 0-indexed
                if selected_page in candidates:
                    logger.info(f"  Selected page {selected_page + 1} as best match")
                    return selected_page
                    
            # Fallback to first candidate if parsing fails
            logger.warning("Could not parse page selection, using first candidate")
            return candidates[0]
            
        except Exception as e:
            logger.error(f"Error selecting best candidate: {e}")
            return candidates[0]
    
    def extract_information_from_page(self, doc: fitz.Document, page_num: int, 
                                    extraction_model: str, extraction_instruction: str,
                                    guide_with_text: bool = False) -> str:
        """Extract information from a page using only the page and extraction instructions"""
        try:
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            page_img_b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
            
            llm = chat_model_registry.get_model(extraction_model)
            
            human_content = [
                {"type": "text", "text": "Analyze this document page and extract the requested information:"}
            ]
            
            # Add text guidance if enabled
            if guide_with_text:
                page_text = self.extract_text_with_layout(doc, page_num, 
                    (0, 0, page.rect.width, page.rect.height))
                human_content.append({
                    "type": "text",
                    "text": f"\n\nExtracted text from the page:\n{page_text}"
                })
            
            human_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_img_b64}"}})
            
            messages = [
                SystemMessage(content=extraction_instruction),
                HumanMessage(content=human_content)
            ]
            
            response = llm.invoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Error extracting from page {page_num + 1}: {e}")
            return f"Error extracting information: {str(e)}"
    
    def extract_information_from_page_text_only(self, doc: fitz.Document, page_num: int, 
                                               extraction_model: str, extraction_instruction: str,
                                               reference_bbox: Tuple[float, float, float, float]) -> str:
        """Extract information from a page using only text"""
        try:
            # Try to find similar region based on text patterns
            page = doc[page_num]
            full_page_text = self.extract_text_with_layout(doc, page_num, 
                (0, 0, page.rect.width, page.rect.height))
            
            llm = chat_model_registry.get_model(extraction_model)
            
            messages = [
                SystemMessage(content=extraction_instruction),
                HumanMessage(content=f"""
Analyze this document page text and extract the requested information.
The reference element was originally found in a region of approximately {reference_bbox[2]-reference_bbox[0]:.0f}x{reference_bbox[3]-reference_bbox[1]:.0f} pixels.

Page text:
{full_page_text}

Please extract the relevant information that matches the pattern of the reference element.""")
            ]
            
            response = llm.invoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Error extracting from page {page_num + 1} with text: {e}")
            return f"Error extracting information: {str(e)}"

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

    def compare_position_not_guaranteed(self, box: Dict[str, Any]) -> ComparisonResult:
        """Scenario 5: Position not guaranteed - 2-step approach with or without vision"""
        logger.info(f"Comparing with position not guaranteed for box {box['id']}")
        
        settings = box.get('settings', {})
        use_vision_model = settings.get('useVisionModel', False)
        reference_image_b64 = settings.get('base64Image', '')
        
        # For text-only search, we need reference text
        reference_text = settings.get('referenceGuidingText', '')
        if not use_vision_model and not reference_text:
            # Extract text from the reference region if not provided
            page_num = box['page'] - 1
            bbox = (box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
            reference_text = self.extract_text_with_layout(self.doc1, page_num, bbox)
            
        if use_vision_model and not reference_image_b64:
            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='position_not_guaranteed',
                status='error',
                details={},
                error_message="Vision model selected but no reference image found in template"
            )
        
        # Save reference image for debugging if using vision
        if self.debug_mode and use_vision_model:
            self.save_debug_image(reference_image_b64, f"box_{box['id']}_reference.png")
        
        # Get model settings
        if use_vision_model:
            search_model = settings.get('visionModel', 'gpt-4o-mini')
            extraction_model = search_model
        else:
            # For text-only, use the comparison model for searching
            search_model = settings.get('comparisonModel', settings.get('chatModel', 'gpt-4o-mini'))
            extraction_model = search_model
            
        extraction_instruction = settings.get('visionTaskDescription', 
                                           'Extract detailed information from this element.')
        
        comparison_model = settings.get('comparisonModel', settings.get('chatModel', 'gpt-4o-mini'))
        comparison_instruction = settings.get('comparisonTaskDescription', 
                                           'Compare the extracted information and describe differences.')
        
        # Check if text guidance is enabled (only relevant for vision mode)
        guide_with_text = settings.get('guideWithTextIfAvailable', False) and use_vision_model
        
        try:
            # Step 1: Find element in Document 1
            logger.info("Step 1: Searching for element in Document 1...")
            candidates1 = self.find_all_candidate_pages(
                self.doc1, reference_image_b64, search_model, reference_text, 
                use_vision_model, guide_with_text
            )
            
            if not candidates1:
                logger.info("  Element not found in Document 1")
                page1 = None
                description1 = None
            else:
                # Select best candidate
                page1 = self.select_best_candidate(
                    self.doc1, candidates1, reference_text, search_model, 
                    use_vision_model, reference_image_b64
                )
                
                # Step 2: Extract information from selected page
                logger.info(f"Step 2: Extracting information from Document 1, page {page1 + 1}...")
                
                if use_vision_model:
                    description1 = self.extract_information_from_page(
                        self.doc1, page1, extraction_model, extraction_instruction, guide_with_text
                    )
                else:
                    bbox = (box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
                    description1 = self.extract_information_from_page_text_only(
                        self.doc1, page1, extraction_model, extraction_instruction, bbox
                    )
                
                if self.debug_mode and use_vision_model:
                    page = self.doc1[page1]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    page_img_b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
                    self.save_debug_image(page_img_b64, f"box_{box['id']}_doc1_FOUND_page{page1 + 1}.png")
                    
                    # Also save images of other candidates for debugging
                    for i, candidate in enumerate(candidates1):
                        if candidate != page1:
                            page = self.doc1[candidate]
                            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
                            page_img_b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
                            self.save_debug_image(page_img_b64, f"box_{box['id']}_doc1_candidate_page{candidate + 1}.png")
            
            # Step 1: Find element in Document 2
            logger.info("Step 1: Searching for element in Document 2...")
            candidates2 = self.find_all_candidate_pages(
                self.doc2, reference_image_b64, search_model, reference_text, 
                use_vision_model, guide_with_text
            )
            
            if not candidates2:
                logger.info("  Element not found in Document 2")
                page2 = None
                description2 = None
            else:
                # Select best candidate
                page2 = self.select_best_candidate(
                    self.doc2, candidates2, reference_text, search_model, 
                    use_vision_model, reference_image_b64
                )
                
                # Step 2: Extract information from selected page
                logger.info(f"Step 2: Extracting information from Document 2, page {page2 + 1}...")
                
                if use_vision_model:
                    description2 = self.extract_information_from_page(
                        self.doc2, page2, extraction_model, extraction_instruction, guide_with_text
                    )
                else:
                    bbox = (box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
                    description2 = self.extract_information_from_page_text_only(
                        self.doc2, page2, extraction_model, extraction_instruction, bbox
                    )
                
                if self.debug_mode and use_vision_model:
                    page = self.doc2[page2]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    page_img_b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
                    self.save_debug_image(page_img_b64, f"box_{box['id']}_doc2_FOUND_page{page2 + 1}.png")
                    
                    # Also save images of other candidates for debugging
                    for i, candidate in enumerate(candidates2):
                        if candidate != page2:
                            page = self.doc2[candidate]
                            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
                            page_img_b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
                            self.save_debug_image(page_img_b64, f"box_{box['id']}_doc2_candidate_page{candidate + 1}.png")

            # Handle cases where element is not found
            if page1 is None or page2 is None:
                status = 'not_found'
                details = {
                    'doc1_found': page1 is not None,
                    'doc1_page': page1 + 1 if page1 is not None else None,
                    'doc1_candidates': len(candidates1),
                    'doc2_found': page2 is not None,
                    'doc2_page': page2 + 1 if page2 is not None else None,
                    'doc2_candidates': len(candidates2),
                    'search_method': 'vision' if use_vision_model else 'text'
                }
                
                if page1 is None and page2 is None:
                    error_msg = "Element not found in either document"
                elif page1 is None:
                    error_msg = "Element not found in Document 1"
                else:
                    error_msg = "Element not found in Document 2"
                    
                return ComparisonResult(
                    box_id=box['id'],
                    box_type=box['type'],
                    comparison_type='position_not_guaranteed',
                    status=status,
                    details=details,
                    error_message=error_msg
                )
            
            # Step 3: Compare using only the extracted descriptions
            logger.info("Step 3: Comparing extracted information...")
            comparison_llm = chat_model_registry.get_model(comparison_model)
            
            messages = [
                SystemMessage(content=comparison_instruction),
                HumanMessage(content=f"""
Extracted information from Document 1 (Page {page1 + 1}):
{description1}

Extracted information from Document 2 (Page {page2 + 1}):
{description2}

Please provide a detailed comparison based on the extracted information.""")
            ]
            
            response = comparison_llm.invoke(messages)
            
            return ComparisonResult(
                box_id=box['id'],
                box_type=box['type'],
                comparison_type='position_not_guaranteed',
                status='match',
                details={
                    'doc1_page': page1 + 1,
                    'doc1_candidates': len(candidates1),
                    'doc2_page': page2 + 1,
                    'doc2_candidates': len(candidates2),
                    'description1': description1,
                    'description2': description2,
                    'search_method': 'vision' if use_vision_model else 'text',
                    'extraction_model': extraction_model,
                    'comparison_model': comparison_model
                },
                llm_response=response.content
            )
            
        except Exception as e:
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
            
            annotation_boxes = self.workflow.get('annotationBoxes', [])
            logger.info(f"Found {len(annotation_boxes)} annotation boxes to process")
            
            # Process each annotation box
            for box in annotation_boxes:
                result = self.process_annotation_box(box)
                self.results.append(result)
            
            # Generate summary
            summary = self.generate_summary()
            
            return {
                'summary': summary,
                'results': [self._result_to_dict(r) for r in self.results],
                'metadata': {
                    'workflow': self.workflow_path,
                    'document1': self.pdf1_path,
                    'document2': self.pdf2_path,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        finally:
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