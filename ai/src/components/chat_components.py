"""
Chat Components with Original UI Design + New Reliable Backend
Beautiful sidebar interface powered by simple_llm service
"""
import json
import base64
from datetime import datetime

import dash
from dash import html, dcc, callback, Input, Output, State, no_update, ctx, clientside_callback, ALL

from utils.simple_llm import simple_llm
from utils.graph_renderer import parse_message_for_graphs


def create_simple_chat():
    """Create a ChatGPT-style interface with sidebar"""
    return html.Div([
        # Sidebar
        html.Div([
            # Sidebar header
            html.Div([
                html.Button([
                    html.Span("+ ", className="mr-2"),
                    "New Chat"
                ], 
                id="new-chat-btn",
                className="w-full bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg text-left transition-colors mb-4"
                ),
            ]),
            
            # Chat history list
            html.Div([
                html.Div("Search chats", className="text-gray-500 text-sm mb-2"),
                html.Div(id="chat-list", className="flex-1 overflow-y-auto")
            ], className="flex-1"),
            
            # Sidebar footer
            html.Div([
                html.Div("AI Services", className="text-gray-500 text-sm p-2"),
                html.Div("Settings", className="text-gray-500 text-sm p-2 hover:bg-gray-200 rounded cursor-pointer"),
            ], className="border-t border-gray-200 pt-4")
            
        ], className="w-64 bg-gray-50 text-gray-800 p-4 flex flex-col h-screen fixed left-0 top-0 border-r border-gray-200"),
        
        # Main chat area
        html.Div([
            # Header
            html.Div([
                html.H1("CORE-AI", className="text-2xl font-bold text-center text-gray-800 py-4")
            ], className="border-b border-gray-200"),
            
            # Chat messages area (scrollable)
            html.Div([
                html.Div(id="chat-messages", children=[
                    html.Div([
                        html.H2("How can I help you today?", className="text-2xl font-normal text-gray-800 mb-6 text-center"),
                        html.Div([
                            html.Div("💡 Ask about anything", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 mr-2 inline-block"),
                            html.Div("📊 Create interactive charts", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 mr-2 inline-block"),
                            html.Div("🖼️ Analyze images", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 mr-2 inline-block"),
                            html.Div("📎 Upload documents", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 inline-block")
                        ], className="text-center")
                    ], className="flex items-center justify-center h-full flex-col")
                ], className="w-full px-6 py-6 space-y-6")
            ], id="messages-container", className="flex-1 overflow-y-auto bg-white"),
            
            # Chat input area (always at bottom)
            html.Div([
                # File upload area (hidden by default)
                dcc.Upload(
                    id="file-upload",
                    children=html.Div([]),
                    style={"display": "none"},
                    multiple=True,
                    accept="image/*,.pdf,.docx,.pptx,.xlsx,.txt,.md,.csv,.html,.json"
                ),
                
                # File preview area (shows when file is selected)
                html.Div(id="file-preview", className="mb-2", style={"display": "none"}),
                
                html.Div([
                    html.Div([
                        # File attachment button
                        html.Button(
                            "📎",
                            id="attach-file-btn",
                            className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 bg-transparent border-none cursor-pointer p-1 rounded hover:bg-gray-100 transition-colors",
                            style={
                                "fontSize": "18px",
                                "padding": "4px",
                                "zIndex": "10"
                            },
                            title="Attach file or image"
                        ),
                        dcc.Textarea(
                            id="chat-input",
                            placeholder="Message CORE-AI...",
                            className="w-full pl-12 pr-12 border border-gray-200 rounded-3xl resize-none focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300 bg-white text-gray-900 shadow-sm",
                            style={
                                "minHeight": "52px", 
                                "maxHeight": "120px",
                                "fontSize": "16px",
                                "lineHeight": "22px",
                                "padding": "15px 48px 15px 44px"
                            }
                        ),
                        # Model selector
                        dcc.Dropdown(
                            id="model-selector",
                            options=[{"label": model, "value": model} for model in simple_llm.get_available_models()],
                            value=simple_llm.get_current_model(),
                            className="absolute right-14 top-1/2 transform -translate-y-1/2 w-28",
                            style={
                                "fontSize": "12px",
                                "zIndex": "20"
                            }
                        ),
                        html.Button(
                            "▲",
                            id="send-btn",
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 bg-gray-800 hover:bg-gray-700 text-white rounded-full w-8 h-8 flex items-center justify-center border-none cursor-pointer transition-colors",
                            style={
                                "fontSize": "12px",
                                "zIndex": "10"
                            },
                            title="Send message"
                        )
                    ], className="relative max-w-4xl mx-auto"),
                    
                    html.Div(id="status", className="text-center text-gray-500 text-sm mt-2 h-6")
                    
                ], className="px-6 py-4")
                
            ], className="border-t border-gray-200 bg-white")
            
        ], className="ml-64 h-screen flex flex-col bg-white"),
        
    ], className="bg-gray-50 min-h-screen")


def create_message_bubble(message):
    """Create a message bubble"""
    is_user = message["role"] == "user"
    timestamp = datetime.fromisoformat(message["timestamp"]).strftime("%H:%M")
    
    # Handle content
    content_elements = []
    
    # Add files if any
    for filename in message.get("files", []):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            icon = "🖼️"
            label = "Image"
        else:
            icon = "📄"
            label = "Document"
        
        content_elements.append(
            html.Div([
                html.Span(icon, className="mr-2"),
                html.Span(filename, className="text-sm text-gray-600")
            ], className="bg-gray-100 rounded px-2 py-1 mb-2 inline-block mr-2")
        )
    
    # Add text content and any graphs
    if isinstance(message["content"], str):
        if message["role"] == "assistant":
            # Parse for graphs in AI responses
            cleaned_content, graph_components = parse_message_for_graphs(message["content"])
            if cleaned_content.strip():
                content_elements.append(
                    html.Div(cleaned_content, className="whitespace-pre-wrap")
                )
            # Add graph components
            content_elements.extend(graph_components)
        else:
            content_elements.append(
                html.Div(message["content"], className="whitespace-pre-wrap")
            )
    elif isinstance(message["content"], list):
        # Handle multimodal content - extract text parts (but only displayable ones)
        for part in message["content"]:
            if isinstance(part, dict) and part.get("type") == "text":
                # Only show text parts that are meant to be displayed (not hidden document content)
                if part.get("display", True):  # Default to True if not specified
                    content_elements.append(
                        html.Div(part["text"], className="whitespace-pre-wrap")
                    )
    
    if is_user:
        return html.Div([
            html.Div([
                html.Div("You", className="text-xs font-medium text-gray-600 mb-1"),
                html.Div(content_elements),
                html.Div(timestamp, className="text-xs text-gray-400 mt-2")
            ], className="bg-blue-50 border border-blue-200 p-4 rounded-lg max-w-2xl ml-auto")
        ], className="mb-4 flex justify-end")
    else:
        return html.Div([
            html.Div([
                html.Div("CORE-AI", className="text-xs font-medium text-gray-600 mb-1"),
                html.Div(content_elements),
                html.Div(timestamp, className="text-xs text-gray-400 mt-2")
            ], className="p-4 rounded-lg max-w-2xl")
        ], className="mb-4")


# Handle file attachment
@callback(
    [Output("file-preview", "children"), Output("file-preview", "style")],
    Input("file-upload", "contents"),
    State("file-upload", "filename"),
    prevent_initial_call=True
)
def handle_file_upload(contents, filenames):
    """Handle file upload and show preview"""
    if not contents:
        return [], {"display": "none"}
    
    if not isinstance(contents, list):
        contents = [contents]
        filenames = [filenames] if filenames else []
    
    preview_items = []
    for content, filename in zip(contents, filenames):
        if not filename:
            continue
        
        # Get file size
        try:
            file_size = len(base64.b64decode(content.split(',')[1])) if ',' in content else 0
            file_size_kb = round(file_size / 1024, 1)
        except:
            file_size_kb = 0
        
        # Check if image
        is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'))
        
        if is_image:
            preview_items.append(
                html.Div([
                    html.Img(src=content, className="w-16 h-16 object-cover rounded mr-3"),
                    html.Div([
                        html.Div(filename, className="font-medium text-sm"),
                        html.Div(f"{file_size_kb} KB • Image", className="text-xs text-gray-500")
                    ], className="flex-1")
                ], className="bg-blue-50 border border-blue-200 rounded p-3 mb-2 flex items-center")
            )
        else:
            preview_items.append(
                html.Div([
                    html.Div("📄", className="text-2xl mr-3"),
                    html.Div([
                        html.Div(filename, className="font-medium text-sm"),
                        html.Div(f"{file_size_kb} KB • Document", className="text-xs text-gray-500")
                    ], className="flex-1")
                ], className="bg-gray-50 border border-gray-200 rounded p-3 mb-2 flex items-center")
            )
    
    return preview_items, {"display": "block"} if preview_items else {"display": "none"}


# Trigger file upload
clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            const fileInput = document.querySelector('#file-upload input[type="file"]');
            if (fileInput) {
                fileInput.click();
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("attach-file-btn", "data-clicked"),
    Input("attach-file-btn", "n_clicks"),
    prevent_initial_call=True
)


# Handle message sending
@callback(
    [Output("chat-messages", "children"),
     Output("chat-input", "value"),
     Output("status", "children"),
     Output("file-upload", "contents"),
     Output("file-preview", "children", allow_duplicate=True),
     Output("file-preview", "style", allow_duplicate=True)],
    Input("send-btn", "n_clicks"),
    [State("chat-input", "value"),
     State("chat-messages", "children"),
     State("file-upload", "contents"),
     State("file-upload", "filename")],
    prevent_initial_call=True
)
def handle_send_message(n_clicks, message_text, current_messages, file_contents, filenames):
    """Handle sending a message"""
    if not n_clicks or not message_text or not message_text.strip():
        return no_update, no_update, no_update, no_update, no_update, no_update
    
    try:
        # Process files
        files = []
        file_data = []
        
        if file_contents and filenames:
            if not isinstance(file_contents, list):
                file_contents = [file_contents]
                filenames = [filenames] if filenames else []
            
            for content, filename in zip(file_contents, filenames):
                if content and filename:
                    files.append(filename)
                    file_data.append(content)
        
        # Add user message to simple_llm
        simple_llm.add_user_message(message_text.strip(), files, file_data)
        
        # Get all messages to display
        messages = simple_llm.get_messages()
        
        # Create message bubbles
        message_bubbles = []
        for msg in messages[:-1]:  # All except the last (which we're about to get response for)
            message_bubbles.append(create_message_bubble(msg))
        
        # Add the latest user message
        if messages:
            message_bubbles.append(create_message_bubble(messages[-1]))
        
        # Add typing indicator
        typing_indicator = html.Div([
            html.Div([
                html.Div("CORE-AI", className="text-xs font-medium text-gray-600 mb-1"),
                html.Div([
                    html.Span("●", className="animate-pulse text-gray-400 mr-1"),
                    html.Span("●", className="animate-pulse text-gray-400 mr-1"),
                    html.Span("●", className="animate-pulse text-gray-400")
                ])
            ], className="p-4 rounded-lg max-w-2xl")
        ], className="mb-4")
        
        message_bubbles.append(typing_indicator)
        
        return message_bubbles, "", "Getting AI response...", None, [], {"display": "none"}
        
    except Exception as e:
        error_msg = f"Error sending message: {str(e)}"
        return no_update, no_update, error_msg, no_update, no_update, no_update


# Get AI response (triggered by status change)
@callback(
    [Output("chat-messages", "children", allow_duplicate=True),
     Output("status", "children", allow_duplicate=True)],
    Input("status", "children"),
    State("chat-messages", "children"),
    prevent_initial_call=True
)
def get_ai_response(status, current_messages):
    """Get AI response when status indicates we're waiting"""
    if status != "Getting AI response...":
        return no_update, no_update
    
    try:
        # Get AI response
        ai_response = simple_llm.get_ai_response()
        
        # Get all messages and create bubbles
        messages = simple_llm.get_messages()
        message_bubbles = []
        
        for msg in messages:
            message_bubbles.append(create_message_bubble(msg))
        
        return message_bubbles, ""
        
    except Exception as e:
        error_msg = f"Error getting AI response: {str(e)}"
        
        # Remove typing indicator and add error
        if current_messages and len(current_messages) > 0:
            current_messages = current_messages[:-1]  # Remove typing indicator
        
        error_bubble = html.Div([
            html.Div([
                html.Div("CORE-AI", className="text-xs font-medium text-gray-600 mb-1"),
                html.Div(error_msg, className="text-red-600")
            ], className="p-4 rounded-lg max-w-2xl")
        ], className="mb-4")
        
        return current_messages + [error_bubble], ""


# New chat button
@callback(
    [Output("chat-messages", "children", allow_duplicate=True),
     Output("status", "children", allow_duplicate=True)],
    Input("new-chat-btn", "n_clicks"),
    prevent_initial_call=True
)
def handle_new_chat(n_clicks):
    """Handle new chat button"""
    if not n_clicks:
        return no_update, no_update
    
    # Create a new session (keeping the old ones)
    simple_llm.create_new_session()
    
    # Return to welcome screen
    welcome_content = html.Div([
        html.H2("How can I help you today?", className="text-2xl font-normal text-gray-800 mb-6 text-center"),
        html.Div([
            html.Div("💡 Ask about anything", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 mr-2 inline-block"),
            html.Div("📊 Analyze images", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 mr-2 inline-block"),
            html.Div("📎 Upload documents", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 inline-block")
        ], className="text-center")
    ], className="flex items-center justify-center h-full flex-col")
    
    return [welcome_content], ""


# Populate chat list on page load
@callback(
    Output("chat-list", "children"),
    [Input("chat-messages", "children"),
     Input("new-chat-btn", "n_clicks")],
    prevent_initial_call=False
)
def update_chat_list(current_messages, new_chat_clicks):
    """Update the chat history list in sidebar"""
    all_sessions = simple_llm.get_all_sessions()
    current_session_id = simple_llm.current_session_id
    
    if not all_sessions:
        return html.Div("No chats yet", className="text-gray-400 text-sm p-2")
    
    chat_items = []
    
    for session_id, session in all_sessions.items():
        if not session.messages:
            continue
            
        # Get first user message as chat title
        first_user_msg = None
        for msg in session.messages:
            if msg["role"] == "user":
                if isinstance(msg["content"], str):
                    first_user_msg = msg["content"]
                elif isinstance(msg["content"], list):
                    for part in msg["content"]:
                        if isinstance(part, dict) and part.get("type") == "text" and part.get("display", True):
                            first_user_msg = part["text"]
                            break
                break
        
        if not first_user_msg:
            continue
        
        # Truncate title
        title = (first_user_msg[:40] + "...") if len(first_user_msg) > 40 else first_user_msg
        
        # Check if this is the current session
        is_current = session_id == current_session_id
        bg_class = "bg-blue-50 border-blue-200" if is_current else "bg-white border-gray-200"
        hover_class = "hover:bg-blue-100" if is_current else "hover:bg-gray-50"
        
        chat_items.append(
            html.Div([
                html.Div(title, className="text-sm font-medium text-gray-800 mb-1"),
                html.Div(f"{len([m for m in session.messages if m['role'] == 'user'])} messages", 
                        className="text-xs text-gray-500")
            ], 
            className=f"p-3 {bg_class} border rounded-lg cursor-pointer {hover_class} transition-colors mb-2",
            id={"type": "chat-item", "session_id": session_id})
        )
    
    return chat_items if chat_items else html.Div("No chats yet", className="text-gray-400 text-sm p-2")


# Handle clicking on chat items to switch sessions
@callback(
    [Output("chat-messages", "children", allow_duplicate=True),
     Output("status", "children", allow_duplicate=True)],
    Input({"type": "chat-item", "session_id": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def switch_chat_session(n_clicks_list):
    """Switch to a different chat session when clicked"""
    if not any(n_clicks_list) or not ctx.triggered:
        return no_update, no_update
    
    # Get the session_id from the triggered component
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    import json
    session_data = json.loads(triggered_id)
    session_id = session_data["session_id"]
    
    # Switch to the selected session
    if simple_llm.switch_to_session(session_id):
        # Load messages from the selected session
        messages = simple_llm.get_messages()
        
        if not messages:
            # Show welcome screen for empty session
            welcome_content = html.Div([
                html.H2("How can I help you today?", className="text-2xl font-normal text-gray-800 mb-6 text-center"),
                html.Div([
                    html.Div("💡 Ask about anything", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 mr-2 inline-block"),
                    html.Div("📊 Create interactive charts", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 mr-2 inline-block"),
                    html.Div("🖼️ Analyze images", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 mr-2 inline-block"),
                    html.Div("📎 Upload documents", className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm mb-2 inline-block")
                ], className="text-center")
            ], className="flex items-center justify-center h-full flex-col")
            return [welcome_content], ""
        else:
            # Show all messages from the session
            message_bubbles = []
            for msg in messages:
                message_bubbles.append(create_message_bubble(msg))
            return message_bubbles, ""
    
    return no_update, no_update


# Handle model selection
@callback(
    Output("status", "children", allow_duplicate=True),
    Input("model-selector", "value"),
    prevent_initial_call=True
)
def handle_model_selection(selected_model):
    """Handle model selection change"""
    if selected_model and selected_model != simple_llm.get_current_model():
        success = simple_llm.switch_model(selected_model)
        if success:
            return f"Switched to {selected_model}"
        else:
            return f"Failed to switch to {selected_model}"
    return ""


# Enter key handling
clientside_callback(
    """
    function(id) {
        setTimeout(function() {
            const textarea = document.getElementById('chat-input');
            const sendButton = document.getElementById('send-btn');
            
            if (textarea && sendButton) {
                textarea.removeEventListener('keydown', textarea._enterHandler);
                
                textarea._enterHandler = function(event) {
                    if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();
                        sendButton.click();
                    }
                };
                
                textarea.addEventListener('keydown', textarea._enterHandler);
            }
        }, 100);
        
        return window.dash_clientside.no_update;
    }
    """,
    Output("chat-input", "data-enter-handler"),
    Input("chat-input", "id"),
    prevent_initial_call=False
)