from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///water_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

db = SQLAlchemy(app)

# Database Models
class SensorReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    water_level = db.Column(db.Float, nullable=False)
    flow_rate = db.Column(db.Float, nullable=False)
    soil_moisture = db.Column(db.Float, nullable=False)
    water_temperature = db.Column(db.Float, nullable=False)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    alert_type = db.Column(db.String(20), nullable=False)  # warning, danger, success
    icon = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class SystemMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    cpu_utilization = db.Column(db.Float, nullable=False)
    response_time = db.Column(db.Float, nullable=False)
    throughput = db.Column(db.Float, nullable=False)
    storage_util = db.Column(db.Float, nullable=False)
    energy_consumption = db.Column(db.Float, nullable=False)
    alert_accuracy = db.Column(db.Float, nullable=False)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sensors/current')
def get_current_sensors():
    """Get the latest sensor readings"""
    latest = SensorReading.query.order_by(SensorReading.timestamp.desc()).first()
    if not latest:
        return jsonify({'error': 'No sensor data available'}), 404
    
    return jsonify({
        'timestamp': latest.timestamp.isoformat(),
        'water_level': latest.water_level,
        'flow_rate': latest.flow_rate,
        'soil_moisture': latest.soil_moisture,
        'water_temperature': latest.water_temperature
    })

@app.route('/api/sensors/history')
def get_sensor_history():
    """Get sensor readings for the last 24 hours"""
    since = datetime.utcnow() - timedelta(hours=24)
    readings = SensorReading.query.filter(
        SensorReading.timestamp >= since
    ).order_by(SensorReading.timestamp.desc()).limit(50).all()
    
    data = []
    for reading in reversed(readings):
        data.append({
            'timestamp': reading.timestamp.isoformat(),
            'water_level': reading.water_level,
            'flow_rate': reading.flow_rate,
            'soil_moisture': reading.soil_moisture,
            'water_temperature': reading.water_temperature
        })
    
    return jsonify(data)

@app.route('/api/alerts')
def get_alerts():
    """Get recent alerts"""
    alerts = Alert.query.filter_by(is_active=True).order_by(
        Alert.timestamp.desc()
    ).limit(10).all()
    
    data = []
    for alert in alerts:
        data.append({
            'id': alert.id,
            'timestamp': alert.timestamp.isoformat(),
            'type': alert.alert_type,
            'icon': alert.icon,
            'title': alert.title,
            'message': alert.message
        })
    
    return jsonify(data)

@app.route('/api/metrics/current')
def get_current_metrics():
    """Get the latest system metrics"""
    latest = SystemMetrics.query.order_by(SystemMetrics.timestamp.desc()).first()
    if not latest:
        return jsonify({'error': 'No metrics data available'}), 404
    
    return jsonify({
        'timestamp': latest.timestamp.isoformat(),
        'cpu_utilization': latest.cpu_utilization,
        'response_time': latest.response_time,
        'throughput': latest.throughput,
        'storage_util': latest.storage_util,
        'energy_consumption': latest.energy_consumption,
        'alert_accuracy': latest.alert_accuracy
    })

@app.route('/api/sensors', methods=['POST'])
def add_sensor_reading():
    """Add a new sensor reading"""
    data = request.get_json()
    
    reading = SensorReading(
        water_level=data['water_level'],
        flow_rate=data['flow_rate'],
        soil_moisture=data['soil_moisture'],
        water_temperature=data['water_temperature']
    )
    
    db.session.add(reading)
    db.session.commit()
    
    # Check for alerts
    check_and_create_alerts(reading)
    
    return jsonify({'message': 'Sensor reading added successfully'}), 201

