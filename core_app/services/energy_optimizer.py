"""
Feature 5: Energy Optimization via Adaptive Sampling Frequency

Patent Claim: A method for optimizing energy consumption in an IoT sensor 
network comprising: dynamically adjusting sensor sampling frequency based 
on detected environmental stability; wherein during periods of stable 
readings the system reduces sampling rate and enters low-power mode, 
and during volatile conditions or detected anomalies the system increases 
sampling rate to capture transient events, thereby extending battery life 
while maintaining monitoring fidelity.

Key Innovation:
- Environmental stability index computation
- Multi-tier power modes (high_freq, normal, low_power, deep_sleep)
- Event-driven wake-up on anomaly detection
- Battery life estimation based on current power profile
- Sensor-selective activation (disable unnecessary sensors in stable periods)
"""

from datetime import datetime, timedelta
from core_app.models.models import SensorReading, EnergyProfile, Alert
from core_app import db
import json
import math


class EnergyOptimizer:
    """
    Dynamically optimizes sensor sampling frequency and power consumption
    based on environmental conditions and detected events.
    
    Power Modes:
    - high_freq (2s):   Anomaly detected, leak in progress, rapid changes
    - normal (5s):      Standard operation, moderate changes
    - low_power (15s):  Stable environment, slow changes
    - deep_sleep (60s): Night mode, extremely stable, no events
    
    Battery Model (ESP8266 + sensors):
    - Active reading: ~80mA for ~200ms
    - WiFi transmission: ~170mA for ~500ms  
    - Deep sleep: ~20μA
    - Battery capacity: typical 18650 = 3000mAh
    """

    # Sampling intervals per mode (seconds)
    MODE_INTERVALS = {
        'high_freq': 2,
        'normal': 5,
        'low_power': 15,
        'deep_sleep': 60,
    }

    # Power consumption per mode (mAh per hour)
    MODE_POWER_MAH = {
        'high_freq': 95.0,    # Very frequent wake+transmit
        'normal': 45.0,       # Standard duty cycle
        'low_power': 15.0,    # Reduced duty cycle
        'deep_sleep': 2.0,    # Mostly sleeping
    }

    BATTERY_CAPACITY_MAH = 3000  # Typical 18650 cell

    # Stability thresholds
    STABILITY_HIGH = 0.8          # Very stable → can reduce sampling
    STABILITY_MEDIUM = 0.5        # Moderate → normal sampling
    STABILITY_LOW = 0.2           # Volatile → increase sampling
    
    # Change rate thresholds (per reading)
    MAX_CHANGE_RATES = {
        'water_level': 5.0,
        'flow_rate': 10.0,
        'soil_moisture': 4.0,
        'water_temperature': 2.0,
    }

    def __init__(self):
        self.current_mode = 'normal'
        self.current_interval = self.MODE_INTERVALS['normal']
        self.current_stability = 0.5
        self._active_sensors = {
            'water_level': True,
            'flow_rate': True,
            'soil_moisture': True,
            'water_temperature': True,
        }
        self._mode_history = []
        self._total_energy_saved_pct = 0.0

    def optimize(self, current_reading, has_anomaly=False, has_leak=False):
        """
        Main entry: evaluate conditions and adjust sampling strategy.
        
        Args:
            current_reading: Latest SensorReading
            has_anomaly: Whether ML anomaly was detected
            has_leak: Whether leak was detected
            
        Returns:
            dict with optimization decision
        """
        # Get recent readings for stability analysis
        since = datetime.utcnow() - timedelta(minutes=10)
        history = SensorReading.query.filter(
            SensorReading.timestamp >= since
        ).order_by(SensorReading.timestamp.asc()).all()

        if len(history) < 3:
            return self._get_current_profile()

        # Step 1: Compute environmental stability index
        stability = self._compute_stability(history)
        self.current_stability = stability

        # Step 2: Check for event-driven overrides
        if has_leak or has_anomaly:
            new_mode = 'high_freq'
        elif stability >= self.STABILITY_HIGH:
            new_mode = self._check_deep_sleep_eligible(history)
        elif stability >= self.STABILITY_MEDIUM:
            new_mode = 'normal'
        else:
            new_mode = 'high_freq'

        # Step 3: Determine which sensors to keep active
        self._update_active_sensors(stability, has_leak)

        # Step 4: Apply mode change
        old_mode = self.current_mode
        if new_mode != old_mode:
            self._transition_mode(new_mode)

        # Step 5: Calculate energy savings
        energy_saved = self._calculate_energy_savings()

        # Step 6: Save profile
        profile = self._save_profile(stability, energy_saved)

        return profile

    def _compute_stability(self, history):
        """
        Compute environmental stability index (0.0 - 1.0).
        
        Based on coefficient of variation (CV) of each sensor.
        Low CV = stable environment = high stability score.
        """
        sensor_names = ['water_level', 'flow_rate', 'soil_moisture', 'water_temperature']
        stabilities = []

        for sensor in sensor_names:
            values = [getattr(r, sensor) for r in history]
            if len(values) < 2:
                stabilities.append(0.5)
                continue

            mean_val = sum(values) / len(values)
            if abs(mean_val) < 0.01:
                # Near-zero mean → use absolute std instead of CV
                std_val = math.sqrt(sum((v - mean_val) ** 2 for v in values) / len(values))
                cv = std_val / max(self.MAX_CHANGE_RATES.get(sensor, 1.0), 0.01)
            else:
                std_val = math.sqrt(sum((v - mean_val) ** 2 for v in values) / len(values))
                cv = std_val / abs(mean_val)

            # Convert CV to stability: low CV → high stability
            sensor_stability = max(0.0, min(1.0, 1.0 - cv * 5))
            stabilities.append(sensor_stability)

        # Overall stability is the minimum (weakest link)
        # If ANY sensor is volatile, we need higher sampling
        return round(min(stabilities), 3)

    def _check_deep_sleep_eligible(self, history):
        """Check if conditions allow deep sleep mode."""
        hour = datetime.utcnow().hour

        # Night mode (10 PM - 6 AM): eligible for deep sleep if stable
        if hour >= 22 or hour < 6:
            return 'deep_sleep'

        # Daytime but very stable: use low power
        return 'low_power'

    def _update_active_sensors(self, stability, has_leak):
        """
        Determine which sensors need to be active.
        In very stable conditions, some sensors can be sampled less frequently.
        """
        if has_leak:
            # All sensors active during leak
            for s in self._active_sensors:
                self._active_sensors[s] = True
            return

        if stability >= self.STABILITY_HIGH:
            # Stable: temperature can be sampled less (changes slowly)
            self._active_sensors['water_temperature'] = False
            # Everything else stays active
        else:
            # All sensors active
            for s in self._active_sensors:
                self._active_sensors[s] = True

    def _transition_mode(self, new_mode):
        """Transition to a new power mode."""
        old_mode = self.current_mode
        self.current_mode = new_mode
        self.current_interval = self.MODE_INTERVALS[new_mode]

        self._mode_history.append({
            'timestamp': datetime.utcnow(),
            'from': old_mode,
            'to': new_mode
        })
        # Keep last 50 transitions
        self._mode_history = self._mode_history[-50:]

        # Alert on significant transitions
        if new_mode == 'high_freq' and old_mode in ('low_power', 'deep_sleep'):
            alert = Alert(
                alert_type='warning',
                icon='⚡',
                title='High-Frequency Sampling Activated',
                message=f'Switched from {old_mode} to {new_mode} mode. '
                        f'Sampling interval: {self.current_interval}s.'
            )
            db.session.add(alert)
            db.session.commit()

    def _calculate_energy_savings(self):
        """Calculate energy savings compared to constant high-frequency sampling."""
        baseline_power = self.MODE_POWER_MAH['high_freq']  # Worst case
        current_power = self.MODE_POWER_MAH[self.current_mode]

        if baseline_power > 0:
            savings_pct = ((baseline_power - current_power) / baseline_power) * 100
        else:
            savings_pct = 0.0

        self._total_energy_saved_pct = round(savings_pct, 1)
        return savings_pct

    def _estimate_battery_hours(self):
        """Estimate remaining battery life based on current power mode."""
        current_power = self.MODE_POWER_MAH[self.current_mode]
        if current_power > 0:
            return round(self.BATTERY_CAPACITY_MAH / current_power, 1)
        return 9999.0

    def _save_profile(self, stability, energy_saved):
        """Save current energy profile to database."""
        # Debounce: save at most once per 5 minutes
        existing = EnergyProfile.query.filter(
            EnergyProfile.timestamp >= datetime.utcnow() - timedelta(minutes=5)
        ).first()

        if not existing:
            profile = EnergyProfile(
                sampling_interval_s=self.current_interval,
                environmental_stability=stability,
                power_mode=self.current_mode,
                estimated_battery_hours=self._estimate_battery_hours(),
                energy_saved_pct=energy_saved,
                active_sensors=json.dumps(self._active_sensors)
            )
            db.session.add(profile)
            db.session.commit()

        return self._get_current_profile()

    def _get_current_profile(self):
        """Get current energy optimization profile."""
        return {
            'current_mode': self.current_mode,
            'sampling_interval_s': self.current_interval,
            'environmental_stability': self.current_stability,
            'estimated_battery_hours': self._estimate_battery_hours(),
            'energy_saved_pct': self._total_energy_saved_pct,
            'active_sensors': dict(self._active_sensors),
            'mode_description': {
                'high_freq': 'Maximum monitoring — event in progress',
                'normal': 'Standard monitoring — moderate activity',
                'low_power': 'Reduced monitoring — stable environment',
                'deep_sleep': 'Minimal monitoring — night/ultra-stable',
            }.get(self.current_mode, ''),
            'power_consumption_mah': self.MODE_POWER_MAH[self.current_mode],
        }

    def get_energy_summary(self, hours=24):
        """Get energy optimization history and statistics."""
        since = datetime.utcnow() - timedelta(hours=hours)
        profiles = EnergyProfile.query.filter(
            EnergyProfile.timestamp >= since
        ).order_by(EnergyProfile.timestamp.desc()).limit(100).all()

        mode_distribution = {}
        for p in profiles:
            mode_distribution[p.power_mode] = mode_distribution.get(p.power_mode, 0) + 1

        avg_savings = sum(p.energy_saved_pct for p in profiles) / max(len(profiles), 1)
        avg_stability = sum(p.environmental_stability for p in profiles) / max(len(profiles), 1)

        return {
            'current': self._get_current_profile(),
            'mode_distribution': mode_distribution,
            'average_energy_saved_pct': round(avg_savings, 1),
            'average_stability': round(avg_stability, 3),
            'mode_transitions': len(self._mode_history),
            'profiles': [p.to_dict() for p in profiles[:20]],
            'estimated_battery_hours': self._estimate_battery_hours(),
        }


# Singleton instance
energy_optimizer = EnergyOptimizer()
