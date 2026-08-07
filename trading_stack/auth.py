from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse, urljoin
from database import db
from models import User
import logging

# Create blueprint
bp = Blueprint('auth', __name__, url_prefix='/auth')
logger = logging.getLogger(__name__)

def is_safe_url(target):
    """Check if the target URL is safe for redirect (same domain only)"""
    if not target:
        return False
    
    # Parse the target URL
    parsed = urlparse(target)
    
    # Only allow relative URLs (no scheme or netloc)
    # This prevents redirects to external domains
    return not parsed.netloc and not parsed.scheme

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = 'remember_me' in request.form
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password', 'danger')
            logger.warning(f"Failed login attempt for username: {username}")
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember_me)
        logger.info(f"User {username} logged in successfully")
        
        next_page = request.args.get('next')
        if next_page and is_safe_url(next_page):
            return redirect(next_page)
        else:
            return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        # Save to database
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            logger.info(f"New user registered: {username}")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during user registration: {e}")
            flash('An error occurred during registration', 'danger')
            return redirect(url_for('auth.register'))
    
    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Update API keys
        current_user.binance_api_key = request.form.get('binance_api_key', '')
        current_user.binance_api_secret = request.form.get('binance_api_secret', '')
        current_user.oanda_api_key = request.form.get('oanda_api_key', '')
        current_user.oanda_account_id = request.form.get('oanda_account_id', '')
        
        # Update notification settings
        current_user.telegram_chat_id = request.form.get('telegram_chat_id', '')
        current_user.discord_webhook_url = request.form.get('discord_webhook_url', '')
        current_user.enable_email_notifications = 'enable_email_notifications' in request.form
        current_user.enable_telegram_notifications = 'enable_telegram_notifications' in request.form
        current_user.enable_discord_notifications = 'enable_discord_notifications' in request.form
        
        # Update risk management settings
        def safe_float(value, default):
            try:
                result = float(value)
                if not (result == result):  # Check for NaN
                    return default
                if result == float('inf') or result == float('-inf'):  # Check for infinity
                    return default
                return result
            except (ValueError, TypeError):
                return default
        
        try:
            current_user.max_position_size_pct = safe_float(request.form.get('max_position_size_pct', 5.0), 5.0)
            current_user.max_open_positions = int(request.form.get('max_open_positions', 10))
            current_user.default_stop_loss_pct = safe_float(request.form.get('default_stop_loss_pct', 2.0), 2.0)
            current_user.default_take_profit_pct = safe_float(request.form.get('default_take_profit_pct', 4.0), 4.0)
        except ValueError:
            flash('Invalid number format for risk management settings', 'danger')
            return redirect(url_for('auth.profile'))
        
        # Change password if provided
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if current_password and new_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect', 'danger')
                return redirect(url_for('auth.profile'))
            
            if new_password != confirm_password:
                flash('New passwords do not match', 'danger')
                return redirect(url_for('auth.profile'))
            
            current_user.set_password(new_password)
            flash('Password updated successfully', 'success')
        
        # Save changes
        try:
            db.session.commit()
            flash('Profile updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user profile: {e}")
            flash('An error occurred while updating profile', 'danger')
        
        return redirect(url_for('auth.profile'))
    
    return render_template('profile.html')
