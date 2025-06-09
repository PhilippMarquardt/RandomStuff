"""
MCP (Model Context Protocol) Tools for the chat application.
This module contains various tools that can be used by the LLM agent.
"""

import requests
from typing import Dict, Any, Optional
from langchain_core.tools import tool
import os


@tool
def get_weather(city: str) -> str:
    """Get current weather for a given city.
    
    Args:
        city (str): The name of the city to get weather for
        
    Returns:
        str: Weather information for the city
    """
    # For demo purposes, we'll use a mock response
    # In production, you would integrate with a real weather API like OpenWeatherMap
    mock_weather_data = {
        "san francisco": "Partly cloudy, 18°C (64°F), light breeze from the west",
        "new york": "Sunny, 22°C (72°F), calm conditions", 
        "london": "Overcast with light rain, 15°C (59°F), moderate wind",
        "tokyo": "Clear skies, 25°C (77°F), humid conditions",
        "paris": "Partly sunny, 20°C (68°F), light wind from the south",
        "sydney": "Sunny, 28°C (82°F), gentle ocean breeze",
        "berlin": "Cloudy, 16°C (61°F), cool and dry",
        "moscow": "Snow flurries, -5°C (23°F), strong wind",
        "mumbai": "Hot and humid, 32°C (90°F), monsoon season",
        "cairo": "Very sunny, 35°C (95°F), dry desert conditions"
    }
    
    city_lower = city.lower().strip()
    
    if city_lower in mock_weather_data:
        return f"Current weather in {city}: {mock_weather_data[city_lower]}"
    else:
        # For unknown cities, provide a generic response
        return f"Weather data for {city} is not available. This is a demo weather tool. In a real implementation, this would connect to a weather API service."


@tool  
def get_weather_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a given city for the next few days.
    
    Args:
        city (str): The name of the city to get forecast for
        days (int): Number of days to forecast (1-7, default 3)
        
    Returns:
        str: Weather forecast information
    """
    if days < 1 or days > 7:
        return "Forecast can only be provided for 1-7 days ahead."
        
    # Mock forecast data
    forecasts = {
        "today": "Partly cloudy, High: 22°C, Low: 15°C",
        "tomorrow": "Sunny, High: 25°C, Low: 17°C", 
        "day_after": "Light rain, High: 19°C, Low: 12°C",
        "day_3": "Overcast, High: 21°C, Low: 14°C",
        "day_4": "Sunny, High: 26°C, Low: 18°C",
        "day_5": "Partly cloudy, High: 23°C, Low: 16°C",
        "day_6": "Thunderstorms, High: 20°C, Low: 13°C",
        "day_7": "Clear skies, High: 24°C, Low: 17°C"
    }
    
    forecast_days = ["today", "tomorrow", "day_after", "day_3", "day_4", "day_5", "day_6", "day_7"]
    
    result = f"{days}-day weather forecast for {city}:\n"
    for i in range(days):
        day_name = "Today" if i == 0 else f"Day {i+1}"
        result += f"{day_name}: {forecasts[forecast_days[i]]}\n"
    
    return result.strip()


@tool
def search_web(query: str) -> str:
    """Search the web for information on a given topic.
    
    Args:
        query (str): The search query
        
    Returns:
        str: Search results summary
    """
    # This is a mock search tool for demonstration
    # In production, you would integrate with a real search API
    return f"Mock search results for '{query}': This is a demo search tool. In a real implementation, this would perform web searches and return relevant information."


@tool
def calculate(expression: str) -> str:
    """Safely evaluate mathematical expressions.
    
    Args:
        expression (str): Mathematical expression to evaluate
        
    Returns:
        str: Result of the calculation
    """
    try:
        # Only allow safe mathematical operations
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Only basic mathematical operations are allowed (+, -, *, /, parentheses, and numbers)."
        
        # Evaluate the expression safely
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating '{expression}': {str(e)}"


# Available MCP tools - add new tools to this list
AVAILABLE_TOOLS = [
    get_weather,
    get_weather_forecast,
    search_web,
    calculate
]

# Tool categories for UI organization
TOOL_CATEGORIES = {
    "Weather": [get_weather, get_weather_forecast],
    "Utilities": [search_web, calculate]
} 