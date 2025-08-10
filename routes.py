import os
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import app, db
from models import User

# ------------------------------
# Home
# ------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# ------------------------------
# Auth: Login
# ------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# ------------------------------
# Auth: Register
# ------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_pw, tokens=5)  # free tokens
        db.session.add(new_user)
        db.session.commit()

        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# ------------------------------
# Auth: Logout
# ------------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ------------------------------
# Dashboard
# ------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', tokens=current_user.tokens)

# ------------------------------
# Buy Tokens Page
# ------------------------------
@app.route('/buy_tokens', methods=['GET', 'POST'])
@login_required
def buy_tokens():
    if request.method == 'POST':
        try:
            tokens_to_buy = int(request.form.get('tokens'))
            payment_method = request.form.get('payment_method')

            if tokens_to_buy <= 0:
                flash('Invalid token amount.', 'danger')
                return redirect(url_for('buy_tokens'))

            # Manual payment simulation
            # Here you would normally integrate MPESA/PayPal APIs
            current_user.tokens += tokens_to_buy
            db.session.commit()

            flash(f'Successfully purchased {tokens_to_buy} tokens!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            flash(f'Error processing purchase: {e}', 'danger')
            return redirect(url_for('buy_tokens'))

    return render_template('buy_tokens.html')

# ------------------------------
# AI Tutor Endpoint
# ------------------------------
@app.route('/ask_ai', methods=['POST'])
@login_required
def ask_ai():
    if current_user.tokens <= 0:
        return jsonify({'error': 'You have no tokens left. Please buy more.'}), 403

    user_input = request.json.get('message')

    if not user_input:
        return jsonify({'error': 'Message is required'}), 400

    # Deduct token
    current_user.tokens -= 1
    db.session.commit()

    # Call AI API (placeholder)
    ai_response = f"AI Response to: {user_input}"

    return jsonify({'response': ai_response, 'tokens_left': current_user.tokens})
