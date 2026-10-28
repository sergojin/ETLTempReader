#!/usr/bin/env python3
"""Live temperature graph for ETLTempReader's temperature_log.csv.

Install: python3 -m pip install dash plotly pandas
Run:     python3 dashboard.py --log-file temperature_log.csv
Access remotely via SSH: ssh -L 8050:localhost:8050 daq@timingdaq03
Then open http://localhost:8050 on your own computer.
"""
import argparse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--log-file', default='temperature_log.csv')
parser.add_argument('--port', type=int, default=8050)
args = parser.parse_args()
LOG_FILE = Path(args.log_file).expanduser().resolve()

app = Dash(__name__)
app.title = 'ETL Temperature Monitor'

app.layout = html.Div([
    html.H1('ETL Temperature Monitor', style={'marginBottom': '8px'}),
    html.Div(id='latest', style={'fontSize': '24px', 'fontWeight': 'bold'}),
    html.Div(id='status', style={'color': '#666', 'margin': '8px 0 16px'}),
    html.Label('Show measurements from:'),
    dcc.Dropdown(id='range', options=[
        {'label': 'Last hour', 'value': '1h'},
        {'label': 'Last 6 hours', 'value': '6h'},
        {'label': 'Last 24 hours', 'value': '24h'},
        {'label': 'Last 7 days', 'value': '7d'},
        {'label': 'All data', 'value': 'all'},
    ], value='24h', clearable=False, style={'maxWidth': '250px'}),
    dcc.Graph(id='temperature-graph', style={'height': '65vh', 'minHeight': '350px'}),
    dcc.Interval(id='refresh', interval=5000, n_intervals=0),
], style={'fontFamily': 'Arial, sans-serif', 'maxWidth': '1100px',
          'margin': '30px auto', 'padding': '0 16px'})


@app.callback(
    Output('temperature-graph', 'figure'),
    Output('latest', 'children'),
    Output('status', 'children'),
    Input('refresh', 'n_intervals'),
    Input('range', 'value'),
)
def refresh_graph(_n, selected_range):
    fig = go.Figure()
    fig.update_layout(template='plotly_white', xaxis_title='Time',
                      yaxis_title='Temperature (°C)', margin=dict(l=50, r=20, t=35, b=50))
    if not LOG_FILE.exists():
        return fig, 'Waiting for data…', f'CSV file not found: {LOG_FILE}'
    try:
        df = pd.read_csv(LOG_FILE, usecols=['timestamp', 'temperature_C'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        df['temperature_C'] = pd.to_numeric(df['temperature_C'], errors='coerce')
        df = df.dropna().sort_values('timestamp')
    except (OSError, ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        return fig, 'Waiting for valid data…', f'Cannot read CSV: {exc}'
    if df.empty:
        return fig, 'Waiting for readings…', 'CSV has no valid measurements yet.'

    latest = df.iloc[-1]
    now = pd.Timestamp.now(tz='UTC')
    age = (now - latest['timestamp']).total_seconds()
    status = f"Last reading: {latest['timestamp'].astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}"
    if age > 60:
        status += f' · Warning: last reading is {int(age)} seconds old'

    hours = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}.get(selected_range)
    if hours is not None:
        df = df[df['timestamp'] >= now - pd.Timedelta(hours=hours)]
    if not df.empty:
        fig.add_trace(go.Scatter(x=df['timestamp'].dt.tz_convert(None),
                                 y=df['temperature_C'], mode='lines+markers',
                                 line={'width': 2}, marker={'size': 3},
                                 name='RTD200'))
        fig.update_layout(hovermode='x unified')
    else:
        status += ' · No readings in selected time range'
    return fig, f"Current temperature: {latest['temperature_C']:.2f} °C", status


if __name__ == '__main__':
    print(f'Reading {LOG_FILE}')
    print(f'Dashboard at http://127.0.0.1:{args.port}')
    app.run(host='127.0.0.1', port=args.port, debug=False)
