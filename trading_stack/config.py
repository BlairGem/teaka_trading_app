import os

# Application configuration
DEBUG = True
SECRET_KEY = os.environ.get("SESSION_SECRET", "dev-secret-key")
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///trading_app.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# TeAka recovery-fork safety gates (live orders stay off unless both are true)
TEAKA_MODE = os.environ.get("TEAKA_MODE", "paper").lower()
LIVE_TRADING_ENABLED = os.environ.get("LIVE_TRADING_ENABLED", "false").lower() == "true"
PRIVATE_EXCHANGE_API_ENABLED = (
    os.environ.get("PRIVATE_EXCHANGE_API_ENABLED", "false").lower() == "true"
)


def live_orders_allowed() -> bool:
    return (
        TEAKA_MODE == "live"
        and LIVE_TRADING_ENABLED
        and PRIVATE_EXCHANGE_API_ENABLED
    )

# API Keys
KUCOIN_API_KEY = os.environ.get("KUCOIN_API_KEY", "")
KUCOIN_SECRET_KEY = os.environ.get("KUCOIN_SECRET_KEY", "")
KUCOIN_PASSPHRASE = os.environ.get("KUCOIN_PASSPHRASE", "")
OANDA_API_KEY = os.environ.get("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID", "")
IB_API_KEY = os.environ.get("IB_API_KEY", "")
IB_ACCOUNT_ID = os.environ.get("IB_ACCOUNT_ID", "")

# Telegram and Discord webhook configurations
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# MATLAB configuration
MATLAB_ENABLED = os.environ.get("MATLAB_ENABLED", "False").lower() == "true"

# Backtesting parameters
DEFAULT_BACKTEST_PERIOD = 90  # days

# Risk management settings
MAX_POSITION_SIZE_PERCENTAGE = 5  # % of account balance
MAX_OPEN_POSITIONS = 10
STOP_LOSS_PERCENTAGE = 2.0  # Default stop loss %
TAKE_PROFIT_PERCENTAGE = 4.0  # Default take profit %

# Trading pairs configuration
CRYPTO_TRADING_PAIRS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "ADA/USDT", 
    "XRP/USDT", "DOT/USDT", "DOGE/USDT", "AVAX/USDT", "MATIC/USDT"
]

FOREX_TRADING_PAIRS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", 
    "USD/CHF", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY", "XAU/USD"
]

# Timeframes available for analysis
TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]

# Technical indicators to use in strategies
AVAILABLE_INDICATORS = [
    "SMA", "EMA", "RSI", "MACD", "Bollinger Bands", "Stochastic", 
    "Ichimoku Cloud", "ADX", "ATR", "OBV", "CCI"
]

# ML Model parameters
ML_FEATURES = [
    "open", "high", "low", "close", "volume", 
    "sma_20", "ema_50", "rsi_14", "macd", "bb_upper", "bb_lower"
]

ML_PREDICTION_HORIZONS = [15, 30, 60, 240]  # minutes

# WebSocket configurations
KUCOIN_WS_URL = "wss://ws-api-spot.kucoin.com/"
KUCOIN_FUTURES_WS_URL = "wss://ws-api-futures.kucoin.com/"
OANDA_WS_URL = "wss://stream-fxpractice.oanda.com"
IB_WS_URL = "ws://localhost:5555"  # TWS API Gateway
