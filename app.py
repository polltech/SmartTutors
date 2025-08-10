import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager

# ---------------------------
# Logging setup
# ---------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------
# SQLAlchemy base and DB init
# ---------------------------
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# ---------------------------
# Flask app initialization
# ---------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# ---------------------------
# File size config
# ---------------------------
app.config['MAX_CONTENT_LENGTH'] = 5000 * 1024 * 1024  # 50MB limit

# ---------------------------
# Database config
# ---------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///tutoring_platform.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize DB
db.init_app(app)

# ---------------------------
# Flask-Login config
# ---------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# ---------------------------
# App Context: DB setup and Admin user creation
# ---------------------------
with app.app_context():
    try:
        import models
        db.create_all()

        # Create default admin user
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
            logger.info("✅ Default admin user and settings created.")
        else:
            logger.info("✅ Admin user already exists.")

        # Initialize API keys from environment if they exist
        try:
            from gemini_service import initialize_api_keys
            initialize_api_keys()
            logger.info("✅ API keys initialized from environment")
        except ImportError as e:
            logger.warning(f"⚠️ API keys initialization failed - missing module: {e}")
        except Exception as e:
            logger.warning(f"⚠️ API keys initialization failed: {e}")

    except Exception as e:
        logger.error(f"❌ Error during app initialization: {e}")
        raise

# ---------------------------
# Import and register routes
# ---------------------------
try:
    import routes  # <- This is crucial to make your views work
    logger.info("✅ Routes imported successfully")
except Exception as e:
    logger.error(f"❌ Error importing routes: {e}")
    raise

# ---------------------------
# Render / local run support
# ---------------------------
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
        logger.info("✅ App started successfully")
    except Exception as e:
        logger.error(f"❌ Error starting app: {e}")
        raise
