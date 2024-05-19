import time
import threading
import os
import signal
from dash import Dash, dcc, html, Input, Output, State, callback
from dash.dash import no_update
from dash_daq import StopButton
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.subplots as sp
import serial
import serial.serialutil

# Global variables
altitude = 0
alt_data = []
ctrl_c_pressed = False


lock = threading.Lock()

def serial_monitor(port: str, baudrate: int) -> None:
    global ser, altitude
    ser = serial.Serial(port=port, baudrate=baudrate)
    while True:
        try:
            line = ser.readline().decode().strip()
            with lock:
                altitude = line.split(',')[0]
                alt_data.append(altitude)
            with open("ultrasonic.csv", 'a') as file:
                print(time.strftime("%H:%M:%S,"), altitude, file=file)
        except serial.serialutil.SerialException as e:
            print("Arduino disconnected.")
            with open("ultrasonic.csv", 'a') as file:
                print("Arduino disconnected.", file=file)
            app.server_context['disconnected'] = True
            break
        except KeyboardInterrupt:
            print("User terminated operation.")
            with open("ultrasonic.csv", 'a') as file:
                print("User terminated operation.", file=file)
            break
    end_code(1, 1)
    os.kill(os.getpid(), signal.SIGINT)

@callback(Output("live-updates-text", "children"), Input("interval-component", "n_intervals"))
def update_altitude_value(n):
    style = {"padding": "15px", "fontSize": "60px"}
    with lock:
        current_altitude = altitude
    return [html.Span(f'Altitude: {current_altitude}ft', style=style)]

@callback(Output("live-updates-graph", "figure"), Input("interval-component", "n_intervals"))
def update_graph_live(n):
    with lock:
        time_data = data['time']
        altitude_data = data['altitude']
        if len(alt_data) > 0:
            time_data.append(time.strftime("%H:%M:%S"))
            altitude_data.append(float(alt_data[-1]))
    
    fig = sp.make_subplots(rows=1, cols=1)
    fig['layout']['legend'] = {'x': 0, 'y': 0, 'xanchor': 'left'}
    fig.add_trace(
        go.Scatter(
            x=time_data,
            y=altitude_data,
            name='Altitude',
            mode='lines+markers',
            type='scatter'
        ),
        row=1, col=1
    )
    return fig

@callback(
    Output("EOE-modal", "is_open"),
    [Input("stop-button", "n_clicks"), Input("interval-component", "n_intervals")],
    [State("EOE-modal", "is_open")]
)
def end_code(stop_pressed, n_intervals, is_open):
    if stop_pressed and not is_open:
        return True
    if app.server_context.get('disconnected', False):
        return True
    return is_open

@callback(
    Output("ctrlc-modal", "is_open"),
    Input("interval-component", "n_intervals"),
    State("ctrlc-modal", "is_open")
)
def show_ctrlc_modal(n_intervals, is_open):
    if ctrl_c_pressed and not is_open and not app.server_context.get('disconnected', False):
        return True
    return is_open

@callback(Output("stopbtn-output", "children"), Input("stop-button", "n_clicks"))
def end_execution(n_clicks):
    if n_clicks:
        with open("ultrasonic.csv", 'a') as file:
            print("User terminated operation.")
            print("User terminated operation.", file=file)
        time.sleep(0.2)
        os.kill(os.getpid(), signal.SIGINT)

if __name__ == "__main__":
    data = {
        'time': [],
        'altitude': [],
    }
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.server_context = {}

    thread_serial = threading.Thread(target=serial_monitor, args=("COM8", 9600))
    thread_serial.start()

    app.layout = html.Div([
        html.Div([
            html.H4("Arduino Live Data Feed"),
            html.Div(id="live-updates-text"),
            dcc.Graph(id="live-updates-graph"),
            dcc.Interval(id="interval-component", interval=1000, n_intervals=0),
        ]),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Error"), close_button=True),
            dbc.ModalBody("The sensor has been disconnected from the COM port."),
        ], id="EOE-modal", size="sm", keyboard=False, backdrop=True, centered=True, is_open=False),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Error"), close_button=True),
            dbc.ModalBody("PROGRAM INTERRUPTED BY KEYBOARD."),
        ], id="ctrlc-modal", size="sm", keyboard=False, backdrop=True, centered=True, is_open=False),
        StopButton(id="stop-button", n_clicks=0),
        html.Div(id="stopbtn-output"),
    ])

    print("Setup complete")

    app_thread = threading.Thread(target=lambda: app.run(debug=False, use_reloader=False))
    app_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Ctrl+C pressed.")
        ctrl_c_pressed = True
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)
