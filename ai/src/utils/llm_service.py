"""
LLM Service - Clean abstraction for all LangChain operations
Handles chat, tools, file processing, and conversation management
"""
import os
import json
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode
    from typing_extensions import Annotated, TypedDict, Sequence
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    from utils.document_processor import document_service
    DOCUMENT_PROCESSING_AVAILABLE = True
except ImportError:
    DOCUMENT_PROCESSING_AVAILABLE = False

import numpy as np


@dataclass
class ChatMessage:
    """Simple chat message structure"""
    content: str
    role: str  # 'user' or 'assistant'
    timestamp: datetime = field(default_factory=datetime.now)
    files: List[str] = field(default_factory=list)
    file_contents: Dict[str, str] = field(default_factory=dict)


@dataclass
class ChatSession:
    """Chat session with conversation history"""
    id: str
    name: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    system_prompt: str = "You are a helpful AI assistant."


class LLMService:
    """Main LLM service handling all AI interactions"""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.current_session_id: Optional[str] = None
        self.agent = None
        self._tools_registry = {}
        self._setup_default_tools()
        
    def _setup_default_tools(self):
        """Setup default tools for the AI assistant"""
        if not LANGCHAIN_AVAILABLE:
            return
            
        @tool
        def get_current_weather(location: str) -> str:
            """Get the current weather for a given location."""
            weather_data = {
                "new york": "Sunny, 72°F",
                "san francisco": "It's sunny in San Francisco, but you better look out if you're a Gemini 😈.",
                "london": "Cloudy, 15°C", 
                "tokyo": "Rainy, 20°C",
                "paris": "Partly cloudy, 18°C"
            }
            location_lower = location.lower()
            for city in weather_data:
                if city in location_lower:
                    return weather_data[city]
            return f"Weather data not available for {location}"

        @tool
        def create_sample_chart(chart_type: str, data_points: int = 10) -> Dict[str, Any]:
            """Create a sample chart with specified type and number of data points."""
            # Generate sample data
            x_data = list(range(data_points))
            y_data = np.random.randint(10, 100, data_points).tolist()
            
            return {
                "success": True,
                "message": f"Created a {chart_type} chart with {data_points} data points",
                "chart_data": {"x": x_data, "y": y_data, "type": chart_type}
            }

        @tool
        def calculate_metrics(numbers: List[float]) -> Dict[str, float]:
            """Calculate basic statistical metrics for a list of numbers."""
            if not numbers:
                return {"error": "No numbers provided"}
            
            return {
                "count": len(numbers),
                "sum": sum(numbers),
                "mean": sum(numbers) / len(numbers),
                "min": min(numbers),
                "max": max(numbers),
                "range": max(numbers) - min(numbers)
            }
        
        # Register tools
        self._tools_registry = {
            'get_current_weather': get_current_weather,
            'create_sample_chart': create_sample_chart,
            'calculate_metrics': calculate_metrics
        }
    
    def _create_agent(self, system_prompt: str) -> Optional[Any]:
        """Create a new LangGraph agent with the given system prompt"""
        if not LANGCHAIN_AVAILABLE:
            return None
            
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or api_key == "your_openai_api_key_here":
                return None
                
            # Initialize model with vision support
            model = ChatOpenAI(
                model="gpt-5-mini",  # Use gpt-4o for vision and text (guaranteed vision support)
                
                max_tokens=int(os.getenv("MAX_TOKENS", "2000")),
                api_key=api_key
            )
            
            # Get tools
            tools = list(self._tools_registry.values())
            model_with_tools = model.bind_tools(tools)
            
            # Define agent state
            class AgentState(TypedDict):
                messages: Annotated[Sequence[BaseMessage], add_messages]
            
            # Define tool node
            def tool_node(state: AgentState):
                outputs = []
                for tool_call in state["messages"][-1].tool_calls:
                    try:
                        tool_result = self._tools_registry[tool_call["name"]].invoke(tool_call["args"])
                        outputs.append(
                            ToolMessage(
                                content=json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result),
                                name=tool_call["name"],
                                tool_call_id=tool_call["id"],
                            )
                        )
                    except Exception as e:
                        outputs.append(
                            ToolMessage(
                                content=f"Error using tool {tool_call['name']}: {str(e)}",
                                name=tool_call["name"],
                                tool_call_id=tool_call["id"],
                            )
                        )
                return {"messages": outputs}
            
            # Define model node
            def call_model(state: AgentState):
                system_message = SystemMessage(system_prompt)
                response = model_with_tools.invoke([system_message] + state["messages"])
                return {"messages": [response]}
            
            # Define conditional edge
            def should_continue(state: AgentState):
                messages = state["messages"]
                last_message = messages[-1]
                if not last_message.tool_calls:
                    return "end"
                else:
                    return "continue"
            
            # Create the graph
            workflow = StateGraph(AgentState)
            
            # Add nodes
            workflow.add_node("agent", call_model)
            workflow.add_node("tools", tool_node)
            
            # Set entry point
            workflow.set_entry_point("agent")
            
            # Add conditional edges
            workflow.add_conditional_edges(
                "agent",
                should_continue,
                {
                    "continue": "tools",
                    "end": END,
                },
            )
            
            # Add edge from tools back to agent
            workflow.add_edge("tools", "agent")
            
            # Compile the graph
            return workflow.compile()
            
        except Exception as e:
            # Log quietly without printing unicode that may break some consoles
            try:
                msg = str(e)
            except Exception:
                msg = "Exception in _create_agent"
            # Use ascii-safe replacement
            print(msg.encode('ascii', 'replace').decode('ascii'))
            return None
    
    def create_session(self, name: str = None, system_prompt: str = None) -> str:
        """Create a new chat session"""
        session_id = f"chat_{len(self.sessions) + 1}"
        if name is None:
            name = f"Chat {len(self.sessions) + 1}"
        
        if system_prompt is None:
            system_prompt = "You are a helpful AI assistant. You can help with weather information, create charts, and calculate statistics. Be conversational and helpful!"
        
        session = ChatSession(
            id=session_id,
            name=name,
            system_prompt=system_prompt
        )
        
        self.sessions[session_id] = session
        self.current_session_id = session_id
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID"""
        return self.sessions.get(session_id)
    
    def get_current_session(self) -> Optional[ChatSession]:
        """Get the current active session"""
        if self.current_session_id:
            return self.sessions.get(self.current_session_id)
        return None
    
    def set_current_session(self, session_id: str) -> bool:
        """Set the current active session"""
        if session_id in self.sessions:
            self.current_session_id = session_id
            return True
        return False
    
    def list_sessions(self) -> List[ChatSession]:
        """List all chat sessions"""
        return list(self.sessions.values())
    
    def process_uploaded_files(self, file_contents: List[str], filenames: List[str]) -> Tuple[str, Dict[str, str]]:
        """Process uploaded files and return context string and file content mapping"""
        if not file_contents or not filenames:
            return "", {}
        
        file_context = ""
        file_content_map = {}
        
        for content, filename in zip(file_contents, filenames):
            if not content or not filename:
                continue
                
            try:
                # Check if it's an image file
                if self._is_image_file(filename):
                    # For images, store the raw base64 data for GPT-4V
                    file_content_map[filename] = content  # Store the full data:image/...;base64,... string
                    file_context += f"\n\n[Image uploaded: {filename}] - Image will be processed by AI vision capabilities."
                    continue
                
                # For non-image files, process with document service if available
                if not DOCUMENT_PROCESSING_AVAILABLE:
                    file_context += f"\n\n[File uploaded: {filename}] - Document processing not available."
                    file_content_map[filename] = f"File {filename} uploaded but document processing not available."
                    continue
                
                # Decode file contents
                content_type, content_string = content.split(',')
                decoded = base64.b64decode(content_string)
                
                # Save file temporarily
                temp_file_path = document_service.save_uploaded_file(decoded, filename)
                
                # Process the document
                result = document_service.process_file(temp_file_path)
                
                if result['success']:
                    # Get document summary
                    summary = document_service.get_document_summary(result['documents'])
                    file_ctx = f"\n\n[File uploaded: {filename}]\n{summary}"
                    
                    # Store full document content
                    full_content = "\n\n".join([doc.page_content for doc in result['documents']])
                    file_ctx += f"\n\nFull document content:\n{full_content}"
                    
                    file_context += file_ctx
                    file_content_map[filename] = full_content
                else:
                    error_ctx = f"\n\n[File upload error for {filename}: {result['error']}]"
                    file_context += error_ctx
                    file_content_map[filename] = f"Error processing file: {result['error']}"
                
                # Clean up temporary file
                document_service.cleanup_file(temp_file_path)
                
            except Exception as e:
                error_ctx = f"\n\n[File processing error for {filename}: {str(e)}]"
                file_context += error_ctx
                file_content_map[filename] = f"Error processing file: {str(e)}"
        
        return file_context, file_content_map
    
    def _get_previous_file_context(self, session: ChatSession, exclude_current_message: bool = True) -> str:
        """Get context from all previously uploaded NON-IMAGE files in the session"""
        if not DOCUMENT_PROCESSING_AVAILABLE:
            return ""
        
        previous_contexts = []
        
        # Skip the last message if exclude_current_message is True (to avoid duplicate processing)
        messages_to_check = session.messages[:-1] if exclude_current_message and session.messages else session.messages
        
        for message in messages_to_check:
            if message.role == "user" and message.file_contents:
                for filename, content in message.file_contents.items():
                    # Skip images - they should be handled as image_url content parts
                    if self._is_image_file(filename):
                        continue
                        
                    # Only include non-image files as text context
                    if content and content.strip() and not content.startswith("Error") and not content.startswith("data:image/"):
                        previous_contexts.append(f"\n\n[Previously uploaded file: {filename}]\nFull content:\n{content}")
                    else:
                        previous_contexts.append(f"\n\n[Previously uploaded file: {filename} - content not available]")
        
        return "".join(previous_contexts)
    
    def add_user_message(self, message: str, file_contents: List[str] = None, filenames: List[str] = None, 
                        session_id: str = None) -> Tuple[ChatMessage, str]:
        """
        Add a user message to the session (for immediate display)
        
        Returns:
            Tuple of (user_message, session_id)
        """
        # Get or create session
        if session_id:
            session = self.get_session(session_id)
            if not session:
                session_id = self.create_session()
                session = self.get_session(session_id)
        else:
            session = self.get_current_session()
            if not session:
                session_id = self.create_session()
                session = self.get_session(session_id)
        
        # Process uploaded files
        file_context = ""
        file_content_map = {}
        
        if file_contents and filenames:
            file_context, file_content_map = self.process_uploaded_files(file_contents, filenames)
        
        # Create user message
        user_message = ChatMessage(
            content=message,
            role="user",
            files=filenames or [],
            file_contents=file_content_map
        )
        
        # Add to session
        session.messages.append(user_message)
        
        return user_message, session_id

    def get_ai_response(self, session_id: str = None) -> Tuple[str, bool]:
        """
        Generate AI response for the last user message in the session
        
        Returns:
            Tuple of (response_text, success)
        """
        # Get session
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if not session or not session.messages:
            return "No session or messages found", False
        
        # Get AI response
        if not LANGCHAIN_AVAILABLE:
            response = "I'm sorry, but I need an OpenAI API key to function. Please add your API key to the .env file."
            ai_message = ChatMessage(content=response, role="assistant")
            session.messages.append(ai_message)
            return response, False
        
        # Create or get agent
        agent = self._create_agent(session.system_prompt)
        if not agent:
            response = "I'm sorry, but I couldn't initialize the AI agent. Please check your OpenAI API key."
            ai_message = ChatMessage(content=response, role="assistant")
            session.messages.append(ai_message)
            return response, False
        
        try:
            # Prepare messages for the agent (last 10 for context)
            messages = []
            recent_messages = session.messages[-10:]  # Get last 10 messages
            
            for msg in recent_messages:
                if msg.role == "user":
                    # Handle images and files properly with multimodal content
                    message_content = self._prepare_user_message_content(msg, session)
                    print(f"\n=== DEBUG: USER MESSAGE CONTENT ===")
                    if isinstance(message_content, list):
                        print(f"Content parts: {len(message_content)}")
                        for i, part in enumerate(message_content):
                            if part["type"] == "text":
                                print(f"Part {i}: TEXT - {part['text'][:200]}...")
                            elif part["type"] == "image_url":
                                print(f"Part {i}: IMAGE - URL length: {len(part['image_url']['url'])}")
                    else:
                        print(f"Simple text: {message_content[:200]}...")
                    print("=== END DEBUG ===\n")
                    
                    messages.append(HumanMessage(content=message_content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))
            
            # Run the agent
            result = agent.invoke({"messages": messages})
            
            # Extract AI response
            ai_response = ""
            for msg in result["messages"]:
                if isinstance(msg, AIMessage) and msg.content:
                    ai_response = msg.content
                    break
            
            if not ai_response:
                ai_response = "I apologize, but I couldn't generate a proper response. Please try again."
            
            # Create AI message
            ai_message = ChatMessage(content=ai_response, role="assistant")
            session.messages.append(ai_message)
            
            return ai_response, True
            
        except Exception as e:
            error_response = f"Sorry, I encountered an error: {str(e)}"
            ai_message = ChatMessage(content=error_response, role="assistant")
            session.messages.append(ai_message)
            return error_response, False

    def _prepare_user_message_content(self, message: ChatMessage, session: ChatSession) -> Any:
        """
        Prepare user message content with direct image handling for gpt-4o
        """
        # Start with content parts list for multimodal support
        content_parts = []
        
        # Add text content
        if message.content.strip():
            content_parts.append({
                "type": "text",
                "text": message.content
            })
        
        # Add ONLY the files from THIS message (not previous context)
        if message.files and message.file_contents:
            for filename in message.files:
                if self._is_image_file(filename) and filename in message.file_contents:
                    # For images, pass the data URL directly to gpt-4o
                    file_content = message.file_contents[filename]
                    
                    if file_content.startswith('data:image/'):
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": file_content
                            }
                        })
                    else:
                        # Fallback
                        content_parts.append({
                            "type": "text",
                            "text": f"\n\n[Image file: {filename}] - Could not process image"
                        })
                else:
                    # Non-image files - add as text context
                    if filename in message.file_contents:
                        file_content = message.file_contents[filename]
                        content_parts.append({
                            "type": "text",
                            "text": f"\n\n[File: {filename}]\n{file_content}"
                        })
        
        # Return the content parts for multimodal or single text
        if len(content_parts) == 1 and content_parts[0]["type"] == "text":
            return content_parts[0]["text"]
        else:
            return content_parts

    def _is_image_file(self, filename: str) -> bool:
        """Check if file is an image"""
        if not filename:
            return False
        image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')
        return filename.lower().endswith(image_extensions)
    
    def update_system_prompt(self, system_prompt: str, session_id: str = None):
        """Update the system prompt for a session"""
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if session:
            session.system_prompt = system_prompt
    
    def clear_session(self, session_id: str = None):
        """Clear messages from a session"""
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if session:
            session.messages = []
    
    def delete_session(self, session_id: str):
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.current_session_id == session_id:
                # Set current to the first available session or None
                if self.sessions:
                    self.current_session_id = list(self.sessions.keys())[0]
                else:
                    self.current_session_id = None
    
    def export_session(self, session_id: str = None) -> Dict[str, Any]:
        """Export session data for persistence"""
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if not session:
            return {}
        
        return {
            'id': session.id,
            'name': session.name,
            'system_prompt': session.system_prompt,
            'created_at': session.created_at.isoformat(),
            'messages': [
                {
                    'content': msg.content,
                    'role': msg.role,
                    'timestamp': msg.timestamp.isoformat(),
                    'files': msg.files,
                    'file_contents': msg.file_contents
                }
                for msg in session.messages
            ]
        }
    
    def import_session(self, session_data: Dict[str, Any]) -> str:
        """Import session data from persistence"""
        try:
            session = ChatSession(
                id=session_data['id'],
                name=session_data['name'],
                system_prompt=session_data.get('system_prompt', 'You are a helpful AI assistant.'),
                created_at=datetime.fromisoformat(session_data.get('created_at', datetime.now().isoformat()))
            )
            
            for msg_data in session_data.get('messages', []):
                message = ChatMessage(
                    content=msg_data['content'],
                    role=msg_data['role'],
                    timestamp=datetime.fromisoformat(msg_data.get('timestamp', datetime.now().isoformat())),
                    files=msg_data.get('files', []),
                    file_contents=msg_data.get('file_contents', {})
                )
                session.messages.append(message)
            
            self.sessions[session.id] = session
            return session.id
            
        except Exception as e:
            try:
                msg = str(e)
            except Exception:
                msg = "Exception while importing session"
            print(msg.encode('ascii', 'replace').decode('ascii'))
            return ""
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools for display"""
        if not LANGCHAIN_AVAILABLE:
            return []
        
        tools_info = []
        for name, tool in self._tools_registry.items():
            tools_info.append({
                'name': name,
                'description': tool.description or 'No description available'
            })
        
        return tools_info


# Global service instance
llm_service = LLMService()
