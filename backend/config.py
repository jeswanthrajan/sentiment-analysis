import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'sentimentscope-secret-key')
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:root@localhost/sentiment_analysis')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
    LM_STUDIO_API_URL = os.getenv('LM_STUDIO_API_URL', 'http://localhost:1234/v1/chat/completions')
    USE_LOCAL_LLM = os.getenv('USE_LOCAL_LLM', 'false').lower() == 'true'
    MAX_REVIEWS_PER_PRODUCT = int(os.getenv('MAX_REVIEWS_PER_PRODUCT', '50'))
    SCRAPING_DELAY = int(os.getenv('SCRAPING_DELAY', '2'))

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'sqlite:///test.db')

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Get current configuration
def get_config():
    """Get the current configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
