#!/usr/bin/env python3
"""
Debug script for testing vision LLM capabilities
Edit the variables below to test different images and prompts
"""

import base64
from pathlib import Path
from app.services.chat_models import model_registry
from langchain_core.messages import HumanMessage, SystemMessage
import json

# ============================================================
# EDIT THESE VARIABLES
# ============================================================

# Path to your image file (PNG, JPG, etc.)
IMAGE_PATH = r"C:\Users\pmarq\source\repos\CoreAI\backend\scripts\debug_comparison_20250626_140652\box_grouped-1750938673053-k5dc7b3mo_doc2_FOUND_page1.png"

# The model to use (e.g., "gpt-4o-mini", "gpt-4-vision-preview", etc.)
MODEL_NAME = "gpt-4o-mini"

# System prompt (optional)
SYSTEM_PROMPT = "You are a helpful assistant that can analyze images."

# User prompt/question about the image
USER_PROMPT = """
Extract the sustainability rating of this graph. The rating is the letter in the green box
"""

# Whether to save the response to a file
SAVE_RESPONSE = True
OUTPUT_FILE = "vision_debug_response.json"

# ============================================================
# SCRIPT LOGIC (Don't need to edit below)
# ============================================================

def load_image_as_base64(image_path: str) -> str:
    """Load an image file and convert to base64"""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    with open(path, 'rb') as f:
        image_bytes = f.read()
    
    return base64.b64encode(image_bytes).decode('utf-8')


def test_vision_llm():
    """Test the vision LLM with the configured image and prompt"""
    print("="*60)
    print("VISION LLM DEBUG TEST")
    print("="*60)
    
    print(f"\nConfiguration:")
    print(f"  Image: {IMAGE_PATH}")
    print(f"  Model: {MODEL_NAME}")
    print(f"  System Prompt: {SYSTEM_PROMPT[:50]}..." if len(SYSTEM_PROMPT) > 50 else f"  System Prompt: {SYSTEM_PROMPT}")
    print(f"  User Prompt: {USER_PROMPT[:50]}..." if len(USER_PROMPT) > 50 else f"  User Prompt: {USER_PROMPT}")
    
    try:
        # Load image
        print("\nLoading image...")
        image_b64 = load_image_as_base64(IMAGE_PATH)
        print(f"  Image loaded successfully (size: {len(image_b64)} base64 chars)")
        
        # Initialize model
        print(f"\nInitializing model: {MODEL_NAME}")
        llm = model_registry.get_model(MODEL_NAME)
        print("  Model initialized")
        
        # Build messages
        messages = []
        if SYSTEM_PROMPT:
            messages.append(SystemMessage(content=SYSTEM_PROMPT))
        
        # Create content with text and image
        content = [
            {"type": "text", "text": USER_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
        ]
        messages.append(HumanMessage(content=content))
        
        # Call LLM
        print("\nCalling LLM...")
        response = llm.invoke(messages)
        
        print("\n" + "="*60)
        print("RESPONSE:")
        print("="*60)
        print(response.content)
        print("="*60)
        
        # Save response if requested
        if SAVE_RESPONSE:
            output_data = {
                "configuration": {
                    "image_path": IMAGE_PATH,
                    "model": MODEL_NAME,
                    "system_prompt": SYSTEM_PROMPT,
                    "user_prompt": USER_PROMPT
                },
                "response": response.content,
                "metadata": {
                    "response_length": len(response.content),
                    "image_size_b64": len(image_b64)
                }
            }
            
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\nResponse saved to: {OUTPUT_FILE}")
        
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("Please check the IMAGE_PATH variable")
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def test_multiple_images():
    """Test with multiple images in one prompt"""
    print("\n" + "="*60)
    print("TESTING MULTIPLE IMAGES")
    print("="*60)
    
    # Configure multiple images here
    IMAGE_PATHS = [
        "path/to/image1.png",
        "path/to/image2.png"
    ]
    
    MULTI_PROMPT = """
    Compare these two images and describe the differences between them.
    """
    
    try:
        # Load all images
        images_b64 = []
        for path in IMAGE_PATHS:
            print(f"Loading {path}...")
            img_b64 = load_image_as_base64(path)
            images_b64.append(img_b64)
        
        # Build content with multiple images
        content = [{"type": "text", "text": MULTI_PROMPT}]
        for i, img_b64 in enumerate(images_b64):
            content.append({"type": "text", "text": f"\n\nImage {i+1}:"})
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}})
        
        # Initialize model and call
        llm = model_registry.get_model(MODEL_NAME)
        messages = [
            SystemMessage(content="You are an expert at comparing visual content."),
            HumanMessage(content=content)
        ]
        
        response = llm.invoke(messages)
        
        print("\nRESPONSE:")
        print(response.content)
        
    except Exception as e:
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    # Run single image test
    test_vision_llm()
    
    # Uncomment to test multiple images
    # test_multiple_images() 