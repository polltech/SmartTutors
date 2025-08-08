import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure upload size limits for large images/videos
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///tutoring_platform.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Define routes - THIS IS CRUCIAL
@app.route('/')
def index():
    return {"message": "Tutoring Platform API is running!"}

@app.route('/health')
def health():
    return {"status": "healthy"}

@app.route('/api/v1/courses')
def courses():
    # Return sample data or implement your actual logic
    return {"message": "Courses endpoint", "courses": []}

# Create default admin user and settings
def create_default_admin():
    with app.app_context():
        # Import models to ensure tables are created
        import models
        db.create_all()
        
        # Create default admin user if it doesn't exist
        admin_user = models.User.query.filter_by(email='admin@tutor.com').first()
        if not admin_user:
            from werkzeug.security import generate_password_hash
            admin = models.User()
            admin.username = 'admin'
            admin.email = 'admin@tutor.com'
            admin.password_hash = generate_password_hash('admin123')
            admin.role = 'admin'
            admin.tokens = 1000
            admin.education_level = 'Campus'
            admin.curriculum = 'CBC'
            db.session.add(admin)
            
            # Create default settings
            settings = models.AdminSettings()
            settings.free_tokens_per_user = 5
            settings.theme = 'blue'
            settings.background_type = 'image'
            settings.background_url = ''
            settings.video_muted = True
            db.session.add(settings)
            db.session.commit()
            logging.info("Default admin user and settings created")

# Main execution block - CRITICAL FOR RENDER
if __name__ == '__main__':
    create_default_admin()
    
    # Get port from environment variable or default to 10000
    port = int(os.environ.get('PORT', 10000))
    
    # Run the app - BIND TO 0.0.0.0 for Render
    app.run(host='0.0.0.0', port=port, debug=False)
