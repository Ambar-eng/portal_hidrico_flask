from dash import html, dcc, page_registry

def fibonacci_card():
    return html.Div([
        html.Div(id='live-update-text-fibonacci'),
        dcc.Graph(id='graph-fibonacci'),
        dcc.Interval(
            id='interval-component',
            interval=10*1000,  # Update every 10 seconds (in milliseconds)
            n_intervals=0
        )
    ])