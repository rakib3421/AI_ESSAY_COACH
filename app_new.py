"""
Main Flask application for the Essay Revision System
Modularized for better maintainability
"""
from flask import Flask, render_template, request, jsonify
import os
import logging
from config import Config
from routes import register_routes

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
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

# Error handlers
@app.errorhandler(413)
def file_too_large(error):
    """Handle file too large error"""
    max_size_mb = Config.MAX_CONTENT_LENGTH / (1024 * 1024)
    return jsonify({
        'error': f'File too large. Maximum size allowed is {max_size_mb:.1f} MB.'
    }), 413

@app.errorhandler(400)
def bad_request(error):
    """Handle bad request error"""
    return jsonify({
        'error': 'Bad request. Please check your input and try again.'
    }), 400

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({'error': 'Resource not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {error}")
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({
            'error': 'Internal server error. Please try again later.',
            'message': 'If the problem persists, please contact support.'
        }), 500
    return render_template('500.html'), 500

@app.errorhandler(503)
def service_unavailable(error):
    """Handle service unavailable errors"""
    logger.error(f"Service unavailable: {error}")
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({
            'error': 'Service temporarily unavailable. Please try again later.',
            'message': 'Our AI analysis service is experiencing high demand. Please try again in a few minutes.'
        }), 503
    return render_template('500.html'), 503

# Register all routes
register_routes(app)

if __name__ == '__main__':
    app.run(host='10.10.12.31', port=5000, debug=True)
