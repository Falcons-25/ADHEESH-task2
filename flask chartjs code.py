from flask import Flask, render_template, jsonify
import serial
import threading

sensor_value = 0

def read_sensor_data():
    global sensor_value
    try:
        with serial.Serial("COM8", baudrate=9600) as ser:
            while True:
                value = ser.readline().decode('UTF-8').strip()
                try:
                    processed_value = float(value.split(',')[0])
                    sensor_value = processed_value
                    print("Sensor value:", sensor_value)
                except (ValueError, IndexError) as e:
                    print(f"Error parsing sensor data: {e}. Raw data: {value}")
    except serial.SerialException as e:
        print(f"Error connecting to serial port: {e}")

sensor_thread = threading.Thread(target=read_sensor_data)
sensor_thread.daemon = True
sensor_thread.start()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('flask_chartjs.html')

@app.route('/sensor_data')
def get_sensor_data():
    print(f"Returning sensor value: {sensor_value}")
    data = {'sensor_value': sensor_value}
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
