from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.sql import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, admin
    tokens = db.Column(db.Integer, default=5)
    education_level = db.Column(db.String(50), nullable=True)  # Baby Class, Lower Primary, etc.
    curriculum = db.Column(db.String(20), nullable=True)  # CBC, 8-4-4
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    chats = db.relationship('Chat', backref='user', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', lazy=True, cascade='all, delete-orphan')

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    tokens_used = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tokens_added = db.Column(db.Integer, nullable=False)
    transaction_id = db.Column(db.String(100), nullable=True)
    payment_method = db.Column(db.String(20), nullable=False)  # MPESA, Manual
    status = db.Column(db.String(20), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdminSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    free_tokens_per_user = db.Column(db.Integer, default=5)
    gemini_api_key = db.Column(db.String(200), nullable=True)
    theme = db.Column(db.String(20), default='blue')  # blue, red, white, gray
    background_type = db.Column(db.String(10), default='image')  # image, video
    background_url = db.Column(db.Text, nullable=True)
    video_muted = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_settings():
        settings = AdminSettings.query.first()
        if not settings:
            settings = AdminSettings()
            db.session.add(settings)
            db.session.commit()
        return settings

class PendingPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(100), nullable=False)  # M-PESA transaction code
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('pending_payments', lazy=True))

# -------- New uptime ping log model --------

class PingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
