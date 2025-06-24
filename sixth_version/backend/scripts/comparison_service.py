import os
import fitz  # PyMuPDF
import json
import pymupdf4llm
from pathlib import Path
from app.services.chat_models import model_registry
from langchain_core.messages import HumanMessage, SystemMessage
import os
import base64
import argparse

# --- Constants ---
# Path to the JSON workflow file created by the annotation tool
JSON_WORKFLOW_PATH = r"C:\Users\pmarq\Downloads\workflow-FSD_CH0047533549_SWC_CH_de.pdf (17).json"

# Path to the new PDF document you want to process against the workflow
PDF_TO_PROCESS_PATH = r"C:\Users\pmarq\Downloads\FSD_CH0047533549_SWC_CH_de.pdf"

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

def run_comparison_service(workflow_path, pdf_path, model_name):
    """
    Simulates the final service that processes a PDF against a JSON workflow.
    """
    print(f"--- Starting Comparison Service ---")
    print(f"Workflow: {workflow_path}")
    print(f"PDF to Process: {pdf_path}\n")
    print(f"Using model: {model_name}")

    # Initialize the LLM
    llm = model_registry.get_model(model_name)

    try:
        # 1. Load the JSON workflow
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        
        template_boxes = workflow.get("annotationBoxes", [])
        
        # 2. Open the PDF to be processed
        doc = fitz.open(pdf_path)
        
        # --- Results and Logging ---
        results = {
            "mismatches": [],
            "llm_responses": []
        }
        
        # Cache extracted live boxes per page to avoid re-processing
        live_data_cache = {}

        # 3. Iterate through each box in the workflow template
        for i, template_box in enumerate(template_boxes):
            print(f"\n[Processing Template Box {i}] ID: {template_box['id']}")
            settings = template_box.get("settings", {})

            # 4. Skip boxes where position is not guaranteed
            if settings.get("positionIsNotGuaranteed", False):
                print("  -> Skipping: Position is not guaranteed.")
                continue

            page_num = template_box.get("page", 1) - 1
            if page_num not in live_data_cache:
                print(f"  -> Extracting live data for page {page_num + 1}...")
                page = doc[page_num]
                live_data_cache[page_num] = {
                    "words": [fitz.Rect(w[:4]) for w in page.get_text("words")],
                    "images": [fitz.Rect(img["bbox"]) for img in page.get_image_info()]
                }
            
            live_boxes = live_data_cache[page_num]["words"] + live_data_cache[page_num]["images"]
            template_rect = fitz.Rect(template_box["x"], template_box["y"], 
                                      template_box["x"] + template_box["width"], 
                                      template_box["y"] + template_box["height"])

            # 5. Handle "Must Match Exactly"
            if settings.get("mustMatchExactly", False):
                print("  -> Mode: Must Match Exactly")
                match_found = any(check_overlap(template_rect, live_rect) for live_rect in live_boxes)
                
                if not match_found:
                    print("  -> !! STRICT MISMATCH: No overlapping content found in the document.")
                    results["mismatches"].append({
                        "box_id": template_box["id"],
                        "reason": "No overlapping content found at the specified position."
                    })
                else:
                    print("  -> OK: Overlapping content found.")
            
            # 6. Handle LLM Comparison
            else:
                print("  -> Mode: LLM Comparison")
                page = doc[page_num]
                
                if settings.get("useVisionModel") and settings.get("visionModel") != "None":
                    print("    -> Processing with Vision Model...")
                    
                    # Use the vision task description as the system prompt
                    messages = [SystemMessage(content=settings.get("visionTaskDescription", ""))]
                    
                    # Extract image data
                    crop_rect = fitz.Rect(template_rect)
                    pix = page.get_pixmap(clip=crop_rect, matrix=fitz.Matrix(300 / 72, 300 / 72))
                    img_data = pix.tobytes("png")
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    
                    vision_prompt = {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                    }
                    
                    human_content = [vision_prompt]
                    
                    if settings.get("guideWithTextIfAvailable", False):
                        page_height = page.rect.height
                        page_width = page.rect.width
                        margins = (template_rect.x0, template_rect.y0, page_width - template_rect.x1, page_height - template_rect.y1)
                        extracted_text = pymupdf4llm.to_markdown(doc, pages=[page_num], margins=margins).strip()
                        if extracted_text:
                            human_content.append({"type": "text", "text": f"\n\nAccompanying text for context:\n{extracted_text}"})

                    messages.append(HumanMessage(content=human_content))

                else:
                    print("    -> Processing with Chat Model...")
                    messages = [SystemMessage(content=settings.get("chatTaskDescription", ""))]
                    page_height = page.rect.height
                    page_width = page.rect.width
                    margins = (template_rect.x0, template_rect.y0, page_width - template_rect.x1, page_height - template_rect.y1)
                    extracted_text = pymupdf4llm.to_markdown(doc, pages=[page_num], margins=margins).strip()
                    messages.append(HumanMessage(content=extracted_text))

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

        doc.close()

    except FileNotFoundError:
        print(f"Error: Could not find workflow at {workflow_path} or PDF at {pdf_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run comparison service against a PDF and a workflow.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Name of the model to use.")
    args = parser.parse_args()

    if not Path(JSON_WORKFLOW_PATH).exists() or not Path(PDF_TO_PROCESS_PATH).exists():
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! PLEASE UPDATE 'JSON_WORKFLOW_PATH' AND 'PDF_TO_PROCESS_PATH' !!!")
        print("!!! in backend/scripts/comparison_service.py                !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        run_comparison_service(JSON_WORKFLOW_PATH, PDF_TO_PROCESS_PATH, args.model) 