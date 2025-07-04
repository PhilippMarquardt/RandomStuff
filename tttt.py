import argparse
import asyncio
import sys
import os
import json
import base64
import fitz  # PyMuPDF

# Add the backend directory to the Python path to resolve `app` module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pymupdf4llm
from app.services.chat_models import chat_model_registry
from langchain_core.messages import HumanMessage, SystemMessage

SYSTEM_PROMPT = """
You are an expert system that converts unstructured document content into a structured JSON format.
Your task is to analyze the content of a single PDF page, provided to you as both text extracted via OCR/text extraction and an image of the page.
You must use both the text and the image to create a clean, hierarchical JSON object. The image is the ground truth. The text can be used to copy-paste content.
The content can be anything: text, tables, charts, forms, etc. It can have a single-column or multi-column layout.

**JSON Structure Requirements:**

1.  The root of the JSON should be an object.
2.  Identify the main headline or title of the page from the image and use it for a "title" field. If no clear title exists, use a concise summary of the page content as the title.
3.  Identify logical sections on the page based on the visual layout in the image. Each section should be a key in the JSON object. Use descriptive keys based on the section's heading or content.
4.  For each section, capture its content, using the image as a reference for structure and the text for the data.
    *   If it's a table, represent it as an array of objects, where each object is a row.
    *   If it's a chart, describe the chart type, its title, labels, and data points as seen in the image.
    *   If it's a list, use a JSON array.
    *   If it's simple text, store it as a string value.
    *   If it's a key-value pair, represent it as a JSON object.
5.  Preserve the hierarchy. If there are nested sections or elements, reflect that in the JSON structure.
6.  If the page has a multi-column layout, analyze the image to process each column's content separately and then merge them logically under appropriate sections.

**Output Format:**

*   Your output MUST be a single, well-formed JSON object.
*   Do not include any explanations or text outside of the JSON object.
"""

async def process_pdf(pdf_path: str):
    """
    Processes a PDF file, page by page, converting each page's content to JSON using an LLM.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
        return

    print(f"Processing {pdf_path}...")

    doc_fitz = fitz.open(pdf_path)

    # Get the model instance directly from the registry
    model = chat_model_registry.get_model("gpt-4o-mini", temperature=0.1)

    total_input_tokens = 0
    total_output_tokens = 0

    for i in range(len(doc_fitz)):
        page_number = i + 1
        print(f"--- Processing Page {page_number} ---")

        page = doc_fitz[i]
        
        # 1. Extract text for the single page
        page_text = pymupdf4llm.to_markdown(doc_fitz, pages=[i])
        
        # 2. Get the page image
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("png")
        img_base64 = base64.b64encode(img_data).decode('utf-8')

        try:
            # 3. Construct messages with the corrected structure
            system_message = SystemMessage(content=SYSTEM_PROMPT)
            human_content = [
                {"type": "text", "text": "Here is the extracted text for the page:\n" + page_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                }
            ]
            human_message = HumanMessage(content=human_content)

            # 4. Invoke the model directly
            response = await model.ainvoke([system_message, human_message])
            llm_response = response.content
            print(response)
            # 5. Track token usage from response metadata
            if hasattr(response, 'response_metadata') and 'token_usage' in response.response_metadata:
                token_usage = response.response_metadata['token_usage']
                input_tokens = token_usage.get('prompt_tokens', 0)
                output_tokens = token_usage.get('completion_tokens', 0)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                print(f"Page {page_number} Tokens: Input={input_tokens}, Output={output_tokens}")

            # Clean up the response to ensure it's valid JSON
            # The model might sometimes wrap the JSON in ```json ... ```
            clean_response = llm_response.strip().removeprefix("```json").removesuffix("```").strip()

            # Try to parse and print the JSON
            try:
                json_output = json.loads(clean_response)
                print(json.dumps(json_output, indent=2))
            except json.JSONDecodeError:
                print("Error: LLM did not return a valid JSON object.")
                print("Raw response:")
                print(llm_response)

        except Exception as e:
            print(f"An error occurred while processing page {page_number}: {e}")
    
    doc_fitz.close()
    print("--- Finished processing all pages. ---")

    print("\n--- Total Token Usage ---")
    print(f"Total Input Tokens:  {total_input_tokens}")
    print(f"Total Output Tokens: {total_output_tokens}")
    print(f"Total Combined Tokens: {total_input_tokens + total_output_tokens}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDF pages to structured JSON using an LLM.")
    parser.add_argument("pdf_path", help="The full path to the PDF file to process.")
    args = parser.parse_args()

    asyncio.run(process_pdf(args.pdf_path)) 