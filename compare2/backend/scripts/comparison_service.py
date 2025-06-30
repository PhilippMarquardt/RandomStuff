import os
import fitz  # PyMuPDF
import json
import pymupdf4llm
from pathlib import Path
from app.services.chat_models import chat_model_registry
from langchain_core.messages import HumanMessage, SystemMessage
import os
import base64
import argparse

# --- Constants ---
# Path to the JSON workflow file created by the annotation tool
JSON_WORKFLOW_PATH = r"C:\Users\pmarq\Downloads\workflow-FSD_CH0047533549_SWC_CH_de.pdf (17).json"

# Path to the new PDF document you want to process against the workflow
PDF_TO_PROCESS_PATH_1 = r"C:\Users\pmarq\Downloads\FSD_CH0047533549_SWC_CH_de.pdf"
PDF_TO_PROCESS_PATH_2 = r"C:\Users\pmarq\Downloads\FSD_CH0047533549_SWC_CH_de (1).pdf"

# --- Main Service Simulation ---

def check_overlap(rect1, rect2, threshold=0.9):
    """Check if the intersection area is above a certain threshold of the smaller rect."""
    intersect = rect1 & rect2
    
    area1 = rect1.get_area()
    area2 = rect2.get_area()

    if area1 == 0 or area2 == 0:
        return False

    overlap_ratio = intersect.get_area() / min(area1, area2)
    return overlap_ratio >= threshold

def extract_text_from_box(doc, page_num, box_rect):
    """Extracts text from a given bounding box on a specific page."""
    page = doc[page_num]
    page_height = page.rect.height
    page_width = page.rect.width
    margins = (box_rect.x0, box_rect.y0, page_width - box_rect.x1, page_height - box_rect.y1)
    return pymupdf4llm.to_markdown(doc, pages=[page_num], margins=margins).strip()

def find_element_in_pdf(llm, doc, reference_image_b64):
    """Iterates through a PDF to find a reference image, returning the page number."""
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"    -> Scanning page {page_num + 1}...")

        pix = page.get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72))  # Use lower res for speed
        page_img_data = pix.tobytes("png")
        page_img_base64 = base64.b64encode(page_img_data).decode('utf-8')

        messages = [
            SystemMessage(content="You are a visual assistant. Your task is to determine if a reference image appears anywhere on a page image. Respond with only 'yes' or 'no'."),
            HumanMessage(content=[
                {"type": "text", "text": "Does the main page image contain the smaller reference image?"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_img_base64}", "detail": "low"}},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{reference_image_b64}"}}
            ])
        ]
        
        response = llm.invoke(messages)
        
        if 'yes' in response.content.lower():
            print(f"  -> Found a match on page {page_num + 1}")
            return page_num + 1
            
    return None

def compare_position_not_exact(llm, doc1, doc2, template_box):
    """Finds a chart in two documents and returns the pages it was found on."""
    print("  -> Mode: Position Not Guaranteed (Visual Search)")
    reference_image_b64 = template_box.get("reference_image")

    if not reference_image_b64:
        print("  -> !! ERROR: No reference image found for this box. Skipping.")
        return None, None

    print("  -> Searching in Document 1...")
    page1 = find_element_in_pdf(llm, doc1, reference_image_b64)
    
    print("  -> Searching in Document 2...")
    page2 = find_element_in_pdf(llm, doc2, reference_image_b64)

    return page1, page2

