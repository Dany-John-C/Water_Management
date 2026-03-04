"""
Patent Claim 2: Weather-Adaptive Irrigation Scheduling Engine

A system that dynamically adjusts irrigation schedules by: fetching weather 
forecast data; computing an evapotranspiration estimate from temperature, 
humidity, and rainfall probability; and modifying the irrigation duty cycle 
proportionally to predicted natural water availability.

Uses the Hargreaves evapotranspiration model (simplified) combined with 
real-time weather forecasts to compute optimal irrigation percentages.
"""

import requests
import math
from datetime import datetime, timedelta
from core_app.models.models import WeatherData, SensorReading
from core_app import db


class WeatherIrrigationEngine:
    """
    Fetches weather forecasts and computes optimal irrigation schedules.
    
    Novel method:
    1. Pull weather forecast (temp, humidity, rain probability, wind)
    2. Compute reference evapotranspiration (ET₀) using Hargreaves equation
    3. Factor in rain probability to estimate natural water input
    4. Compute irrigation recommendation as % of normal
    5. Track cumulative water savings
    """

    # OpenWeatherMap free API (user should replace with their key)
    API_KEY = "demo"  # Replace with real key for production
    DEFAULT_LAT = 28.6139   # Default: New Delhi
    DEFAULT_LON = 77.2090

    # Irrigation parameters
    NORMAL_IRRIGATION_LITERS_PER_HOUR = 50.0  # Baseline irrigation rate
    RAIN_ABSORPTION_FACTOR = 0.7  # 70% of rain is usable by soil
    
    # Hargreaves equation constants
    SOLAR_CONSTANT = 0.0820  # MJ m⁻² min⁻¹

    def __init__(self, api_key=None, lat=None, lon=None):
        if api_key:
            self.API_KEY = api_key
        if lat:
            self.DEFAULT_LAT = lat
        if lon:
            self.DEFAULT_LON = lon

    def fetch_weather(self):
        """
        Fetch current weather and forecast from OpenWeatherMap API.
        Falls back to simulated data if API key is not set or API fails.
        """
        if self.API_KEY == "demo":
            return self._simulate_weather()

        try:
            # Current weather
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?lat={self.DEFAULT_LAT}&lon={self.DEFAULT_LON}"
                f"&appid={self.API_KEY}&units=metric"
            )
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return self._simulate_weather()

            data = resp.json()

            weather = {
                'temperature': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed'],
                'description': data['weather'][0]['description'],
                'rain_volume_mm': data.get('rain', {}).get('1h', 0.0),
            }

            # Forecast for rain probability
            forecast_url = (
                f"https://api.openweathermap.org/data/2.5/forecast"
                f"?lat={self.DEFAULT_LAT}&lon={self.DEFAULT_LON}"
                f"&appid={self.API_KEY}&units=metric&cnt=8"
            )
            forecast_resp = requests.get(forecast_url, timeout=5)
            if forecast_resp.status_code == 200:
                forecast_data = forecast_resp.json()
                rain_count = sum(
                    1 for item in forecast_data['list']
                    if 'rain' in item or any(
                        w['main'].lower() in ('rain', 'drizzle', 'thunderstorm')
                        for w in item['weather']
                    )
                )
                weather['rain_probability'] = rain_count / len(forecast_data['list'])
                # Sum expected rain
                total_rain = sum(
                    item.get('rain', {}).get('3h', 0.0)
                    for item in forecast_data['list']
                )
                weather['rain_volume_mm'] = max(weather['rain_volume_mm'], total_rain)
            else:
                weather['rain_probability'] = 0.1

            return weather

        except Exception as e:
            print(f"Weather API error: {e}, using simulated data")
            return self._simulate_weather()

    def _simulate_weather(self):
        """Generate realistic simulated weather data for demo/testing."""
        import random
        hour = datetime.now().hour

        # Temperature varies by time of day
        base_temp = 25 + 8 * math.sin((hour - 6) * math.pi / 12)
        temp = base_temp + random.uniform(-3, 3)

        # Humidity inversely related to temperature
        humidity = max(20, min(95, 70 - (temp - 25) * 2 + random.uniform(-10, 10)))

        # Rain probability varies
        rain_prob = random.uniform(0, 0.6)
        rain_mm = rain_prob * random.uniform(0, 15) if rain_prob > 0.3 else 0

        descriptions = [
            'clear sky', 'few clouds', 'scattered clouds',
            'broken clouds', 'light rain', 'overcast clouds'
        ]
        if rain_prob > 0.5:
            desc = random.choice(['light rain', 'moderate rain', 'rain expected'])
        elif rain_prob > 0.3:
            desc = random.choice(['broken clouds', 'overcast clouds'])
        else:
            desc = random.choice(['clear sky', 'few clouds', 'scattered clouds'])

        return {
            'temperature': round(temp, 1),
            'humidity': round(humidity, 1),
            'rain_probability': round(rain_prob, 2),
            'rain_volume_mm': round(rain_mm, 1),
            'wind_speed': round(random.uniform(0.5, 8.0), 1),
            'description': desc
        }

    def compute_evapotranspiration(self, temp_c, humidity, wind_speed):
        """
        Simplified Hargreaves reference evapotranspiration (ET₀).
        
        ET₀ = 0.0023 × (T_mean + 17.8) × (T_max - T_min)^0.5 × Ra
        
        Since we only have current temp, we estimate T_max/T_min from 
        humidity (high humidity = smaller diurnal range).
        """
        # Estimate diurnal temperature range from humidity
        diurnal_range = max(2, 15 - humidity * 0.1)  # Higher humidity = smaller range
        t_max = temp_c + diurnal_range / 2
        t_min = temp_c - diurnal_range / 2

        # Extraterrestrial radiation estimate (simplified, ~latitude dependent)
        # For mid-latitudes, Ra ≈ 15-25 MJ/m²/day
        day_of_year = datetime.now().timetuple().tm_yday
        ra = 20 + 5 * math.sin((day_of_year - 80) * 2 * math.pi / 365)

        # Hargreaves equation
        et0 = 0.0023 * (temp_c + 17.8) * math.sqrt(max(0, t_max - t_min)) * ra

        # Wind adjustment (higher wind = more evaporation)
        wind_factor = 1.0 + wind_speed * 0.04
        et0 *= wind_factor

        return max(0, round(et0, 2))  # mm/day

    def compute_irrigation_recommendation(self, weather, current_soil_moisture=None):
        """
        THE CORE NOVEL ALGORITHM:
        
        Computes what percentage of normal irrigation should be applied,
        considering:
        1. Evapotranspiration demand (how much water plants need)
        2. Rain forecast (natural water supply)
        3. Current soil moisture (existing reserves)
        
        Returns: 0% (skip entirely) to 150% (extra hot/dry, irrigate more)
        """
        et0 = self.compute_evapotranspiration(
            weather['temperature'],
            weather['humidity'],
            weather['wind_speed']
        )

        # Expected natural water input from rain (mm)
        expected_rain = weather['rain_volume_mm'] * self.RAIN_ABSORPTION_FACTOR
        # Weight by probability
        effective_rain = expected_rain * weather['rain_probability']

        # Net water deficit (mm/day)
        # Positive = plants need more water than rain provides
        net_deficit = et0 - effective_rain

        # Base recommendation: proportion of normal irrigation
        # If deficit = ET₀ (no rain), use 100% irrigation
        # If deficit < 0 (rain > evaporation), reduce irrigation
        if et0 > 0:
            recommendation_pct = (net_deficit / et0) * 100
        else:
            recommendation_pct = 50.0  # Minimal ET, reduce irrigation

        # Adjust for current soil moisture if available
        if current_soil_moisture is not None:
            if current_soil_moisture > 70:
                # Soil already wet, reduce further
                recommendation_pct *= 0.5
            elif current_soil_moisture > 50:
                recommendation_pct *= 0.8
            elif current_soil_moisture < 25:
                # Very dry, boost irrigation
                recommendation_pct *= 1.3

        # Clamp to valid range
        recommendation_pct = max(0, min(150, recommendation_pct))

        # Calculate water savings
        water_saved = self.NORMAL_IRRIGATION_LITERS_PER_HOUR * (100 - recommendation_pct) / 100

        return {
            'evapotranspiration': et0,
            'effective_rain': round(effective_rain, 2),
            'net_deficit': round(net_deficit, 2),
            'irrigation_recommendation': round(recommendation_pct, 1),
            'water_saved_liters': round(max(0, water_saved), 1),
            'reasoning': self._build_reasoning(
                et0, weather, effective_rain, recommendation_pct, current_soil_moisture
            )
        }

    def _build_reasoning(self, et0, weather, effective_rain, rec_pct, soil_moisture):
        """Build human-readable reasoning for the recommendation."""
        parts = []

        if weather['rain_probability'] > 0.5:
            parts.append(f"High rain probability ({weather['rain_probability']*100:.0f}%) — "
                        f"expecting ~{weather['rain_volume_mm']:.1f}mm")
        elif weather['rain_probability'] > 0.2:
            parts.append(f"Moderate rain chance ({weather['rain_probability']*100:.0f}%)")
        else:
            parts.append("Low rain probability — irrigation needed")

        parts.append(f"ET₀ demand: {et0:.1f}mm/day")

        if soil_moisture is not None:
            if soil_moisture > 70:
                parts.append(f"Soil already moist ({soil_moisture:.0f}%)")
            elif soil_moisture < 30:
                parts.append(f"Soil is dry ({soil_moisture:.0f}%) — priority irrigation")

        if rec_pct < 20:
            parts.append("RECOMMENDATION: Skip irrigation cycle")
        elif rec_pct < 60:
            parts.append(f"RECOMMENDATION: Reduce to {rec_pct:.0f}% of normal")
        elif rec_pct > 110:
            parts.append(f"RECOMMENDATION: Increase to {rec_pct:.0f}% of normal")
        else:
            parts.append("RECOMMENDATION: Normal irrigation")

        return " | ".join(parts)

    def update_and_recommend(self):
        """
        Full pipeline: fetch weather → compute recommendation → save to DB.
        Called periodically (e.g., every 30 minutes).
        """
        weather = self.fetch_weather()

        # Get current soil moisture
        latest_reading = SensorReading.query.order_by(
            SensorReading.timestamp.desc()
        ).first()
        soil_moisture = latest_reading.soil_moisture if latest_reading else None

        result = self.compute_irrigation_recommendation(weather, soil_moisture)

        # Save to database
        weather_record = WeatherData(
            temperature=weather['temperature'],
            humidity=weather['humidity'],
            rain_probability=weather['rain_probability'],
            rain_volume_mm=weather['rain_volume_mm'],
            wind_speed=weather['wind_speed'],
            description=weather['description'],
            evapotranspiration=result['evapotranspiration'],
            irrigation_recommendation=result['irrigation_recommendation'],
            water_saved_liters=result['water_saved_liters']
        )
        db.session.add(weather_record)
        db.session.commit()

        return {
            'weather': weather,
            'recommendation': result,
            'soil_moisture': soil_moisture
        }

    def get_savings_summary(self):
        """Calculate total water saved by weather-adaptive scheduling."""
        all_records = WeatherData.query.all()
        total_saved = sum(r.water_saved_liters for r in all_records)
        avg_recommendation = (
            sum(r.irrigation_recommendation for r in all_records) / len(all_records)
            if all_records else 100
        )

        return {
            'total_water_saved_liters': round(total_saved, 1),
            'average_irrigation_pct': round(avg_recommendation, 1),
            'data_points': len(all_records),
            'efficiency_gain': round(100 - avg_recommendation, 1)
        }


# Singleton instance
weather_engine = WeatherIrrigationEngine()
