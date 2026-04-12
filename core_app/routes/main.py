from flask import Blueprint, render_template, request, jsonify
from core_app.services.pump_control import pump_controller

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/api/motor', methods=['GET', 'POST'])
def control_motor():
    if request.method == 'POST':
        data = request.json
        if data and 'state' in data:
            if data['state'] in ['on', 'off']:
                pump_controller.manual_override(data['state'])
                return jsonify({'success': True, 'motor_state': pump_controller.state})
        return jsonify({'success': False, 'error': 'Invalid state provided'}), 400
    
    return jsonify({'motor_state': pump_controller.state})
