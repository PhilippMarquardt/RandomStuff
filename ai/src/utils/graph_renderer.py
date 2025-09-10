"""
Graph Rendering Utilities for Chat Interface
Handles rendering of Dash graphs from AI tool responses
"""
import json
import uuid
from typing import Dict, Any, Optional

from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px


def create_dash_graph_component(graph_data: Dict[str, Any]) -> Optional[html.Div]:
    """
    Create a Dash graph component from AI tool response data
    
    Args:
        graph_data: Dictionary containing graph configuration
        
    Returns:
        html.Div containing the graph or None if invalid
    """
    try:
        if not isinstance(graph_data, dict) or graph_data.get("type") != "dash_graph":
            return None
        
        graph_type = graph_data.get("graph_type")
        title = graph_data.get("title", "Chart")
        x_label = graph_data.get("x_label", "X")
        y_label = graph_data.get("y_label", "Y")
        data = graph_data.get("data", {})
        
        # Generate unique ID for the graph
        graph_id = f"chat-graph-{uuid.uuid4().hex[:8]}"
        
        # Create the appropriate plotly figure
        fig = None
        
        if graph_type == "line":
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=data.get("x", []),
                y=data.get("y", []),
                mode='lines+markers',
                name=title,
                line=dict(color='#3B82F6', width=3),
                marker=dict(size=6)
            ))
            
        elif graph_type == "bar":
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=data.get("x", []),
                y=data.get("y", []),
                name=title,
                marker=dict(color='#10B981')
            ))
            
        elif graph_type == "scatter":
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=data.get("x", []),
                y=data.get("y", []),
                mode='markers',
                name=title,
                marker=dict(
                    size=8,
                    color='#8B5CF6',
                    opacity=0.8
                )
            ))
            
        elif graph_type == "pie":
            fig = go.Figure()
            fig.add_trace(go.Pie(
                labels=data.get("labels", []),
                values=data.get("values", []),
                name=title,
                hole=0.3  # Creates a donut chart
            ))
            
        elif graph_type == "histogram":
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=data.get("values", []),
                name=title,
                marker=dict(color='#F59E0B'),
                opacity=0.8
            ))
        
        if fig is None:
            return None
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=18, family="Inter, sans-serif"),
                x=0.5,
                xanchor='center'
            ),
            xaxis_title=x_label if graph_type != "pie" else None,
            yaxis_title=y_label if graph_type != "pie" else None,
            font=dict(family="Inter, sans-serif", size=12),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=40, r=40, t=60, b=40),
            height=400,
            showlegend=graph_type == "pie"
        )
        
        # Style grid lines
        if graph_type not in ["pie"]:
            fig.update_xaxes(
                gridcolor='rgba(0,0,0,0.1)',
                zerolinecolor='rgba(0,0,0,0.2)'
            )
            fig.update_yaxes(
                gridcolor='rgba(0,0,0,0.1)',
                zerolinecolor='rgba(0,0,0,0.2)'
            )
        
        # Create the Dash component
        graph_component = html.Div([
            html.Div([
                html.Span("📊", className="mr-2 text-lg"),
                html.Span(f"Interactive {graph_type.title()} Chart", className="font-medium text-gray-700")
            ], className="flex items-center mb-3 text-sm"),
            dcc.Graph(
                id=graph_id,
                figure=fig,
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': f'{title.lower().replace(" ", "_")}_chart',
                        'height': 400,
                        'width': 600,
                        'scale': 2
                    }
                },
                className="border border-gray-200 rounded-lg"
            )
        ], className="bg-gray-50 p-4 rounded-lg my-3 max-w-2xl")
        
        return graph_component
        
    except Exception as e:
        # Return error display
        return html.Div([
            html.Div([
                html.Span("⚠️", className="mr-2 text-yellow-500"),
                html.Span("Graph Rendering Error", className="font-medium text-gray-700")
            ], className="flex items-center mb-2 text-sm"),
            html.Div(f"Error creating graph: {str(e)}", className="text-red-600 text-sm")
        ], className="bg-red-50 border border-red-200 p-4 rounded-lg my-3 max-w-2xl")


