"""
Feature 3: Adaptive Sensor Calibration and Drift Compensation

Patent Claim: A method for maintaining sensor accuracy comprising:
continuously monitoring each sensor's long-term reading distribution 
against a physical consistency model; wherein persistent deviation 
triggers adaptive recalibration using correlated measurements from 
neighboring sensors as reference, producing real-time correction 
factors that compensate for environmental drift without manual 
intervention.

Key Innovation:
- Long-term drift detection via rolling baseline comparison
- Cross-sensor reference calibration (use flow to validate level, etc.)
- Physical model consistency checks for correction validation
- Adaptive correction factors that evolve over time
- Automatic vs. manual recalibration tracking
"""

from datetime import datetime, timedelta
from core_app.models.models import SensorReading, CalibrationRecord, Alert
from core_app import db
import json
import math


class CalibrationEngine:
    """
    Detects sensor drift over time and applies adaptive corrections.
    
    Drift Detection Methods:
    1. Historical Baseline Comparison: Compare rolling mean against long-term baseline
    2. Cross-Sensor Reference: Use physical relationships to validate/correct
    3. Physical Bounds Check: Enforce thermodynamic and hydraulic constraints
    
    Correction Methods:
    1. Offset correction: value_corrected = value_raw + offset
    2. Scale correction: value_corrected = value_raw * scale_factor
    3. Combined: value_corrected = value_raw * scale_factor + offset
    """

    # --- Configuration ---
    BASELINE_WINDOW_HOURS = 24       # Long-term baseline window
    RECENT_WINDOW_MINUTES = 30       # Recent readings window
    DRIFT_THRESHOLD_PCT = 8.0        # >8% sustained deviation = drift
    MIN_READINGS_BASELINE = 50       # Need 50+ readings for reliable baseline
    CORRECTION_DAMPING = 0.3         # Apply corrections gradually (30% per cycle)
    MAX_CORRECTION_FACTOR = 0.20     # Never correct more than ±20%

    # Physical constraints for validation
    PHYSICAL_RANGES = {
        'water_level': (0, 100),       # %
        'flow_rate': (0, 50),          # L/min
        'soil_moisture': (0, 100),     # %
        'water_temperature': (0, 50),  # °C
    }

    # Cross-sensor reference relationships
    # "If flow is X, level should change by approximately Y per minute"
    FLOW_TO_LEVEL_FACTOR = 0.1  # 1 L/min ≈ 0.1% level change per minute

    def __init__(self):
        self.sensor_names = ['water_level', 'flow_rate', 'soil_moisture', 'water_temperature']
        # Active correction factors (evolve over time)
        self._correction_factors = {
            name: {'scale': 1.0, 'offset': 0.0, 'drift_history': []}
            for name in self.sensor_names
        }
        self._calibration_count = 0

    def check_and_calibrate(self, current_reading):
        """
        Main entry: check for drift and apply corrections if needed.
        
        Returns list of calibration actions taken.
        """
        calibrations = []

        for sensor_name in self.sensor_names:
            result = self._check_drift(sensor_name, current_reading)
            if result:
                calibrations.append(result)

        return calibrations

    def _check_drift(self, sensor_name, current_reading):
        """
        Check if a sensor has drifted from its baseline.
        Uses rolling statistical comparison + cross-sensor validation.
        """
        current_value = getattr(current_reading, sensor_name)

        # Get long-term baseline
        baseline = self._compute_baseline(sensor_name)
        if baseline is None:
            return None

        # Get recent statistics
        recent = self._compute_recent_stats(sensor_name)
        if recent is None:
            return None

        # Calculate drift
        drift = recent['mean'] - baseline['mean']
        drift_pct = abs(drift) / max(abs(baseline['mean']), 0.01) * 100

        # Record drift for trend analysis
        self._correction_factors[sensor_name]['drift_history'].append({
            'timestamp': datetime.utcnow(),
            'drift': drift,
            'drift_pct': drift_pct
        })
        # Keep last 100 entries
        self._correction_factors[sensor_name]['drift_history'] = \
            self._correction_factors[sensor_name]['drift_history'][-100:]

        # Check if drift exceeds threshold
        if drift_pct < self.DRIFT_THRESHOLD_PCT:
            return None

        # --- Drift confirmed: determine correction ---

        # Method 1: Cross-sensor reference correction
        cross_correction = self._cross_sensor_correction(sensor_name, current_reading, drift)

        # Method 2: Historical baseline correction
        hist_correction = self._historical_correction(sensor_name, drift, baseline)

        # Choose best correction method
        if cross_correction and cross_correction['confidence'] > 0.6:
            correction = cross_correction
        else:
            correction = hist_correction

        if correction is None:
            return None

        # Apply correction with damping
        corrected_value = self._apply_correction(
            sensor_name, current_value, correction
        )

        # Validate corrected value is within physical bounds
        phys_min, phys_max = self.PHYSICAL_RANGES.get(sensor_name, (0, 100))
        corrected_value = max(phys_min, min(phys_max, corrected_value))

        # Save calibration record
        self._save_calibration(
            sensor_name, drift, correction,
            current_value, corrected_value
        )

        self._calibration_count += 1

        return {
            'sensor_name': sensor_name,
            'drift_detected': round(drift, 4),
            'drift_pct': round(drift_pct, 2),
            'raw_value': current_value,
            'corrected_value': round(corrected_value, 2),
            'correction_method': correction['method'],
            'confidence': correction['confidence']
        }

    def _compute_baseline(self, sensor_name):
        """Compute long-term baseline statistics."""
        since = datetime.utcnow() - timedelta(hours=self.BASELINE_WINDOW_HOURS)
        readings = SensorReading.query.filter(
            SensorReading.timestamp >= since
        ).order_by(SensorReading.timestamp.asc()).all()

        if len(readings) < self.MIN_READINGS_BASELINE:
            return None

        values = [getattr(r, sensor_name) for r in readings]
        mean_val = sum(values) / len(values)
        std_val = math.sqrt(sum((v - mean_val) ** 2 for v in values) / len(values))

        return {
            'mean': mean_val,
            'std': std_val,
            'count': len(values),
            'min': min(values),
            'max': max(values)
        }

    def _compute_recent_stats(self, sensor_name):
        """Compute recent reading statistics."""
        since = datetime.utcnow() - timedelta(minutes=self.RECENT_WINDOW_MINUTES)
        readings = SensorReading.query.filter(
            SensorReading.timestamp >= since
        ).order_by(SensorReading.timestamp.asc()).all()

        if len(readings) < 5:
            return None

        values = [getattr(r, sensor_name) for r in readings]
        mean_val = sum(values) / len(values)
        std_val = math.sqrt(sum((v - mean_val) ** 2 for v in values) / len(values))

        return {
            'mean': mean_val,
            'std': std_val,
            'count': len(values)
        }

    def _cross_sensor_correction(self, sensor_name, current_reading, drift):
        """
        Use physically related sensors to compute a correction.
        
        Example: If flow sensor reads consistently higher than what level 
        changes suggest, the flow sensor may have drifted upward.
        """
        since = datetime.utcnow() - timedelta(minutes=15)
        history = SensorReading.query.filter(
            SensorReading.timestamp >= since
        ).order_by(SensorReading.timestamp.asc()).all()

        if len(history) < 5:
            return None

        if sensor_name == 'flow_rate':
            # Cross-validate flow against level changes
            return self._calibrate_flow_from_level(history, drift)

        elif sensor_name == 'water_level':
            # Cross-validate level against flow
            return self._calibrate_level_from_flow(history, drift)

        elif sensor_name == 'soil_moisture':
            # Cross-validate moisture against temperature and flow
            return self._calibrate_moisture_from_context(history, drift, current_reading)

        elif sensor_name == 'water_temperature':
            # Temperature drift — use physical bounds
            return self._calibrate_temperature(history, drift)

        return None

    def _calibrate_flow_from_level(self, history, drift):
        """
        If we know how much the level changed, we can estimate what the 
        flow SHOULD have been, and compute a correction factor.
        """
        if len(history) < 3:
            return None

        time_span = (history[-1].timestamp - history[0].timestamp).total_seconds() / 60.0
        if time_span < 1:
            return None

        level_change = history[0].water_level - history[-1].water_level  # positive = level dropped
        implied_flow = level_change / (self.FLOW_TO_LEVEL_FACTOR * time_span)  # L/min

        actual_avg_flow = sum(r.flow_rate for r in history) / len(history)

        if actual_avg_flow < 0.5 and abs(implied_flow) < 0.5:
            return None  # Both near zero, can't calibrate

        if actual_avg_flow > 0.1:
            correction_scale = implied_flow / actual_avg_flow
            # Clamp correction
            correction_scale = max(1 - self.MAX_CORRECTION_FACTOR,
                                   min(1 + self.MAX_CORRECTION_FACTOR, correction_scale))

            return {
                'method': 'cross_sensor',
                'reference_sensor': 'water_level',
                'scale_factor': correction_scale,
                'offset': 0.0,
                'confidence': min(0.85, abs(level_change) / 5.0),
                'reason': f'Flow calibrated against level change. '
                         f'Level dropped {level_change:.2f}% implying flow ≈{implied_flow:.1f} L/min, '
                         f'but sensor reads {actual_avg_flow:.1f} L/min.'
            }

        return None

    def _calibrate_level_from_flow(self, history, drift):
        """Calibrate water level sensor using flow data as reference."""
        if len(history) < 3:
            return None

        time_span = (history[-1].timestamp - history[0].timestamp).total_seconds() / 60.0
        if time_span < 1:
            return None

        avg_flow = sum(r.flow_rate for r in history) / len(history)
        expected_level_drop = avg_flow * self.FLOW_TO_LEVEL_FACTOR * time_span

        actual_level_change = history[0].water_level - history[-1].water_level

        if expected_level_drop < 0.1:
            return None  # Negligible flow

        offset = expected_level_drop - actual_level_change

        if abs(offset) > 0.5:
            return {
                'method': 'cross_sensor',
                'reference_sensor': 'flow_rate',
                'scale_factor': 1.0,
                'offset': -offset * self.CORRECTION_DAMPING,
                'confidence': min(0.80, avg_flow / 20.0),
                'reason': f'Level calibrated against flow. '
                         f'Flow suggests {expected_level_drop:.2f}% drop, '
                         f'but level changed by {actual_level_change:.2f}%.'
            }

        return None

    def _calibrate_moisture_from_context(self, history, drift, current):
        """Calibrate moisture using temperature and flow context."""
        avg_temp = sum(r.water_temperature for r in history) / len(history)
        avg_flow = sum(r.flow_rate for r in history) / len(history)

        moisture_values = [r.soil_moisture for r in history]
        moisture_trend = moisture_values[-1] - moisture_values[0]

        # If it's hot and no irrigation, moisture should decrease
        if avg_temp > 28 and avg_flow < 2.0 and moisture_trend > 3.0:
            # Moisture rising when it should fall → sensor drifting up
            offset = -moisture_trend * self.CORRECTION_DAMPING
            return {
                'method': 'physical_model',
                'reference_sensor': 'water_temperature',
                'scale_factor': 1.0,
                'offset': offset,
                'confidence': 0.6,
                'reason': f'Moisture rising ({moisture_trend:+.1f}%) despite hot conditions '
                         f'({avg_temp:.1f}°C) and no irrigation. Applying drift correction.'
            }

        return None

    def _calibrate_temperature(self, history, drift):
        """Temperature sensor drift correction using physical constraints."""
        temps = [r.water_temperature for r in history]
        mean_temp = sum(temps) / len(temps)

        # Temperature should be within reasonable outdoor range
        if mean_temp < 0 or mean_temp > 45:
            offset = (22.0 - mean_temp) * self.CORRECTION_DAMPING
            return {
                'method': 'physical_model',
                'reference_sensor': None,
                'scale_factor': 1.0,
                'offset': offset,
                'confidence': 0.5,
                'reason': f'Temperature reading {mean_temp:.1f}°C outside expected range. '
                         f'Applying conservative correction.'
            }

        return None

    def _historical_correction(self, sensor_name, drift, baseline):
        """Fall-back correction using historical baseline."""
        offset = -drift * self.CORRECTION_DAMPING

        return {
            'method': 'historical',
            'reference_sensor': None,
            'scale_factor': 1.0,
            'offset': offset,
            'confidence': 0.5,
            'reason': f'{sensor_name} drifted {drift:+.2f} from baseline '
                     f'(mean={baseline["mean"]:.2f}). Applying historical correction.'
        }

    def _apply_correction(self, sensor_name, raw_value, correction):
        """Apply correction to a sensor value."""
        scale = correction.get('scale_factor', 1.0)
        offset = correction.get('offset', 0.0)

        # Update running correction factors
        cf = self._correction_factors[sensor_name]
        cf['scale'] = cf['scale'] * 0.9 + scale * 0.1  # Exponential smoothing
        cf['offset'] = cf['offset'] * 0.9 + offset * 0.1

        return raw_value * cf['scale'] + cf['offset']

    def _save_calibration(self, sensor_name, drift, correction, raw_value, corrected_value):
        """Save calibration event to database."""
        # Debounce: one calibration per sensor per 10 minutes
        existing = CalibrationRecord.query.filter_by(
            sensor_name=sensor_name
        ).filter(
            CalibrationRecord.timestamp >= datetime.utcnow() - timedelta(minutes=10)
        ).first()

        if existing:
            return

        record = CalibrationRecord(
            sensor_name=sensor_name,
            drift_detected=abs(drift),
            drift_direction='positive' if drift > 0 else 'negative',
            correction_factor=correction.get('scale_factor', 1.0),
            offset_applied=correction.get('offset', 0.0),
            raw_value=raw_value,
            corrected_value=corrected_value,
            reference_sensor=correction.get('reference_sensor'),
            method=correction['method']
        )
        db.session.add(record)

        alert = Alert(
            alert_type='warning',
            icon='🔧',
            title=f'Auto-Calibration: {sensor_name.replace("_", " ").title()}',
            message=correction.get('reason', 'Drift correction applied')[:200]
        )
        db.session.add(alert)
        db.session.commit()

    def get_calibration_status(self):
        """Get current calibration state for all sensors."""
        recent = CalibrationRecord.query.filter(
            CalibrationRecord.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(CalibrationRecord.timestamp.desc()).all()

        sensor_cal = {}
        for name in self.sensor_names:
            cals = [r for r in recent if r.sensor_name == name]
            cf = self._correction_factors[name]

            sensor_cal[name] = {
                'current_scale_factor': round(cf['scale'], 6),
                'current_offset': round(cf['offset'], 4),
                'calibrations_24h': len(cals),
                'last_calibration': cals[0].to_dict() if cals else None,
                'drift_trend': [
                    {'drift': d['drift'], 'drift_pct': d['drift_pct']}
                    for d in cf['drift_history'][-10:]
                ]
            }

        return {
            'sensors': sensor_cal,
            'total_calibrations': self._calibration_count,
            'calibrations_24h': len(recent),
            'auto_calibration_enabled': True
        }


# Singleton instance
calibration_engine = CalibrationEngine()
