"""
Utility functions for the Dash application
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_data(data_type='sales', days=365):
    """
    Generate sample data for demonstration purposes
    
    Args:
        data_type (str): Type of data to generate ('sales', 'users', 'performance')
        days (int): Number of days of data to generate
    
    Returns:
        pd.DataFrame: Generated sample data
    """
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                         end=datetime.now(), freq='D')
    
    if data_type == 'sales':
        # Generate sales data with seasonal patterns
        base_sales = 1000
        seasonal = np.sin(np.arange(len(dates)) * 2 * np.pi / 365) * 200
        trend = np.arange(len(dates)) * 0.5
        noise = np.random.normal(0, 100, len(dates))
        values = base_sales + seasonal + trend + noise
        
    elif data_type == 'users':
        # Generate user growth data
        base_users = 500
        growth = np.arange(len(dates)) * 1.2
        noise = np.random.normal(0, 50, len(dates))
        values = base_users + growth + noise
        
    elif data_type == 'performance':
        # Generate performance metrics (0-100 scale)
        base_performance = 80
        variation = np.sin(np.arange(len(dates)) * 2 * np.pi / 30) * 10
        noise = np.random.normal(0, 5, len(dates))
        values = np.clip(base_performance + variation + noise, 0, 100)
        
    else:
        raise ValueError(f"Unknown data_type: {data_type}")
    
    return pd.DataFrame({
        'date': dates,
        'value': values,
        'data_type': data_type
    })

def format_number(number, format_type='currency'):
    """
    Format numbers for display
    
    Args:
        number (float): Number to format
        format_type (str): Type of formatting ('currency', 'percentage', 'integer')
    
    Returns:
        str: Formatted number string
    """
    if format_type == 'currency':
        return f"${number:,.2f}"
    elif format_type == 'percentage':
        return f"{number:.2f}%"
    elif format_type == 'integer':
        return f"{int(number):,}"
    else:
        return f"{number:.2f}"

def calculate_metrics(data):
    """
    Calculate basic metrics from data
    
    Args:
        data (pd.Series or list): Data to analyze
    
    Returns:
        dict: Dictionary containing calculated metrics
    """
    if isinstance(data, list):
        data = pd.Series(data)
    
    return {
        'mean': data.mean(),
        'median': data.median(),
        'std': data.std(),
        'min': data.min(),
        'max': data.max(),
        'count': len(data),
        'sum': data.sum()
    }

def get_color_palette(n_colors=10):
    """
    Get a color palette for charts
    
    Args:
        n_colors (int): Number of colors needed
    
    Returns:
        list: List of color hex codes
    """
    # Modern color palette
    colors = [
        '#3B82F6',  # Blue
        '#10B981',  # Green
        '#F59E0B',  # Yellow
        '#EF4444',  # Red
        '#8B5CF6',  # Purple
        '#06B6D4',  # Cyan
        '#84CC16',  # Lime
        '#F97316',  # Orange
        '#EC4899',  # Pink
        '#6B7280'   # Gray
    ]
    
    # Repeat colors if more are needed
    while len(colors) < n_colors:
        colors.extend(colors[:n_colors - len(colors)])
    
    return colors[:n_colors]

