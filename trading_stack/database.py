import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Create database instance
db = SQLAlchemy(model_class=Base)

def create_app(settings=None):
    """Create and configure the Flask application"""
    app = Flask('trading_stack', root_path=os.path.dirname(__file__))
    
    # Configure app
    import secrets
    app.secret_key = secrets.token_hex(32)
    
    # Database configuration (SQLite by default for local / phone-side bring-up)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config.update(settings or {})
    if app.config["SQLALCHEMY_DATABASE_URI"] not in ("sqlite://", "sqlite:///:memory:"):
        raise ValueError("Paper app requires an isolated in-memory database")
    app.config.update(TEAKA_MODE="paper", LIVE_TRADING_ENABLED=False,
                      PRIVATE_EXCHANGE_API_ENABLED=False)
    
    # Initialize database
    db.init_app(app)
    
    return app
