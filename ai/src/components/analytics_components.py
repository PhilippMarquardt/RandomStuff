from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

def create_analytics_chart():
    """Create the main analytics chart component"""
    return html.Div([
        html.H2("Data Visualization", className="text-2xl font-bold text-gray-900 mb-6"),
        html.Div([
            # Main Chart
            html.Div([
                dcc.Graph(id="main-analytics-chart", className="w-full h-96")
            ], className="w-full lg:w-2/3 px-2"),
            
            # Side Panel with additional info
            html.Div([
                html.Div([
                    html.H3("Chart Insights", className="text-lg font-semibold text-gray-900 mb-4"),
                    html.Div(id="chart-insights", className="text-gray-600"),
                    
                    html.Hr(className="my-6"),
                    
                    html.H3("Data Summary", className="text-lg font-semibold text-gray-900 mb-4"),
                    html.Div(id="data-summary", className="text-gray-600")
                ], className="bg-gray-50 rounded-lg p-4")
            ], className="w-full lg:w-1/3 px-2")
            
        ], className="flex flex-wrap -mx-2")
    ], className="bg-white rounded-lg shadow-md p-6 mb-8")

def create_metrics_cards():
    """Create key metrics cards component"""
    return html.Div([
        html.H2("Key Metrics", className="text-2xl font-bold text-gray-900 mb-6"),
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Total Revenue", className="text-lg font-semibold text-gray-700"),
                    html.P("$124,500", className="text-3xl font-bold text-green-600")
                ], className="text-center")
            ], className="bg-white rounded-lg shadow-md p-6"),
            
            html.Div([
                html.Div([
                    html.H3("Active Users", className="text-lg font-semibold text-gray-700"),
                    html.P("2,847", className="text-3xl font-bold text-blue-600")
                ], className="text-center")
            ], className="bg-white rounded-lg shadow-md p-6"),
            
            html.Div([
                html.Div([
                    html.H3("Conversion Rate", className="text-lg font-semibold text-gray-700"),
                    html.P("3.24%", className="text-3xl font-bold text-purple-600")
                ], className="text-center")
            ], className="bg-white rounded-lg shadow-md p-6"),
            
            html.Div([
                html.Div([
                    html.H3("Avg. Session", className="text-lg font-semibold text-gray-700"),
                    html.P("4m 32s", className="text-3xl font-bold text-orange-600")
                ], className="text-center")
            ], className="bg-white rounded-lg shadow-md p-6")
            
        ], className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6")
    ], className="mb-8")

@callback(
    [Output('main-analytics-chart', 'figure'),
     Output('chart-insights', 'children'),
     Output('data-summary', 'children')],
    [Input('dataset-selector', 'value'),
     Input('chart-type-selector', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def update_analytics_chart(dataset, chart_type, start_date, end_date):
    """Update the analytics chart based on user selections"""
    
    # Generate sample data based on dataset selection
    if dataset == 'sales':
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        np.random.seed(42)
        values = np.random.normal(1000, 200, len(dates)) + np.sin(np.arange(len(dates)) * 0.1) * 300
        df = pd.DataFrame({'Date': dates, 'Value': values, 'Category': 'Sales'})
        title = 'Sales Performance Over Time'
        y_label = 'Sales ($)'
        
    elif dataset == 'users':
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        np.random.seed(24)
        values = np.random.normal(500, 100, len(dates)) + np.arange(len(dates)) * 0.5
        df = pd.DataFrame({'Date': dates, 'Value': values, 'Category': 'Users'})
        title = 'User Growth Over Time'
        y_label = 'Active Users'
        
    else:  # performance
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        np.random.seed(36)
        values = np.random.normal(85, 10, len(dates)) + np.cos(np.arange(len(dates)) * 0.05) * 5
        df = pd.DataFrame({'Date': dates, 'Value': values, 'Category': 'Performance'})
        title = 'Performance Metrics Over Time'
        y_label = 'Performance Score (%)'
    
    # Filter data by date range
    df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
    
    # Create chart based on type
    if chart_type == 'line':
        fig = px.line(df, x='Date', y='Value', title=title)
    elif chart_type == 'bar':
        # Resample to monthly for bar chart
        df_monthly = df.set_index('Date').resample('M').mean().reset_index()
        fig = px.bar(df_monthly, x='Date', y='Value', title=title)
    else:  # scatter
        df['Index'] = range(len(df))
        fig = px.scatter(df, x='Index', y='Value', title=title, hover_data=['Date'])
    
    fig.update_layout(
        font=dict(family="Arial", size=12),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=40, b=0),
        yaxis_title=y_label
    )
    
    # Generate insights
    avg_value = df['Value'].mean()
    max_value = df['Value'].max()
    min_value = df['Value'].min()
    trend = "increasing" if df['Value'].iloc[-1] > df['Value'].iloc[0] else "decreasing"
    
    insights = html.Div([
        html.P(f"• Average: {avg_value:.2f}", className="mb-2"),
        html.P(f"• Maximum: {max_value:.2f}", className="mb-2"),
        html.P(f"• Minimum: {min_value:.2f}", className="mb-2"),
        html.P(f"• Trend: {trend}", className="mb-2"),
    ])
    
    # Generate summary
    summary = html.Div([
        html.P(f"Dataset: {dataset.title()}", className="mb-2"),
        html.P(f"Chart Type: {chart_type.title()}", className="mb-2"),
        html.P(f"Data Points: {len(df)}", className="mb-2"),
        html.P(f"Date Range: {(pd.to_datetime(end_date) - pd.to_datetime(start_date)).days} days", className="mb-2"),
    ])
    
    return fig, insights, summary

