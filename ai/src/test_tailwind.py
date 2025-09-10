"""
Simple test to verify TailwindCSS is working with Dash
"""
import dash
from dash import Dash, html

# Initialize the Dash app
app = Dash(__name__)

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

app.layout = html.Div([
    html.H1("TailwindCSS Test", className="text-4xl font-bold text-blue-600 text-center py-8"),
    html.Div([
        html.Div("This should be a blue box", className="bg-blue-500 text-white p-4 rounded-lg mb-4"),
        html.Div("This should be a green box", className="bg-green-500 text-white p-4 rounded-lg mb-4"),
        html.Div("This should be a red box", className="bg-red-500 text-white p-4 rounded-lg mb-4"),
    ], className="max-w-md mx-auto"),
    html.P("If you see colored boxes above, TailwindCSS is working!", className="text-center text-gray-600")
], className="min-h-screen bg-gray-100 py-8")

if __name__ == '__main__':
    app.run(debug=True, port=8051)  # Use different port to avoid conflicts

