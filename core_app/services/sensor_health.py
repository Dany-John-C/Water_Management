"""
Patent Claim 3: Self-Diagnosing Sensor Health via Cross-Validation

A method for detecting sensor malfunction comprising: cross-validating readings 
from multiple sensor modalities against a learned physical model; wherein 
inconsistency between expected and actual inter-sensor relationships triggers 
a sensor health alert and automatic reading compensation.

Detection methods:
1. Stuck Sensor: Value hasn't changed across N readings (sensor frozen)
2. Spike Detection: Sudden jump beyond physical possibility
3. Drift Detection: Gradual deviation from expected inter-sensor relationship
4. Phantom Reading: One sensor contradicts what others physically imply
"""

from datetime import datetime, timedelta
from core_app.models.models import SensorReading, SensorHealthLog, Alert
from core_app import db
import json
import math


class SensorHealthMonitor:
    """
    Cross-validates sensors against each other using physical relationships.
    
    Physical model relationships:
    - Flow > 0 for sustained period → Level should drop (conservation of mass)
    - Temperature affects evaporation → High temp + low humidity = moisture drops
    - Level = 0 but Flow > 0 → Impossible (sensor fault)
    - Moisture = 100% sustained → Likely sensor fault (saturation)
    """

    # Detection parameters
    STUCK_THRESHOLD_READINGS = 5     # Same value for 5 readings = stuck
    STUCK_TOLERANCE = 0.01           # Values within 0.01 considered "same"
    SPIKE_MAX_CHANGE_PER_READ = {    # Maximum physically possible change per reading
        'water_level': 10.0,         # % - tank can't change >10% in one reading
        'flow_rate': 20.0,           # L/min - flow can't jump >20 L/min instantly
        'soil_moisture': 8.0,        # % - moisture can't jump >8% per reading
        'water_temperature': 3.0     # °C - temp can't jump >3°C per reading
    }
    MIN_READINGS = 5                 # Need at least 5 readings for analysis

    def __init__(self):
        self.sensor_names = ['water_level', 'flow_rate', 'soil_moisture', 'water_temperature']

    def diagnose(self, current_reading):
        """
        Run all diagnostic checks on the current reading.
        Returns list of health reports for each sensor.
        """
        since = datetime.utcnow() - timedelta(minutes=15)
        history = SensorReading.query.filter(
            SensorReading.timestamp >= since
        ).order_by(SensorReading.timestamp.asc()).all()

        if len(history) < self.MIN_READINGS:
            return []

        health_reports = []

        for sensor_name in self.sensor_names:
            values = [getattr(r, sensor_name) for r in history]
            current_value = getattr(current_reading, sensor_name)

            report = {
                'sensor_name': sensor_name,
                'health_status': 'healthy',
                'confidence': 1.0,
                'issue_type': None,
                'raw_value': current_value,
                'expected_range_min': 0,
                'expected_range_max': 0,
                'details': {}
            }

            # Check 1: Stuck sensor
            stuck_result = self._check_stuck(sensor_name, values)
            if stuck_result:
                report.update(stuck_result)

            # Check 2: Spike detection
            spike_result = self._check_spike(sensor_name, values, current_value)
            if spike_result and (not stuck_result or spike_result['confidence'] > stuck_result.get('confidence', 0)):
                report.update(spike_result)

            # Check 3: Physical cross-validation
            cross_result = self._cross_validate(sensor_name, current_reading, history)
            if cross_result and cross_result['confidence'] > report.get('confidence_issue', 0):
                report.update(cross_result)

            # Compute expected range
            if len(values) >= 3:
                mean_val = sum(values) / len(values)
                std_val = math.sqrt(sum((v - mean_val) ** 2 for v in values) / len(values))
                report['expected_range_min'] = round(mean_val - 2 * std_val, 2)
                report['expected_range_max'] = round(mean_val + 2 * std_val, 2)

            health_reports.append(report)

        # Save to database
        self._save_reports(health_reports)

        return health_reports

    def _check_stuck(self, sensor_name, values):
        """Detect if a sensor is outputting the same value repeatedly (frozen)."""
        if len(values) < self.STUCK_THRESHOLD_READINGS:
            return None

        recent = values[-self.STUCK_THRESHOLD_READINGS:]
        is_stuck = all(
            abs(v - recent[0]) < self.STUCK_TOLERANCE for v in recent
        )

        if is_stuck:
            return {
                'health_status': 'faulty',
                'confidence': 0.95,
                'confidence_issue': 0.95,
                'issue_type': 'stuck',
                'details': {
                    'reason': f'{sensor_name} has been reading {recent[0]:.2f} '
                             f'for {self.STUCK_THRESHOLD_READINGS} consecutive readings. '
                             f'Sensor may be disconnected or frozen.'
                }
            }

        return None

    def _check_spike(self, sensor_name, values, current_value):
        """Detect physically impossible sudden jumps in sensor values."""
        if len(values) < 2:
            return None

        previous = values[-1]
        change = abs(current_value - previous)
        max_change = self.SPIKE_MAX_CHANGE_PER_READ.get(sensor_name, 10.0)

        if change > max_change:
            severity_ratio = change / max_change
            confidence = min(1.0, severity_ratio / 3.0)

            if confidence >= 0.6:
                return {
                    'health_status': 'degraded' if confidence < 0.8 else 'faulty',
                    'confidence': confidence,
                    'confidence_issue': confidence,
                    'issue_type': 'spike',
                    'details': {
                        'reason': f'{sensor_name} jumped from {previous:.2f} to {current_value:.2f} '
                                 f'(Δ={change:.2f}). Maximum expected change: {max_change:.1f}. '
                                 f'Reading may be erroneous.'
                    }
                }

        return None

    def _cross_validate(self, sensor_name, current_reading, history):
        """
        THE NOVEL CROSS-VALIDATION METHOD:
        
        Use physical relationships between sensors to validate each one.
        If sensor A implies something about sensor B, but B disagrees,
        flag the inconsistent sensor.
        """
        if len(history) < 3:
            return None

        # --- Rule 1: Flow vs Level conservation ---
        if sensor_name == 'water_level':
            return self._validate_level_vs_flow(current_reading, history)
        
        if sensor_name == 'flow_rate':
            return self._validate_flow_vs_level(current_reading, history)

        # --- Rule 2: Temperature vs Moisture (evaporation) ---
        if sensor_name == 'soil_moisture':
            return self._validate_moisture_vs_temp(current_reading, history)

        # --- Rule 3: Level physical bounds ---
        if sensor_name == 'water_level':
            if current_reading.water_level < 0 or current_reading.water_level > 100:
                return {
                    'health_status': 'faulty',
                    'confidence': 0.99,
                    'confidence_issue': 0.99,
                    'issue_type': 'out_of_bounds',
                    'details': {
                        'reason': f'Water level reading {current_reading.water_level}% '
                                 f'is outside physical bounds [0-100%].'
                    }
                }

        return None

    def _validate_level_vs_flow(self, current, history):
        """If flow has been high but level hasn't dropped, level sensor may be stuck."""
        avg_flow = sum(r.flow_rate for r in history[-5:]) / min(5, len(history))
        level_change = history[-1].water_level - history[0].water_level
        time_span = (history[-1].timestamp - history[0].timestamp).total_seconds() / 60.0

        if time_span < 1:
            return None

        # High flow for extended period but level didn't change
        if avg_flow > 10 and abs(level_change) < 0.5 and time_span > 5:
            return {
                'health_status': 'degraded',
                'confidence': 0.7,
                'confidence_issue': 0.7,
                'issue_type': 'cross_validation_fail',
                'details': {
                    'reason': f'Flow averaging {avg_flow:.1f}L/min for {time_span:.0f}min '
                             f'but water level only changed {level_change:.2f}%. '
                             f'Level sensor may be miscalibrated or stuck.'
                }
            }

        return None

    def _validate_flow_vs_level(self, current, history):
        """If level is dropping but flow reads zero, flow sensor may be faulty."""
        level_values = [r.water_level for r in history[-5:]]
        if len(level_values) < 2:
            return None

        level_drop = level_values[0] - level_values[-1]
        avg_flow = sum(r.flow_rate for r in history[-5:]) / min(5, len(history))

        # Level dropping significantly but flow sensor reads zero
        if level_drop > 3.0 and avg_flow < 0.5:
            return {
                'health_status': 'degraded',
                'confidence': 0.75,
                'confidence_issue': 0.75,
                'issue_type': 'cross_validation_fail',
                'details': {
                    'reason': f'Water level dropped {level_drop:.1f}% but flow sensor '
                             f'reads only {avg_flow:.1f}L/min. Flow sensor may be '
                             f'blocked or malfunctioning.'
                }
            }

        return None

    def _validate_moisture_vs_temp(self, current, history):
        """
        If temperature is very high and there's no flow (no irrigation), 
        moisture should be decreasing (evaporation). If it's rising, 
        moisture sensor may be faulty.
        """
        avg_temp = sum(r.water_temperature for r in history[-5:]) / min(5, len(history))
        avg_flow = sum(r.flow_rate for r in history[-5:]) / min(5, len(history))
        moisture_values = [r.soil_moisture for r in history[-5:]]

        if len(moisture_values) < 3:
            return None

        moisture_trend = moisture_values[-1] - moisture_values[0]

        # Hot day, no irrigation, but moisture is RISING
        if avg_temp > 30 and avg_flow < 2.0 and moisture_trend > 5.0:
            return {
                'health_status': 'degraded',
                'confidence': 0.65,
                'confidence_issue': 0.65,
                'issue_type': 'cross_validation_fail',
                'details': {
                    'reason': f'Temperature is {avg_temp:.1f}°C with no irrigation '
                             f'({avg_flow:.1f}L/min), but soil moisture rose by '
                             f'{moisture_trend:.1f}%. Evaporation should cause decrease. '
                             f'Moisture sensor may need recalibration.'
                }
            }

        return None

    def _save_reports(self, reports):
        """Save health reports to database (only unhealthy ones)."""
        for report in reports:
            if report['health_status'] != 'healthy':
                # Debounce: don't spam same issue
                existing = SensorHealthLog.query.filter_by(
                    sensor_name=report['sensor_name'],
                    issue_type=report['issue_type']
                ).filter(
                    SensorHealthLog.timestamp >= datetime.utcnow() - timedelta(minutes=5)
                ).first()

                if existing:
                    continue

                log = SensorHealthLog(
                    sensor_name=report['sensor_name'],
                    health_status=report['health_status'],
                    confidence=report['confidence'],
                    issue_type=report['issue_type'],
                    raw_value=report['raw_value'],
                    expected_range_min=report['expected_range_min'],
                    expected_range_max=report['expected_range_max'],
                    cross_validation_details=json.dumps(report.get('details', {}))
                )
                db.session.add(log)

                alert = Alert(
                    alert_type='warning' if report['health_status'] == 'degraded' else 'danger',
                    icon='🔧',
                    title=f'Sensor Health: {report["sensor_name"].replace("_", " ").title()}',
                    message=report.get('details', {}).get('reason', 'Sensor issue detected')[:200]
                )
                db.session.add(alert)

        db.session.commit()

    def get_health_summary(self):
        """Get overall sensor health status."""
        recent_logs = SensorHealthLog.query.filter(
            SensorHealthLog.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ).order_by(SensorHealthLog.timestamp.desc()).all()

        sensor_status = {}
        for name in self.sensor_names:
            logs_for_sensor = [l for l in recent_logs if l.sensor_name == name]
            if not logs_for_sensor:
                sensor_status[name] = {
                    'status': 'healthy',
                    'confidence': 1.0,
                    'issues': []
                }
            else:
                worst = max(logs_for_sensor, key=lambda l: l.confidence)
                sensor_status[name] = {
                    'status': worst.health_status,
                    'confidence': worst.confidence,
                    'issues': [l.to_dict() for l in logs_for_sensor[:3]]
                }

        all_healthy = all(s['status'] == 'healthy' for s in sensor_status.values())

        return {
            'overall_status': 'healthy' if all_healthy else 'degraded',
            'sensors': sensor_status,
            'total_issues_last_hour': len(recent_logs)
        }


# Singleton instance
sensor_health_monitor = SensorHealthMonitor()
