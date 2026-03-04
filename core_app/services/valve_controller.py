"""
Feature 1: Automatic Leak Response via Valve Actuation

Patent Claim: A method for automatic water loss mitigation comprising:
upon detection of a leak probability exceeding a predetermined threshold,
the system automatically actuates an electronically controlled valve to 
isolate the affected irrigation zone, logs the intervention event, and 
estimates water saved during the isolation period.

Key Innovation:
- Threshold-gated automatic valve closure  
- Zone-based isolation (only affected zones shut off)
- Post-isolation flow verification (checks if closing the valve stopped the leak)
- Water savings calculation from intervention
- Automatic re-opening after configurable timeout + verification
"""

from datetime import datetime, timedelta
from core_app.models.models import ValveAction, LeakEvent, SensorReading, Alert
from core_app import db
import json


class ValveController:
    """
    Manages automatic valve actuation in response to leak detection.
    
    Zones in the system:
    - zone_A: Primary irrigation zone (garden/field)
    - zone_B: Secondary irrigation zone
    - main_supply: Main water supply line
    
    The controller simulates solenoid valve control. In a real deployment,
    this would send GPIO signals or MQTT commands to the ESP8266.
    """

    # --- Configuration ---
    LEAK_CONFIDENCE_THRESHOLD = 0.70    # Auto-close valve when leak confidence > 70%
    CRITICAL_THRESHOLD = 0.90           # Immediately close ALL valves
    AUTO_REOPEN_MINUTES = 30            # Auto-reopen after 30 minutes for re-evaluation
    MAX_WATER_LOSS_LITERS_PER_MIN = 10  # Assume max 10 L/min leak rate for savings calc
    VERIFICATION_WAIT_SECONDS = 60      # Wait 60s after valve close to verify leak stopped

    # Zone mapping — which leak types map to which zones
    LEAK_ZONE_MAP = {
        'pipe_leak': 'main_supply',
        'underground_leak': 'zone_A',
        'downstream_leak': 'zone_A',
        'unmetered_leak': 'main_supply',
        'multi_sensor_fusion': 'main_supply',
    }

    # Valve state tracking (in-memory simulation)
    _valve_states = {
        'zone_A': 'open',
        'zone_B': 'open',
        'main_supply': 'open',
    }

    def __init__(self):
        self.last_action_time = {}

    def evaluate_and_respond(self, leak_detections):
        """
        Main entry: evaluate leak detections and actuate valves if needed.
        Called after leak_detector.analyze() returns results.
        
        Args:
            leak_detections: list of detection dicts from LeakDetector.analyze()
        
        Returns:
            list of valve actions taken
        """
        if not leak_detections:
            # Check if any valves can be reopened
            self._check_auto_reopen()
            return []

        actions_taken = []

        for detection in leak_detections:
            confidence = detection.get('confidence', 0)
            leak_type = detection.get('leak_type', 'unknown')

            # Determine target zone
            target_zone = self.LEAK_ZONE_MAP.get(leak_type, 'zone_A')

            # --- Critical threshold: shut everything ---
            if confidence >= self.CRITICAL_THRESHOLD:
                for zone in self._valve_states:
                    action = self._close_valve(zone, detection, 'leak_response')
                    if action:
                        actions_taken.append(action)
                continue

            # --- Standard threshold: isolate affected zone ---
            if confidence >= self.LEAK_CONFIDENCE_THRESHOLD:
                action = self._close_valve(target_zone, detection, 'leak_response')
                if action:
                    actions_taken.append(action)

        # Check for auto-reopen on other valves
        self._check_auto_reopen()

        return actions_taken

    def _close_valve(self, zone_id, detection, trigger_type):
        """
        Close a valve for a specific zone.
        Returns action dict if valve was actually closed, None if already closed.
        """
        # Debounce: don't re-close a valve that was closed recently
        last_action = self.last_action_time.get(zone_id)
        if last_action and (datetime.utcnow() - last_action).total_seconds() < 120:
            return None

        if self._valve_states.get(zone_id) == 'closed':
            return None  # Already closed

        # Get current flow reading for "before" snapshot
        latest_reading = SensorReading.query.order_by(
            SensorReading.timestamp.desc()
        ).first()
        flow_before = latest_reading.flow_rate if latest_reading else 0.0

        # Find the associated LeakEvent
        leak_event = LeakEvent.query.filter_by(
            is_resolved=False
        ).order_by(LeakEvent.timestamp.desc()).first()

        # --- ACTUATE VALVE (simulated) ---
        self._valve_states[zone_id] = 'closed'
        self.last_action_time[zone_id] = datetime.utcnow()

        # Create valve action record
        valve_action = ValveAction(
            zone_id=zone_id,
            action='close',
            trigger_type=trigger_type,
            leak_event_id=leak_event.id if leak_event else None,
            leak_confidence=detection.get('confidence', 0),
            flow_before=flow_before,
            flow_after=None,  # Will be updated after verification
            water_saved_liters=0.0,
            is_active=True
        )
        db.session.add(valve_action)

        # Create alert
        alert = Alert(
            alert_type='danger',
            icon='🚨',
            title=f'Valve CLOSED: {zone_id.replace("_", " ").title()}',
            message=f'Automatic leak response activated. '
                    f'Leak confidence: {detection["confidence"]:.0%}. '
                    f'Zone {zone_id} isolated. Flow before: {flow_before:.1f} L/min.'
        )
        db.session.add(alert)
        db.session.commit()

        return {
            'zone_id': zone_id,
            'action': 'close',
            'confidence': detection['confidence'],
            'flow_before': flow_before,
            'leak_type': detection.get('leak_type', 'unknown')
        }

    def _check_auto_reopen(self):
        """
        Automatically reopen valves after timeout period.
        Verifies that the leak condition has cleared before reopening.
        """
        for zone_id, state in self._valve_states.items():
            if state != 'closed':
                continue

            last_action = self.last_action_time.get(zone_id)
            if not last_action:
                continue

            elapsed_minutes = (datetime.utcnow() - last_action).total_seconds() / 60.0

            if elapsed_minutes >= self.AUTO_REOPEN_MINUTES:
                # Verify: check if there are still active leak events
                active_leaks = LeakEvent.query.filter_by(is_resolved=False).count()

                if active_leaks == 0:
                    self._open_valve(zone_id)
                else:
                    # Extend the closure but log it
                    self.last_action_time[zone_id] = datetime.utcnow()

    def _open_valve(self, zone_id):
        """Reopen a valve and calculate water saved during closure."""
        self._valve_states[zone_id] = 'open'

        # Find the closure action
        closure = ValveAction.query.filter_by(
            zone_id=zone_id,
            action='close',
            is_active=True
        ).order_by(ValveAction.timestamp.desc()).first()

        if closure:
            # Calculate water saved
            closure_duration_min = (datetime.utcnow() - closure.timestamp).total_seconds() / 60.0
            estimated_saved = closure.flow_before * closure_duration_min  # L
            closure.is_active = False
            closure.released_at = datetime.utcnow()
            closure.water_saved_liters = estimated_saved

            # Get current flow for "after" reading
            latest = SensorReading.query.order_by(SensorReading.timestamp.desc()).first()
            closure.flow_after = latest.flow_rate if latest else 0.0

        # Create reopen action record
        reopen = ValveAction(
            zone_id=zone_id,
            action='open',
            trigger_type='auto_reopen',
            flow_before=0.0,
            is_active=False
        )
        db.session.add(reopen)

        alert = Alert(
            alert_type='success',
            icon='✅',
            title=f'Valve REOPENED: {zone_id.replace("_", " ").title()}',
            message=f'Automatic reopen after timeout. '
                    f'Water saved: ~{closure.water_saved_liters:.0f}L' if closure else 'Zone reopened.'
        )
        db.session.add(alert)
        db.session.commit()

    def manual_override(self, zone_id, action):
        """Manual valve control (open/close) for testing or emergencies."""
        if action == 'close':
            self._valve_states[zone_id] = 'closed'
        elif action == 'open':
            self._valve_states[zone_id] = 'open'
            self._open_valve(zone_id)

        override = ValveAction(
            zone_id=zone_id,
            action=action,
            trigger_type='manual',
            is_active=(action == 'close')
        )
        db.session.add(override)
        db.session.commit()

        return {'zone_id': zone_id, 'action': action, 'trigger': 'manual'}

    def verify_post_closure(self, zone_id):
        """
        After closing a valve, verify that the leak stopped.
        Compares flow before vs after closure.
        """
        closure = ValveAction.query.filter_by(
            zone_id=zone_id,
            action='close',
            is_active=True
        ).order_by(ValveAction.timestamp.desc()).first()

        if not closure:
            return {'verified': False, 'reason': 'No active closure found'}

        elapsed = (datetime.utcnow() - closure.timestamp).total_seconds()
        if elapsed < self.VERIFICATION_WAIT_SECONDS:
            return {'verified': False, 'reason': f'Waiting for verification ({elapsed:.0f}s / {self.VERIFICATION_WAIT_SECONDS}s)'}

        latest = SensorReading.query.order_by(SensorReading.timestamp.desc()).first()
        if not latest:
            return {'verified': False, 'reason': 'No sensor data available'}

        closure.flow_after = latest.flow_rate
        flow_reduction = closure.flow_before - latest.flow_rate
        reduction_pct = (flow_reduction / max(closure.flow_before, 0.1)) * 100

        db.session.commit()

        return {
            'verified': True,
            'flow_before': closure.flow_before,
            'flow_after': latest.flow_rate,
            'flow_reduction': round(flow_reduction, 2),
            'reduction_pct': round(reduction_pct, 1),
            'leak_confirmed': reduction_pct > 30  # >30% reduction confirms leak was in this zone
        }

    def get_status(self):
        """Get current valve controller status."""
        active_closures = ValveAction.query.filter_by(
            action='close', is_active=True
        ).all()

        recent_actions = ValveAction.query.order_by(
            ValveAction.timestamp.desc()
        ).limit(20).all()

        total_water_saved = db.session.query(
            db.func.sum(ValveAction.water_saved_liters)
        ).filter(
            ValveAction.water_saved_liters > 0
        ).scalar() or 0.0

        return {
            'valve_states': dict(self._valve_states),
            'active_closures': [a.to_dict() for a in active_closures],
            'recent_actions': [a.to_dict() for a in recent_actions],
            'total_water_saved_liters': round(total_water_saved, 1),
            'auto_response_enabled': True,
            'confidence_threshold': self.LEAK_CONFIDENCE_THRESHOLD
        }


# Singleton instance
valve_controller = ValveController()
