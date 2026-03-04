"""
API Routes for Novel Intelligence Features.

Exposes ALL patent-worthy engines via REST endpoints:

Original Patent Claims:
- /api/intelligence/leak           → Leak detection status
- /api/intelligence/weather        → Weather-adaptive irrigation
- /api/intelligence/health         → Sensor health diagnostics
- /api/intelligence/anomaly        → ML anomaly detection

Enhancement Features:
- /api/intelligence/valve          → Automatic valve response (Feature 1)
- /api/intelligence/localization   → Leak localization (Feature 2)
- /api/intelligence/calibration    → Sensor calibration (Feature 3)
- /api/intelligence/architecture   → Edge-cloud architecture (Feature 4)
- /api/intelligence/energy         → Energy optimization (Feature 5)
- /api/intelligence/baseline       → Baseline modeling (Feature 6)

Combined:
- /api/intelligence/dashboard      → Full intelligence dashboard
"""

from flask import Blueprint, jsonify, request
from core_app.services.leak_detector import leak_detector
from core_app.services.weather_engine import weather_engine
from core_app.services.sensor_health import sensor_health_monitor
from core_app.services.ml_anomaly import anomaly_detector
from core_app.services.valve_controller import valve_controller
from core_app.services.leak_localizer import leak_localizer
from core_app.services.calibration_engine import calibration_engine
from core_app.services.edge_cloud import edge_cloud_manager
from core_app.services.energy_optimizer import energy_optimizer
from core_app.services.baseline_learner import baseline_learner

intelligence_bp = Blueprint('intelligence', __name__)


# ============================================================
# LEAK DETECTION (Patent Claim 1)
# ============================================================

@intelligence_bp.route('/leak', methods=['GET'])
def get_leak_status():
    """Get current leak detection status and history."""
    status = leak_detector.get_status()
    return jsonify(status)


# ============================================================
# WEATHER-ADAPTIVE IRRIGATION (Patent Claim 2)
# ============================================================

@intelligence_bp.route('/weather', methods=['GET'])
def get_weather_recommendation():
    """Fetch weather and compute irrigation recommendation."""
    result = weather_engine.update_and_recommend()
    return jsonify(result)


@intelligence_bp.route('/weather/savings', methods=['GET'])
def get_water_savings():
    """Get cumulative water savings from adaptive scheduling."""
    savings = weather_engine.get_savings_summary()
    return jsonify(savings)


# ============================================================
# SENSOR HEALTH (Patent Claim 3)
# ============================================================

@intelligence_bp.route('/health', methods=['GET'])
def get_sensor_health():
    """Get sensor health diagnostics."""
    health = sensor_health_monitor.get_health_summary()
    return jsonify(health)


# ============================================================
# ML ANOMALY DETECTION
# ============================================================

@intelligence_bp.route('/anomaly', methods=['GET'])
def get_anomaly_history():
    """Get ML anomaly detection history."""
    history = anomaly_detector.get_anomaly_history()
    return jsonify(history)


# ============================================================
# FEATURE 1: AUTOMATIC VALVE RESPONSE
# ============================================================

@intelligence_bp.route('/valve', methods=['GET'])
def get_valve_status():
    """Get valve controller status and history."""
    status = valve_controller.get_status()
    return jsonify(status)


@intelligence_bp.route('/valve/override', methods=['POST'])
def valve_manual_override():
    """Manual valve control. Body: {"zone_id": "zone_A", "action": "close"}"""
    data = request.get_json()
    if not data or 'zone_id' not in data or 'action' not in data:
        return jsonify({'error': 'Missing zone_id or action'}), 400
    result = valve_controller.manual_override(data['zone_id'], data['action'])
    return jsonify(result)


@intelligence_bp.route('/valve/verify/<zone_id>', methods=['GET'])
def verify_valve_closure(zone_id):
    """Verify if closing a valve stopped the leak."""
    result = valve_controller.verify_post_closure(zone_id)
    return jsonify(result)


# ============================================================
# FEATURE 2: LEAK LOCALIZATION
# ============================================================

@intelligence_bp.route('/localization', methods=['GET'])
def get_leak_localization():
    """Get leak localization history with zone mapping."""
    history = leak_localizer.get_localization_history()
    return jsonify(history)


# ============================================================
# FEATURE 3: SENSOR CALIBRATION
# ============================================================

@intelligence_bp.route('/calibration', methods=['GET'])
def get_calibration_status():
    """Get sensor calibration status and history."""
    status = calibration_engine.get_calibration_status()
    return jsonify(status)


# ============================================================
# FEATURE 4: EDGE-CLOUD ARCHITECTURE
# ============================================================

