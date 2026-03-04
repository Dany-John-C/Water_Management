from flask import Blueprint, jsonify
from core_app.models.models import Alert

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('', methods=['GET'])
def get_alerts():
    """Get recent alerts"""
    alerts = Alert.query.filter_by(is_active=True).order_by(
        Alert.timestamp.desc()
    ).limit(10).all()
    
    return jsonify([alert.to_dict() for alert in alerts])
