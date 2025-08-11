from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.sql import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, admi
    tokens = db.Column(db.Integer, default=5)
    education_level = db.Column(db.String(50), nullable=True)  # Baby Class, Lower Primary, etc.
    curriculum = db.Column(db.String(20), nullable=True)  # CBC, 8-4-4, TVET
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    chats = db.relationship('Chat', backref='user', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', lazy=True, cascade='all, delete-orphan')
    pending_payments = db.relationship('PendingPayment', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    tokens_used = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Chat {self.id}>'

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tokens_added = db.Column(db.Integer, nullable=False)
    transaction_id = db.Column(db.String(100), nullable=True)
    payment_method = db.Column(db.String(20), nullable=False)  # MPESA, Manual
    status = db.Column(db.String(20), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Payment {self.id}>'

class AdminSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    free_tokens_per_user = db.Column(db.Integer, default=5)
    gemini_api_key = db.Column(db.String(200), nullable=True)
    hf_token = db.Column(db.String(200), nullable=True)  # Hugging Face API key
    pixabay_key = db.Column(db.String(200), nullable=True)  # Pixabay API key
    unsplash_key = db.Column(db.String(200), nullable=True)  # Unsplash API key
    pexels_key = db.Column(db.String(200), nullable=True)  # Pexels API key
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

    def __repr__(self):
        return f'<AdminSettings {self.id}>'

class PendingPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(100), nullable=False)  # M-PESA transaction code
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship - Fixed the backref to avoid naming conflicts
    user = db.relationship('User', backref='pending_payments')

    def __repr__(self):
        return f'<PendingPayment {self.id}>'

# -------- New uptime ping log model --------
class PingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    @classmethod
    def get_uptime_duration(cls):
        """Calculate uptime duration from ping logs"""
        first_ping = cls.query.order_by(cls.timestamp.asc()).first()
        last_ping = cls.query.order_by(cls.timestamp.desc()).first()
        
        if first_ping and last_ping:
            return last_ping.timestamp - first_ping.timestamp
        return None
    
    @classmethod
    def get_last_ping(cls):
        """Get the timestamp of the last ping"""
        last_ping = cls.query.order_by(cls.timestamp.desc()).first()
        return last_ping.timestamp if last_ping else None

    @classmethod
    def get_ping_count(cls):
        """Get total number of pings"""
        return cls.query.count()

    def __repr__(self):
        return f'<PingLog {self.id}>'

# -------- Additional Model for Image Generation Logs --------
class ImageGenerationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    subject = db.Column(db.String(50), nullable=True)
    image_url = db.Column(db.Text, nullable=True)
    api_source = db.Column(db.String(20), nullable=True)  # huggingface, pixabay, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='image_logs')

    def __repr__(self):
        return f'<ImageGenerationLog {self.id}>'
