from datetime import datetime
from core_app import db

class SensorReading(db.Model):
    __tablename__ = 'sensor_readings'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    water_level = db.Column(db.Float, nullable=False)
    flow_rate = db.Column(db.Float, nullable=False)
    soil_moisture = db.Column(db.Float, nullable=False)
    water_temperature = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'water_level': self.water_level,
            'flow_rate': self.flow_rate,
            'soil_moisture': self.soil_moisture,
            'water_temperature': self.water_temperature
        }

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    alert_type = db.Column(db.String(20), nullable=False)  # warning, danger, success
    icon = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'type': self.alert_type,
            'icon': self.icon,
            'title': self.title,
            'message': self.message
        }

class SystemMetrics(db.Model):
    __tablename__ = 'system_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    cpu_utilization = db.Column(db.Float, nullable=False)
    response_time = db.Column(db.Float, nullable=False)
    throughput = db.Column(db.Float, nullable=False)
    storage_util = db.Column(db.Float, nullable=False)
    energy_consumption = db.Column(db.Float, nullable=False)
    alert_accuracy = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'cpu_utilization': self.cpu_utilization,
            'response_time': self.response_time,
            'throughput': self.throughput,
            'storage_util': self.storage_util,
            'energy_consumption': self.energy_consumption,
            'alert_accuracy': self.alert_accuracy
        }


# ============================================================
# NOVEL PATENT-WORTHY MODELS
# ============================================================

class LeakEvent(db.Model):
    """Patent Claim 1: Multi-Sensor Fusion Leak Detection records"""
    __tablename__ = 'leak_events'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    leak_type = db.Column(db.String(50), nullable=False)        # pipe_leak, sensor_phantom, overflow
    confidence = db.Column(db.Float, nullable=False)             # 0.0 - 1.0
    severity = db.Column(db.String(20), nullable=False)          # low, medium, high, critical
    flow_rate_at_detection = db.Column(db.Float, nullable=False)
    water_level_at_detection = db.Column(db.Float, nullable=False)
    soil_moisture_at_detection = db.Column(db.Float, nullable=False)
    level_drop_rate = db.Column(db.Float, nullable=False)        # % per minute
    expected_drop_rate = db.Column(db.Float, nullable=False)     # based on flow
    moisture_anomaly_score = db.Column(db.Float, nullable=False) # deviation from baseline
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'leak_type': self.leak_type,
            'confidence': round(self.confidence, 3),
            'severity': self.severity,
            'flow_rate': self.flow_rate_at_detection,
            'water_level': self.water_level_at_detection,
            'soil_moisture': self.soil_moisture_at_detection,
            'level_drop_rate': round(self.level_drop_rate, 4),
            'expected_drop_rate': round(self.expected_drop_rate, 4),
            'moisture_anomaly_score': round(self.moisture_anomaly_score, 3),
            'is_resolved': self.is_resolved,
            'resolved_at': self.resolved_at.isoformat() + 'Z' if self.resolved_at else None
        }


class WeatherData(db.Model):
    """Patent Claim 2: Weather-Adaptive Irrigation Scheduling data"""
    __tablename__ = 'weather_data'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temperature = db.Column(db.Float, nullable=False)            # °C
    humidity = db.Column(db.Float, nullable=False)                # %
    rain_probability = db.Column(db.Float, nullable=False)       # 0.0 - 1.0
    rain_volume_mm = db.Column(db.Float, default=0.0)            # mm expected
    wind_speed = db.Column(db.Float, default=0.0)                # m/s
    description = db.Column(db.String(100), nullable=False)
    evapotranspiration = db.Column(db.Float, default=0.0)        # mm/day (computed)
    irrigation_recommendation = db.Column(db.Float, default=100) # % of normal (0=skip, 100=full)
    water_saved_liters = db.Column(db.Float, default=0.0)        # liters saved by adapting

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'temperature': self.temperature,
            'humidity': self.humidity,
            'rain_probability': round(self.rain_probability, 2),
            'rain_volume_mm': self.rain_volume_mm,
            'wind_speed': self.wind_speed,
            'description': self.description,
            'evapotranspiration': round(self.evapotranspiration, 2),
            'irrigation_recommendation': round(self.irrigation_recommendation, 1),
            'water_saved_liters': round(self.water_saved_liters, 1)
        }


