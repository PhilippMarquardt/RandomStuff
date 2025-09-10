import dash
from dash import html, dcc
from components.chat_components import create_simple_chat

# Register this page with Dash Pages
dash.register_page(__name__, path='/', title='AI Chat - CoreAI Dashboard')

def layout():
    """Simple chat interface"""
    return create_simple_chat()