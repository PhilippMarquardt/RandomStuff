import dash
from dash import Dash, html, dcc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the Dash app with pages support
app = Dash(
    __name__, 
    use_pages=True,
    pages_folder="pages",
    assets_folder="assets",
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "description", "content": "A modern Dash application with TailwindCSS"},
        {"name": "author", "content": "CoreAIDash"}
    ]
)

# Custom index template with TailwindCSS CDN
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {
                theme: {
                    extend: {
                        colors: {
                            'brand-blue': '#3B82F6',
                            'brand-purple': '#8B5CF6',
                        }
                    }
                }
            }
        </script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Set the app title
app.title = "CoreAI Dashboard"

# Main app layout - just the page container for full-screen chat
app.layout = html.Div([
    dash.page_container
], className="h-screen overflow-hidden")

if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG', 'True').lower() == 'true'
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 8050))
    
    app.run(
        debug=debug_mode,
        host=host,
        port=port
    )