def extract_graph_data_from_message(message_content: str) -> Optional[Dict[str, Any]]:
    """
    Extract graph data from AI message content that contains tool results
    
    Args:
        message_content: The AI response content
        
    Returns:
        Graph data dictionary if found, None otherwise
    """
    try:
        # Debug: Print the message content to see what we're working with
        print(f"=== GRAPH EXTRACTION DEBUG ===")
        print(f"Message content: {message_content[:500]}...")
        print("=== END DEBUG ===")
        
        # Look for the special marker we embed in responses
        if "__DASH_GRAPH_DATA__:" in message_content:
            try:
                start_marker = "__DASH_GRAPH_DATA__:"
                end_marker = "__END_DASH_GRAPH_DATA__"
                
                start_idx = message_content.find(start_marker) + len(start_marker)
                end_idx = message_content.find(end_marker)
                
                if start_idx > len(start_marker) - 1 and end_idx > start_idx:
                    graph_json = message_content[start_idx:end_idx]
                    graph_data = json.loads(graph_json)
                    
                    if isinstance(graph_data, dict) and graph_data.get("type") == "dash_graph":
                        print(f"Found graph data via marker: {graph_data}")
                        return graph_data
            except Exception as e:
                print(f"Error parsing graph marker: {e}")
        
        # Look for various patterns that indicate tool results with graph data
        patterns_to_check = [
            "Tool create_dash_graph result:",
            '"type": "dash_graph"',
            '"graph_type":',
            "create_dash_graph",
        ]
        
        # Check if any graph-related content exists
        has_graph_content = any(pattern in message_content for pattern in patterns_to_check)
        
        if not has_graph_content:
            return None
        
        # Try to extract JSON from various formats
        lines = message_content.split('\n')
        
        for line in lines:
            # Look for lines that contain "Tool create_dash_graph result:"
            if "Tool create_dash_graph result:" in line:
                # Extract the JSON part after the result prefix
                result_part = line.split("Tool create_dash_graph result:", 1)[1].strip()
                try:
                    graph_data = json.loads(result_part)
                    if isinstance(graph_data, dict) and graph_data.get("type") == "dash_graph":
                        print(f"Found graph data via tool result pattern: {graph_data}")
                        return graph_data
                except json.JSONDecodeError:
                    continue
        
        # Try to find JSON blocks in the content
        import re
        json_pattern = r'\{[^{}]*"type"\s*:\s*"dash_graph"[^{}]*\}'
        matches = re.findall(json_pattern, message_content, re.DOTALL)
        
        for match in matches:
            try:
                graph_data = json.loads(match)
                if isinstance(graph_data, dict) and graph_data.get("type") == "dash_graph":
                    print(f"Found graph data via JSON pattern: {graph_data}")
                    return graph_data
            except json.JSONDecodeError:
                continue
        
        # Look for more complex JSON structures
        brace_count = 0
        json_start = -1
        
        for i, char in enumerate(message_content):
            if char == '{':
                if brace_count == 0:
                    json_start = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and json_start != -1:
                    potential_json = message_content[json_start:i+1]
                    try:
                        data = json.loads(potential_json)
                        if isinstance(data, dict) and data.get("type") == "dash_graph":
                            print(f"Found graph data via brace parsing: {data}")
                            return data
                    except json.JSONDecodeError:
                        pass
                    json_start = -1
        
        return None
        
    except Exception as e:
        print(f"Error in extract_graph_data_from_message: {e}")
        return None


def parse_message_for_graphs(message_content: str) -> tuple[str, list]:
    """
    Parse AI message content and extract both text and graph components
    
    Args:
        message_content: The AI response content
        
    Returns:
        Tuple of (cleaned_text_content, list_of_graph_components)
    """
    graph_components = []
    cleaned_content = message_content
    
    # Extract graph data
    graph_data = extract_graph_data_from_message(message_content)
    
    if graph_data:
        # Create graph component
        graph_component = create_dash_graph_component(graph_data)
        if graph_component:
            graph_components.append(graph_component)
        
        # Clean the message content by removing graph markers and tool result lines
        cleaned_content = message_content
        
        # Remove the special marker we added
        if "__DASH_GRAPH_DATA__:" in cleaned_content:
            start_marker = "__DASH_GRAPH_DATA__:"
            end_marker = "__END_DASH_GRAPH_DATA__"
            
            start_idx = cleaned_content.find(start_marker)
            end_idx = cleaned_content.find(end_marker) + len(end_marker)
            
            if start_idx != -1 and end_idx > start_idx:
                cleaned_content = cleaned_content[:start_idx] + cleaned_content[end_idx:]
        
        # Remove tool result lines
        lines = cleaned_content.split('\n')
        cleaned_lines = []
        for line in lines:
            if not ("Tool create_dash_graph result:" in line):
                cleaned_lines.append(line)
        
        cleaned_content = '\n'.join(cleaned_lines).strip()
        
        # Also remove any markdown image references that the AI might have generated
        import re
        cleaned_content = re.sub(r'!\[.*?\]\(#?\)', '', cleaned_content)
        cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_content)  # Clean up extra newlines
    
    return cleaned_content, graph_components
