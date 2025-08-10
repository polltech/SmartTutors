from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from models import User, Chat, Payment, AdminSettings, PendingPayment, PingLog
# Fixed imports - only import what actually exists
from gemini_service import get_ai_response, generate_exam, generate_combined_response, update_api_keys_from_admin
import logging
from datetime import datetime

# Secret key for /ping endpoint
PING_SECRET = "PaulKeepAlive2025"

@app.route('/ping')
def ping():
    key = request.args.get("key")
    if key != PING_SECRET:
        return "Unauthorized", 403
    
    # Save ping to DB
    ping_log = PingLog(timestamp=datetime.utcnow())
    db.session.add(ping_log)
    db.session.commit()
    
    return "pong", 200

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        education_level = request.form['education_level']
        curriculum = request.form['curriculum']
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered!')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken!')
            return redirect(url_for('register'))
        
        # Get free tokens from settings
        settings = AdminSettings.get_settings()
        
        # Create new user
        user = User()
        user.username = username
        user.email = email
        user.password_hash = generate_password_hash(password)
        user.education_level = education_level
        user.curriculum = curriculum
        user.tokens = settings.free_tokens_per_user
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    settings = AdminSettings.get_settings()
    return render_template('dashboard.html', user=current_user, settings=settings)

@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST':
        question = request.form['question']
        subject = request.form.get('subject', '')
        request_type = request.form.get('request_type', 'question')
        
        # Check if user has tokens
        if current_user.tokens <= 0:
            flash('You have no tokens left! Contact admin or make a payment.')
            return redirect(url_for('dashboard'))
        
        # Determine token cost based on request type
        token_cost = 1
        if request_type in ['exam', 'combined']:
            token_cost = 2  # More complex requests cost more tokens
        
        if current_user.tokens < token_cost:
            flash(f'You need {token_cost} tokens for this request! You have {current_user.tokens} tokens.')
            return redirect(url_for('dashboard'))
        
        # Get AI response based on request type
        try:
            answer = None
            if request_type == 'exam':
                num_questions = int(request.form.get('num_questions', 10))
                question_type = request.form.get('question_type', 'mixed')
                answer = generate_exam(
                    topic=question,
                    education_level=current_user.education_level,
                    curriculum=current_user.curriculum,
                    subject=subject,
                    num_questions=num_questions,
                    question_type=question_type
                )
            elif request_type == 'combined':
                answer = generate_combined_response(
                    topic=question,
                    education_level=current_user.education_level,
                    curriculum=current_user.curriculum,
                    subject=subject
                )
            else:  # Default question type
                answer = get_ai_response(
                    question=question,
                    education_level=current_user.education_level,
                    curriculum=current_user.curriculum,
                    subject=subject,
                    user_id=current_user.id
                )
            
            # Save chat to database
            chat = Chat()
            chat.user_id = current_user.id
            chat.subject = subject
            chat.question = f"[{request_type.upper()}] {question}"
            chat.answer = answer
            chat.tokens_used = token_cost
            db.session.add(chat)
            
            # Deduct tokens from user
            current_user.tokens -= token_cost
            db.session.commit()
            
            flash('Response generated successfully!')
            latest_response = {
                'question': question,
                'answer': answer,
                'subject': subject or 'General',
                'request_type': request_type,
                'tokens_used': token_cost
            }
            
        except Exception as e:
            logging.error(f"Error in chat: {e}")
            flash(f'Error generating response: {str(e)}')
            return redirect(url_for('dashboard'))
    
    # Get recent chats for this user
    recent_chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).limit(10).all()
    return render_template('chat.html', recent_chats=recent_chats, user=current_user, 
                         latest_response=locals().get('latest_response'))

@app.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('history.html', chats=chats, user=current_user)

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash('Access denied! Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    settings = AdminSettings.get_settings()
    recent_chats = Chat.query.order_by(Chat.created_at.desc()).limit(20).all()
    pending_payments = PendingPayment.query.filter_by(status='pending').order_by(PendingPayment.date_submitted.desc()).all()

    # Get last ping time
    last_ping_record = PingLog.query.order_by(PingLog.timestamp.desc()).first()
    last_ping_time = last_ping_record.timestamp.strftime("%Y-%m-%d %H:%M:%S") if last_ping_record else None
    uptime_duration = PingLog.get_uptime_duration()
    ping_count = PingLog.get_ping_count()

    return render_template('admin.html', users=users, settings=settings, recent_chats=recent_chats, 
                           pending_payments=pending_payments, last_ping_time=last_ping_time, 
                           uptime_duration=uptime_duration, ping_count=ping_count)

# ------------------------
# FIXED BLOCK
# ------------------------
@app.route('/api/admin/update-api-keys', methods=['POST'])
def api_update_api_keys():
    """API endpoint to update API keys from admin panel"""
    try:
        data = request.get_json()

        # Update settings in database
        settings = AdminSettings.get_settings()

        if 'hf_token' in data:
            settings.hf_token = data['hf_token']
        if 'pixabay_key' in data:
            settings.pixabay_key = data['pixabay_key']
        if 'unsplash_key' in data:
            settings.unsplash_key = data['unsplash_key']
        if 'pexels_key' in data:
            settings.pexels_key = data['pexels_key']
        if 'gemini_key' in data:
            settings.gemini_api_key = data['gemini_key']

        db.session.commit()

        # Update runtime keys in gemini_service
        update_api_keys_from_admin(
            hf_token=data.get('hf_token'),
            pixabay_key=data.get('pixabay_key'),
            unsplash_key=data.get('unsplash_key'),
            pexels_key=data.get('pexels_key'),
            gemini_key=data.get('gemini_key')
        )

        return jsonify({'success': True, 'message': 'API keys updated successfully'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
# ------------------------

# The rest of your routes remain unchanged...
