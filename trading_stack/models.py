from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .database import db
import json


class PaperRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data_origin = db.Column(db.Text, nullable=False)
    start_time = db.Column(db.String(64), nullable=False)
    end_time = db.Column(db.String(64), nullable=False)
    summary = db.Column(db.Text)


class PaperDecision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('paper_run.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    strategy_id = db.Column(db.Integer, db.ForeignKey('trading_strategy.id'))
    candle_time = db.Column(db.String(64), nullable=False)
    trading_pair = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(32), nullable=False)
    reason = db.Column(db.Text)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # API Keys for different platforms
    kucoin_api_key = db.Column(db.String(64))
    kucoin_api_secret = db.Column(db.String(64))
    kucoin_passphrase = db.Column(db.String(64))
    oanda_api_key = db.Column(db.String(64))
    oanda_account_id = db.Column(db.String(64))
    ib_api_key = db.Column(db.String(64))
    ib_account_id = db.Column(db.String(64))
    
    # Notification settings
    telegram_chat_id = db.Column(db.String(64))
    discord_webhook_url = db.Column(db.String(256))
    enable_email_notifications = db.Column(db.Boolean, default=False)
    enable_telegram_notifications = db.Column(db.Boolean, default=False)
    enable_discord_notifications = db.Column(db.Boolean, default=False)
    
    # Risk management settings
    max_position_size_pct = db.Column(db.Float, default=5.0)  # % of account
    max_open_positions = db.Column(db.Integer, default=10)
    default_stop_loss_pct = db.Column(db.Float, default=2.0)
    default_take_profit_pct = db.Column(db.Float, default=4.0)

    # Live auto-trading is OFF by default in this recovery fork.
    enable_automated_trading = db.Column(db.Boolean, default=False)
    
    # Relationships
    strategies = db.relationship('TradingStrategy', backref='user', lazy='dynamic')
    signals = db.relationship('TradingSignal', backref='user', lazy='dynamic')
    trade_executions = db.relationship('TradeExecution', backref='user', lazy='dynamic')
    backtest_results = db.relationship('BacktestResult', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class TradingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text)
    trading_pairs = db.Column(db.String(512))  # Stored as JSON string
    timeframe = db.Column(db.String(8))  # e.g., "1m", "5m", "1h", "1d"
    indicators_config = db.Column(db.Text)  # JSON with indicator parameters
    entry_conditions = db.Column(db.Text)  # JSON with entry conditions
    exit_conditions = db.Column(db.Text)  # JSON with exit conditions
    risk_per_trade_pct = db.Column(db.Float, default=1.0)
    stop_loss_pct = db.Column(db.Float)
    take_profit_pct = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ML model configuration (if applicable)
    use_ml_model = db.Column(db.Boolean, default=False)
    ml_model_id = db.Column(db.Integer, db.ForeignKey('ml_model.id'), nullable=True)
    
    def get_trading_pairs(self):
        if self.trading_pairs:
            return json.loads(self.trading_pairs)
        return []
    
    def set_trading_pairs(self, pairs_list):
        self.trading_pairs = json.dumps(pairs_list)
    
    def get_indicators_config(self):
        if self.indicators_config:
            return json.loads(self.indicators_config)
        return {}
    
    def set_indicators_config(self, config_dict):
        self.indicators_config = json.dumps(config_dict)
    
    def get_entry_conditions(self):
        if self.entry_conditions:
            return json.loads(self.entry_conditions)
        return []
    
    def set_entry_conditions(self, conditions_list):
        self.entry_conditions = json.dumps(conditions_list)
    
    def get_exit_conditions(self):
        if self.exit_conditions:
            return json.loads(self.exit_conditions)
        return []
    
    def set_exit_conditions(self, conditions_list):
        self.exit_conditions = json.dumps(conditions_list)
    
    def __repr__(self):
        return f'<Strategy {self.name}>'


