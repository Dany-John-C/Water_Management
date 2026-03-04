#!/usr/bin/env python3
"""
Data Simulator for Water Management System
Continuously generates realistic sensor data and adds it to the database
"""

import time
import random
import requests
from datetime import datetime
import threading

class WaterSensorSimulator:
    def __init__(self, api_url="http://localhost:5000/api"):
        self.api_url = api_url
        self.running = False
        
        # Initial sensor values
        self.water_level = 85.0
        self.flow_rate = 24.5
        self.soil_moisture = 67.0
        self.water_temperature = 22.5
        
        # Simulation parameters
        self.update_interval = 10  # seconds
        
    def generate_realistic_data(self):
        """Generate realistic sensor data with natural variations"""
        
        # Water level changes slowly, affected by flow rate
        level_change = (self.flow_rate - 25) * 0.1 + random.uniform(-2, 2)
        self.water_level += level_change
        self.water_level = max(0, min(100, self.water_level))
        
        # Flow rate has some variation
        self.flow_rate += random.uniform(-3, 3)
        self.flow_rate = max(0, min(50, self.flow_rate))
        
        # Soil moisture decreases over time, increases with irrigation
        moisture_change = -0.5 + (self.flow_rate > 30) * 2 + random.uniform(-2, 2)
        self.soil_moisture += moisture_change
        self.soil_moisture = max(0, min(100, self.soil_moisture))
        
        # Water temperature varies with time of day and flow
        hour = datetime.now().hour
        base_temp = 20 + 5 * abs(12 - hour) / 12  # Varies with time of day
        temp_change = (base_temp - self.water_temperature) * 0.1 + random.uniform(-1, 1)
        self.water_temperature += temp_change
        self.water_temperature = max(5, min(35, self.water_temperature))
        
        return {
            'water_level': round(self.water_level, 1),
            'flow_rate': round(self.flow_rate, 1),
            'soil_moisture': round(self.soil_moisture, 1),
            'water_temperature': round(self.water_temperature, 1)
        }
    
    def send_sensor_data(self, data):
        """Send sensor data to the Flask API"""
        try:
            response = requests.post(f"{self.api_url}/sensors", json=data, timeout=5)
            if response.status_code == 201:
                print(f"✓ Data sent: Level={data['water_level']}%, Flow={data['flow_rate']}L/min, "
                      f"Moisture={data['soil_moisture']}%, Temp={data['water_temperature']}°C")
                return True
            else:
                print(f"✗ Failed to send data: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection error: {e}")
            return False
    
    def run_simulation(self):
        """Main simulation loop"""
        print("Starting Water Management System Data Simulator")
        print(f"Sending data to: {self.api_url}")
        print(f"Update interval: {self.update_interval} seconds")
        print("Press Ctrl+C to stop the simulator")
        
        self.running = True
        
        try:
            while self.running:
                # Generate new sensor data
                sensor_data = self.generate_realistic_data()
                
                # Send to API
                success = self.send_sensor_data(sensor_data)
                
                if not success:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
                    continue
                
                # Wait for next update
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print("Simulator stopped.")
            self.running = False
        except Exception as e:
            print(f"Simulation error: {e}")
            self.running = False
    
    def stop(self):
        """Stop the simulation"""
        self.running = False

def main():
    simulator = WaterSensorSimulator()
    
    # Run simulation in a separate thread so we can handle interrupts
    sim_thread = threading.Thread(target=simulator.run_simulation)
    sim_thread.daemon = True
    sim_thread.start()
    
    try:
        sim_thread.join()
    except KeyboardInterrupt:
        simulator.stop()
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()