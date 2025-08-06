# Configuration file for AI Essay Revision Application

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'essay_revision')
    
    # Database configuration dictionary for compatibility
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'essay_revision'),
        'charset': 'utf8mb4'
    }
    
    # OpenAI configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Upload configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'docx', 'txt'}
    
    # Error handling configuration
    ERROR_HANDLING = {
        'db_retry_attempts': 3,
        'db_retry_delay': 1,  # seconds
        'ai_retry_attempts': 3,
        'ai_retry_delay': 2,  # seconds
        'file_max_text_length': 50000,  # characters
        'file_min_text_length': 50,  # characters
        'fallback_analysis_enabled': True
    }
    
    # Performance configuration
    PERFORMANCE = {
        # Cache configuration
        'cache_enabled': True,
        'cache_ttl': 3600,  # 1 hour in seconds
        'cache_max_size': 1000,  # Maximum number of cached analyses
        
        # Database connection pooling
        'db_pool_enabled': True,
        'db_pool_size': 10,  # Maximum number of connections in pool
        'db_pool_max_overflow': 20,  # Additional connections beyond pool_size
        'db_pool_timeout': 30,  # Timeout for getting connection from pool
        'db_pool_recycle': 3600,  # Recycle connections after 1 hour
        
        # File handling
        'file_streaming_enabled': True,
        'file_chunk_size': 8192,  # 8KB chunks for streaming
        'file_memory_threshold': 1024 * 1024,  # 1MB - stream files larger than this
    }
    
    # Temporary storage configuration
    TEMP_STORAGE = {
        'directory': 'temp_data',  # Directory for temporary files
        'ttl': 3600,  # Time to live in seconds (1 hour)
        'cleanup_interval': 3600,  # Cleanup interval in seconds (1 hour)
        'max_file_size': 10 * 1024 * 1024,  # 10MB max per temp file
    }
    
    # Essay analysis configuration
    ESSAY_TYPES = [
        'argumentative',
        'narrative', 
        'literary_analysis',
        'hybrid'
    ]
    
    # Scoring configuration
    SCORING_WEIGHTS = {
        'ideas': 30,
        'organization': 25,
        'style': 20,
        'grammar': 25
    }
    
    # AI model configuration
    AI_MODEL = 'gpt-3.5-turbo'
    AI_MAX_TOKENS = 2000
    AI_TEMPERATURE = 0.7
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    # Application features
    FEATURES = {
        'file_upload': True,
        'ai_analysis': True,
        'progress_tracking': True,
        'teacher_feedback': True,
        'assignment_management': True,
        'export_functionality': True
    }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    # Additional production settings would go here

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    DB_NAME = 'essay_revision_test'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
