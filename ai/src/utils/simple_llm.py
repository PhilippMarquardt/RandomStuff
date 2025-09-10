"""
SIMPLE LLM Service - No overcomplicated BS, just works like ChatGPT
"""
import os
import json
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

import numpy as np

try:
    from utils.document_processor import document_service
    DOCUMENT_PROCESSING_AVAILABLE = True
except ImportError:
    DOCUMENT_PROCESSING_AVAILABLE = False

try:
    from utils.model_registry import model_registry
    MODEL_REGISTRY_AVAILABLE = True
except ImportError:
    MODEL_REGISTRY_AVAILABLE = False


class SimpleChatSession:
    def __init__(self):
        self.messages = []  # List of {"role": "user/assistant", "content": str/list, "files": [...]}
        self.system_prompt = """You are a helpful AI assistant with vision capabilities. You can analyze images and process documents. 

Available tools:
- get_current_weather: Get weather information for any location
- create_sample_chart: Generate sample charts with data visualization
- calculate_metrics: Calculate statistical metrics for numbers
- create_dash_graph: Create interactive graphs and charts that render directly in the chat window

IMPORTANT: When users ask for graphs, charts, or data visualization, you MUST use the create_dash_graph tool. Do NOT generate markdown images, base64 images, or describe charts - use the tool to create actual interactive Dash components.

Examples:
- User: "Create a line chart of sales data" → Use create_dash_graph with graph_type="line"
- User: "Show me a bar chart" → Use create_dash_graph with graph_type="bar"  
- User: "Make a pie chart" → Use create_dash_graph with graph_type="pie"

After using the create_dash_graph tool, DO NOT add markdown images like ![Chart](#) - the tool will automatically render the interactive chart in the interface. Just describe what you created in text.

Use these tools when appropriate to help users with their requests. Be conversational and helpful."""
    
    def add_user_message(self, text: str, files: List[str] = None, file_contents: List[str] = None):
        """Add a user message with optional file attachments"""
        content_parts = []
        
        # Add text
        if text.strip():
            content_parts.append({"type": "text", "text": text.strip()})
        
        # Process files
        processed_files = []
        if files and file_contents:
            for filename, file_data in zip(files, file_contents):
                if not filename or not file_data:
                    continue
                    
                if self._is_image(filename):
                    # Image file
                    if file_data.startswith('data:image/'):
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": file_data}
                        })
                        processed_files.append(filename)
                else:
                    # Document file - process it
                    doc_content = self._process_document(file_data, filename)
                    if doc_content:
                        # Add document content for AI but don't show in UI
                        content_parts.append({
                            "type": "text", 
                            "text": f"\n\n[Document: {filename}]\n{doc_content}",
                            "display": False  # Hide from UI display
                        })
                        processed_files.append(filename)
        
        # Store message
        message = {
            "role": "user",
            "content": content_parts if len(content_parts) > 1 or (content_parts and content_parts[0]["type"] != "text") else text.strip(),
            "files": processed_files,
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages.append(message)
        print(f"Added user message: {len(content_parts)} parts, files: {processed_files}")
        
        return message
    
    def add_ai_message(self, text: str):
        """Add an AI response"""
        message = {
            "role": "assistant", 
            "content": text,
            "files": [],
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(message)
        return message
    
    def _is_image(self, filename: str) -> bool:
        """Check if file is an image"""
        return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'))
    
    def _process_document(self, file_data: str, filename: str) -> str:
        """Process a document file and return its text content"""
        if not DOCUMENT_PROCESSING_AVAILABLE:
            return f"Document processing not available for {filename}"
        
        try:
            # Decode base64 file data
            if ',' in file_data:
                content_string = file_data.split(',')[1]
                decoded = base64.b64decode(content_string)
                
                # Save temporarily
                temp_path = document_service.save_uploaded_file(decoded, filename)
                
                # Process
                result = document_service.process_file(temp_path)
                
                # Clean up
                document_service.cleanup_file(temp_path)
                
                if result['success'] and result['documents']:
                    # Get all document content - NO LIMITS
                    content = "\n".join([doc.page_content for doc in result['documents']])
                    # Clean encoding issues aggressively
                    content = content.encode('ascii', errors='ignore').decode('ascii')
                    return content  # Use FULL document content
                else:
                    return f"Error processing {filename}: {result.get('error', 'Unknown error')}"
                    
        except Exception as e:
            return f"Error processing {filename}: {str(e)}"
        
        return f"Could not process {filename}"


class SimpleLLM:
    def __init__(self):
        self.sessions = {}  # Dict of session_id -> SimpleChatSession
        self.current_session_id = None
        self.model = None
        self.agent = None
        self.tools = []
        self.current_model_name = "gpt-5-mini"  # Default model
        self._setup_tools()
        self._init_model()
        
        # Create initial session
        self.create_new_session()
    
    def _setup_tools(self):
        """Setup tools for the AI assistant"""
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
        
        @tool
        def create_dash_graph(graph_type: str, data: Dict[str, Any], title: str = "Chart", x_label: str = "X", y_label: str = "Y") -> Dict[str, Any]:
            """Create a Dash graph component that will be rendered in the chat window.
            
            Args:
                graph_type: Type of graph ('line', 'bar', 'scatter', 'pie', 'histogram')
                data: Dictionary containing graph data. For most charts: {'x': [...], 'y': [...]}. For pie: {'labels': [...], 'values': [...]}
                title: Title for the chart
                x_label: Label for x-axis
                y_label: Label for y-axis
            
            Returns:
                Dictionary with graph configuration for Dash rendering
            """
            try:
                # Validate graph type
                valid_types = ['line', 'bar', 'scatter', 'pie', 'histogram']
                if graph_type not in valid_types:
                    return {"error": f"Invalid graph type. Must be one of: {valid_types}"}
                
                # Prepare graph configuration
                graph_config = {
                    "type": "dash_graph",
                    "graph_type": graph_type,
                    "title": title,
                    "x_label": x_label,
                    "y_label": y_label,
                    "data": data,
                    "success": True,
                    "message": f"Created {graph_type} chart: {title}"
                }
                
                # Validate data structure based on graph type
                if graph_type == 'pie':
                    if not ('labels' in data and 'values' in data):
                        return {"error": "Pie charts require 'labels' and 'values' in data"}
                    if len(data['labels']) != len(data['values']):
                        return {"error": "Labels and values must have the same length"}
                elif graph_type == 'histogram':
                    if 'values' not in data:
                        return {"error": "Histogram requires 'values' in data"}
                else:
                    if not ('x' in data and 'y' in data):
                        return {"error": f"{graph_type} charts require 'x' and 'y' in data"}
                    if len(data['x']) != len(data['y']):
                        return {"error": "X and Y data must have the same length"}
                
                return graph_config
                
            except Exception as e:
                return {"error": f"Error creating graph: {str(e)}"}
        
        self.tools = [get_current_weather, create_sample_chart, calculate_metrics, create_dash_graph]
    
    def _init_model(self):
        """Initialize model using model registry"""
        if not LANGCHAIN_AVAILABLE:
            print("LangChain not available")
            return
        
        if not MODEL_REGISTRY_AVAILABLE:
            print("Model registry not available, falling back to direct initialization")
            self._init_model_fallback()
            return
            
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            print("No OpenAI API key found")
            return
        
        try:
            # Use model registry to get the model
            self.model = model_registry.get_model(self.current_model_name)
            
            # Create LangGraph agent using prebuilt create_react_agent
            self.agent = self._create_react_agent()
            
            print(f"LLM model '{self.current_model_name}' and LangGraph agent initialized successfully")
        except Exception as e:
            print(f"Error initializing model: {e}")
            self.model = None
            self.agent = None
    
    def _init_model_fallback(self):
        """Fallback model initialization without registry"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            print("No OpenAI API key found")
            return
        
        try:
            base_model = ChatOpenAI(
                model="gpt-5-mini",
                temperature=0.7,
                max_tokens=2000,
                api_key=api_key
            )
            self.model = base_model
            self.agent = self._create_react_agent()
            print("LLM model initialized with fallback method")
        except Exception as e:
            print(f"Error initializing fallback model: {e}")
            self.model = None
            self.agent = None
    
    def _create_react_agent(self):
        """Create LangGraph agent using prebuilt create_react_agent"""
        if not LANGCHAIN_AVAILABLE or not self.tools or not self.model:
            return None
            
        try:
            # Get system prompt from current session
            session = self.get_current_session()
            system_prompt = session.system_prompt if session else "You are a helpful AI assistant with vision capabilities and tools."
            
            # Create agent using prebuilt create_react_agent
            agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                state_modifier=system_prompt
            )
            
            print("LangGraph agent created with prebuilt create_react_agent")
            return agent
            
        except Exception as e:
            print(f"Error creating LangGraph agent: {e}")
            return None
    
    def create_new_session(self) -> str:
        """Create a new chat session"""
        import uuid
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = SimpleChatSession()
        self.current_session_id = session_id
        return session_id
    
    def get_current_session(self) -> SimpleChatSession:
        """Get the current active session"""
        if self.current_session_id and self.current_session_id in self.sessions:
            return self.sessions[self.current_session_id]
        # If no current session, create one
        self.create_new_session()
        return self.sessions[self.current_session_id]
    
    def get_all_sessions(self) -> Dict[str, SimpleChatSession]:
        """Get all chat sessions"""
        return self.sessions
    
    def switch_to_session(self, session_id: str):
        """Switch to a different session"""
        if session_id in self.sessions:
            self.current_session_id = session_id
            return True
        return False
    
    def add_user_message(self, text: str, files: List[str] = None, file_contents: List[str] = None):
        """Add user message and return the message object"""
        return self.get_current_session().add_user_message(text, files, file_contents)
    
    def get_ai_response(self) -> str:
        """Get AI response using prebuilt LangGraph agent"""
        if not self.agent:
            return "AI agent not available. Please check your OpenAI API key and LangGraph setup."
        
        try:
            session = self.get_current_session()
            
            # Prepare messages for the prebuilt agent (last 10 for context)
            messages = []
            recent_messages = session.messages[-10:]  # Get last 10 messages
            
            for msg in recent_messages:
                if msg["role"] == "user":
                    # Handle multimodal content properly
                    if isinstance(msg["content"], list):
                        # Convert content parts to proper format for multimodal
                        content_parts = []
                        for part in msg["content"]:
                            if part["type"] == "text":
                                content_parts.append({"type": "text", "text": part["text"]})
                            elif part["type"] == "image_url":
                                content_parts.append({
                                    "type": "image_url", 
                                    "image_url": {"url": part["image_url"]["url"]}
                                })
                        messages.append(HumanMessage(content=content_parts))
                    else:
                        messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            
            print(f"Sending {len(messages)} messages to prebuilt LangGraph agent")
            
            # Run the prebuilt LangGraph agent - it expects {"messages": [...]}
            result = self.agent.invoke({"messages": messages})
            
            # Extract AI response and any graph data from the result
            ai_response = ""
            graph_data = None
            
            if "messages" in result:
                print(f"=== AGENT RESULT DEBUG ===")
                print(f"Number of messages in result: {len(result['messages'])}")
                for i, msg in enumerate(result["messages"]):
                    print(f"Message {i}: {type(msg).__name__} - {str(msg)[:200]}...")
                print("=== END AGENT RESULT DEBUG ===")
                
                # Look for graph data in ToolMessages
                from langchain_core.messages import ToolMessage
                for msg in result["messages"]:
                    if isinstance(msg, ToolMessage) and "create_dash_graph" in str(msg):
                        try:
                            tool_content = msg.content
                            if isinstance(tool_content, str):
                                import json
                                tool_result = json.loads(tool_content)
                                if isinstance(tool_result, dict) and tool_result.get("type") == "dash_graph":
                                    graph_data = tool_result
                                    print(f"Found graph data in ToolMessage: {graph_data}")
                                    break
                        except Exception as e:
                            print(f"Error parsing tool message: {e}")
                
                # Get the last AI message
                for msg in reversed(result["messages"]):
                    if isinstance(msg, AIMessage) and msg.content:
                        ai_response = msg.content
                        break
            
            if not ai_response:
                ai_response = "I apologize, but I couldn't generate a proper response. Please try again."
            
            # If we found graph data, modify the response to include it
            if graph_data:
                # Create a special marker that the graph renderer can detect
                graph_marker = f"\n\n__DASH_GRAPH_DATA__:{json.dumps(graph_data)}__END_DASH_GRAPH_DATA__\n\n"
                ai_response = ai_response + graph_marker
            
            # Store AI response
            session.add_ai_message(ai_response)
            
            return ai_response
            
        except Exception as e:
            error_msg = f"Error getting AI response: {str(e)}"
            print(f"Full error details: {e}")
            session = self.get_current_session()
            session.add_ai_message(error_msg)
            return error_msg
    
    def get_messages(self):
        """Get all messages in the current session"""
        return self.get_current_session().messages
    
    def clear_session(self):
        """Clear the current session"""
        if self.current_session_id:
            self.sessions[self.current_session_id] = SimpleChatSession()
    
    def get_available_models(self):
        """Get list of available models from registry"""
        if MODEL_REGISTRY_AVAILABLE:
            return model_registry.get_available_models()
        else:
            return ["gpt-5-mini"]  
    
    def get_current_model(self):
        """Get current model name"""
        return self.current_model_name
    
    def switch_model(self, model_name: str):
        """Switch to a different model"""
        available_models = self.get_available_models()
        if model_name not in available_models:
            print(f"Model '{model_name}' not available. Available models: {available_models}")
            return False
        
        try:
            self.current_model_name = model_name
            self._init_model()
            print(f"Successfully switched to model: {model_name}")
            return True
        except Exception as e:
            print(f"Error switching to model '{model_name}': {e}")
            return False


# Global instance
simple_llm = SimpleLLM()