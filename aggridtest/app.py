import pandas as pd
import numpy as np
from dash import Dash, html
import dash_ag_grid as dag
import plotly.graph_objects as go

def make_diverge_chart(neg_values, pos_values, colors, max_range):
    """Creates a diverging bar chart figure with one distinct color per bar."""
    # This function now uses the max_range passed into it.

    if not any(neg_values) and not any(pos_values):
        return go.Figure()

    # We NO LONGER calculate max_range here. It's provided as an argument.
    # max_range = max(sum(neg_values), sum(pos_values), 1)  <- DELETE THIS LINE

    fig = go.Figure()

    # plot negatives
    current_base = 0
    for i, val in enumerate(neg_values):
        fig.add_trace(go.Bar(
            y=[0], x=[-val], base=current_base, orientation='h',
            width=0.4, marker_color=colors[i], showlegend=False
        ))
        current_base -= val

    # plot positives
    current_base = 0
    for i, val in enumerate(pos_values):
        fig.add_trace(go.Bar(
            y=[0], x=[val], base=current_base, orientation='h',
            width=0.4, marker_color=colors[len(neg_values) + i], showlegend=False
        ))
        current_base += val

    # zero-line
    fig.add_shape(
        type='line', x0=0, x1=0, y0=-0.5, y1=0.5,
        line=dict(color='black', width=1)
    )

    # The layout now uses the global max_range for a consistent scale.
    fig.update_layout(
        barmode='stack', bargap=0, bargroupgap=0,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False, range=[-max_range * 1.1, max_range * 1.1]),
        yaxis=dict(visible=False),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def create_legend_item(color, text):
    """Creates a single item for the legend."""
    return html.Div([
        html.Div(style={'width': '30px', 'height': '4px', 'backgroundColor': color, 'marginRight': '10px'}),
        html.Span(text, style={'color': '#003366', 'fontSize': '14px'})
    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'})

def create_sdg_grid(df, title="SDG Revenue Exposure (%)"):
    """
    Creates a self-contained Dash AG Grid component with SDG data, charts, and a legend.
    """
    # --- Data Processing ---
    df_processed = df.copy()

    # (Text processing for leftText and rightText remains the same)
    df_processed['leftText'] = df_processed.apply(
        lambda r: f"""<div style='text-align:center'>
                        {f'{r.pf_left:.1f}%' if pd.notna(r.pf_left) else '-'}
                        <br>
                        {f'{r.bm_left:.1f}%' if pd.notna(r.bm_left) else '-'}
                      </div>""", axis=1)

    df_processed['rightText'] = df_processed.apply(
        lambda r: f"""<div style='text-align:center'>
                         {f'{r.pf_right:.1f}%' if pd.notna(r.pf_right) else '-'}
                         <br>
                         {f'{r.bm_right:.1f}%' if pd.notna(r.bm_right) else '-'}
                       </div>""", axis=1)

    chart_data_cols = ['pf_neg1', 'pf_neg2', 'pf_pos1', 'pf_pos2',
                       'bm_neg1', 'bm_neg2', 'bm_pos1', 'bm_pos2']
    df_processed[chart_data_cols] = df_processed[chart_data_cols].fillna(0)


    # --- Color and Chart Creation ---
    PF_COLORS = ['#555555', '#AAAAAA', '#0074D9', '#64B5F6']
    BM_COLORS = ['#555555', '#AAAAAA', '#2ECC40', '#90EE90']

    # NEW: Calculate the single global maximum scale for all charts
    pf_neg_total = df_processed['pf_neg1'] + df_processed['pf_neg2']
    pf_pos_total = df_processed['pf_pos1'] + df_processed['pf_pos2']
    bm_neg_total = df_processed['bm_neg1'] + df_processed['bm_neg2']
    bm_pos_total = df_processed['bm_pos1'] + df_processed['bm_pos2']
    global_max_range = max(
        pf_neg_total.max(),
        pf_pos_total.max(),
        bm_neg_total.max(),
        bm_pos_total.max()
    )


    df_processed['pf_neg_values'] = df_processed.apply(lambda r: [r.pf_neg1, r.pf_neg2], axis=1)
    df_processed['pf_pos_values'] = df_processed.apply(lambda r: [r.pf_pos1, r.pf_pos2], axis=1)
    df_processed['bm_neg_values'] = df_processed.apply(lambda r: [r.bm_neg1, r.bm_neg2], axis=1)
    df_processed['bm_pos_values'] = df_processed.apply(lambda r: [r.bm_pos1, r.bm_pos2], axis=1)

    # UPDATE: Pass the global_max_range to each chart creation call
    df_processed['pf_chart'] = df_processed.apply(
        lambda r: make_diverge_chart(r.pf_neg_values, r.pf_pos_values, PF_COLORS, global_max_range), axis=1)
    df_processed['bm_chart'] = df_processed.apply(
        lambda r: make_diverge_chart(r.bm_neg_values, r.bm_pos_values, BM_COLORS, global_max_range), axis=1)

    # ... (The rest of the function, columnDefs, legend, etc. remains exactly the same) ...

    # --- Column and Row Definitions ---
    revenue_header_template = """
    <div class="ag-cell-label-container" role="presentation" style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
        <span style="flex: 1; text-align: left;">Negative</span>
        <span style="flex: 1; text-align: center; font-weight: bold;">Revenue Based</span>
        <span style="flex: 1; text-align: right;">Positive</span>
    </div>
    """
    columnDefs = [
        {"headerName": "SDGs", "field": "svg", "cellRenderer": "SvgRenderer", "width": 200, "suppressSizeToFit": True},
        {"headerName": "Portfolio / Benchmark", "field": "leftText", "cellRenderer": "HtmlRenderer", "width": 200, "suppressSizeToFit": True, "headerClass": "ag-center-header"},
        {
            "headerComponentParams": {"template": revenue_header_template},
            "field": "pf_chart",
            "cellRenderer": "DualDivergeRenderer",
            "flex": 1,
            "headerClass": "ag-center-header"
        },
        {"headerName": "Portfolio / Benchmark", "field": "rightText", "cellRenderer": "HtmlRenderer", "width": 200, "suppressSizeToFit": True, "headerClass": "ag-center-header"}
    ]
    total_pf_left = df['pf_left'].sum()
    total_bm_left = df['bm_left'].sum()
    total_pf_right = df['pf_right'].sum()
    total_bm_right = df['bm_right'].sum()
    total_row = {
        "svg": "<div style='font-weight:bold; padding-left: 10px;'>Total Portfolio<br>Total Benchmark</div>",
        "leftText": f"<div style='text-align:center; font-weight:bold;'>{total_pf_left:.1f}%<br>{total_bm_left:.1f}%</div>",
        "rightText": f"<div style='text-align:center; font-weight:bold;'>{total_pf_right:.1f}%<br>{total_bm_right:.1f}%</div>",
        "pf_chart": None, "bm_chart": None
    }
    pinned_row_data = [total_row]
    legend = html.Div([
        create_legend_item(PF_COLORS[0], 'Negative, high impact'),
        create_legend_item(PF_COLORS[1], 'Negative, medium impact'),
        create_legend_item(PF_COLORS[2], 'Portfolio, high impact'),
        create_legend_item(PF_COLORS[3], 'Portfolio, medium impact'),
        create_legend_item(BM_COLORS[2], 'Benchmark, high impact'),
        create_legend_item(BM_COLORS[3], 'Benchmark, medium impact'),
    ], style={'display': 'flex', 'justifyContent': 'center', 'marginTop': '20px', 'flexWrap': 'wrap'})
    grid = dag.AgGrid(
        rowData=df_processed.to_dict('records'),
        columnDefs=columnDefs,
        defaultColDef={"resizable": False},
        dashGridOptions={
            "rowHeight": 80, "pinnedBottomRowData": pinned_row_data
        },
        className="ag-theme-alpine custom-grid",
        style={"width": "100%", "height": "540px"},
        dangerously_allow_code=True,
    )
    return html.Div([
        html.H4(title, className="page-title"),
        html.Div([
            grid,
            legend
        ], className="grid-legend-wrapper")
    ], id="sdg-revenue-grid-container")

# --- Example Usage ---
if __name__ == '__main__':
    SVG_ICON = """<svg width="24" height="24" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" fill="#0074D9"/></svg>"""
    sample_df = pd.DataFrame({
        "svg":      [SVG_ICON] * 5,
        "pf_left":  [11.0, 10.5, np.nan, 9.8, 8.6],
        "bm_left":  [10.1, 9.7, 11.0, 8.5, 7.9],
        "pf_neg1":  [10, 12, 8, 9, 7], "pf_neg2": [5, 3, 4, 2, 6],
        "pf_pos1":  [20, 18, 22, 15, 19], "pf_pos2": [7, np.nan, 6, 8, 4],
        "bm_neg1":  [8, 10, 6, 7, 100], "bm_neg2": [4, 2, 3, 1, 5],
        "bm_pos1":  [18, 16, 20, 13, 17], "bm_pos2": [6, 4, 5, 7, 100],
        "pf_right": [12.4, 9.7, 11.2, 8.9, 10.1],
        "bm_right": [11.0, 9.2, 10.8, np.nan, 9.4]
    })

    app = Dash(__name__, external_stylesheets=['/assets/styles.css'])
    app.layout = create_sdg_grid(sample_df)
    app.run_server(debug=True)