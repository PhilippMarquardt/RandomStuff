import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple
import itertools
import pymupdf4llm

class PyMuPDFService:
    def _text_rects(self, page, use_blocks=False, pad=0.0):
        """
        Return rectangles for text; enlarge by `pad` points each side.
        • use_blocks=False  -> word boxes
        • use_blocks=True   -> larger text-block boxes
        """
        if use_blocks:
            blocks = page.get_text("dict")["blocks"]
            rects = [fitz.Rect(*b["bbox"]) for b in blocks if b["type"] == 0]
        else:
            rects = [fitz.Rect(*w[:4]) for w in page.get_text("words")]

        if pad:
            rects = [r + (-pad, -pad, pad, pad) for r in rects]
        return rects

    def _non_text_boxes(self, page, mask_rects, overlap=0.10, x_tol=3, y_tol=3):
        """
        Return rectangles of images + vector drawings that overlap the text mask
        by less than `overlap` (fraction of candidate area).
        """
        images = [fitz.Rect(*i["bbox"]) for i in page.get_image_info(xrefs=True)]
        draws = page.cluster_drawings(x_tolerance=x_tol, y_tolerance=y_tol)

        print(f"DEBUG: Page {page.number + 1} - Found {len(images)} images, {len(draws)} drawings")

        keep = []
        for rect in itertools.chain(images, draws):
            if rect.get_area() > 0:  # Only process rectangles with area
                ovr = sum((rect & m).get_area() for m in mask_rects)
                if ovr / rect.get_area() < overlap:
                    keep.append(rect)
                    print(f"DEBUG: Keeping rect {rect} (overlap: {ovr / rect.get_area():.3f})")
                else:
                    print(f"DEBUG: Skipping rect {rect} (overlap: {ovr / rect.get_area():.3f})")
        
        print(f"DEBUG: Total kept: {len(keep)} non-text boxes")
        return keep

    def extract_words_with_bbox(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract word-level bounding boxes and images from PDF using PyMuPDF.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Dictionary containing pages with word-level bounding box data and image data
        """
        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Get words with bounding boxes
                # Returns tuple: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
                words = page.get_text("words")
                
                # Get page dimensions
                page_rect = page.rect
                
                # Extract images and drawings
                mask_rects = self._text_rects(page, use_blocks=True, pad=1)
                non_text_boxes = self._non_text_boxes(page, mask_rects, overlap=0.10)
                
                page_data = {
                    "page_number": page_num + 1,
                    "dimensions": {
                        "width": float(page_rect.width),
                        "height": float(page_rect.height)
                    },
                    "words": [
                        {
                            "text": word[4],
                            "bbox": [float(word[0]), float(word[1]), float(word[2]), float(word[3])],
                            "block_no": word[5],
                            "line_no": word[6],
                            "word_no": word[7]
                        }
                        for word in words if word[4].strip()  # Only include non-empty words
                    ],
                    "images": [
                        {
                            "bbox": [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)],
                            "area": float(rect.get_area()),
                            "type": "non_text_element"
                        }
                        for rect in non_text_boxes
                    ]
                }
                
                print(f"DEBUG: Page {page_num + 1} processed - {len(page_data['words'])} words, {len(page_data['images'])} images")
                pages.append(page_data)
            
            doc.close()
            return {"pages": pages}
            
        except Exception as e:
            raise Exception(f"Error processing PDF with PyMuPDF: {str(e)}")

    def extract_image_from_region(self, pdf_bytes: bytes, page_number: int, bbox: List[float]) -> str:
        """
        Extract a specific region from a PDF page as a base64 encoded image.
        
        Args:
            pdf_bytes: PDF file content as bytes
            page_number: The 1-based page number
            bbox: A list of four floats [x0, y0, x1, y1] defining the bounding box
            
        Returns:
            A base64 encoded PNG image string.
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            if not (0 < page_number <= doc.page_count):
                raise ValueError(f"Page number {page_number} is out of valid range (1-{doc.page_count})")
            
            page = doc[page_number - 1] # fitz uses 0-based indexing
            
            # Define the clipping rectangle from the bounding box
            clip_rect = fitz.Rect(bbox)
            
            # Get a pixmap of the specified region.
            # matrix=fitz.Matrix(3, 3) creates a 3x zoom for higher quality.
            pix = page.get_pixmap(clip=clip_rect, matrix=fitz.Matrix(3, 3))
            
            # Get PNG image bytes
            img_bytes = pix.tobytes("png")
            
            doc.close()
            
            # Encode bytes to base64 string
            import base64
            base64_image = base64.b64encode(img_bytes).decode('utf-8')
            
            return base64_image
            
        except Exception as e:
            raise Exception(f"Error extracting image from PDF region: {str(e)}")

    def extract_text_with_layout(self, pdf_bytes: bytes, page_num: int, bbox: Tuple[float, float, float, float]) -> str:
        """Extract text with layout preservation using pymupdf4llm"""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            if not (0 <= page_num < doc.page_count):
                raise ValueError(f"Page number {page_num} is out of valid range (0-{doc.page_count-1})")
            
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
            markdown_text = pymupdf4llm.to_markdown(
                doc, 
                pages=[page_num], 
                margins=margins,
                page_chunks=False
            )
            
            doc.close()
            return markdown_text.strip()
            
        except Exception as e:
            raise Exception(f"Error extracting text with layout: {str(e)}") 