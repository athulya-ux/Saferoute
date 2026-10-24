import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'safe-route-super-secret-key-women-safety-2026')
    DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1')

    # Database configuration
    # Auto mode: attempts MySQL first; if unavailable, uses SQLite smoothly
    DB_TYPE = os.environ.get('DB_TYPE', 'auto') # 'mysql', 'sqlite', or 'auto'
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'saferoute_db')
    
    SQLITE_PATH = os.path.join(BASE_DIR, 'database', 'saferoute.sqlite')

    # Routing & Overpass APIs
    OVERPASS_URL = os.environ.get('OVERPASS_URL', 'https://overpass-api.de/api/interpreter')
    OSRM_URL = os.environ.get('OSRM_URL', 'https://router.project-osrm.org/route/v1/walking')

    # Safety Scoring Weights (total base = 100)
    WEIGHT_LIGHTING = 30
    WEIGHT_CROWD = 25
    WEIGHT_HELP_POINTS = 25
    PENALTY_NIGHT = 15
    PENALTY_EVENING = 5
    
    # Incident Expiry Days
    INCIDENT_EXPIRY_DAYS = 30

    # Rate Limiting & Verification
    MAX_OTP_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15
    OTP_EXPIRY_SECONDS = 300

    # Walk Together Radius (meters)
    WALK_TOGETHER_RADIUS_M = 1000
