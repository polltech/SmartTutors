from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from models import User, Chat, Payment, AdminSettings, PendingPayment, PingLog
from gemini_service import get_ai_response, analyze_uploaded_document, generate_exam, generate_explanation, generate_image, generate_combined_response, update_api_keys_from_admin
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
        if request_type in ['exam', 'combined', 'image']:
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
            elif request_type == 'explanation':
                answer = generate_explanation(
                    topic=question,
                    education_level=current_user.education_level,
                    curriculum=current_user.curriculum,
                    subject=subject
                )
            elif request_type == 'image':
                answer = generate_image(
                    description=question,
                    education_level=current_user.education_level,
                    subject=subject
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
            # Return the new response to display
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

    # Get last ping time from DB
    last_ping_record = PingLog.query.order_by(PingLog.timestamp.desc()).first()
    last_ping_time = last_ping_record.timestamp.strftime("%Y-%m-%d %H:%M:%S") if last_ping_record else None
    
    # Get uptime duration
    uptime_duration = PingLog.get_uptime_duration()
    
    # Get ping count
    ping_count = PingLog.get_ping_count()

    return render_template('admin.html', users=users, settings=settings, recent_chats=recent_chats, pending_payments=pending_payments, last_ping_time=last_ping_time, uptime_duration=uptime_duration, ping_count=ping_count)

@app.route('/admin/add_tokens', methods=['POST'])
@login_required
def add_tokens():
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    user_id = request.form['user_id']
    tokens = int(request.form['tokens'])
    
    user = User.query.get(user_id)
    if user:
        user.tokens += tokens
        
        # Log as manual payment
        payment = Payment()
        payment.user_id = user_id
        payment.amount = 0
        payment.tokens_added = tokens
        payment.payment_method = 'Manual'
        payment.transaction_id = f'ADMIN_ADD_{user_id}_{tokens}'
        db.session.add(payment)
        db.session.commit()
        
        flash(f'Added {tokens} tokens to {user.username}')
    else:
        flash('User not found!')
    
    return redirect(url_for('admin'))

@app.route('/admin/update_settings', methods=['POST'])
@login_required
def update_settings():
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    try:
        settings = AdminSettings.get_settings()
        
        settings.free_tokens_per_user = int(request.form.get('free_tokens_per_user', 5))
        settings.gemini_api_key = request.form.get('gemini_api_key', '')
        settings.theme = request.form.get('theme', 'blue')
        settings.background_type = request.form.get('background_type', 'image')
        background_url = request.form.get('background_url', '').strip()
        
        # Validate and limit background URL if needed
        if len(background_url) > 10000:  # Reasonable limit for very large base64 images
            flash('Background URL too large. Please use a smaller image or external URL.')
            return redirect(url_for('admin'))
            
        settings.background_url = background_url
        settings.video_muted = 'video_muted' in request.form
        
        db.session.commit()
        flash('Settings updated successfully!')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating settings: {str(e)}')
        logging.error(f"Settings update error: {e}")
    
    return redirect(url_for('admin'))

@app.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    user = User.query.get(user_id)
    if user and user.id != current_user.id:  # Can't delete self
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} deleted successfully!')
    else:
        flash('Cannot delete user!')
    
    return redirect(url_for('admin'))

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    current_user.education_level = request.form['education_level']
    current_user.curriculum = request.form['curriculum']
    db.session.commit()
    flash('Profile updated successfully!')
    return redirect(url_for('dashboard'))

@app.route('/admin/bulk_add_tokens', methods=['POST'])
@login_required
def bulk_add_tokens():
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    tokens = int(request.form['tokens'])
    
    # Add tokens to all users except admin
    users = User.query.filter(User.role != 'admin').all()
    total_users_updated = 0
    
    for user in users:
        user.tokens += tokens
        
        # Log as manual payment for each user
        payment = Payment()
        payment.user_id = user.id
        payment.amount = 0
        payment.tokens_added = tokens
        payment.payment_method = 'Bulk Manual'
        payment.transaction_id = f'ADMIN_BULK_{user.id}_{tokens}'
        db.session.add(payment)
        total_users_updated += 1
    
    db.session.commit()
    flash(f'Successfully added {tokens} tokens to {total_users_updated} users!')
    
    return redirect(url_for('admin'))

# API endpoint for getting current theme
@app.route('/api/theme')
def get_theme():
    settings = AdminSettings.get_settings()
    return jsonify({
        'theme': settings.theme,
        'background_type': settings.background_type,
        'background_url': settings.background_url,
        'video_muted': settings.video_muted
    })

# API endpoints for admin key management
@app.route('/api/admin/update-api-keys', methods=['POST'])
def api_update_api_keys():
    """
    API endpoint to update API keys from admin panel
    """
    try:
        data = request.get_json()
        
        # Update settings in database
        settings = AdminSettings.get_settings()
        
        if 'hf_token' in data:
            settings.hf_token = data['hf_token']
        if 'pixabay_key' in 
            settings.pixabay_key = data['pixabay_key']
        if 'unsplash_key' in 
            settings.unsplash_key = data['unsplash_key']
        if 'pexels_key' in data:
            settings.pexels_key = data['pexels_key']
        if 'gemini_key' in 
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

