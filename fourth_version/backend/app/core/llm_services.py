import asyncio
from typing import List, Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.pydantic_v1 import BaseModel, Field
import os

# Import our MCP tools
from .mcp_tools import AVAILABLE_TOOLS
os.environ["OPENAI_API_KEY"] = 

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


def get_available_tools_info() -> List[Dict[str, Any]]:
    """Returns a list of all available tools with their details."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "enabled": True  # Default to enabled on the frontend
        }
        for tool in AVAILABLE_TOOLS
    ]


async def get_llm_response(
    user_message: str,
    temperature: float,
    history: List[Any],
    enabled_tools: Optional[List[str]] = None,
    system_prompt: Optional[str] = "You are a helpful assistant."
) -> str:
    """
    Get LLM response using LangGraph agent with selected tools.
    
    Args:
        user_message: The user's message
        temperature: Model temperature setting
        history: Chat history
        enabled_tools: Optional list of names of enabled tools
        system_prompt: Optional system prompt to guide the AI
        
    Returns:
        str: The LLM response
    """
    try:
        # Filter the available tools based on the names provided in the request
        if enabled_tools is None:
            # If the client provides no selection, use all available tools by default
            tools_to_use = AVAILABLE_TOOLS
        else:
            tools_to_use = [
                tool for tool in AVAILABLE_TOOLS if tool.name in enabled_tools
            ]

        # Create the language model
        model = ChatOpenAI(
            temperature=temperature,
            model="gpt-4o-mini"
        )
        
        # Use the provided system prompt or the default
        system_content = system_prompt if system_prompt else "You are a helpful assistant. Use the available tools to provide accurate responses."
        
        if "Attached Files:" in user_message:
            system_content += " The user has attached files. Analyze them carefully."
        
        # Create the agent with the selected tools
        agent = create_react_agent(
            model=model,
            tools=tools_to_use,
            state_modifier=system_content
        )

        # Convert history to message format for LangGraph
        messages = []
        for msg in history:
            if msg.sender == "user":
                messages.append(HumanMessage(content=msg.text))
            elif msg.sender == "llm":
                messages.append(AIMessage(content=msg.text))
        
        messages.append(HumanMessage(content=user_message))
        
        # Invoke the agent
        response = await agent.ainvoke({"messages": messages})
        
        if "messages" in response and response["messages"]:
            last_message = response["messages"][-1]
            print(last_message.content)
            return last_message.content if hasattr(last_message, 'content') else str(last_message)
            
        return "I apologize, but I couldn't generate a response."

    except Exception as e:
        print(f"Error in get_llm_response: {str(e)}")
        return f"An error occurred: {str(e)}"