class SensorHealthLog(db.Model):
    """Patent Claim 3: Self-Diagnosing Sensor Cross-Validation records"""
    __tablename__ = 'sensor_health_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sensor_name = db.Column(db.String(50), nullable=False)       # water_level, flow_rate, etc.
    health_status = db.Column(db.String(20), nullable=False)     # healthy, degraded, faulty
    confidence = db.Column(db.Float, nullable=False)             # 0.0 - 1.0
    issue_type = db.Column(db.String(50), nullable=True)         # stuck, drift, spike, phantom
    raw_value = db.Column(db.Float, nullable=False)
    expected_range_min = db.Column(db.Float, nullable=False)
    expected_range_max = db.Column(db.Float, nullable=False)
    cross_validation_details = db.Column(db.Text, nullable=True) # JSON string of reasoning

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'sensor_name': self.sensor_name,
            'health_status': self.health_status,
            'confidence': round(self.confidence, 3),
            'issue_type': self.issue_type,
            'raw_value': self.raw_value,
            'expected_range_min': self.expected_range_min,
            'expected_range_max': self.expected_range_max,
            'cross_validation_details': self.cross_validation_details
        }


class AnomalyLog(db.Model):
    """ML-based anomaly detection results"""
    __tablename__ = 'anomaly_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    anomaly_score = db.Column(db.Float, nullable=False)          # -1 (anomaly) to 1 (normal)
    is_anomaly = db.Column(db.Boolean, nullable=False)
    water_level = db.Column(db.Float, nullable=False)
    flow_rate = db.Column(db.Float, nullable=False)
    soil_moisture = db.Column(db.Float, nullable=False)
    water_temperature = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'anomaly_score': round(self.anomaly_score, 3),
            'is_anomaly': self.is_anomaly,
            'water_level': self.water_level,
            'flow_rate': self.flow_rate,
            'soil_moisture': self.soil_moisture,
            'water_temperature': self.water_temperature,
            'description': self.description
        }


# ============================================================
# ENHANCEMENT PATENT MODELS (Features 1-6)
# ============================================================

class ValveAction(db.Model):
    """Feature 1: Automatic Leak Response — valve actuation records"""
    __tablename__ = 'valve_actions'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    zone_id = db.Column(db.String(50), nullable=False)           # e.g. "zone_A", "main_supply"
    action = db.Column(db.String(20), nullable=False)            # close, open, throttle
    trigger_type = db.Column(db.String(50), nullable=False)      # leak_response, manual, scheduled
    leak_event_id = db.Column(db.Integer, db.ForeignKey('leak_events.id'), nullable=True)
    leak_confidence = db.Column(db.Float, default=0.0)
    flow_before = db.Column(db.Float, default=0.0)               # L/min before valve action
    flow_after = db.Column(db.Float, nullable=True)               # L/min after valve action
    water_saved_liters = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    released_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'zone_id': self.zone_id,
            'action': self.action,
            'trigger_type': self.trigger_type,
            'leak_event_id': self.leak_event_id,
            'leak_confidence': round(self.leak_confidence, 3),
            'flow_before': self.flow_before,
            'flow_after': self.flow_after,
            'water_saved_liters': round(self.water_saved_liters, 1),
            'is_active': self.is_active,
            'released_at': self.released_at.isoformat() + 'Z' if self.released_at else None
        }


class LeakLocalization(db.Model):
    """Feature 2: Leak Localization — moisture gradient triangulation"""
    __tablename__ = 'leak_localizations'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    leak_event_id = db.Column(db.Integer, db.ForeignKey('leak_events.id'), nullable=True)
    estimated_zone = db.Column(db.String(50), nullable=False)     # zone closest to leak
    gradient_vector = db.Column(db.Text, nullable=True)           # JSON: direction of moisture increase
    confidence = db.Column(db.Float, nullable=False)
    pressure_differential = db.Column(db.Float, default=0.0)     # kPa between zones
    moisture_readings = db.Column(db.Text, nullable=True)         # JSON: per-zone moisture snapshot
    estimated_distance_m = db.Column(db.Float, nullable=True)     # meters from nearest sensor

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'leak_event_id': self.leak_event_id,
            'estimated_zone': self.estimated_zone,
            'gradient_vector': self.gradient_vector,
            'confidence': round(self.confidence, 3),
            'pressure_differential': self.pressure_differential,
            'moisture_readings': self.moisture_readings,
            'estimated_distance_m': self.estimated_distance_m
        }


