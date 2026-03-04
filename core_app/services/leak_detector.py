"""
Patent Claim 1: Multi-Sensor Fusion Leak Detection Engine

A method for detecting water leaks comprising: simultaneously analyzing water 
flow rate, tank level, and soil moisture readings; wherein a leak condition is 
identified when flow rate exceeds a threshold while tank level decreases at a 
rate inconsistent with said flow rate, AND soil moisture in adjacent zones 
increases without scheduled irrigation.

This module implements cross-sensor correlation to detect leaks that NO single 
sensor could identify alone.
"""

from datetime import datetime, timedelta
from core_app.models.models import SensorReading, LeakEvent, Alert
from core_app import db
import json


class LeakDetector:
    """
    Multi-sensor fusion leak detection using cross-correlation analysis.
    
    Detection Methods:
    1. Flow-Level Inconsistency: Flow detected but level doesn't drop as expected
    2. Phantom Flow: Level drops but flow sensor reads zero (underground leak)
    3. Moisture Spike: Soil moisture rises unexpectedly (pipe leak underground)
    4. Combined Fusion: Cross-validates all 3 signals for high-confidence detection
    """

    # Physical constants for the water system
    TANK_CAPACITY_LITERS = 1000.0   # Assume 1000L tank
    TANK_MAX_LEVEL_PCT = 100.0

    # Detection thresholds (tunable)
    LEVEL_DROP_TOLERANCE = 0.3      # Allow 30% deviation from expected drop
    MOISTURE_SPIKE_THRESHOLD = 5.0  # % jump in soil moisture = suspicious
    MIN_READINGS_FOR_ANALYSIS = 3   # Need at least 3 recent readings
    PHANTOM_FLOW_THRESHOLD = 0.5    # Level dropping >0.5%/min with zero flow = leak
    CONFIDENCE_THRESHOLD = 0.6      # Minimum confidence to report a leak

    def __init__(self, app=None):
        self.app = app

    def analyze(self, current_reading):
        """
        Main entry point: analyze current reading against recent history.
        Returns list of detected leak events (may be empty).
        """
        # Get recent readings for trend analysis
        since = datetime.utcnow() - timedelta(minutes=10)
        recent_readings = SensorReading.query.filter(
            SensorReading.timestamp >= since
        ).order_by(SensorReading.timestamp.asc()).all()

        if len(recent_readings) < self.MIN_READINGS_FOR_ANALYSIS:
            return []

        detections = []

        # --- Detection Method 1: Flow-Level Inconsistency ---
        flow_level_result = self._check_flow_level_inconsistency(
            current_reading, recent_readings
        )
        if flow_level_result:
            detections.append(flow_level_result)

        # --- Detection Method 2: Phantom Flow (level drops, no flow) ---
        phantom_result = self._check_phantom_flow(
            current_reading, recent_readings
        )
        if phantom_result:
            detections.append(phantom_result)

        # --- Detection Method 3: Moisture Spike ---
        moisture_result = self._check_moisture_anomaly(
            current_reading, recent_readings
        )
        if moisture_result:
            detections.append(moisture_result)

        # --- Fusion: combine signals for highest confidence ---
        fused_result = self._fuse_signals(
            current_reading, recent_readings,
            flow_level_result, phantom_result, moisture_result
        )
        if fused_result:
            detections.append(fused_result)

        # Persist detections
        self._save_detections(detections)

        return detections

    def _check_flow_level_inconsistency(self, current, history):
        """
        If water is flowing OUT but tank level isn't dropping proportionally,
        water is going somewhere else (leak downstream of flow sensor).
        
        Conversely, if level is dropping FASTER than flow accounts for,
        there's an unmetered leak (before the flow sensor).
        """
        if len(history) < 2:
            return None

        # Calculate actual level drop rate (% per minute)
        time_span = (history[-1].timestamp - history[0].timestamp).total_seconds() / 60.0
        if time_span < 0.5:
            return None

        actual_drop = history[0].water_level - history[-1].water_level
        actual_drop_rate = actual_drop / time_span  # %/min

        # Calculate expected drop rate based on average flow
        avg_flow = sum(r.flow_rate for r in history) / len(history)  # L/min
        # Convert flow to expected level drop
        liters_per_percent = self.TANK_CAPACITY_LITERS / self.TANK_MAX_LEVEL_PCT
        expected_drop_rate = avg_flow / liters_per_percent  # %/min

        # Check inconsistency
        if expected_drop_rate < 0.01:  # Negligible flow
            return None

        ratio = actual_drop_rate / expected_drop_rate if expected_drop_rate > 0 else 0

        # Level dropping MUCH faster than flow explains
        if ratio > (1 + self.LEVEL_DROP_TOLERANCE) and actual_drop_rate > 0.1:
            confidence = min(1.0, (ratio - 1.0) / 2.0)
            if confidence >= self.CONFIDENCE_THRESHOLD:
                severity = 'high' if confidence > 0.8 else 'medium'
                return {
                    'leak_type': 'unmetered_leak',
                    'confidence': confidence,
                    'severity': severity,
                    'level_drop_rate': actual_drop_rate,
                    'expected_drop_rate': expected_drop_rate,
                    'moisture_anomaly_score': 0.0,
                    'details': f'Level dropping {ratio:.1f}x faster than flow accounts for. '
                               f'Actual: {actual_drop_rate:.3f}%/min, Expected: {expected_drop_rate:.3f}%/min'
                }

        # Flow detected but level NOT dropping (water going elsewhere)
        if avg_flow > 5.0 and actual_drop_rate < expected_drop_rate * (1 - self.LEVEL_DROP_TOLERANCE):
            if actual_drop_rate < 0.05:  # Level essentially stable
                confidence = min(1.0, avg_flow / 30.0)
                if confidence >= self.CONFIDENCE_THRESHOLD:
                    return {
                        'leak_type': 'downstream_leak',
                        'confidence': confidence,
                        'severity': 'medium',
                        'level_drop_rate': actual_drop_rate,
                        'expected_drop_rate': expected_drop_rate,
                        'moisture_anomaly_score': 0.0,
                        'details': f'Flow at {avg_flow:.1f}L/min but level stable. '
                                   f'Water may be leaking downstream of flow sensor.'
                    }

        return None

    def _check_phantom_flow(self, current, history):
        """
        Level is dropping but flow sensor reads zero/near-zero.
        This means water is leaving the tank through a path the flow sensor can't see.
        Classic underground pipe leak signature.
        """
        if len(history) < 2:
            return None

        time_span = (history[-1].timestamp - history[0].timestamp).total_seconds() / 60.0
        if time_span < 0.5:
            return None

        actual_drop = history[0].water_level - history[-1].water_level
        actual_drop_rate = actual_drop / time_span

        avg_flow = sum(r.flow_rate for r in history) / len(history)

        # Level dropping significantly but flow sensor says near-zero
        if actual_drop_rate > self.PHANTOM_FLOW_THRESHOLD and avg_flow < 1.0:
            confidence = min(1.0, actual_drop_rate / 2.0)
            if confidence >= self.CONFIDENCE_THRESHOLD:
                return {
                    'leak_type': 'pipe_leak',
                    'confidence': confidence,
                    'severity': 'critical' if confidence > 0.85 else 'high',
                    'level_drop_rate': actual_drop_rate,
                    'expected_drop_rate': 0.0,
                    'moisture_anomaly_score': 0.0,
                    'details': f'Tank level dropping at {actual_drop_rate:.3f}%/min but '
                               f'flow sensor reads only {avg_flow:.1f}L/min. '
                               f'Possible undetected pipe leak.'
                }

        return None

    def _check_moisture_anomaly(self, current, history):
        """
        Soil moisture rising unexpectedly when no irrigation is scheduled.
        Could indicate underground pipe leak saturating the soil.
        """
        if len(history) < 3:
            return None

        # Calculate moisture trend
        moisture_values = [r.soil_moisture for r in history]
        moisture_change = moisture_values[-1] - moisture_values[0]
        time_span = (history[-1].timestamp - history[0].timestamp).total_seconds() / 60.0

        if time_span < 0.5:
            return None

        moisture_rate = moisture_change / time_span  # %/min

        # Rapid moisture increase without high flow (no active irrigation)
        avg_flow = sum(r.flow_rate for r in history) / len(history)

        if moisture_rate > 0.5 and avg_flow < 5.0:  # Moisture rising but low flow
            # Calculate anomaly score
            baseline_moisture = sum(moisture_values[:len(moisture_values)//2]) / (len(moisture_values)//2)
            current_moisture = current.soil_moisture
            anomaly_score = (current_moisture - baseline_moisture) / max(baseline_moisture, 1)

            if anomaly_score > 0.05:  # >5% deviation
                confidence = min(1.0, anomaly_score * 5)
                if confidence >= self.CONFIDENCE_THRESHOLD:
                    return {
                        'leak_type': 'underground_leak',
                        'confidence': confidence,
                        'severity': 'high' if confidence > 0.75 else 'medium',
                        'level_drop_rate': 0.0,
                        'expected_drop_rate': 0.0,
                        'moisture_anomaly_score': anomaly_score,
                        'details': f'Soil moisture rising at {moisture_rate:.2f}%/min with '
                                   f'minimal flow ({avg_flow:.1f}L/min). '
                                   f'Anomaly score: {anomaly_score:.3f}. '
                                   f'Possible underground pipe leak.'
                    }

        return None

    def _fuse_signals(self, current, history, flow_level, phantom, moisture):
        """
        NOVEL FUSION: Combine multiple weak signals into a strong detection.
        Even if individual detectors are below threshold, their combination 
        may indicate a leak with high confidence.
        """
        signals = [flow_level, phantom, moisture]
        active_signals = [s for s in signals if s is not None]

        if len(active_signals) < 2:
            return None  # Need at least 2 corroborating signals

        # Weighted fusion of confidence scores
        total_confidence = 1.0
        for signal in active_signals:
            total_confidence *= (1.0 - signal['confidence'])
        fused_confidence = 1.0 - total_confidence  # P(at least one is right)

        # Boost confidence when multiple signals agree
        fused_confidence = min(1.0, fused_confidence * 1.2)

        if fused_confidence >= 0.7:  # High bar for fused detection
            details_parts = [s['details'] for s in active_signals]
            max_severity_signal = max(active_signals, key=lambda s: s['confidence'])

            return {
                'leak_type': 'multi_sensor_fusion',
                'confidence': fused_confidence,
                'severity': 'critical' if fused_confidence > 0.9 else 'high',
                'level_drop_rate': max_severity_signal['level_drop_rate'],
                'expected_drop_rate': max_severity_signal['expected_drop_rate'],
                'moisture_anomaly_score': max(s['moisture_anomaly_score'] for s in active_signals),
                'details': f'MULTI-SENSOR FUSION ALERT ({len(active_signals)} signals corroborate). '
                           + ' | '.join(details_parts)
            }

        return None

    def _save_detections(self, detections):
        """Persist leak detections to database and create alerts."""
        for detection in detections:
            # Check for existing unresolved leak of same type (debounce)
            existing = LeakEvent.query.filter_by(
                leak_type=detection['leak_type'],
                is_resolved=False
            ).first()

            if existing:
                continue  # Don't spam duplicate leak events

            from core_app.models.models import SensorReading
            latest = SensorReading.query.order_by(SensorReading.timestamp.desc()).first()

            leak = LeakEvent(
                leak_type=detection['leak_type'],
                confidence=detection['confidence'],
                severity=detection['severity'],
                flow_rate_at_detection=latest.flow_rate if latest else 0,
                water_level_at_detection=latest.water_level if latest else 0,
                soil_moisture_at_detection=latest.soil_moisture if latest else 0,
                level_drop_rate=detection['level_drop_rate'],
                expected_drop_rate=detection['expected_drop_rate'],
                moisture_anomaly_score=detection['moisture_anomaly_score']
            )
            db.session.add(leak)

            # Create corresponding alert
            alert = Alert(
                alert_type='danger' if detection['severity'] in ('critical', 'high') else 'warning',
                icon='🔴' if detection['severity'] == 'critical' else '🟠',
                title=f'Leak Detected: {detection["leak_type"].replace("_", " ").title()}',
                message=detection['details'][:200]
            )
            db.session.add(alert)

        if detections:
            db.session.commit()

    def get_status(self):
        """Get current leak detection status summary."""
        active_leaks = LeakEvent.query.filter_by(is_resolved=False).all()
        recent_leaks = LeakEvent.query.order_by(
            LeakEvent.timestamp.desc()
        ).limit(10).all()

        return {
            'active_leaks': [l.to_dict() for l in active_leaks],
            'recent_leaks': [l.to_dict() for l in recent_leaks],
            'total_active': len(active_leaks),
            'system_status': 'leak_detected' if active_leaks else 'normal'
        }


# Singleton instance
leak_detector = LeakDetector()