class TradingSignal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    strategy_id = db.Column(db.Integer, db.ForeignKey('trading_strategy.id'))
    trading_pair = db.Column(db.String(16), nullable=False)
    signal_type = db.Column(db.String(4), nullable=False)  # BUY or SELL
    entry_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(16), default='pending')  # pending, executed, canceled, expired
    timeframe = db.Column(db.String(8))
    confidence = db.Column(db.Float)  # From 0 to 1, can be used for ML signals
    signal_data = db.Column(db.Text)  # Additional JSON data about the signal
    
    # Relationships
    strategy = db.relationship('TradingStrategy', backref='signals')
    executions = db.relationship('TradeExecution', backref='signal', lazy='dynamic')
    
    def get_signal_data(self):
        if self.signal_data:
            return json.loads(self.signal_data)
        return {}
    
    def set_signal_data(self, data_dict):
        self.signal_data = json.dumps(data_dict)
    
    def __repr__(self):
        return f'<Signal {self.trading_pair} {self.signal_type} at {self.timestamp}>'


class TradeExecution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    signal_id = db.Column(db.Integer, db.ForeignKey('trading_signal.id'), nullable=True)
    trading_pair = db.Column(db.String(16), nullable=False)
    order_type = db.Column(db.String(4), nullable=False)  # BUY or SELL
    order_id = db.Column(db.String(64))  # Exchange order ID
    amount = db.Column(db.Float)
    price = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(16))  # filled, pending, canceled, etc.
    platform = db.Column(db.String(16))  # binance, oanda, etc.
    fee = db.Column(db.Float)
    pnl = db.Column(db.Float)  # For closing trades
    is_automated = db.Column(db.Boolean, default=True)  # Was trade executed by automated system?
    executed_by = db.Column(db.String(64))  # Strategy name or "Manual"
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Trade {self.order_type} {self.trading_pair} at {self.timestamp}>'


class BacktestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    strategy_id = db.Column(db.Integer, db.ForeignKey('trading_strategy.id'))
    trading_pair = db.Column(db.String(16), nullable=False)
    timeframe = db.Column(db.String(8))
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    initial_balance = db.Column(db.Float)
    final_balance = db.Column(db.Float)
    total_trades = db.Column(db.Integer)
    winning_trades = db.Column(db.Integer)
    losing_trades = db.Column(db.Integer)
    profit_factor = db.Column(db.Float)
    max_drawdown_pct = db.Column(db.Float)
    sharpe_ratio = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    result_data = db.Column(db.Text)  # JSON with detailed results
    
    # Relationships
    strategy = db.relationship('TradingStrategy', backref='backtests')
    
    def get_result_data(self):
        if self.result_data:
            return json.loads(self.result_data)
        return {}
    
    def set_result_data(self, data_dict):
        self.result_data = json.dumps(data_dict)
    
    def __repr__(self):
        return f'<Backtest {self.strategy.name} {self.trading_pair} {self.start_date} to {self.end_date}>'


class MLModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text)
    model_type = db.Column(db.String(32))  # LSTM, RandomForest, etc.
    target_variable = db.Column(db.String(32))  # price_direction, price_change, etc.
    features = db.Column(db.Text)  # JSON with list of features
    hyperparameters = db.Column(db.Text)  # JSON with hyperparameters
    training_start_date = db.Column(db.DateTime)
    training_end_date = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    performance_metrics = db.Column(db.Text)  # JSON with metrics
    is_active = db.Column(db.Boolean, default=False)
    model_path = db.Column(db.String(256))  # Path to saved model
    
    # Relationship with strategies
    strategies = db.relationship('TradingStrategy', backref='ml_model')
    
    def get_features(self):
        if self.features:
            return json.loads(self.features)
        return []
    
    def set_features(self, features_list):
        self.features = json.dumps(features_list)
    
    def get_hyperparameters(self):
        if self.hyperparameters:
            return json.loads(self.hyperparameters)
        return {}
    
    def set_hyperparameters(self, hyperparameters_dict):
        self.hyperparameters = json.dumps(hyperparameters_dict)
    
    def get_performance_metrics(self):
        if self.performance_metrics:
            return json.loads(self.performance_metrics)
        return {}
    
    def set_performance_metrics(self, metrics_dict):
        self.performance_metrics = json.dumps(metrics_dict)
    
    def __repr__(self):
        return f'<MLModel {self.name}>'
