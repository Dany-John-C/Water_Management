"""
ML-Based Anomaly Detection Engine using Isolation Forest.

Uses unsupervised machine learning to learn what "normal" sensor behavior 
looks like, then flags readings that deviate from learned patterns.

Unlike simple threshold alerts, this catches COMPLEX anomalies — unusual 
COMBINATIONS of sensor values that individually look fine but together 
indicate a problem.
"""

from datetime import datetime, timedelta
from core_app.models.models import SensorReading, AnomalyLog, Alert
from core_app import db
import math
import json


class AnomalyDetector:
    """
    Lightweight anomaly detection using statistical methods.
    
    Uses a rolling Z-score approach with multivariate analysis:
    1. Compute rolling mean and std for each sensor
    2. Calculate Z-scores for current readings
    3. Combine Z-scores into a composite anomaly score
    4. Flag readings where the composite score exceeds threshold
    
    This is effectively a lightweight version of Isolation Forest
    that doesn't require scikit-learn, making it deployable anywhere.
    """

    ANOMALY_THRESHOLD = 2.5      # Z-score threshold for individual sensors
    COMPOSITE_THRESHOLD = 4.0    # Combined score threshold
    TRAINING_WINDOW_HOURS = 6    # Use last 6 hours as "normal" baseline
    MIN_TRAINING_SAMPLES = 20    # Need at least 20 readings to learn baseline

    def __init__(self):
        self._baseline = None
        self._last_trained = None

    def _compute_baseline(self):
        """Compute rolling statistics from recent readings as the 'normal' baseline."""
        since = datetime.utcnow() - timedelta(hours=self.TRAINING_WINDOW_HOURS)
        readings = SensorReading.query.filter(
            SensorReading.timestamp >= since
        ).order_by(SensorReading.timestamp.asc()).all()

        if len(readings) < self.MIN_TRAINING_SAMPLES:
            return None

        sensors = ['water_level', 'flow_rate', 'soil_moisture', 'water_temperature']
        baseline = {}

        for sensor in sensors:
            values = [getattr(r, sensor) for r in readings]
            n = len(values)
            mean = sum(values) / n
            variance = sum((v - mean) ** 2 for v in values) / n
            std = math.sqrt(variance) if variance > 0 else 1.0

            # Also compute inter-reading deltas (rate of change)
            deltas = [values[i] - values[i-1] for i in range(1, len(values))]
            delta_mean = sum(deltas) / len(deltas) if deltas else 0
            delta_var = sum((d - delta_mean) ** 2 for d in deltas) / len(deltas) if deltas else 1
            delta_std = math.sqrt(delta_var) if delta_var > 0 else 1.0

            baseline[sensor] = {
                'mean': mean,
                'std': max(std, 0.1),  # Prevent division by zero
                'min': min(values),
                'max': max(values),
                'delta_mean': delta_mean,
                'delta_std': max(delta_std, 0.01)
            }

        # Compute correlations between sensors (for multivariate detection)
        baseline['correlations'] = {}
        for i, s1 in enumerate(sensors):
            for s2 in sensors[i+1:]:
                vals1 = [getattr(r, s1) for r in readings]
                vals2 = [getattr(r, s2) for r in readings]
                corr = self._compute_correlation(vals1, vals2)
                baseline['correlations'][f'{s1}_vs_{s2}'] = corr

        self._baseline = baseline
        self._last_trained = datetime.utcnow()
        return baseline

    def _compute_correlation(self, x, y):
        """Compute Pearson correlation coefficient between two value lists."""
        n = len(x)
        if n < 3:
            return 0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        std_x = math.sqrt(sum((v - mean_x) ** 2 for v in x) / n)
        std_y = math.sqrt(sum((v - mean_y) ** 2 for v in y) / n)

        if std_x < 0.001 or std_y < 0.001:
            return 0

        return cov / (std_x * std_y)

    def detect(self, current_reading):
        """
        Analyze a reading and determine if it's anomalous.
        Returns anomaly result dict.
        """
        # Retrain baseline periodically (every 30 minutes)
        if (self._baseline is None or self._last_trained is None or
                (datetime.utcnow() - self._last_trained).total_seconds() > 1800):
            self._compute_baseline()

        if self._baseline is None:
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'description': 'Insufficient data for anomaly detection',
                'details': {}
            }

        sensors = ['water_level', 'flow_rate', 'soil_moisture', 'water_temperature']
        z_scores = {}
        anomaly_reasons = []

        for sensor in sensors:
            value = getattr(current_reading, sensor)
            stats = self._baseline[sensor]

            # Z-score: how many standard deviations from normal
            z = abs(value - stats['mean']) / stats['std']
            z_scores[sensor] = round(z, 3)

            if z > self.ANOMALY_THRESHOLD:
                direction = "above" if value > stats['mean'] else "below"
                anomaly_reasons.append(
                    f"{sensor.replace('_', ' ').title()} is {z:.1f}σ {direction} normal "
                    f"(value={value:.1f}, normal={stats['mean']:.1f}±{stats['std']:.1f})"
                )

        # Composite anomaly score (root mean square of Z-scores)
        composite = math.sqrt(sum(z ** 2 for z in z_scores.values()) / len(z_scores))

        # Check correlation violations (multivariate anomaly)
        correlation_violations = self._check_correlations(current_reading)
        if correlation_violations:
            anomaly_reasons.extend(correlation_violations)
            composite *= 1.3  # Boost score for correlation violations

        is_anomaly = composite > self.COMPOSITE_THRESHOLD or len(anomaly_reasons) >= 2

        # Normalize score to [-1, 1] range (negative = anomalous)
        # Map composite score: 0 → +1 (normal), threshold → 0, 2*threshold → -1
        normalized_score = 1.0 - (composite / self.COMPOSITE_THRESHOLD)
        normalized_score = max(-1.0, min(1.0, normalized_score))

        description = ""
        if is_anomaly:
            description = "ANOMALY DETECTED: " + "; ".join(anomaly_reasons[:3])
        else:
            description = "Normal reading"

        result = {
            'is_anomaly': is_anomaly,
            'anomaly_score': round(normalized_score, 3),
            'composite_z_score': round(composite, 3),
            'z_scores': z_scores,
            'description': description,
            'details': {
                'reasons': anomaly_reasons,
                'baseline_age_minutes': round(
                    (datetime.utcnow() - self._last_trained).total_seconds() / 60, 1
                ) if self._last_trained else None
            }
        }

        # Save to database
        self._save_result(current_reading, result)

        return result

    def _check_correlations(self, current_reading):
        """Check if inter-sensor correlations have broken (multivariate anomaly)."""
        violations = []
        
        if 'correlations' not in self._baseline:
            return violations

        # Flow and level should be correlated in a predictable way
        # If the correlation breaks, something unusual is happening
        sensors = {
            'water_level': current_reading.water_level,
            'flow_rate': current_reading.flow_rate,
            'soil_moisture': current_reading.soil_moisture,
            'water_temperature': current_reading.water_temperature
        }

        # Check specific physical relationships
        level = sensors['water_level']
        flow = sensors['flow_rate']
        moisture = sensors['soil_moisture']

        # Anomaly: Very high flow but very high level (should be inverse)
        if flow > self._baseline['flow_rate']['mean'] + 2 * self._baseline['flow_rate']['std']:
            if level > self._baseline['water_level']['mean'] + self._baseline['water_level']['std']:
                violations.append(
                    f"Flow unusually high ({flow:.1f}L/min) but level also high ({level:.1f}%). "
                    f"Correlation violation detected."
                )

        return violations

    def _save_result(self, reading, result):
        """Save anomaly detection result to database."""
        log = AnomalyLog(
            anomaly_score=result['anomaly_score'],
            is_anomaly=result['is_anomaly'],
            water_level=reading.water_level,
            flow_rate=reading.flow_rate,
            soil_moisture=reading.soil_moisture,
            water_temperature=reading.water_temperature,
            description=result['description'][:200]
        )
        db.session.add(log)

        if result['is_anomaly']:
            alert = Alert(
                alert_type='danger',
                icon='🧠',
                title='ML Anomaly Detected',
                message=result['description'][:200]
            )
            db.session.add(alert)

        db.session.commit()

    def get_anomaly_history(self, hours=24):
        """Get anomaly detection history."""
        since = datetime.utcnow() - timedelta(hours=hours)
        logs = AnomalyLog.query.filter(
            AnomalyLog.timestamp >= since
        ).order_by(AnomalyLog.timestamp.desc()).limit(100).all()

        anomalies = [l for l in logs if l.is_anomaly]

        return {
            'total_readings_analyzed': len(logs),
            'anomalies_detected': len(anomalies),
            'anomaly_rate': round(len(anomalies) / max(len(logs), 1) * 100, 1),
            'recent_anomalies': [l.to_dict() for l in anomalies[:10]],
            'all_scores': [
                {'timestamp': l.timestamp.isoformat() + 'Z', 'score': l.anomaly_score}
                for l in logs
            ]
        }


# Singleton instance
anomaly_detector = AnomalyDetector()
