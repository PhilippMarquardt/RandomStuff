import dash
from dash import html, dcc

# Register this page as the custom 404 page
dash.register_page(__name__, title='Page Not Found - CoreAI Dashboard')

layout = html.Div([
    html.Section([
        html.Div([
            html.Div([
                # 404 Illustration
                html.Div([
                    html.H1("404", className="text-9xl font-bold text-gray-300 mb-4"),
                ], className="text-center mb-8"),
                
                # Error Message
                html.H2("Oops! Page Not Found", className="text-4xl font-bold text-gray-900 text-center mb-4"),
                html.P(
                    "The page you're looking for doesn't exist. It might have been moved, deleted, or you entered the wrong URL.",
                    className="text-xl text-gray-600 text-center mb-8 max-w-2xl mx-auto"
                ),
                
                # Action Buttons
                html.Div([
                    dcc.Link(
                        "Go Home",
                        href="/",
                        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-8 rounded-lg transition-colors mr-4"
                    ),
                    html.A(
                        "Go Back",
                        href="javascript:history.back()",
                        className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-3 px-8 rounded-lg transition-colors inline-block text-center no-underline"
                    )
                ], className="text-center"),
                
                # Helpful Links
                html.Div([
                    html.H3("Or try these links:", className="text-lg font-semibold text-gray-900 mb-4 text-center"),
                    html.Div([
                        dcc.Link("Home", href="/", className="text-blue-600 hover:text-blue-800 mx-4"),
                        dcc.Link("Analytics", href="/analytics", className="text-blue-600 hover:text-blue-800 mx-4"),
                        dcc.Link("Dashboard", href="/dashboard", className="text-blue-600 hover:text-blue-800 mx-4"),
                        dcc.Link("About", href="/about", className="text-blue-600 hover:text-blue-800 mx-4")
                    ], className="text-center")
                ], className="mt-12")
                
            ], className="max-w-4xl mx-auto text-center")
        ], className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20")
    ], className="bg-gray-50 min-h-screen flex items-center")
])
