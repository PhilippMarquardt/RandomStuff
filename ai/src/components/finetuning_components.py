"""
Fine-tuning Components with Same UI Style as Chat
Settings interface for model fine-tuning with model and dataset selection
"""
import os
import dash
from dash import html, dcc, callback, Input, Output, State, no_update


def get_available_finetuning_models():
    """Get available finetuning model folders from FINETUNING_MODEL_LOCATION"""
    finetuning_location = os.getenv("FINETUNING_MODEL_LOCATION", "")
    
    if not finetuning_location:
        return []
    
    if not os.path.exists(finetuning_location):
        return []
    
    try:
        # Get all directories in the finetuning location
        folders = []
        for item in os.listdir(finetuning_location):
            item_path = os.path.join(finetuning_location, item)
            if os.path.isdir(item_path):
                folders.append(item)
        
        return sorted(folders)  # Return sorted list of folder names
    except Exception as e:
        print(f"Error reading finetuning model location: {e}")
        return []


def create_finetuning_interface():
    """Create a fine-tuning settings interface with sidebar"""
    return html.Div([
        # Sidebar
        html.Div([
           
            
            # Sidebar menu items
            html.Div([
                html.Div("Configuration", className="text-gray-500 text-sm mb-4 font-medium"),
                html.Div([
                    html.Div("Training Jobs", className="text-gray-700 text-sm p-2 hover:bg-gray-200 rounded cursor-pointer mb-1"),
                    html.Div("Model Performance", className="text-gray-700 text-sm p-2 hover:bg-gray-200 rounded cursor-pointer mb-1"),
                    html.Div("Dataset Manager", className="text-gray-700 text-sm p-2 hover:bg-gray-200 rounded cursor-pointer mb-1"),
                ])
            ], className="flex-1"),
            
            # Sidebar footer
            html.Div([
                html.Div("Model Training", className="text-gray-500 text-sm p-2"),
                html.Div("Status: Ready", className="text-green-600 text-sm p-2 font-medium"),
            ], className="border-t border-gray-200 pt-4")
            
        ], className="w-64 bg-gray-50 text-gray-800 p-4 flex flex-col h-screen fixed left-0 top-0 border-r border-gray-200"),
        
        # Main content area
        html.Div([
            # Header
            html.Div([
                html.H1("Fine-tuning Settings", className="text-2xl font-bold text-center text-gray-800 py-4")
            ], className="border-b border-gray-200"),
            
            # Settings content area (scrollable)
            html.Div([
                html.Div([
                    # Welcome section
                    html.Div([
                        html.H2("Configure Model Fine-tuning", className="text-xl font-semibold text-gray-800 mb-4"),
                        html.P("Select your base model and training dataset to create a custom fine-tuned model.", 
                              className="text-gray-600 mb-8")
                    ], className="mb-8"),
                    
                    # Model Selection
                    html.Div([
                        html.Label("Base Model", className="block text-sm font-medium text-gray-700 mb-2"),
                        dcc.Dropdown(
                            id="model-selection",
                            options=[
                                {"label": "GPT-4o", "value": "gpt-4o"},
                                {"label": "GPT-4o Mini", "value": "gpt-4o-mini"},
                                {"label": "GPT-4 Turbo", "value": "gpt-4-turbo"},
                                {"label": "GPT-3.5 Turbo", "value": "gpt-3.5-turbo"},
                            ],
                            value="gpt-4o-mini",
                            className="mb-6",
                            style={"fontSize": "14px"}
                        ),
                        html.P("Choose the base model that will be fine-tuned with your dataset.", 
                              className="text-xs text-gray-500 mb-6")
                    ]),
                    
                    # Fine-tuned Model Selection
                    html.Div([
                        html.Div([
                            html.Label("Fine-tuned Models", className="block text-sm font-medium text-gray-700 mb-2"),
                            html.Button(
                                "🔄 Refresh",
                                id="refresh-models-btn",
                                className="ml-2 text-xs bg-gray-200 hover:bg-gray-300 text-gray-700 px-2 py-1 rounded transition-colors",
                                style={"fontSize": "11px"}
                            )
                        ], className="flex items-center justify-between"),
                        dcc.Dropdown(
                            id="finetuned-model-selection",
                            options=[{"label": folder, "value": folder} for folder in get_available_finetuning_models()],
                            value=None,
                            placeholder="Select a fine-tuned model...",
                            className="mb-6",
                            style={"fontSize": "14px"}
                        ),
                        html.P(f"Available models from: {os.getenv('FINETUNING_MODEL_LOCATION', 'Environment variable not set')}", 
                              className="text-xs text-gray-500 mb-6")
                    ]),
                    
                    # Dataset Selection
                    html.Div([
                        html.Label("Training Dataset", className="block text-sm font-medium text-gray-700 mb-2"),
                        dcc.Dropdown(
                            id="dataset-selection",
                            options=[
                                {"label": "Customer Support Dataset", "value": "customer_support"},
                                {"label": "Code Generation Dataset", "value": "code_generation"},
                                {"label": "Medical Q&A Dataset", "value": "medical_qa"},
                                {"label": "Legal Documents Dataset", "value": "legal_docs"},
                                {"label": "Custom Dataset (Upload)", "value": "custom"},
                            ],
                            value=None,
                            placeholder="Select a training dataset...",
                            className="mb-6",
                            style={"fontSize": "14px"}
                        ),
                        html.P("Select the dataset that will be used to fine-tune your model.", 
                              className="text-xs text-gray-500 mb-6")
                    ]),
                    
                    # Training Parameters Section
                    html.Div([
                        html.H3("Training Parameters", className="text-lg font-medium text-gray-800 mb-4"),
                        
                        html.Div([
                            # Learning Rate
                            html.Div([
                                html.Label("Learning Rate", className="block text-sm font-medium text-gray-700 mb-2"),
                                dcc.Input(
                                    id="learning-rate",
                                    type="number",
                                    value=0.001,
                                    step=0.0001,
                                    min=0.0001,
                                    max=0.01,
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                                )
                            ], className="mb-4"),
                            
                            # Batch Size
                            html.Div([
                                html.Label("Batch Size", className="block text-sm font-medium text-gray-700 mb-2"),
                                dcc.Input(
                                    id="batch-size",
                                    type="number",
                                    value=4,
                                    min=1,
                                    max=32,
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                                )
                            ], className="mb-4"),
                            
                            # Epochs
                            html.Div([
                                html.Label("Training Epochs", className="block text-sm font-medium text-gray-700 mb-2"),
                                dcc.Input(
                                    id="epochs",
                                    type="number",
                                    value=3,
                                    min=1,
                                    max=10,
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                                )
                            ], className="mb-6")
                        ], className="grid grid-cols-3 gap-4")
                    ], className="mb-8"),
                    
                    # Action Buttons
                    html.Div([
                        html.Button(
                            "Start Training",
                            id="start-training-btn",
                            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-lg mr-4 transition-colors",
                            disabled=True
                        ),
                        html.Button(
                            "Save Configuration",
                            id="save-config-btn",
                            className="bg-gray-600 hover:bg-gray-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors"
                        )
                    ], className="flex"),
                    
                    # Status Message
                    html.Div(id="training-status", className="mt-6 p-4 bg-gray-50 rounded-lg text-sm text-gray-600")
                    
                ], className="max-w-4xl")
            ], className="flex-1 overflow-y-auto bg-white p-8"),
            
        ], className="ml-64 h-screen flex flex-col bg-white"),
        
    ], className="bg-gray-50 min-h-screen")