@app.route('/api/export')
def export_data():
    """Export all data as JSON"""
    # Get recent sensor data
    sensors = SensorReading.query.order_by(SensorReading.timestamp.desc()).limit(100).all()
    alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(50).all()
    metrics = SystemMetrics.query.order_by(SystemMetrics.timestamp.desc()).limit(50).all()
    
    export_data = {
        'export_timestamp': datetime.utcnow().isoformat(),
        'sensors': [{
            'timestamp': s.timestamp.isoformat(),
            'water_level': s.water_level,
            'flow_rate': s.flow_rate,
            'soil_moisture': s.soil_moisture,
            'water_temperature': s.water_temperature
        } for s in sensors],
        'alerts': [{
            'timestamp': a.timestamp.isoformat(),
            'type': a.alert_type,
            'title': a.title,
            'message': a.message
        } for a in alerts],
        'metrics': [{
            'timestamp': m.timestamp.isoformat(),
            'cpu_utilization': m.cpu_utilization,
            'response_time': m.response_time,
            'throughput': m.throughput,
            'storage_util': m.storage_util,
            'energy_consumption': m.energy_consumption,
            'alert_accuracy': m.alert_accuracy
        } for m in metrics]
    }
    
    return jsonify(export_data)

def check_and_create_alerts(reading):
    """Check sensor readings and create alerts if needed"""
    alerts_to_create = []
    
    if reading.water_level > 95:
        alerts_to_create.append({
            'type': 'danger',
            'icon': '🚨',
            'title': 'Tank Overflow Warning',
            'message': 'Water level critically high'
        })
    
    if reading.flow_rate > 40:
        alerts_to_create.append({
            'type': 'warning',
            'icon': '⚠️',
            'title': 'High Flow Rate Detected',
            'message': 'Possible leak detected'
        })
    
    if reading.soil_moisture < 20:
        alerts_to_create.append({
            'type': 'warning',
            'icon': '🌱',
            'title': 'Low Soil Moisture',
            'message': 'Irrigation may be needed'
        })
    
    if reading.water_temperature > 30:
        alerts_to_create.append({
            'type': 'warning',
            'icon': '🌡️',
            'title': 'High Water Temperature',
            'message': 'Temperature exceeds optimal range'
        })
    
    if reading.water_temperature < 10:
        alerts_to_create.append({
            'type': 'warning',
            'icon': '❄️',
            'title': 'Low Water Temperature',
            'message': 'Risk of freezing detected'
        })
    
    for alert_data in alerts_to_create:
        alert = Alert(
            alert_type=alert_data['type'],
            icon=alert_data['icon'],
            title=alert_data['title'],
            message=alert_data['message']
        )
        db.session.add(alert)
    
    db.session.commit()

def generate_sample_data():
    """Generate sample data for testing"""
    print("Generating sample data...")
    
    # Clear existing data
    db.session.query(SensorReading).delete()
    db.session.query(Alert).delete()
    db.session.query(SystemMetrics).delete()
    
    # Generate sensor readings for the last 24 hours
    base_time = datetime.utcnow() - timedelta(hours=24)
    
    for i in range(288):  # Every 5 minutes for 24 hours
        timestamp = base_time + timedelta(minutes=i * 5)
        
        # Generate realistic sensor data with some variation
        water_level = 85 + random.uniform(-15, 10)
        flow_rate = 24.5 + random.uniform(-10, 15)
        soil_moisture = 67 + random.uniform(-20, 25)
        water_temperature = 22.5 + random.uniform(-5, 8)
        
        # Keep values in realistic ranges
        water_level = max(0, min(100, water_level))
        flow_rate = max(0, min(50, flow_rate))
        soil_moisture = max(0, min(100, soil_moisture))
        water_temperature = max(5, min(35, water_temperature))
        
        reading = SensorReading(
            timestamp=timestamp,
            water_level=water_level,
            flow_rate=flow_rate,
            soil_moisture=soil_moisture,
            water_temperature=water_temperature
        )
        db.session.add(reading)
    
    # Generate some sample alerts
    sample_alerts = [
        {'type': 'success', 'icon': '✅', 'title': 'System Online', 'message': 'All systems operational'},
        {'type': 'warning', 'icon': '⚠️', 'title': 'High Water Usage', 'message': 'Usage above normal levels'},
        {'type': 'success', 'icon': '💧', 'title': 'Tank Refilled', 'message': 'Water tank successfully refilled'},
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
    
    # Generate system metrics for the last 24 hours
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
    print("Sample data generated successfully!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Check if we need to generate sample data
        if SensorReading.query.count() == 0:
            generate_sample_data()
    
    app.run(debug=True, host='0.0.0.0', port=5000)