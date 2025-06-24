import fitz  # PyMuPDF
import json
from PIL import Image
import pymupdf4llm

# --- Constants ---
# Path to your exported JSON workflow
JSON_WORKFLOW_PATH = r"C:\Users\pmarq\Downloads\workflow-FSD_CH0047533549_SWC_CH_de.pdf (7).json"

# Path to the original PDF document
PDF_PATH = r"C:\Users\pmarq\Downloads\FSD_CH0047533549_SWC_CH_de.pdf"

# Index of the annotation box you want to extract
BOX_INDEX = 0

# --- Main Script ---

def extract_content_from_box(json_path, pdf_path, box_index):
    """
    Extracts content from a PDF based on the coordinates of a specific
    annotation box in an exported JSON workflow.
    """
    try:
        # Load the JSON workflow
        with open(json_path, 'r') as f:
            workflow = json.load(f)
        
        annotation_boxes = workflow.get("annotationBoxes", [])
        
        if not annotation_boxes or box_index >= len(annotation_boxes):
            print(f"Error: Box index {box_index} is out of bounds.")
            return

        # Get the specified annotation box
        box_to_extract = annotation_boxes[box_index]
        print(f"Extracting content for box at index {box_index}: {box_to_extract}")

        # Open the PDF document
        doc = fitz.open(pdf_path)
        
        # Get the page number (adjust for 0-based index)
        page_number = box_to_extract.get("page", 1) - 1
        
        if page_number >= doc.page_count:
            print(f"Error: Page number {page_number + 1} is out of bounds for the PDF.")
            doc.close()
            return

        page = doc[page_number]

        # Get the bounding box coordinates
        x0 = box_to_extract.get("x", 0)
        y0 = box_to_extract.get("y", 0)
        width = box_to_extract.get("width", 0)
        height = box_to_extract.get("height", 0)
        x1 = x0 + width
        y1 = y0 + height
        
        # Define the margins for extraction based on the bounding box
        # The 'margins' parameter in to_markdown expects (left, top, right, bottom)
        page_height = page.rect.height
        page_width = page.rect.width
        margins = (x0, y0, page_width - x1, page_height - y1)
        
        # Use pymupdf4llm to extract the text in markdown format from the specified region
        markdown_text = pymupdf4llm.to_markdown(
            doc, 
            pages=[page_number], 
            margins=margins
        )

        print("\n--- Extracted Markdown Text ---")
        print(markdown_text)
        print("-----------------------------\n")
        
        # Also save the image of the box for verification
        output_image_path = f"extracted_image_box_{box_index}.png"
        crop_rect = fitz.Rect(x0, y0, x1, y1)
        dpi = 300
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(clip=crop_rect, matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(output_image_path, "PNG")
        print(f"Saved image of the box to {output_image_path} for verification.")


        # Clean up
        doc.close()

    except FileNotFoundError:
        print(f"Error: Could not find JSON file at {json_path} or PDF at {pdf_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    extract_content_from_box(JSON_WORKFLOW_PATH, PDF_PATH, BOX_INDEX) 