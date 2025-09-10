from dash import html, dcc

def create_footer():
    """Create a footer component with TailwindCSS styling"""
    return html.Footer([
        html.Div([
            html.Div([
                # Company Info
                html.Div([
                    html.H3("CoreAI Dashboard", className="text-lg font-semibold text-white mb-4"),
                    html.P("A modern analytics platform built with Dash and TailwindCSS.", 
                          className="text-gray-300 text-sm")
                ], className="mb-6 md:mb-0"),
                
                # Links
                html.Div([
                    html.H4("Quick Links", className="text-md font-semibold text-white mb-4"),
                    html.Ul([
                        html.Li([
                            dcc.Link("Home", href="/", className="text-gray-300 hover:text-white text-sm transition-colors")
                        ], className="mb-2"),
                        html.Li([
                            dcc.Link("Analytics", href="/analytics", className="text-gray-300 hover:text-white text-sm transition-colors")
                        ], className="mb-2"),
                        html.Li([
                            dcc.Link("Dashboard", href="/dashboard", className="text-gray-300 hover:text-white text-sm transition-colors")
                        ], className="mb-2"),
                        html.Li([
                            dcc.Link("About", href="/about", className="text-gray-300 hover:text-white text-sm transition-colors")
                        ])
                    ])
                ], className="mb-6 md:mb-0"),
                
                # Contact Info
                html.Div([
                    html.H4("Contact", className="text-md font-semibold text-white mb-4"),
                    html.P("Built with ❤️ using Dash & TailwindCSS", className="text-gray-300 text-sm")
                ])
                
            ], className="grid grid-cols-1 md:grid-cols-3 gap-8"),
            
            # Copyright
            html.Hr(className="border-gray-600 my-8"),
            html.Div([
                html.P(f"© 2024 CoreAI Dashboard. All rights reserved.", 
                      className="text-gray-300 text-sm text-center")
            ])
            
        ], className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8")
    ], className="bg-gray-800 text-white mt-auto")

