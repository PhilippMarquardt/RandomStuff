from fastapi import APIRouter, HTTPException
from schemas.chat import ChatMessageRequest, ChatMessageResponse
from core.llm_services import get_llm_response, get_mcp_server_status, get_available_tools
from langchain_openai import OpenAI
from typing import Dict, Any
from pydantic import BaseModel


router = APIRouter()
llm = OpenAI(model_name = "gpt-3.5-turbo-instruct")


class MCPServerUpdateRequest(BaseModel):
    servers: Dict[str, bool]


@router.post("/invoke", response_model=ChatMessageResponse)
async def invoke_llm_chat(request: ChatMessageRequest):
    try:
        print("Processing chat request with MCP tools")
        
        # Process attachments and add them to the context
        user_message = request.text
        if request.attachments:
            attachment_context = "\n\nAttached Files:\n"
            for attachment in request.attachments:
                attachment_context += f"\n--- {attachment.filename} ({attachment.content_type}) ---\n"
                attachment_context += attachment.content
                attachment_context += "\n" + "-" * 50 + "\n"
            
            # Add attachment context to the user message
            user_message = user_message + attachment_context
        
        # Extract MCP server configuration from request if available
        mcp_servers = getattr(request, 'mcp_servers', None)
        
        response_text = await get_llm_response(
            user_message=user_message, 
            temperature=request.temperature,
            history=request.history,
            mcp_servers=mcp_servers
        )
        return ChatMessageResponse(text=response_text)
    except ValueError as ve:
        # This can happen if API key is missing
        raise HTTPException(status_code=500, detail=str(ve))
    except Exception as e:
        # Catch any other exceptions from the LLM service
        print(f"Unhandled error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.") 


@router.get("/mcp/status")
async def get_mcp_status() -> Dict[str, Any]:
    """Get the current status of MCP servers and available tools."""
    try:
        return get_mcp_server_status()
    except Exception as e:
        print(f"Error getting MCP status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get MCP server status")


@router.get("/mcp/tools")
async def get_tools() -> Dict[str, Any]:
    """Get information about available MCP tools."""
    try:
        return get_available_tools()
    except Exception as e:
        print(f"Error getting tools: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tool information")


@router.post("/mcp/servers/update")
async def update_mcp_servers(request: MCPServerUpdateRequest) -> Dict[str, Any]:
    """Update MCP server configurations."""
    try:
        # Import here to avoid circular imports
        from core.llm_services import mcp_manager
        
        # Update server statuses
        for server_name, enabled in request.servers.items():
            mcp_manager.update_server_status(server_name, enabled)
        
        # Return updated status
        return {
            "message": "MCP server configurations updated successfully",
            "status": get_mcp_server_status()
        }
    except Exception as e:
        print(f"Error updating MCP servers: {e}")
        raise HTTPException(status_code=500, detail="Failed to update MCP server configurations")
    

