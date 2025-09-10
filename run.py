#!/usr/bin/env python3
"""
Smart Water Management System - Main Runner
"""

import subprocess
import sys
import time
import threading
from app import app, db, generate_sample_data, SensorReading

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import flask
        import flask_sqlalchemy
        import flask_cors
        import requests
        print("✓ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def setup_database():
    """Initialize database and sample data"""
    print("🗄️  Setting up database...")
    
    with app.app_context():
        db.create_all()
        
        # Check if we need sample data
        if SensorReading.query.count() == 0:
            print("📊 Generating sample data...")
            generate_sample_data()
            print("✓ Sample data created")
        else:
            print("✓ Database already contains data")

def run_flask_app():
    """Run the Flask application"""
    print("🚀 Starting Flask server...")
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)

def run_data_simulator():
    """Run the data simulator in a separate process"""
    time.sleep(3)  # Wait for Flask to start
    print("🤖 Starting data simulator...")
    try:
        subprocess.run([sys.executable, "data_simulator.py"])
    except KeyboardInterrupt:
        print("🛑 Data simulator stopped")

def main():
    print("🌊 Smart Water Management System")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Setup database
    setup_database()
    
    print("\n🎯 Starting system components...")
    print("📱 Web interface will be available at: http://localhost:5000")
    print("🔄 Press Ctrl+C to stop all services\n")
    
    try:
        # Start Flask app in a separate thread
        flask_thread = threading.Thread(target=run_flask_app)
        flask_thread.daemon = True
        flask_thread.start()
        
        # Start data simulator
        run_data_simulator()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down system...")
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()