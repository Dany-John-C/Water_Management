from flask import Blueprint, jsonify, request
from core_app.models.models import SensorReading
from core_app.services.alert_engine import check_and_create_alerts
from core_app.services.leak_detector import leak_detector
from core_app.services.sensor_health import sensor_health_monitor
from core_app.services.ml_anomaly import anomaly_detector
from core_app.services.valve_controller import valve_controller
from core_app.services.leak_localizer import leak_localizer
from core_app.services.calibration_engine import calibration_engine
from core_app.services.energy_optimizer import energy_optimizer
from core_app.services.baseline_learner import baseline_learner
from core_app.services.edge_cloud import edge_cloud_manager
from core_app import db
from datetime import datetime, timedelta
import math

sensors_bp = Blueprint('sensors', __name__)

@sensors_bp.route('/current', methods=['GET'])
def get_current_sensors():
    """Get the latest sensor readings"""
    latest = SensorReading.query.order_by(SensorReading.timestamp.desc()).first()
    if not latest:
        return jsonify({'error': 'No sensor data available'}), 404
    
    return jsonify(latest.to_dict())

@sensors_bp.route('/history', methods=['GET'])
def get_sensor_history():
    """Get sensor readings for the last 24 hours"""
    since = datetime.utcnow() - timedelta(hours=24)
    readings = SensorReading.query.filter(
        SensorReading.timestamp >= since
    ).order_by(SensorReading.timestamp.desc()).limit(50).all()
    
    return jsonify([reading.to_dict() for reading in reversed(readings)])

@sensors_bp.route('', methods=['POST'])
def add_sensor_reading():
    """Add a new sensor reading"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        reading = SensorReading(
            water_level=data['water_level'],
            flow_rate=data['flow_rate'],
            soil_moisture=data['soil_moisture'],
            water_temperature=data['water_temperature']
        )
        
        db.session.add(reading)
        db.session.commit()
        
        # Check for alerts using the centralized engine
        check_and_create_alerts(reading)
        
        # --- Novel Intelligence Engines ---
        # Patent Claim 1: Multi-sensor fusion leak detection
        leak_detections = []
        try:
            leak_detections = leak_detector.analyze(reading)
        except Exception as e:
            print(f"Leak detector error: {e}")

        # Feature 1: Automatic leak response (valve actuation)
        try:
            valve_controller.evaluate_and_respond(leak_detections)
        except Exception as e:
            print(f"Valve controller error: {e}")

        # Feature 2: Leak localization (moisture gradient)
        try:
            leak_localizer.localize(reading, leak_detections)
        except Exception as e:
            print(f"Leak localizer error: {e}")

        # Patent Claim 3: Self-diagnosing sensor health
        try:
            sensor_health_monitor.diagnose(reading)
        except Exception as e:
            print(f"Sensor health error: {e}")

        # Feature 3: Adaptive sensor calibration
        try:
            calibration_engine.check_and_calibrate(reading)
        except Exception as e:
            print(f"Calibration engine error: {e}")

        # ML Anomaly Detection
        has_anomaly = False
        try:
            anomaly_result = anomaly_detector.detect(reading)
            has_anomaly = anomaly_result.get('is_anomaly', False) if anomaly_result else False
        except Exception as e:
            print(f"Anomaly detector error: {e}")

        # Feature 5: Energy optimization (adaptive sampling)
        try:
            energy_optimizer.optimize(
                reading,
                has_anomaly=has_anomaly,
                has_leak=len(leak_detections) > 0
            )
        except Exception as e:
            print(f"Energy optimizer error: {e}")

        # Feature 6: Learning-based baseline modeling
        try:
            baseline_learner.learn(reading)
        except Exception as e:
            print(f"Baseline learner error: {e}")

        # Feature 4: Edge-cloud processing
        try:
            edge_cloud_manager.process_at_edge(reading)
        except Exception as e:
            print(f"Edge-cloud manager error: {e}")
        
        return jsonify({'message': 'Sensor reading added successfully', 'data': reading.to_dict()}), 201
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@sensors_bp.route('/predict', methods=['GET'])
def get_predictions():
    """Get predicted sensor readings based on recent history"""
    readings = SensorReading.query.order_by(SensorReading.timestamp.desc()).limit(24).all()
    if not readings:
        return jsonify({'error': 'Not enough data for predictions'}), 400
    
    data = list(reversed(readings))
    
    def predict_next_values(values, num_points=24):
        preds = []
        if not values:
            return preds
        window = min(5, len(values))
        for i in range(num_points):
            ma = sum(values[-window:]) / window
            trend = (values[-1] - values[-2]) if len(values) >= 2 else 0
            damped_trend = trend * (0.8 ** i)
            seasonal = 1 + math.sin(i * 0.5) * 0.05
            next_val = max(0, (ma + damped_trend) * seasonal)
            preds.append(round(next_val, 2))
            values.append(next_val)
        return preds

    predictions = {
        'flow_rate': predict_next_values([r.flow_rate for r in data]),
        'water_level': predict_next_values([r.water_level for r in data]),
        'water_temperature': predict_next_values([r.water_temperature for r in data]),
        'soil_moisture': predict_next_values([r.soil_moisture for r in data])
    }
    
    return jsonify(predictions)
