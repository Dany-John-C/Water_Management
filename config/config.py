import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '../instance/water_management.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Alert Thresholds
    WATER_LEVEL_MIN = float(os.environ.get('WATER_LEVEL_MIN', 20))
    WATER_LEVEL_MAX = float(os.environ.get('WATER_LEVEL_MAX', 95))
    FLOW_RATE_MAX = float(os.environ.get('FLOW_RATE_MAX', 50))
    SOIL_MOISTURE_MIN = float(os.environ.get('SOIL_MOISTURE_MIN', 30))
    SOIL_MOISTURE_MAX = float(os.environ.get('SOIL_MOISTURE_MAX', 90))
    WATER_TEMP_MIN = float(os.environ.get('WATER_TEMP_MIN', 10))
    WATER_TEMP_MAX = float(os.environ.get('WATER_TEMP_MAX', 35))
