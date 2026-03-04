from core_app.models.models import Alert
from core_app import db
from flask import current_app

def check_and_create_alerts(reading):
    """Centralized logic to check sensor readings and create alerts based on config thresholds."""
    
    # Load configuration parameters
    wl_min = current_app.config['WATER_LEVEL_MIN']
    wl_max = current_app.config['WATER_LEVEL_MAX']
    fr_max = current_app.config['FLOW_RATE_MAX']
    sm_min = current_app.config['SOIL_MOISTURE_MIN']
    sm_max = current_app.config['SOIL_MOISTURE_MAX']
    temp_min = current_app.config['WATER_TEMP_MIN']
    temp_max = current_app.config['WATER_TEMP_MAX']

    alerts_to_create = []
    
    if reading.water_level < wl_min:
        alerts_to_create.append({
            'type': 'danger', 'icon': '🚨', 'title': 'Tank Level Critical', 
            'message': f'Water level critically low ({reading.water_level}%)'
        })
    elif reading.water_level > wl_max:
        alerts_to_create.append({
            'type': 'danger', 'icon': '🚨', 'title': 'Tank Overflow Warning', 
            'message': f'Water level critically high ({reading.water_level}%)'
        })
    
    if reading.flow_rate > fr_max:
        alerts_to_create.append({
            'type': 'warning', 'icon': '⚠️', 'title': 'High Flow Rate Detected', 
            'message': f'Flow rate is {reading.flow_rate}L/min (Max: {fr_max})'
        })
    
    if reading.soil_moisture < sm_min:
        alerts_to_create.append({
            'type': 'warning', 'icon': '🌱', 'title': 'Low Soil Moisture', 
            'message': f'Irrigation needed ({reading.soil_moisture}%)'
        })
    elif reading.soil_moisture > sm_max:
        alerts_to_create.append({
            'type': 'warning', 'icon': '🌱', 'title': 'High Soil Moisture', 
            'message': f'Soil is over-saturated ({reading.soil_moisture}%)'
        })
        
    if reading.water_temperature > temp_max:
        alerts_to_create.append({
            'type': 'warning', 'icon': '🌡️', 'title': 'High Water Temperature', 
            'message': f'Temperature exceeds optimal range ({reading.water_temperature}°C)'
        })
    elif reading.water_temperature < temp_min:
        alerts_to_create.append({
            'type': 'warning', 'icon': '❄️', 'title': 'Low Water Temperature', 
            'message': f'Risk of freezing detected ({reading.water_temperature}°C)'
        })
    
    # Avoid inserting spam if the identical alert is already active
    for idx, alert_data in enumerate(alerts_to_create):
        existing_alert = Alert.query.filter_by(
            title=alert_data['title'], 
            is_active=True
        ).order_by(Alert.timestamp.desc()).first()
        
        # Debounce: Do not create alert if identical one exists and hasn't been cleared
        if not existing_alert:
            new_alert = Alert(
                alert_type=alert_data['type'],
                icon=alert_data['icon'],
                title=alert_data['title'],
                message=alert_data['message']
            )
            db.session.add(new_alert)
            
    if alerts_to_create:
        db.session.commit()
