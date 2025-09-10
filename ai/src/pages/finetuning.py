import dash
from dash import html, dcc, callback, Input, Output, State
from components.finetuning_components import create_finetuning_interface

# Register this page with Dash Pages
dash.register_page(__name__, path='/finetuning', title='Fine-tuning - CoreAI Dashboard')

def layout():
    """Fine-tuning settings interface"""
    return create_finetuning_interface()