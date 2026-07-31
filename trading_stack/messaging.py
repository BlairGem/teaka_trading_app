import logging
import requests
import json
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DISCORD_WEBHOOK_URL

logger = logging.getLogger(__name__)

def send_signal_notification(signal):
    """Send a notification about a new trading signal."""
    user = signal.user
    
    # Create message content
    message = create_signal_message(signal)
    
    # Send notifications based on user preferences
    if user.enable_telegram_notifications and user.telegram_chat_id:
        send_telegram_message(user.telegram_chat_id, message)
    
    if user.enable_discord_notifications and user.discord_webhook_url:
        send_discord_message(user.discord_webhook_url, message)
    
    if user.enable_email_notifications:
        send_email_notification(user.email, "New Trading Signal", message)
    
    logger.info(f"Signal notification sent for {signal.trading_pair} {signal.signal_type}")

def create_signal_message(signal):
    """Create a formatted message for a trading signal."""
    # Get strategy name
    strategy_name = signal.strategy.name if signal.strategy else "Manual"
    
    # Format the signal message
    message = f"🚨 NEW TRADING SIGNAL\n\n"
    message += f"{'🔴 SELL' if signal.signal_type == 'SELL' else '🟢 BUY'} {signal.trading_pair}\n\n"
    message += f"Strategy: {strategy_name}\n"
    message += f"Timeframe: {signal.timeframe}\n"
    message += f"Entry Price: {signal.entry_price:.6f}\n"
    
    if signal.stop_loss:
        message += f"Stop Loss: {signal.stop_loss:.6f}\n"
    
    if signal.take_profit:
        message += f"Take Profit: {signal.take_profit:.6f}\n"
    
    if signal.confidence:
        message += f"Confidence: {signal.confidence:.2%}\n"
    
    message += f"\nTime: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    
    return message

def send_telegram_message(chat_id, message):
    """Send a message via Telegram Bot API."""
    try:
        # If no chat_id is set, try to use the default from config
        if not chat_id:
            chat_id = TELEGRAM_CHAT_ID
            if not chat_id:
                logger.error("No Telegram chat ID configured")
                return False
        
        # If no bot token, use the default from config
        bot_token = TELEGRAM_BOT_TOKEN
        if not bot_token:
            logger.error("No Telegram bot token configured")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            logger.info("Telegram message sent successfully")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def send_discord_message(webhook_url, message):
    """Send a message via Discord webhook."""
    try:
        # If no webhook URL is set, try to use the default from config
        if not webhook_url:
            webhook_url = DISCORD_WEBHOOK_URL
            if not webhook_url:
                logger.error("No Discord webhook URL configured")
                return False
        
        # Create Discord message payload
        payload = {
            'content': message
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
        
        if response.status_code == 204:
            logger.info("Discord message sent successfully")
            return True
        else:
            logger.error(f"Failed to send Discord message: {response.status_code}, {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Error sending Discord message: {e}")
        return False

def send_email_notification(email, subject, message):
    """Send an email notification."""
    # In a real implementation, this would use an email service like SMTP or a third-party service
    # For now, just log the email that would be sent
    logger.info(f"Email would be sent to {email}: {subject} - {message}")
    return True

def send_trade_execution_notification(trade_execution):
    """Send a notification about a trade execution."""
    user = trade_execution.user
    
    # Create message content
    message = create_trade_execution_message(trade_execution)
    
    # Send notifications based on user preferences
    if user.enable_telegram_notifications and user.telegram_chat_id:
        send_telegram_message(user.telegram_chat_id, message)
    
    if user.enable_discord_notifications and user.discord_webhook_url:
        send_discord_message(user.discord_webhook_url, message)
    
    if user.enable_email_notifications:
        send_email_notification(user.email, "Trade Execution Notification", message)
    
    logger.info(f"Trade execution notification sent for {trade_execution.trading_pair}")

def create_trade_execution_message(trade):
    """Create a formatted message for a trade execution."""
    # Format the trade message
    message = f"💰 TRADE EXECUTED\n\n"
    message += f"{'🔴 SELL' if trade.order_type == 'SELL' else '🟢 BUY'} {trade.trading_pair}\n\n"
    message += f"Price: {trade.price:.6f}\n"
    message += f"Amount: {trade.amount:.6f}\n"
    message += f"Platform: {trade.platform}\n"
    
    if trade.is_automated:
        message += f"Executed by: {trade.executed_by}\n"
    else:
        message += "Executed manually\n"
    
    message += f"Status: {trade.status}\n"
    
    if trade.pnl:
        message += f"P&L: {trade.pnl:.6f}\n"
    
    message += f"\nTime: {trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    
    return message

def send_error_notification(user_id, error_message):
    """Send a notification about a system error."""
    from models import User
    
    try:
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found for error notification")
            return False
        
        # Create message content
        message = f"⚠️ SYSTEM ERROR\n\n{error_message}\n\nTime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        
        # Send notifications based on user preferences
        if user.enable_telegram_notifications and user.telegram_chat_id:
            send_telegram_message(user.telegram_chat_id, message)
        
        if user.enable_discord_notifications and user.discord_webhook_url:
            send_discord_message(user.discord_webhook_url, message)
        
        if user.enable_email_notifications:
            send_email_notification(user.email, "Trading System Error", message)
        
        logger.info(f"Error notification sent to user {user_id}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send error notification: {e}")
        return False
