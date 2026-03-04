#!/usr/bin/env python3
import subprocess
import sys
import time
import threading

def check_dependencies():
    try:
        import flask
        import flask_sqlalchemy
        import flask_cors
        import requests
        import dotenv
        return True
    except ImportError as e:
        print(f"Error Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def main():
    print("Smart Water Management System (Clean Architecture)")
    print("=" * 50)
    
    if not check_dependencies():
        return
        
    # Import app factory here to avoid early import circulars
    from core_app import create_app, db
    flask_app = create_app()

    def generate_sample_data():
        from core_app.models.models import SensorReading, Alert, SystemMetrics
        from datetime import datetime, timedelta
        import random
        
        print("Generating sample data...")
        # Clear existing data
        db.session.query(SensorReading).delete()
        db.session.query(Alert).delete()
        db.session.query(SystemMetrics).delete()
        
        # Generate sensor readings for the last 24 hours
        base_time = datetime.utcnow() - timedelta(hours=24)
        
        for i in range(288):  # Every 5 minutes for 24 hours
            timestamp = base_time + timedelta(minutes=i * 5)
            
            water_level = max(0, min(100, 85 + random.uniform(-15, 10)))
            flow_rate = max(0, min(50, 24.5 + random.uniform(-10, 15)))
            soil_moisture = max(0, min(100, 67 + random.uniform(-20, 25)))
            water_temperature = max(5, min(35, 22.5 + random.uniform(-5, 8)))
            
            reading = SensorReading(
                timestamp=timestamp,
                water_level=water_level,
                flow_rate=flow_rate,
                soil_moisture=soil_moisture,
                water_temperature=water_temperature
            )
            db.session.add(reading)
        
        sample_alerts = [
            {'type': 'success', 'icon': 'OK', 'title': 'System Online', 'message': 'All systems operational'},
            {'type': 'warning', 'icon': 'WARN', 'title': 'High Water Usage', 'message': 'Usage above normal levels'},
            {'type': 'success', 'icon': 'OK', 'title': 'Tank Refilled', 'message': 'Water tank successfully refilled'},
        ]
        
        for alert_data in sample_alerts:
            alert = Alert(
                timestamp=datetime.utcnow() - timedelta(minutes=random.randint(5, 120)),
                alert_type=alert_data['type'],
                icon=alert_data['icon'],
                title=alert_data['title'],
                message=alert_data['message']
            )
            db.session.add(alert)
        
        for i in range(48):  # Every 30 minutes for 24 hours
            timestamp = base_time + timedelta(minutes=i * 30)
            metrics = SystemMetrics(
                timestamp=timestamp,
                cpu_utilization=random.uniform(50, 90),
                response_time=random.uniform(150, 350),
                throughput=random.uniform(800, 1500),
                storage_util=random.uniform(30, 70),
                energy_consumption=random.uniform(120, 180),
                alert_accuracy=random.uniform(94, 99)
            )
            db.session.add(metrics)
        
        db.session.commit()
        print("Sample data created")

    def setup_database():
        print("Setting up database...")
        from core_app.models.models import SensorReading
        with flask_app.app_context():
            db.create_all()
            if SensorReading.query.count() == 0:
                generate_sample_data()
            else:
                print("Database already contains data")

    def run_flask_app():
        print("Starting modular Flask server...")
        flask_app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)

    def run_data_simulator():
        time.sleep(3) 
        print("Starting data simulator...")
        try:
            subprocess.run([sys.executable, "data_simulator.py"])
        except KeyboardInterrupt:
            print("Data simulator stopped")
            
    setup_database()
    
    print("\nStarting system components...")
    print("Web interface will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop all services\n")
    
    try:
        flask_thread = threading.Thread(target=run_flask_app)
        flask_thread.daemon = True
        flask_thread.start()
        
        run_data_simulator()
        
    except KeyboardInterrupt:
        print("\nShutting down system...")
        print("Goodbye!")

if __name__ == "__main__":
    main()