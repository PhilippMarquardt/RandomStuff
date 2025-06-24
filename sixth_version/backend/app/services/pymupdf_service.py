import fitz  # PyMuPDF
from typing import List, Dict, Any
import itertools

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
        images = [i["bbox"] for i in page.get_image_info(xrefs=True)]
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