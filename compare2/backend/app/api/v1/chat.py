from fastapi import APIRouter, HTTPException
from schemas.chat import ChatMessageRequest, ChatMessageResponse
from core.llm_services import get_llm_response, get_available_tools_info
from services.chat_models import chat_model_registry
from typing import List, Dict, Any

router = APIRouter()

@router.get("/models", response_model=List[str])
async def get_available_models():
    """Get a list of available models."""
    return chat_model_registry.get_available_models()

@router.post("/invoke", response_model=ChatMessageResponse)
async def invoke_llm_chat(request: ChatMessageRequest):
    try:
        user_message = request.text
        if request.attachments:
            attachment_context = "\n\nAttached Files:\n"
            for attachment in request.attachments:
                attachment_context += f"--- {attachment.filename} ---\n{attachment.content}\n\n"
            user_message += attachment_context
        
        response_text = await get_llm_response(
            user_message=user_message, 
            temperature=request.temperature,
            history=request.history,
            model_name=request.model_name,
            enabled_tools=request.enabled_tools,
            system_prompt=request.system_prompt
        )
        return ChatMessageResponse(text=response_text)
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@router.get("/tools/list", response_model=List[Dict[str, Any]])
async def list_available_tools():
    """Get a list of all available tools and their default status."""
    try:
        return get_available_tools_info()
    except Exception as e:
        print(f"Error getting tool list: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tool list.")
    