def run_comparison_service(workflow_path, pdf_path1, pdf_path2, model_name):
    """
    Simulates the final service that processes two PDFs against a JSON workflow.
    """
    print(f"--- Starting Comparison Service ---")
    print(f"Workflow: {workflow_path}")
    print(f"PDF 1: {pdf_path1}")
    print(f"PDF 2: {pdf_path2}\n")
    print(f"Using model: {model_name}")

    # Initialize the LLM
    llm = chat_model_registry.get_model(model_name)

    try:
        # 1. Load the JSON workflow
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        
        template_boxes = workflow.get("annotationBoxes", [])
        
        # 2. Open the PDFs to be processed
        doc1 = fitz.open(pdf_path1)
        doc2 = fitz.open(pdf_path2)
        
        # --- Results and Logging ---
        results = {
            "mismatches": [],
            "llm_responses": []
        }
        
        # 3. Iterate through each box in the workflow template
        for i, template_box in enumerate(template_boxes):
            print(f"\n[Processing Template Box {i}] ID: {template_box['id']}")
            settings = template_box.get("settings", {})

            # 4. Handle boxes where position is not guaranteed
            if settings.get("positionIsNotGuaranteed", False):
                page1, page2 = compare_position_not_exact(llm, doc1, doc2, template_box)
                
                if page1 is None or page2 is None:
                    reason = "Element not found in one or both documents."
                    if page1 is None and page2 is None:
                        reason = "Element not found in either document."
                    elif page1 is None:
                        reason = "Element not found in Document 1."
                    else:
                        reason = "Element not found in Document 2."
                        
                    results["mismatches"].append({
                        "box_id": template_box['id'],
                        "reason": reason,
                        "doc1_found_page": page1,
                        "doc2_found_page": page2,
                    })
                else:
                    # TODO: Once found, we might want to perform a more detailed comparison
                    # on the found pages. For now, just confirming it was found in both.
                    print(f"  -> OK: Element found on Page {page1} (Doc1) and Page {page2} (Doc2).")
                continue

            page_num = template_box.get("page", 1) - 1
            template_rect = fitz.Rect(template_box["x"], template_box["y"], 
                                      template_box["x"] + template_box["width"], 
                                      template_box["y"] + template_box["height"])

            # 5. Handle "Must Match Exactly"
            if settings.get("mustMatchExactly", False):
                print("  -> Mode: Must Match Exactly")
                
                text1 = extract_text_from_box(doc1, page_num, template_rect)
                text2 = extract_text_from_box(doc2, page_num, template_rect)
                
                if text1 == text2:
                    print("  -> OK: Text matches exactly.")
                else:
                    print("  -> !! STRICT MISMATCH: Text does not match.")
                    print(f"     Text 1: '{text1}'")
                    print(f"     Text 2: '{text2}'")
                    results["mismatches"].append({
                        "box_id": template_box["id"],
                        "reason": "Text content does not match exactly.",
                        "text1": text1,
                        "text2": text2
                    })
            
            # 6. Handle LLM Comparison
            else:
                print("  -> Mode: LLM Comparison")
                
                # For LLM tasks, we primarily use text comparison unless vision is specified
                text1 = extract_text_from_box(doc1, page_num, template_rect)
                text2 = extract_text_from_box(doc2, page_num, template_rect)

                # Use chat description as the main instruction
                llm_instruction = settings.get("chatTaskDescription", "Compare the following texts.")
                
                messages = [
                    SystemMessage(content=llm_instruction),
                    HumanMessage(content=f"Text from Document 1:\n```\n{text1}\n```\n\nText from Document 2:\n```\n{text2}\n```")
                ]

                print("    -> Sending to OpenAI API...")
                response = llm.invoke(messages)
                print("    -> Received response.")
                
                results["llm_responses"].append({
                    "box_id": template_box["id"],
                    "response": response.content
                })

        # 7. Final Report
        print("\n--- Comparison Complete ---")
        print(f"Total Mismatches Found: {len(results['mismatches'])}")
        for mismatch in results["mismatches"]:
            print(f"  - {mismatch}")
            
        print(f"\nTotal LLM Responses Received: {len(results['llm_responses'])}")
        for resp in results["llm_responses"]:
            print(f"  - Box ID: {resp['box_id']}")
            print(f"    Response: {resp['response']}")

        doc1.close()
        doc2.close()

    except FileNotFoundError:
        print(f"Error: Could not find workflow at {workflow_path} or PDFs at {pdf_path1}, {pdf_path2}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run comparison service against two PDFs and a workflow.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Name of the model to use.")
    args = parser.parse_args()

    if not Path(JSON_WORKFLOW_PATH).exists() or not Path(PDF_TO_PROCESS_PATH_1).exists() or not Path(PDF_TO_PROCESS_PATH_2).exists():
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! PLEASE UPDATE 'JSON_WORKFLOW_PATH' AND 'PDF_TO_PROCESS_PATH_1/2' !!!")
        print("!!! in backend/scripts/comparison_service.py                !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        run_comparison_service(JSON_WORKFLOW_PATH, PDF_TO_PROCESS_PATH_1, PDF_TO_PROCESS_PATH_2, args.model) 