import serial
import serial.tools.list_ports
import requests
import json
import time

# Config
# Ensure this matches your Flask server's address
API_URL = "http://127.0.0.1:5000/api/sensors" 
MOTOR_API_URL = "http://127.0.0.1:5000/api/motor"
BAUD_RATE = 9600

def find_arduino_port():
    print("Searching for Arduino...")
    ports = list(serial.tools.list_ports.comports())
    # On Windows, Arduino Uno usually shows up as Arduino or CH340 or simply COMx
    for p in ports:
        if "Arduino" in p.description or "CH340" in p.description or "USB Serial" in p.description:
            print(f"Found possible Arduino on port: {p.device}")
            return p.device
            
    # Fallback to the first available COM port if no description matches
    for p in ports:
        if "COM" in p.device:
            print(f"Guessed port: {p.device}")
            return p.device
            
    print("Error: No COM ports found! Is the Arduino plugged in?")
    return None

def main():
    print("═══════════════════════════════════════════════")
    print(" AquaIntel — Python Serial to Web Bridge       ")
    print("═══════════════════════════════════════════════")
    port = find_arduino_port()
    if not port:
        port = input("Please type your Arduino COM port (e.g., COM3) and press Enter: ")
        if not port:
            return

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=2)
        print(f"✅ Successfully connected to Arduino on {port} at {BAUD_RATE} baud.")
        print(f"📡 Forwarding live data to: {API_URL}")
        print("Waiting for sensor data...")
        print("-" * 50)
        
        # Give Arduino time to reset on connection
        time.sleep(2)
        ser.reset_input_buffer()
        
        last_motor_state = "off"
        
        while True:
            # Check for motor commands from the backend every iteration
            try:
                state_resp = requests.get(MOTOR_API_URL, timeout=0.1)
                if state_resp.status_code == 200:
                    current_state = state_resp.json().get('motor_state', 'off')
                    if current_state != last_motor_state:
                        # Send command to Arduino
                        cmd = '{"cmd":"pump","val":"' + current_state + '"}\n'
                        ser.write(cmd.encode('utf-8'))
                        print(f"[➔ Arduino] Sent motor command: {cmd.strip()}")
                        last_motor_state = current_state
            except Exception:
                pass # Ignore if server is down or slow

            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                    
                print(f"[Arduino] {line}")
                
                # Check if it's a JSON payload from the ArduinoEdge code
                if line.startswith('{') and line.endswith('}'):
                    try:
                        # Arduino sends JSON like: {"wl":85.2,"fr":12.3,"sm":67.1,"wt":22.5,"vs":"open","al":0,"pm":0}
                        data = json.loads(line)
                        
                        # Map Arduino's short keys to the Flask server's expected long keys
                        payload = {
                            "water_level": data.get("wl", 0.0),
                            "flow_rate": data.get("fr", 0.0),
                            "soil_moisture": data.get("sm", 0.0),
                            "water_temperature": data.get("wt", 0.0)
                        }
                        
                        # Send via HTTP POST to the Flask backend
                        response = requests.post(API_URL, json=payload)
                        if response.status_code in [200, 201]:
                            print(f"  [➔ Flask] Success! Inserted into database.")
                        else:
                            print(f"  [➔ Flask] Error {response.status_code}: {response.text}")
                            
                    except json.JSONDecodeError:
                        print("  [Warning] Invalid JSON received from Arduino.")
                    except requests.exceptions.ConnectionError:
                        print("  [Error] Cannot connect to Flask server. Is `python run.py` actively running in another terminal?")
                    except Exception as e:
                        print(f"  [Error] Bridge error: {e}")
                        
            time.sleep(0.01) # Tiny sleep to prevent Python from maxing out your CPU
            
    except serial.SerialException as e:
        print(f"❌ Serial Error: Could not open port {port}.")
        print("IMPORTANT: Make sure the Arduino IDE 'Serial Monitor' is CLOSED! Only one program can use the COM port at a time.")
        print(f"Details: {e}")
    except KeyboardInterrupt:
        print("\nStopping Serial Bridge...")
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()