import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, current_user, login_required
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

# Import database and models
from database import db, create_app

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app using the factory function
app = create_app()
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Load configuration from config.py
app.config.from_object('config')

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Import models after app and db initialization
from models import User, TradingStrategy, TradingSignal, TradeExecution, BacktestResult

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Import and register blueprints
try:
    from auth import bp as auth_bp
    app.register_blueprint(auth_bp)
except ImportError:
    logger.warning("Auth blueprint not found, creating basic routes")

# Import API routes if available
try:
    from api import routes as api_routes
    api_routes.init_app(app)
except ImportError:
    logger.warning("API routes not found")

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Basic dashboard data without external APIs for now
        recent_signals = db.session.query(TradingSignal).filter_by(user_id=current_user.id).order_by(TradingSignal.timestamp.desc()).limit(10).all()
        
        return render_template(
            'dashboard.html',
            account_balance={'total': 0, 'available': 0},
            latest_prices={},
            active_positions=[],
            recent_trades=[],
            recent_signals=recent_signals
        )
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', 
                             account_balance={'total': 0, 'available': 0},
                             latest_prices={},
                             active_positions=[],
                             recent_trades=[],
                             recent_signals=[])

@app.route('/market-data')
@login_required
def market_data():
    pairs = app.config.get('CRYPTO_TRADING_PAIRS', []) + app.config.get('FOREX_TRADING_PAIRS', [])
    selected_pair = request.args.get('pair', 'BTC/USDT')
    timeframe = request.args.get('timeframe', '1h')
    
    return render_template(
        'market_data.html',
        pairs=pairs,
        selected_pair=selected_pair,
        timeframe=timeframe,
        timeframes=app.config.get('TIMEFRAMES', ['1h', '4h', '1d'])
    )

@app.route('/backtesting')
@login_required
def backtesting():
    strategies = db.session.query(TradingStrategy).filter_by(user_id=current_user.id).all()
    pairs = app.config.get('CRYPTO_TRADING_PAIRS', []) + app.config.get('FOREX_TRADING_PAIRS', [])
    timeframes = app.config.get('TIMEFRAMES', ['1h', '4h', '1d'])
    
    return render_template(
        'backtesting.html',
        strategies=strategies,
        pairs=pairs,
        timeframes=timeframes
    )

@app.route('/strategy-editor')
@login_required
def strategy_editor():
    strategy_id = request.args.get('id')
    strategy = None
    
    if strategy_id:
        strategy = db.session.query(TradingStrategy).filter_by(id=strategy_id, user_id=current_user.id).first()
    
    indicators = app.config.get('AVAILABLE_INDICATORS', [])
    
    return render_template(
        'strategy_editor.html',
        strategy=strategy,
        indicators=indicators
    )

@app.route('/signals')
@login_required
def signals():
    signals = db.session.query(TradingSignal).filter_by(user_id=current_user.id).order_by(TradingSignal.timestamp.desc()).all()
    return render_template('signals.html', signals=signals)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="404 Page Not Found"), 404

@app.route('/update_kucoin_api', methods=['POST'])
@login_required
def update_kucoin_api():
    """Update KuCoin API settings."""
    current_user.kucoin_api_key = request.form.get('kucoin_api_key')
    current_user.kucoin_api_secret = request.form.get('kucoin_api_secret')
    current_user.kucoin_passphrase = request.form.get('kucoin_passphrase')
    db.session.commit()
    flash('KuCoin API settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/update_ib_api', methods=['POST'])
@login_required
def update_ib_api():
    """Update Interactive Brokers API settings."""
    current_user.ib_api_key = request.form.get('ib_api_key')
    current_user.ib_account_id = request.form.get('ib_account_id')
    db.session.commit()
    flash('Interactive Brokers API settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/update_oanda_api', methods=['POST'])
@login_required
def update_oanda_api():
    """Update OANDA API settings."""
    current_user.oanda_api_key = request.form.get('oanda_api_key')
    current_user.oanda_account_id = request.form.get('oanda_account_id')
    db.session.commit()
    flash('OANDA API settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/update_notification_settings', methods=['POST'])
@login_required
def update_notification_settings():
    """Update notification settings."""
    current_user.enable_email_notifications = 'enable_email_notifications' in request.form
    current_user.enable_telegram_notifications = 'enable_telegram_notifications' in request.form
    current_user.enable_discord_notifications = 'enable_discord_notifications' in request.form
    current_user.telegram_chat_id = request.form.get('telegram_chat_id')
    current_user.discord_webhook_url = request.form.get('discord_webhook_url')
    db.session.commit()
    flash('Notification settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/update_risk_settings', methods=['POST'])
@login_required
def update_risk_settings():
    """Update risk management settings."""
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
    
    current_user.max_position_size_pct = safe_float(request.form.get('max_position_size_pct', 5.0), 5.0)
    current_user.max_open_positions = int(request.form.get('max_open_positions', 10))
    current_user.default_stop_loss_pct = safe_float(request.form.get('default_stop_loss_pct', 2.0), 2.0)
    current_user.default_take_profit_pct = safe_float(request.form.get('default_take_profit_pct', 4.0), 4.0)
    db.session.commit()
    flash('Risk management settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error="500 Internal Server Error"), 500

# Initialize database tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")