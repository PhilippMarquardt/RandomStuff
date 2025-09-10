"""
SIMPLE Chat Component - Just works like ChatGPT, no BS
"""
import json
import base64
from datetime import datetime

import dash
from dash import html, dcc, callback, Input, Output, State, no_update, ctx, clientside_callback

from utils.simple_llm import simple_llm
from utils.graph_renderer import parse_message_for_graphs


def create_chat_interface():
    """Create a simple ChatGPT-like interface"""
    return html.Div([
        # Chat header
        html.Div([
            html.H1("CORE-AI", className="text-2xl font-bold text-center text-white py-4")
        ], className="bg-gray-800 border-b border-gray-700"),
        
        # Messages area
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
            ], className="flex-1 overflow-y-auto p-6")
        ], className="flex-1 bg-white"),
        
        # Input area
        html.Div([
            # File upload (hidden)
            dcc.Upload(
                id="file-upload",
                children=html.Div([]),
                style={"display": "none"},
                multiple=True,
                accept="image/*,.pdf,.docx,.txt,.md,.csv"
            ),
            
            # File preview
            html.Div(id="file-preview", className="mb-2", style={"display": "none"}),
            
            # Input row
            html.Div([
                # Attach button
                html.Button(
                    "📎",
                    id="attach-btn",
                    className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded-l-lg border-none cursor-pointer",
                    title="Attach files"
                ),
                # Text input
                dcc.Textarea(
                    id="message-input",
                    placeholder="Type your message...",
                    className="flex-1 px-4 py-2 border-t border-b border-gray-300 resize-none focus:outline-none",
                    style={"minHeight": "44px", "maxHeight": "120px"}
                ),
                # Model selector
                dcc.Dropdown(
                    id="model-selector",
                    options=[{"label": model, "value": model} for model in simple_llm.get_available_models()],
                    value=simple_llm.get_current_model(),
                    className="w-32 mr-2",
                    style={"fontSize": "14px"}
                ),
                # Send button
                html.Button(
                    "Send",
                    id="send-btn",
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-r-lg border-none cursor-pointer font-semibold"
                )
            ], className="flex w-full max-w-4xl mx-auto"),
            
            # Status
            html.Div(id="status", className="text-center text-gray-500 text-sm mt-2 h-6")
            
        ], className="bg-gray-50 p-4 border-t border-gray-200"),
        
    ], className="h-screen flex flex-col bg-gray-50")


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
    Output("attach-btn", "data-clicked"),
    Input("attach-btn", "n_clicks"),
    prevent_initial_call=True
)


# Handle message sending
@callback(
    [Output("chat-messages", "children"),
     Output("message-input", "value"),
     Output("status", "children"),
     Output("file-upload", "contents"),
     Output("file-preview", "children", allow_duplicate=True),
     Output("file-preview", "style", allow_duplicate=True)],
    Input("send-btn", "n_clicks"),
    [State("message-input", "value"),
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
        
        print(f"Sending message with {len(files)} files: {files}")
        
        # Add user message to LLM
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
        print(error_msg)
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
        print("Getting AI response...")
        
        # Get AI response
        ai_response = simple_llm.get_ai_response()
        
        print(f"Got AI response: {ai_response[:100]}...")
        
        # Get all messages and create bubbles
        messages = simple_llm.get_messages()
        message_bubbles = []
        
        for msg in messages:
            message_bubbles.append(create_message_bubble(msg))
        
        return message_bubbles, ""
        
    except Exception as e:
        error_msg = f"Error getting AI response: {str(e)}"
        print(error_msg)
        
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
            const textarea = document.getElementById('message-input');
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
    Output("message-input", "data-enter-handler"),
    Input("message-input", "id"),
    prevent_initial_call=False
)