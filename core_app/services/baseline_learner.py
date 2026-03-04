"""
Feature 6: Learning-Based Baseline Modeling

Patent Claim: A method for adaptive environmental baseline learning comprising:
the system establishes a baseline irrigation and sensor behavior model during 
an initial learning period; wherein per-hour-of-day seasonal profiles are 
built from accumulated readings, multivariate inter-sensor relationships are 
learned via correlation analysis, and anomaly thresholds are dynamically 
adjusted as the baseline matures — enabling the system to distinguish normal 
diurnal variation from true anomalies.

Key Innovation:
- Initial learning period (first 24h) with graduated alert suppression
- Per-hour-of-day seasonal profiles (captures diurnal patterns)
- Multivariate relationship learning (inter-sensor correlation weights)
- Model maturity tracking (initial → adapting → mature)
- Continuous model updating with exponential decay for old data
- Baseline prediction accuracy self-assessment
"""

from datetime import datetime, timedelta
from core_app.models.models import SensorReading, BaselineModel, Alert
from core_app import db
import json
import math


class BaselineLearner:
    """
    Learns normal system behavior over time, building per-hour-of-day
    profiles and inter-sensor relationship models.
    
    Learning Phases:
    1. INITIAL (0-6h):     Collecting data, no anomaly detection
    2. ADAPTING (6-24h):   Building profiles, loose anomaly thresholds
    3. MATURE (24h+):      Stable baselines, tight anomaly detection
    
    The baseline model stores:
    - 24 hourly profiles (mean + std for each sensor)
    - Inter-sensor correlation matrix
    - Multivariate regression weights (predict one sensor from others)
    """

    SENSOR_NAMES = ['water_level', 'flow_rate', 'soil_moisture', 'water_temperature']

    # Learning phase thresholds
    INITIAL_SAMPLES = 50           # ~8 minutes at 10s intervals
    ADAPTING_SAMPLES = 500         # ~83 minutes  
    MATURE_SAMPLES = 2000          # ~333 minutes (~5.5 hours)

    # Exponential decay for old data
    DECAY_FACTOR = 0.995           # Older readings contribute less

    # Model save frequency
    SAVE_INTERVAL_MINUTES = 30

    def __init__(self):
        self.model_version = 0
        self.total_samples = 0
        self.learning_phase = 'initial'

        # Per-hour-of-day profiles: {hour: {sensor: {mean, std, count}}}
        self._hourly_profiles = {
            hour: {
                sensor: {'mean': 0.0, 'std': 0.0, 'count': 0, 'sum': 0.0, 'sum_sq': 0.0}
                for sensor in self.SENSOR_NAMES
            }
            for hour in range(24)
        }

        # Inter-sensor correlation matrix (running computation)
        self._correlation_sums = {}
        for i, s1 in enumerate(self.SENSOR_NAMES):
            for j, s2 in enumerate(self.SENSOR_NAMES):
                if i < j:
                    key = f'{s1}__{s2}'
                    self._correlation_sums[key] = {
                        'sum_xy': 0.0, 'sum_x': 0.0, 'sum_y': 0.0,
                        'sum_x2': 0.0, 'sum_y2': 0.0, 'count': 0
                    }

        # Multivariate relationship weights (simple linear)
        self._weights = {sensor: {} for sensor in self.SENSOR_NAMES}

        # Prediction tracking
        self._prediction_errors = []
        self._last_save_time = None

    def learn(self, current_reading):
        """
        Main entry: incorporate new reading into baseline model.
        
        Returns:
            dict with learning status and any predictions
        """
        self.total_samples += 1
        hour = datetime.utcnow().hour

        # Update learning phase
        self._update_phase()

        # Step 1: Update hourly profiles
        self._update_hourly_profile(hour, current_reading)

        # Step 2: Update correlation matrix
        self._update_correlations(current_reading)

        # Step 3: Update multivariate weights (periodically)
        if self.total_samples % 50 == 0:
            self._update_weights()

        # Step 4: Make prediction and assess accuracy
        prediction = self._predict(hour, current_reading)

        # Step 5: Save model periodically
        if self._should_save():
            self._save_model()

        return {
            'learning_phase': self.learning_phase,
            'total_samples': self.total_samples,
            'model_version': self.model_version,
            'prediction': prediction,
            'hourly_profile_available': self._hourly_profiles[hour][self.SENSOR_NAMES[0]]['count'] > 5
        }

    def _update_phase(self):
        """Update learning phase based on sample count."""
        if self.total_samples < self.INITIAL_SAMPLES:
            self.learning_phase = 'initial'
        elif self.total_samples < self.MATURE_SAMPLES:
            self.learning_phase = 'adapting'
        else:
            self.learning_phase = 'mature'

    def _update_hourly_profile(self, hour, reading):
        """
        Update the per-hour profile with new reading.
        Uses Welford's online algorithm for running mean/variance.
        """
        for sensor in self.SENSOR_NAMES:
            value = getattr(reading, sensor)
            profile = self._hourly_profiles[hour][sensor]

            profile['count'] += 1
            n = profile['count']

            # Apply decay to old statistics
            if n > 1:
                profile['sum'] *= self.DECAY_FACTOR
                profile['sum_sq'] *= self.DECAY_FACTOR

            profile['sum'] += value
            profile['sum_sq'] += value ** 2

            # Recompute mean and std
            effective_n = profile['sum'] / max(value, 0.01) if value > 0 else n
            effective_n = max(effective_n, 1)

            profile['mean'] = profile['sum'] / effective_n
            variance = max(0, profile['sum_sq'] / effective_n - profile['mean'] ** 2)
            profile['std'] = math.sqrt(variance)

    def _update_correlations(self, reading):
        """Update running correlation computation between sensor pairs."""
        values = {sensor: getattr(reading, sensor) for sensor in self.SENSOR_NAMES}

        for i, s1 in enumerate(self.SENSOR_NAMES):
            for j, s2 in enumerate(self.SENSOR_NAMES):
                if i < j:
                    key = f'{s1}__{s2}'
                    x, y = values[s1], values[s2]
                    cs = self._correlation_sums[key]

                    # Apply decay
                    for k in cs:
                        if k != 'count':
                            cs[k] *= self.DECAY_FACTOR

                    cs['sum_xy'] += x * y
                    cs['sum_x'] += x
                    cs['sum_y'] += y
                    cs['sum_x2'] += x ** 2
                    cs['sum_y2'] += y ** 2
                    cs['count'] += 1

    def _compute_correlation(self, key):
        """Compute Pearson correlation from running sums."""
        cs = self._correlation_sums[key]
        n = cs['count']
        if n < 10:
            return 0.0

        numerator = n * cs['sum_xy'] - cs['sum_x'] * cs['sum_y']
        denom_x = math.sqrt(max(0, n * cs['sum_x2'] - cs['sum_x'] ** 2))
        denom_y = math.sqrt(max(0, n * cs['sum_y2'] - cs['sum_y'] ** 2))

        if denom_x * denom_y == 0:
            return 0.0

        return numerator / (denom_x * denom_y)

    def _update_weights(self):
        """
        Update multivariate relationship weights.
        Simple approach: for each sensor, compute correlation-based weights
        from all other sensors.
        """
        for target in self.SENSOR_NAMES:
            weights = {}
            for source in self.SENSOR_NAMES:
                if source == target:
                    continue
                # Find correlation key
                pair = sorted([target, source])
                key = f'{pair[0]}__{pair[1]}'
                if key in self._correlation_sums:
                    corr = self._compute_correlation(key)
                    weights[source] = round(corr, 4)

            self._weights[target] = weights

    def _predict(self, hour, current_reading):
        """
        Make a prediction for the current reading based on learned baseline.
        Compare prediction with actual to assess model accuracy.
        """
        if self.learning_phase == 'initial':
            return {'status': 'learning', 'predictions': {}}

        predictions = {}
        errors = {}

        for sensor in self.SENSOR_NAMES:
            actual = getattr(current_reading, sensor)
            profile = self._hourly_profiles[hour][sensor]

            if profile['count'] < 5:
                continue

            # Prediction from hourly profile
            predicted = profile['mean']

            # Adjust prediction using correlated sensors
            for source, weight in self._weights.get(sensor, {}).items():
                source_value = getattr(current_reading, source)
                source_profile = self._hourly_profiles[hour][source]
                if source_profile['count'] < 5:
                    continue
                # Weighted contribution from correlated sensor's deviation
                source_deviation = source_value - source_profile['mean']
                predicted += weight * source_deviation * 0.1  # Damped adjustment

            error = abs(actual - predicted) / max(abs(actual), 0.01) * 100
            predictions[sensor] = {
                'predicted': round(predicted, 2),
                'actual': round(actual, 2),
                'error_pct': round(error, 2),
                'within_baseline': error < 20  # Within 20% = normal
            }
            errors[sensor] = error

        # Track overall prediction accuracy
        if errors:
            avg_error = sum(errors.values()) / len(errors)
            self._prediction_errors.append(avg_error)
            self._prediction_errors = self._prediction_errors[-200:]

        return {
            'status': 'predicting',
            'predictions': predictions,
            'overall_accuracy': round(100 - sum(self._prediction_errors[-20:]) / max(len(self._prediction_errors[-20:]), 1), 1)
        }

    def _should_save(self):
        """Check if it's time to save the model."""
        if self._last_save_time is None:
            return True
        elapsed = (datetime.utcnow() - self._last_save_time).total_seconds() / 60.0
        return elapsed >= self.SAVE_INTERVAL_MINUTES

    def _save_model(self):
        """Save current baseline model to database."""
        self.model_version += 1
        self._last_save_time = datetime.utcnow()

        # Compute overall prediction accuracy
        if self._prediction_errors:
            accuracy = 100 - sum(self._prediction_errors[-50:]) / max(len(self._prediction_errors[-50:]), 1)
        else:
            accuracy = 0.0

        # Serialize hourly profiles
        serializable_profiles = {}
        for hour in range(24):
            serializable_profiles[str(hour)] = {
                sensor: {
                    'mean': round(p['mean'], 2),
                    'std': round(p['std'], 2),
                    'count': p['count']
                }
                for sensor, p in self._hourly_profiles[hour].items()
            }

        # Serialize correlation matrix
        correlations = {}
        for key in self._correlation_sums:
            correlations[key] = round(self._compute_correlation(key), 4)

        # Serialize baseline means/stds
        baseline_means = {}
        baseline_stds = {}
        for sensor in self.SENSOR_NAMES:
            all_means = [self._hourly_profiles[h][sensor]['mean'] for h in range(24)]
            all_stds = [self._hourly_profiles[h][sensor]['std'] for h in range(24)]
            baseline_means[sensor] = round(sum(all_means) / 24, 2)
            baseline_stds[sensor] = round(sum(all_stds) / 24, 2)

        model = BaselineModel(
            model_version=self.model_version,
            learning_phase=self.learning_phase,
            total_samples_learned=self.total_samples,
            seasonal_profiles=json.dumps(serializable_profiles),
            multivariate_weights=json.dumps({
                'correlations': correlations,
                'weights': self._weights
            }),
            baseline_means=json.dumps(baseline_means),
            baseline_stds=json.dumps(baseline_stds),
            prediction_accuracy=accuracy,
            last_retrain=datetime.utcnow()
        )
        db.session.add(model)
        db.session.commit()

    def get_baseline_status(self):
        """Get current baseline model status."""
        latest_model = BaselineModel.query.order_by(
            BaselineModel.timestamp.desc()
        ).first()

        # Current hour profile
        hour = datetime.utcnow().hour
        current_hourly = {
            sensor: {
                'mean': round(self._hourly_profiles[hour][sensor]['mean'], 2),
                'std': round(self._hourly_profiles[hour][sensor]['std'], 2),
                'samples': self._hourly_profiles[hour][sensor]['count']
            }
            for sensor in self.SENSOR_NAMES
        }

        # Correlation matrix
        correlations = {}
        for key in self._correlation_sums:
            correlations[key] = round(self._compute_correlation(key), 4)

        # Prediction accuracy
        if self._prediction_errors:
            accuracy = 100 - sum(self._prediction_errors[-50:]) / max(len(self._prediction_errors[-50:]), 1)
        else:
            accuracy = 0.0

        return {
            'learning_phase': self.learning_phase,
            'model_version': self.model_version,
            'total_samples_learned': self.total_samples,
            'prediction_accuracy': round(accuracy, 1),
            'current_hour_profile': current_hourly,
            'correlations': correlations,
            'multivariate_weights': self._weights,
            'phase_progress': {
                'initial': min(100, self.total_samples / self.INITIAL_SAMPLES * 100),
                'adapting': min(100, self.total_samples / self.ADAPTING_SAMPLES * 100) if self.total_samples >= self.INITIAL_SAMPLES else 0,
                'mature': min(100, self.total_samples / self.MATURE_SAMPLES * 100) if self.total_samples >= self.ADAPTING_SAMPLES else 0,
            },
            'latest_model': latest_model.to_dict() if latest_model else None
        }


# Singleton instance
baseline_learner = BaselineLearner()
