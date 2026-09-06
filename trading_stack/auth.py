from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse, urljoin
from .database import db
from .models import User
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
    
    return render_template('paper_auth.html', register=False)

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
    
    return render_template('paper_auth.html', register=True)

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
        return render_template('paper_account.html', section='profile', error='Profile changes unavailable in this memory-only paper session'), 503
    return render_template('paper_account.html', section='profile')
