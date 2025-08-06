"""
Main Flask application for the Essay Revision System
Modularized for better maintainability
"""
from flask import Flask
import os
import logging
from config import Config
from auth_routes import auth_bp
from student_routes import student_bp
from teacher_routes import teacher_bp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Configure app settings
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# Ensure upload folder exists
if not os.path.exists(Config.UPLOAD_FOLDER):
    os.makedirs(Config.UPLOAD_FOLDER)

# Initialize temporary storage (this will create the temp_data directory)
from utils import temp_storage
logger.info(f"Temporary storage initialized at: {temp_storage.storage_dir}")

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(teacher_bp)

if __name__ == '__main__':
    app.run(host='10.10.12.31', port=5000, debug=True)
