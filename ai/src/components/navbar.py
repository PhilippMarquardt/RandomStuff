import dash
from dash import html, dcc

def create_navbar():
    """Create a responsive navigation bar with TailwindCSS styling"""
    return html.Nav([
        html.Div([
            # Brand/Logo
            html.Div([
                dcc.Link(
                    "CoreAI Dashboard",
                    href="/",
                    className="text-2xl font-bold text-blue-600 hover:text-blue-800 transition-colors"
                )
            ], className="flex-shrink-0"),
            
            # Navigation Links
            html.Div([
                dcc.Link(
                    "Home",
                    href="/",
                    className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors hover:bg-blue-50"
                ),
                dcc.Link(
                    "Analytics",
                    href="/analytics",
                    className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors hover:bg-blue-50"
                ),
                dcc.Link(
                    "Dashboard",
                    href="/dashboard",
                    className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors hover:bg-blue-50"
                ),
                dcc.Link(
                    "About",
                    href="/about",
                    className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors hover:bg-blue-50"
                )
            ], className="hidden md:flex space-x-6"),
            
            # Mobile menu button (simplified for now)
            html.Div([
                html.Button([
                    "☰"  # Simple hamburger menu character
                ], className="md:hidden text-gray-700 hover:text-blue-600 p-2 text-xl")
            ])
            
        ], className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16")
    ], className="bg-white shadow-lg border-b border-gray-200")