@app.route('/api/admin/test-api-keys')
def api_test_api_keys():
    """
    API endpoint to test if API keys are valid
    """
    try:
        from gemini_service import get_current_api_keys
        
        keys = get_current_api_keys()
        valid_keys = []
        invalid_keys = []
        
        # Test each key (basic validation)
        if keys.get('hf_token'):
            valid_keys.append('Hugging Face')
        else:
            invalid_keys.append('Hugging Face')
            
        if keys.get('pixabay_key'):
            valid_keys.append('Pixabay')
        else:
            invalid_keys.append('Pixabay')
            
        if keys.get('unsplash_key'):
            valid_keys.append('Unsplash')
        else:
            invalid_keys.append('Unsplash')
            
        if keys.get('pexels_key'):
            valid_keys.append('Pexels')
        else:
            invalid_keys.append('Pexels')
            
        if keys.get('gemini_key'):
            valid_keys.append('Gemini')
        else:
            invalid_keys.append('Gemini')
            
        message = f"Valid keys: {', '.join(valid_keys)}" if valid_keys else "No keys configured"
        
        return jsonify({
            'success': True,
            'message': message,
            'valid_keys': valid_keys,
            'invalid_keys': invalid_keys
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/buy_tokens')
@login_required
def buy_tokens():
    """Display the M-PESA payment instructions page"""
    return render_template('buy_tokens.html')

@app.route('/submit_payment_code', methods=['POST'])
@login_required
def submit_payment_code():
    """Handle M-PESA transaction code submission"""
    try:
        code = request.form.get('code', '').strip()
        
        if not code:
            flash('Please enter a valid M-PESA transaction code!')
            return redirect(url_for('buy_tokens'))
        
        # Check if this code has already been submitted
        existing_payment = PendingPayment.query.filter_by(code=code).first()
        if existing_payment:
            flash('This transaction code has already been submitted!')
            return redirect(url_for('buy_tokens'))
        
        # Create new pending payment record
        pending_payment = PendingPayment()
        pending_payment.user_id = current_user.id
        pending_payment.code = code
        pending_payment.status = 'pending'
        
        db.session.add(pending_payment)
        db.session.commit()
        
        flash('Payment code submitted successfully! Your request will be reviewed and approved shortly.')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash('Error submitting payment code. Please try again.')
        logging.error(f"Payment code submission error: {e}")
        return redirect(url_for('buy_tokens'))

@app.route('/admin/approve_payment/<int:payment_id>')
@login_required
def approve_payment(payment_id):
    """Approve a pending M-PESA payment and add tokens to user"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    try:
        pending_payment = PendingPayment.query.get(payment_id)
        if not pending_payment:
            flash('Payment request not found!')
            return redirect(url_for('admin'))
        
        if pending_payment.status != 'pending':
            flash('Payment request has already been processed!')
            return redirect(url_for('admin'))
        
        # Get the user
        user = User.query.get(pending_payment.user_id)
        if not user:
            flash('User not found!')
            return redirect(url_for('admin'))
        
        # Add tokens to user (50 KES = 10 tokens, can be configured)
        tokens_to_add = 10  # This could be made configurable in settings
        user.tokens += tokens_to_add
        
        # Update pending payment status
        pending_payment.status = 'approved'
        
        # Create a payment record for tracking
        payment = Payment()
        payment.user_id = user.id
        payment.amount = 50  # KES 50
        payment.tokens_added = tokens_to_add
        payment.payment_method = 'MPESA'
        payment.transaction_id = pending_payment.code
        payment.status = 'completed'
        db.session.add(payment)
        
        db.session.commit()
        
        flash(f'Payment approved! Added {tokens_to_add} tokens to {user.username}')
        
    except Exception as e:
        db.session.rollback()
        flash('Error approving payment. Please try again.')
        logging.error(f"Payment approval error: {e}")
    
    return redirect(url_for('admin'))

@app.route('/admin/reject_payment/<int:payment_id>')
@login_required
def reject_payment(payment_id):
    """Reject a pending M-PESA payment"""
    if current_user.role != 'admin':
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    try:
        pending_payment = PendingPayment.query.get(payment_id)
        if not pending_payment:
            flash('Payment request not found!')
            return redirect(url_for('admin'))
        
        if pending_payment.status != 'pending':
            flash('Payment request has already been processed!')
            return redirect(url_for('admin'))
        
        # Update pending payment status
        pending_payment.status = 'rejected'
        db.session.commit()
        
        flash('Payment request rejected.')
        
    except Exception as e:
        db.session.rollback()
        flash('Error rejecting payment. Please try again.')
        logging.error(f"Payment rejection error: {e}")
    
    return redirect(url_for('admin'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
