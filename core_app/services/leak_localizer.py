"""
Feature 2: Leak Localization via Moisture Gradient Analysis

Patent Claim: A method for estimating leak location comprising: analyzing 
relative moisture change rates across spatially distributed soil sensors 
to compute a moisture gradient vector; wherein the direction of maximum 
moisture increase indicates the probable leak source, and the magnitude 
ratio between adjacent sensors estimates the distance from the nearest 
sensor node.

Key Innovation:
- Spatial moisture gradient computation across virtual sensor zones
- Pressure differential analysis for pipe network leak triangulation
- Distance estimation using moisture diffusion rate model
- Zone-based probability mapping
"""

from datetime import datetime, timedelta
from core_app.models.models import SensorReading, LeakEvent, LeakLocalization, Alert
from core_app import db
import json
import math


class LeakLocalizer:
    """
    Estimates leak location using moisture gradient analysis and 
    pressure differential modeling.
    
    Virtual Zone Layout (simulated from single moisture sensor):
    Since we have one soil moisture sensor, we simulate multiple zones
    by dividing the moisture signal into spatial components using the
    time-domain signature of moisture propagation.
    
    In a real multi-sensor deployment, each zone would have its own 
    moisture sensor. Here we model it mathematically.
    
    Zone layout:
        [zone_A] ---- pipe ---- [zone_B] ---- pipe ---- [zone_C]
           |                        |                        |
         sensor_A              sensor_B                  sensor_C
    """

    # Zone configuration (distances in meters)
    ZONES = {
        'zone_A': {'position': 0.0, 'name': 'Near Tank'},
        'zone_B': {'position': 15.0, 'name': 'Mid Field'},
        'zone_C': {'position': 30.0, 'name': 'Far Field'},
    }

    # Moisture diffusion parameters
    DIFFUSION_RATE_M_PER_MIN = 0.5    # Moisture front moves at ~0.5 m/min in soil
    MIN_GRADIENT_THRESHOLD = 0.02      # Minimum gradient to consider significant
    PRESSURE_DROP_PER_METER = 0.1      # kPa per meter of pipe (typical)

    def __init__(self):
        self._zone_moisture_history = {zone: [] for zone in self.ZONES}

    def localize(self, current_reading, leak_detections):
        """
        Main entry: when a leak is detected, estimate its location.
        
        Uses the moisture reading to simulate multi-zone moisture distribution
        and compute the gradient vector pointing toward the leak source.
        """
        if not leak_detections:
            return None

        # Get recent readings for temporal moisture analysis
        since = datetime.utcnow() - timedelta(minutes=15)
        history = SensorReading.query.filter(
            SensorReading.timestamp >= since
        ).order_by(SensorReading.timestamp.asc()).all()

        if len(history) < 5:
            return None

        # Simulate multi-zone moisture distribution from single sensor
        zone_moistures = self._simulate_zone_moistures(current_reading, history)

        # Compute moisture gradient
        gradient = self._compute_gradient(zone_moistures, history)

        if not gradient:
            return None

        # Estimate leak location from gradient
        localization = self._estimate_location(gradient, zone_moistures, leak_detections)

        if localization:
            self._save_localization(localization, leak_detections)

        return localization

    def _simulate_zone_moistures(self, current, history):
        """
        Simulate multi-zone moisture distribution.
        
        In a real deployment, each zone has its own sensor. Here we model
        the spatial distribution using temporal analysis of the single 
        moisture sensor, assuming moisture anomalies propagate outward 
        from the leak source with time delay.
        
        Model:
        - zone_A (near tank): base moisture + flow-correlated component
        - zone_B (mid field): base moisture + delayed propagation  
        - zone_C (far field): base moisture + further delayed propagation
        """
        moisture_values = [r.soil_moisture for r in history]
        flow_values = [r.flow_rate for r in history]
        level_values = [r.water_level for r in history]

        base_moisture = sum(moisture_values) / len(moisture_values)
        recent_moisture = sum(moisture_values[-3:]) / min(3, len(moisture_values))
        moisture_trend = recent_moisture - base_moisture

        # Zone A: closest to tank, most affected by supply-side leaks
        # Correlates with flow anomalies
        avg_flow = sum(flow_values) / len(flow_values)
        flow_anomaly = (flow_values[-1] - avg_flow) / max(avg_flow, 1)
        zone_a_moisture = current.soil_moisture + flow_anomaly * 5.0

        # Zone B: mid-field, represents average propagation
        # Uses slightly delayed moisture (older readings)
        mid_idx = len(moisture_values) // 2
        zone_b_moisture = sum(moisture_values[mid_idx:]) / max(1, len(moisture_values) - mid_idx)
        zone_b_moisture += moisture_trend * 0.6  # Partial propagation

        # Zone C: far field, least affected, represents background
        zone_c_moisture = sum(moisture_values[:mid_idx]) / max(1, mid_idx)
        zone_c_moisture += moisture_trend * 0.2  # Minimal propagation

        zone_moistures = {
            'zone_A': round(max(0, min(100, zone_a_moisture)), 2),
            'zone_B': round(max(0, min(100, zone_b_moisture)), 2),
            'zone_C': round(max(0, min(100, zone_c_moisture)), 2),
        }

        # Update history for trend tracking
        for zone, val in zone_moistures.items():
            self._zone_moisture_history[zone].append({
                'timestamp': datetime.utcnow(),
                'value': val
            })
            # Keep last 30 entries
            self._zone_moisture_history[zone] = self._zone_moisture_history[zone][-30:]

        return zone_moistures

    def _compute_gradient(self, zone_moistures, history):
        """
        Compute the spatial moisture gradient vector.
        
        The gradient points in the direction of maximum moisture INCREASE,
        which indicates the direction of the leak source.
        
        Gradient = d(moisture) / d(position)
        """
        zones_sorted = sorted(self.ZONES.items(), key=lambda x: x[1]['position'])

        gradients = []
        for i in range(len(zones_sorted) - 1):
            zone1_name = zones_sorted[i][0]
            zone2_name = zones_sorted[i + 1][0]
            pos1 = zones_sorted[i][1]['position']
            pos2 = zones_sorted[i + 1][1]['position']

            m1 = zone_moistures.get(zone1_name, 0)
            m2 = zone_moistures.get(zone2_name, 0)

            distance = pos2 - pos1
            if distance > 0:
                gradient = (m2 - m1) / distance  # %/meter
                gradients.append({
                    'from': zone1_name,
                    'to': zone2_name,
                    'gradient': gradient,
                    'moisture_diff': m2 - m1,
                    'distance': distance
                })

        if not gradients:
            return None

        # Find maximum absolute gradient — indicates leak direction
        max_gradient = max(gradients, key=lambda g: abs(g['gradient']))

        if abs(max_gradient['gradient']) < self.MIN_GRADIENT_THRESHOLD:
            return None  # No significant gradient

        return {
            'segments': gradients,
            'max_gradient': max_gradient,
            'direction': 'toward_' + max_gradient['to'] if max_gradient['gradient'] > 0
                        else 'toward_' + max_gradient['from']
        }

    def _estimate_location(self, gradient, zone_moistures, leak_detections):
        """
        Estimate the leak location based on gradient analysis.
        
        The zone with the highest moisture increase rate is closest to the leak.
        Distance is estimated using moisture diffusion rate.
        """
        max_grad = gradient['max_gradient']

        # The zone with highest moisture is closest to the leak
        wettest_zone = max(zone_moistures, key=zone_moistures.get)
        wettest_moisture = zone_moistures[wettest_zone]

        # Compute confidence based on gradient strength
        gradient_strength = abs(max_grad['gradient'])
        confidence = min(1.0, gradient_strength / 0.5)  # Normalize to 0-1

        # Estimate distance from nearest sensor using diffusion model
        # Higher moisture = closer to leak
        # d = rate * time_to_saturate
        moisture_excess = wettest_moisture - min(zone_moistures.values())
        estimated_distance = max(0.5, 10.0 - moisture_excess * 0.3)  # Rough estimate in meters

        # Compute pressure differential (simulated)
        # In a real system, this would come from pressure sensors
        zone_a_pos = self.ZONES['zone_A']['position']
        wettest_pos = self.ZONES[wettest_zone]['position']
        pipe_length = abs(wettest_pos - zone_a_pos)
        pressure_diff = pipe_length * self.PRESSURE_DROP_PER_METER

        # Get the primary leak detection for reference
        primary_leak = leak_detections[0] if leak_detections else {}

        return {
            'estimated_zone': wettest_zone,
            'zone_name': self.ZONES[wettest_zone]['name'],
            'confidence': round(confidence, 3),
            'gradient_vector': json.dumps({
                'direction': gradient['direction'],
                'strength': round(gradient_strength, 4),
                'segments': [
                    {'from': s['from'], 'to': s['to'], 'gradient': round(s['gradient'], 4)}
                    for s in gradient['segments']
                ]
            }),
            'pressure_differential': round(pressure_diff, 2),
            'moisture_readings': json.dumps(zone_moistures),
            'estimated_distance_m': round(estimated_distance, 1),
            'zone_moistures': zone_moistures,
            'leak_type': primary_leak.get('leak_type', 'unknown'),
            'details': f'Leak most likely near {self.ZONES[wettest_zone]["name"]} '
                      f'(~{estimated_distance:.1f}m from sensor). '
                      f'Moisture gradient: {gradient_strength:.4f} %/m '
                      f'toward {gradient["direction"]}. '
                      f'Pressure differential: {pressure_diff:.2f} kPa.'
        }

    def _save_localization(self, localization, leak_detections):
        """Save localization result to database."""
        # Find associated leak event
        leak_event = LeakEvent.query.filter_by(
            is_resolved=False
        ).order_by(LeakEvent.timestamp.desc()).first()

        # Debounce: don't spam
        existing = LeakLocalization.query.filter(
            LeakLocalization.timestamp >= datetime.utcnow() - timedelta(minutes=5)
        ).first()
        if existing:
            return

        record = LeakLocalization(
            leak_event_id=leak_event.id if leak_event else None,
            estimated_zone=localization['estimated_zone'],
            gradient_vector=localization['gradient_vector'],
            confidence=localization['confidence'],
            pressure_differential=localization['pressure_differential'],
            moisture_readings=localization['moisture_readings'],
            estimated_distance_m=localization['estimated_distance_m']
        )
        db.session.add(record)

        alert = Alert(
            alert_type='warning',
            icon='📍',
            title=f'Leak Located: {localization["zone_name"]}',
            message=localization['details'][:200]
        )
        db.session.add(alert)
        db.session.commit()

    def get_localization_history(self, hours=24):
        """Get leak localization history."""
        since = datetime.utcnow() - timedelta(hours=hours)
        records = LeakLocalization.query.filter(
            LeakLocalization.timestamp >= since
        ).order_by(LeakLocalization.timestamp.desc()).limit(20).all()

        return {
            'localizations': [r.to_dict() for r in records],
            'total': len(records),
            'zones': {
                zone_id: {
                    'name': info['name'],
                    'position_m': info['position'],
                    'current_moisture': self._zone_moisture_history.get(zone_id, [{}])[-1].get('value', 0)
                    if self._zone_moisture_history.get(zone_id) else 0
                }
                for zone_id, info in self.ZONES.items()
            }
        }


# Singleton instance
leak_localizer = LeakLocalizer()
