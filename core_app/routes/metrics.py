from flask import Blueprint, jsonify
from core_app.models.models import SystemMetrics

metrics_bp = Blueprint('metrics', __name__)

@metrics_bp.route('/current', methods=['GET'])
def get_current_metrics():
    """Get the latest system metrics"""
    latest = SystemMetrics.query.order_by(SystemMetrics.timestamp.desc()).first()
    if not latest:
        return jsonify({'error': 'No metrics data available'}), 404
    
    return jsonify(latest.to_dict())
