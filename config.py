import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load .env if present
load_dotenv(BASE_DIR / '.env')


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'exam_proctoring_super_secret_key_2026_deepmind')
    
    # Database configuration (SQLite default, PostgreSQL ready)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f"sqlite:///{BASE_DIR / 'instance' / 'exam.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload configurations
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', str(BASE_DIR / 'uploads'))
    SCREENSHOT_FOLDER = str(BASE_DIR / 'uploads' / 'screenshots')
    PROFILE_FOLDER = str(BASE_DIR / 'uploads' / 'profiles')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16 MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    # Proctoring configurations
    PROCTORING_ENABLED = os.getenv('PROCTORING_ENABLED', 'true').lower() in ('true', '1', 't')
    FRAME_INTERVAL = float(os.getenv('FRAME_INTERVAL', '2.0'))  # Process 1 frame every 2.0s
    DEMO_MODE = os.getenv('DEMO_MODE', 'false').lower() in ('true', '1', 't')
    
    # Risk scoring thresholds
    RISK_THRESHOLD_LOW = int(os.getenv('RISK_THRESHOLD_LOW', 20))
    RISK_THRESHOLD_MEDIUM = int(os.getenv('RISK_THRESHOLD_MEDIUM', 50))
    RISK_THRESHOLD_HIGH = int(os.getenv('RISK_THRESHOLD_HIGH', 80))

    # Security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = False  # Allows smooth REST/AJAX without token friction while protecting sessions


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    PROCTORING_ENABLED = False
    DEMO_MODE = True


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