# Refresh finetuned models dropdown
@callback(
    Output("finetuned-model-selection", "options"),
    Input("refresh-models-btn", "n_clicks"),
    prevent_initial_call=True
)
def refresh_finetuned_models(n_clicks):
    """Refresh the list of available finetuned models"""
    if n_clicks:
        folders = get_available_finetuning_models()
        return [{"label": folder, "value": folder} for folder in folders]
    return no_update


# Enable Start Training button when both model and dataset are selected
@callback(
    Output("start-training-btn", "disabled"),
    [Input("model-selection", "value"),
     Input("dataset-selection", "value")]
)
def enable_start_button(model, dataset):
    """Enable start training button when both selections are made"""
    return not (model and dataset)


# Handle Start Training button click
@callback(
    Output("training-status", "children"),
    Input("start-training-btn", "n_clicks"),
    [State("model-selection", "value"),
     State("finetuned-model-selection", "value"),
     State("dataset-selection", "value"),
     State("learning-rate", "value"),
     State("batch-size", "value"),
     State("epochs", "value")],
    prevent_initial_call=True
)
def start_training(n_clicks, model, finetuned_model, dataset, learning_rate, batch_size, epochs):
    """Handle start training button click"""
    if not n_clicks:
        return no_update
    
    # Throw NotImplementedError as requested
    try:
        raise NotImplementedError("Fine-tuning functionality is not yet implemented")
    except NotImplementedError as e:
        return html.Div([
            html.Div("❌ Training Failed", className="font-semibold text-red-600 mb-2"),
            html.Div(f"Error: {str(e)}", className="text-red-500"),
            html.Div(f"Configuration: Model={model}, Fine-tuned={finetuned_model}, Dataset={dataset}, LR={learning_rate}, Batch={batch_size}, Epochs={epochs}", 
                    className="text-gray-500 text-xs mt-2")
        ])


# Handle Save Configuration button
@callback(
    Output("training-status", "children", allow_duplicate=True),
    Input("save-config-btn", "n_clicks"),
    [State("model-selection", "value"),
     State("finetuned-model-selection", "value"),
     State("dataset-selection", "value"),
     State("learning-rate", "value"),
     State("batch-size", "value"),
     State("epochs", "value")],
    prevent_initial_call=True
)
def save_configuration(n_clicks, model, finetuned_model, dataset, learning_rate, batch_size, epochs):
    """Handle save configuration button"""
    if not n_clicks:
        return no_update
    
    return html.Div([
        html.Div("✅ Configuration Saved", className="font-semibold text-green-600 mb-2"),
        html.Div(f"Model: {model or 'Not selected'}", className="text-gray-600 text-sm"),
        html.Div(f"Fine-tuned Model: {finetuned_model or 'Not selected'}", className="text-gray-600 text-sm"),
        html.Div(f"Dataset: {dataset or 'Not selected'}", className="text-gray-600 text-sm"),
        html.Div(f"Parameters: LR={learning_rate}, Batch={batch_size}, Epochs={epochs}", className="text-gray-600 text-sm")
    ])