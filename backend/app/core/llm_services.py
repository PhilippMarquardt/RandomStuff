import asyncio
from typing import List, Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.pydantic_v1 import BaseModel, Field
import os

# Import our MCP tools
from .mcp_tools import AVAILABLE_TOOLS, TOOL_CATEGORIES

# Set OpenAI API key if not already set
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = 


class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In-memory chat history implementation for testing purposes."""
    messages: List[BaseMessage] = Field(default_factory=list)
    
    def add_messages(self, messages: List[BaseMessage]) -> None:
        self.messages.extend(messages)
    
    def clear(self) -> None:
        self.messages = []
    
    class Config:
        arbitrary_types_allowed = True


# Global store for chat histories
_store: Dict[str, InMemoryHistory] = {}


def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    """Get chat history by session ID."""
    if session_id not in _store:
        _store[session_id] = InMemoryHistory()
    return _store[session_id]


class MCPServerManager:
    """Manages MCP server configurations and tool availability."""
    
    def __init__(self):
        self.enabled_servers = {
            "weather": True,
            "utilities": True
        }
        self.tool_mapping = {
            "weather": ["get_weather", "get_weather_forecast"],
            "utilities": ["search_web", "calculate"]
        }
    
    def get_enabled_tools(self) -> List:
        """Get list of enabled tools based on server configurations."""
        enabled_tools = []
        for tool in AVAILABLE_TOOLS:
            # Check if any server that provides this tool is enabled
            tool_name = tool.name
            for server_name, tools in self.tool_mapping.items():
                if tool_name in tools and self.enabled_servers.get(server_name, False):
                    enabled_tools.append(tool)
                    break
        return enabled_tools
    
    def update_server_status(self, server_name: str, enabled: bool):
        """Update the status of an MCP server."""
        if server_name in self.enabled_servers:
            self.enabled_servers[server_name] = enabled
    
    def get_server_status(self) -> Dict[str, bool]:
        """Get the current status of all MCP servers."""
        return self.enabled_servers.copy()


# Global MCP server manager instance
mcp_manager = MCPServerManager()


async def get_llm_response(
    user_message: str,
    temperature: float,
    history: List[Any],
    mcp_servers: Optional[Dict[str, bool]] = None
) -> str:
    """
    Get LLM response using LangGraph agent with MCP tools.
    
    Args:
        user_message: The user's message
        temperature: Model temperature setting
        history: Chat history
        mcp_servers: Optional dictionary of MCP server statuses
        
    Returns:
        str: The LLM response
    """
    try:
        # Update MCP server statuses if provided
        if mcp_servers:
            for server_name, enabled in mcp_servers.items():
                mcp_manager.update_server_status(server_name, enabled)
        
        # Get enabled tools based on MCP server configuration
        enabled_tools = mcp_manager.get_enabled_tools()
        
        # Create the language model
        model = ChatOpenAI(
            temperature=temperature,
            model="gpt-4o-mini"  # You can make this configurable
        )
        
        # Create system message with enhanced context
        system_content = "You are a helpful assistant with access to various tools. Use the available tools when appropriate to provide accurate and helpful responses."
        
        if "Attached Files:" in user_message:
            system_content += " The user has attached files to this conversation. Please analyze the file contents carefully and provide helpful responses based on the attached information. If files contain code, data, or documents, feel free to reference specific parts and provide detailed analysis."
        
        # if enabled_tools:
        #     tool_descriptions = []
        #     for tool in enabled_tools:
        #         tool_descriptions.append(f"- {tool.name}: {tool.description}")
        #     system_content += f"\n\nAvailable tools:\n" + "\n".join(tool_descriptions)
        
        # Create the agent with enabled tools
        if enabled_tools:
            agent = create_react_agent(
                model=model,
                tools=enabled_tools,
                state_modifier=system_content
            )
        else:
            # If no tools are enabled, fall back to direct model interaction
            agent = None
        
        if agent:
            # Convert history to message format for LangGraph
            messages = []
            for msg in history:
                if msg.sender == "user":
                    messages.append(HumanMessage(content=msg.text))
                elif msg.sender == "llm":
                    messages.append(AIMessage(content=msg.text))
            
            # Add the current user message
            messages.append(HumanMessage(content=user_message))
            
            # Invoke the agent
            response = await agent.ainvoke({"messages": messages})
            
            # Extract the final response from the agent's output
            if "messages" in response and response["messages"]:
                last_message = response["messages"][-1]
                if hasattr(last_message, 'content'):
                    return last_message.content
                else:
                    return str(last_message)
            else:
                return "I apologize, but I couldn't generate a response. Please try again."
        
        else:
            # Fallback to direct model interaction without tools
            messages = [SystemMessage(content=system_content)]
            
            for msg in history:
                if msg.sender == "user":
                    messages.append(HumanMessage(content=msg.text))
                elif msg.sender == "llm":
                    messages.append(AIMessage(content=msg.text))
            
            messages.append(HumanMessage(content=user_message))
            
            response = await model.agenerate([messages])
            return response.generations[0][0].text
            
    except Exception as e:
        print(f"Error in get_llm_response: {str(e)}")
        return f"I apologize, but I encountered an error while processing your request: {str(e)}"


def get_available_tools() -> Dict[str, List[str]]:
    """Get information about available MCP tools organized by category."""
    result = {}
    for category, tools in TOOL_CATEGORIES.items():
        result[category] = [
            {
                "name": tool.name,
                "description": tool.description,
                "enabled": any(
                    tool.name in mcp_manager.tool_mapping.get(server, [])
                    and mcp_manager.enabled_servers.get(server, False)
                    for server in mcp_manager.enabled_servers.keys()
                )
            }
            for tool in tools
        ]
    return result


def get_mcp_server_status() -> Dict[str, Any]:
    """Get detailed MCP server status information."""
    return {
        "servers": mcp_manager.get_server_status(),
        "tools": get_available_tools(),
        "total_enabled_tools": len(mcp_manager.get_enabled_tools())
    }
