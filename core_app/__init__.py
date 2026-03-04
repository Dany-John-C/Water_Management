from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

db = SQLAlchemy()

def create_app(config_class='config.config.Config'):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    CORS(app)

    # Register Blueprints
    from core_app.routes.main import main_bp
    from core_app.routes.sensors import sensors_bp
    from core_app.routes.alerts import alerts_bp
    from core_app.routes.metrics import metrics_bp
    from core_app.routes.intelligence import intelligence_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(sensors_bp, url_prefix='/api/sensors')
    app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
    app.register_blueprint(metrics_bp, url_prefix='/api/metrics')
    app.register_blueprint(intelligence_bp, url_prefix='/api/intelligence')
    
    with app.app_context():
        import core_app.models.models
        db.create_all()

    return app