class CalibrationRecord(db.Model):
    """Feature 3: Sensor Calibration / Drift Compensation records"""
    __tablename__ = 'calibration_records'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sensor_name = db.Column(db.String(50), nullable=False)
    drift_detected = db.Column(db.Float, nullable=False)         # magnitude of drift
    drift_direction = db.Column(db.String(10), nullable=False)   # positive, negative
    correction_factor = db.Column(db.Float, nullable=False)      # multiplier applied
    offset_applied = db.Column(db.Float, nullable=False)         # additive correction
    raw_value = db.Column(db.Float, nullable=False)
    corrected_value = db.Column(db.Float, nullable=False)
    reference_sensor = db.Column(db.String(50), nullable=True)   # which sensor provided reference
    method = db.Column(db.String(50), nullable=False)            # cross_sensor, historical, physical_model

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'sensor_name': self.sensor_name,
            'drift_detected': round(self.drift_detected, 4),
            'drift_direction': self.drift_direction,
            'correction_factor': round(self.correction_factor, 6),
            'offset_applied': round(self.offset_applied, 4),
            'raw_value': self.raw_value,
            'corrected_value': round(self.corrected_value, 2),
            'reference_sensor': self.reference_sensor,
            'method': self.method
        }


class EnergyProfile(db.Model):
    """Feature 5: Energy Optimization — adaptive sampling records"""
    __tablename__ = 'energy_profiles'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sampling_interval_s = db.Column(db.Float, nullable=False)    # current sampling interval in seconds
    environmental_stability = db.Column(db.Float, nullable=False)  # 0.0 (volatile) - 1.0 (stable)
    power_mode = db.Column(db.String(20), nullable=False)        # high_freq, normal, low_power, deep_sleep
    estimated_battery_hours = db.Column(db.Float, nullable=True)
    energy_saved_pct = db.Column(db.Float, default=0.0)          # % energy saved vs constant sampling
    active_sensors = db.Column(db.Text, nullable=True)           # JSON: which sensors are active

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'sampling_interval_s': self.sampling_interval_s,
            'environmental_stability': round(self.environmental_stability, 3),
            'power_mode': self.power_mode,
            'estimated_battery_hours': self.estimated_battery_hours,
            'energy_saved_pct': round(self.energy_saved_pct, 1),
            'active_sensors': self.active_sensors
        }


class BaselineModel(db.Model):
    """Feature 6: Learning-Based Baseline Modeling records"""
    __tablename__ = 'baseline_models'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    model_version = db.Column(db.Integer, nullable=False)
    learning_phase = db.Column(db.String(20), nullable=False)    # initial, adapting, mature
    total_samples_learned = db.Column(db.Integer, nullable=False)
    seasonal_profiles = db.Column(db.Text, nullable=True)        # JSON: hour-of-day baselines
    multivariate_weights = db.Column(db.Text, nullable=True)     # JSON: inter-sensor relationship weights
    baseline_means = db.Column(db.Text, nullable=True)           # JSON: per-sensor mean baselines
    baseline_stds = db.Column(db.Text, nullable=True)            # JSON: per-sensor std baselines
    prediction_accuracy = db.Column(db.Float, default=0.0)       # % accuracy of baseline predictions
    last_retrain = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'model_version': self.model_version,
            'learning_phase': self.learning_phase,
            'total_samples_learned': self.total_samples_learned,
            'seasonal_profiles': self.seasonal_profiles,
            'multivariate_weights': self.multivariate_weights,
            'prediction_accuracy': round(self.prediction_accuracy, 2),
            'last_retrain': self.last_retrain.isoformat() + 'Z' if self.last_retrain else None
        }
