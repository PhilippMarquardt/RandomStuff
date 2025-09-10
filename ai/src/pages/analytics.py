import dash
from dash import html, dcc, callback, Input, Output
from components.analytics_components import create_analytics_chart, create_metrics_cards

# Register this page
dash.register_page(__name__, path='/analytics', title='Analytics - CoreAI Dashboard')

def layout():
    """Analytics page layout"""
    return html.Div([
        # Page Header
        html.Section([
            html.Div([
                html.H1("Analytics Dashboard", className="text-4xl font-bold text-white mb-4"),
                html.P("Explore your data with advanced analytics and visualizations.", 
                      className="text-xl text-blue-100")
            ], className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center")
        ], className="bg-gradient-to-r from-green-600 to-blue-600 text-white"),
        
        # Analytics Content
        html.Section([
            html.Div([
                # Controls Section
                html.Div([
                    html.H2("Data Controls", className="text-2xl font-bold text-gray-900 mb-6"),
                    html.Div([
                        html.Div([
                            html.Label("Select Dataset:", className="block text-sm font-medium text-gray-700 mb-2"),
                            dcc.Dropdown(
                                id='dataset-selector',
                                options=[
                                    {'label': 'Sales Data', 'value': 'sales'},
                                    {'label': 'User Analytics', 'value': 'users'},
                                    {'label': 'Performance Metrics', 'value': 'performance'}
                                ],
                                value='sales',
                                className="mb-4"
                            )
                        ], className="w-full md:w-1/3 px-2"),
                        
                        html.Div([
                            html.Label("Date Range:", className="block text-sm font-medium text-gray-700 mb-2"),
                            dcc.DatePickerRange(
                                id='date-range-picker',
                                start_date='2024-01-01',
                                end_date='2024-12-31',
                                className="mb-4"
                            )
                        ], className="w-full md:w-1/3 px-2"),
                        
                        html.Div([
                            html.Label("Chart Type:", className="block text-sm font-medium text-gray-700 mb-2"),
                            dcc.RadioItems(
                                id='chart-type-selector',
                                options=[
                                    {'label': 'Line Chart', 'value': 'line'},
                                    {'label': 'Bar Chart', 'value': 'bar'},
                                    {'label': 'Scatter Plot', 'value': 'scatter'}
                                ],
                                value='line',
                                className="space-y-2"
                            )
                        ], className="w-full md:w-1/3 px-2")
                        
                    ], className="flex flex-wrap -mx-2")
                ], className="bg-white rounded-lg shadow-md p-6 mb-8"),
                
                # Analytics Chart Component
                create_analytics_chart(),
                
                # Key Metrics Cards
                create_metrics_cards()
                
            ], className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12")
        ], className="bg-gray-50 min-h-screen")
    ])