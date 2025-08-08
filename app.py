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
logging.basicConfig(level=logging.DEBUG)

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
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

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
        logging.info("✅ Default admin user and settings created.")

# ---------------------------
# Import and register routes
# ---------------------------
import routes  # <- This is crucial to make your views work

# ---------------------------
# Optional root JSON endpoint
# ---------------------------
@app.route("/")
def status():
    return {"message": "Tutoring Platform API is running!"}

# ---------------------------
# Render / local run support
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