@intelligence_bp.route('/architecture', methods=['GET'])
def get_architecture_status():
    """Get edge-cloud architecture status."""
    status = edge_cloud_manager.get_architecture_status()
    return jsonify(status)


@intelligence_bp.route('/architecture/simulate-outage', methods=['POST'])
def simulate_outage():
    """Simulate network outage for testing. Body: {"offline": true}"""
    data = request.get_json() or {}
    result = edge_cloud_manager.simulate_network_outage(data.get('offline', True))
    return jsonify(result)


# ============================================================
# FEATURE 5: ENERGY OPTIMIZATION
# ============================================================

@intelligence_bp.route('/energy', methods=['GET'])
def get_energy_status():
    """Get energy optimization status and sampling profile."""
    summary = energy_optimizer.get_energy_summary()
    return jsonify(summary)


# ============================================================
# FEATURE 6: BASELINE MODELING
# ============================================================

@intelligence_bp.route('/baseline', methods=['GET'])
def get_baseline_status():
    """Get learning-based baseline model status."""
    status = baseline_learner.get_baseline_status()
    return jsonify(status)


# ============================================================
# COMBINED INTELLIGENCE DASHBOARD
# ============================================================

@intelligence_bp.route('/dashboard', methods=['GET'])
def get_intelligence_dashboard():
    """
    Combined intelligence view — ALL novel features in one endpoint.
    This is the main data source for the Intelligence Dashboard UI.
    """
    leak_status = leak_detector.get_status()
    
    try:
        weather_result = weather_engine.update_and_recommend()
    except Exception as e:
        weather_result = {'error': str(e)}
    
    health = sensor_health_monitor.get_health_summary()
    anomaly_history = anomaly_detector.get_anomaly_history(hours=6)
    savings = weather_engine.get_savings_summary()

    # Enhancement features
    valve_status = valve_controller.get_status()
    localization = leak_localizer.get_localization_history(hours=6)
    calibration = calibration_engine.get_calibration_status()
    architecture = edge_cloud_manager.get_architecture_status()
    energy = energy_optimizer.get_energy_summary()
    baseline = baseline_learner.get_baseline_status()

    return jsonify({
        'leak_detection': {
            'status': leak_status['system_status'],
            'active_leaks': leak_status['total_active'],
            'leaks': leak_status['active_leaks']
        },
        'weather_irrigation': {
            'recommendation': weather_result.get('recommendation', {}),
            'weather': weather_result.get('weather', {}),
            'savings': savings
        },
        'sensor_health': health,
        'anomaly_detection': {
            'anomaly_rate': anomaly_history['anomaly_rate'],
            'total_analyzed': anomaly_history['total_readings_analyzed'],
            'anomalies_found': anomaly_history['anomalies_detected'],
            'recent': anomaly_history['recent_anomalies'][:5]
        },
        'valve_control': {
            'valve_states': valve_status['valve_states'],
            'active_closures': len(valve_status['active_closures']),
            'water_saved_by_valves': valve_status['total_water_saved_liters'],
            'auto_response': valve_status['auto_response_enabled']
        },
        'leak_localization': {
            'total_localizations': localization['total'],
            'zones': localization['zones'],
            'recent': localization['localizations'][:3]
        },
        'sensor_calibration': {
            'total_calibrations': calibration['total_calibrations'],
            'auto_enabled': calibration['auto_calibration_enabled'],
            'sensors': {
                name: {
                    'scale': info['current_scale_factor'],
                    'offset': info['current_offset'],
                    'calibrations_24h': info['calibrations_24h']
                }
                for name, info in calibration['sensors'].items()
            }
        },
        'edge_cloud': {
            'data_reduction_pct': architecture['data_efficiency']['data_reduction_pct'],
            'cloud_status': architecture['cloud_status'],
            'readings_processed': architecture['data_efficiency']['total_received'],
            'buffer_pending': architecture['architecture']['tier_3_cloud']['buffer_pending']
        },
        'energy_optimization': {
            'current_mode': energy['current']['current_mode'],
            'sampling_interval_s': energy['current']['sampling_interval_s'],
            'energy_saved_pct': energy['current']['energy_saved_pct'],
            'battery_hours': energy['current']['estimated_battery_hours'],
            'stability': energy['current']['environmental_stability']
        },
        'baseline_model': {
            'learning_phase': baseline['learning_phase'],
            'model_version': baseline['model_version'],
            'samples_learned': baseline['total_samples_learned'],
            'prediction_accuracy': baseline['prediction_accuracy'],
            'phase_progress': baseline['phase_progress']
        }
    })
