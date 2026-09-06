"""Recovered Flask application: explicit, memory-only paper factory."""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, current_user, login_required
import logging
from .database import db, create_app as create_database_app
from .models import User, TradingStrategy, TradingSignal, TradeExecution, BacktestResult
logger = logging.getLogger(__name__)


def create_app(settings=None, runtime=None):
    app = create_database_app(settings)
    from .paper_runtime import PaperRuntime, LocalCandleProvider
    app.extensions['paper_runtime'] = runtime or PaperRuntime(LocalCandleProvider({}, 'unavailable', '1h'))
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    from .api.routes import init_app
    init_app(app)
    register_pages(app)
    with app.app_context():
        db.create_all()
    return app


def register_pages(app):
    from .paper_pages import register_pages as register_paper_pages
    register_paper_pages(app)
