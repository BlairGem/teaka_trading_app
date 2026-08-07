import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models import TradingStrategy, TradingSignal, TradeExecution, db
from broker_apis import execute_trade, get_account_balance
from signal_generator import generate_signals_for_strategy
from risk_management import calculate_position_size, check_risk_limits
from messaging import send_signal_notification
import config

logger = logging.getLogger(__name__)

def run_trading_engine():
    """Main function to run the trading engine. Should be called periodically."""
    # Get all active strategies
    active_strategies = TradingStrategy.query.filter_by(is_active=True).all()
    
    for strategy in active_strategies:
        try:
            # Generate signals for this strategy
            signals = generate_signals_for_strategy(strategy)
            
            if signals:
                for signal in signals:
                    # Check risk management rules
                    user = strategy.user
                    account_balance = get_account_balance(user)
                    
                    # Verify if the trade passes risk management checks
                    if check_risk_limits(user, signal.trading_pair, signal.entry_price):
                        # Calculate position size based on risk parameters
                        position_size = calculate_position_size(
                            account_balance,
                            signal.entry_price,
                            signal.stop_loss,
                            strategy.risk_per_trade_pct
                        )
                        
                        # Save signal to database
                        db.session.add(signal)
                        db.session.commit()
                        
                        # Send notification about signal
                        send_signal_notification(signal)
                        
                        # Execute trade only when user auto-trading AND live gates allow it
                        if strategy.user.enable_automated_trading and config.live_orders_allowed():
                            execute_trade_from_signal(signal, position_size)
                        elif strategy.user.enable_automated_trading:
                            logger.warning(
                                "Auto-trading requested but live order gates are off "
                                "(TEAKA_MODE/LIVE_TRADING_ENABLED/PRIVATE_EXCHANGE_API_ENABLED)"
                            )
                    else:
                        logger.warning(f"Signal for {signal.trading_pair} rejected due to risk management limits")
        
        except Exception as e:
            logger.error(f"Error processing strategy {strategy.name}: {e}")
            continue

def execute_trade_from_signal(signal, position_size):
    """Execute a trade based on a trading signal."""
    try:
        if not config.live_orders_allowed():
            logger.error("Refusing live execution: paper/safety gates are active")
            return False

        # Get platform from trading pair
        platform = get_platform_for_pair(signal.trading_pair)
        
        # Execute the trade
        order_result = execute_trade(
            user=signal.user,
            platform=platform,
            trading_pair=signal.trading_pair,
            order_type=signal.signal_type,
            amount=position_size,
            price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )
        
        if order_result and 'order_id' in order_result:
            # Create trade execution record
            execution = TradeExecution(
                user_id=signal.user_id,
                signal_id=signal.id,
                trading_pair=signal.trading_pair,
                order_type=signal.signal_type,
                order_id=order_result['order_id'],
                amount=position_size,
                price=signal.entry_price,
                status='pending',
                platform=platform,
                is_automated=True,
                executed_by=signal.strategy.name
            )
            
            # Update signal status
            signal.status = 'executed'
            
            # Save to database
            db.session.add(execution)
            db.session.commit()
            
            logger.info(f"Trade executed successfully: {signal.signal_type} {signal.trading_pair}")
            return True
        else:
            logger.error(f"Failed to execute trade: {order_result}")
            return False
            
    except Exception as e:
        logger.error(f"Error executing trade from signal: {e}")
        return False

def get_platform_for_pair(trading_pair):
    """Determine the appropriate platform for a trading pair."""
    # FOREX pairs typically use OANDA
    if trading_pair in config.FOREX_TRADING_PAIRS:
        return 'oanda'
    # Crypto pairs typically use Binance
    elif trading_pair in config.CRYPTO_TRADING_PAIRS:
        return 'binance'
    else:
        # Default to Binance if unknown
        return 'binance'

def get_active_positions(user_id):
    """Get all active positions for a user."""
    # This would typically call the broker API to get real-time positions
    # For now, we'll use a simple mock implementation
    from broker_apis import get_open_positions
    return get_open_positions(user_id)

def get_recent_trades(user_id, limit=10):
    """Get recent trades for a user."""
    return TradeExecution.query.filter_by(user_id=user_id).order_by(
        TradeExecution.timestamp.desc()).limit(limit).all()

def close_position(user_id, position_id):
    """Close a specific position."""
    from broker_apis import close_position as broker_close_position
    
    # Get the position details
    position = get_position_details(position_id, user_id)
    
    if not position:
        logger.error(f"Position {position_id} not found for user {user_id}")
        return False
    
    # Close the position
    result = broker_close_position(user_id, position_id)
    
    if result:
        # Create a trade execution record for the closing trade
        execution = TradeExecution(
            user_id=user_id,
            trading_pair=position['trading_pair'],
            order_type='SELL' if position['order_type'] == 'BUY' else 'BUY',  # Opposite of original
            order_id=result.get('order_id', ''),
            amount=position['amount'],
            price=result.get('price', 0),
            status='filled',
            platform=position['platform'],
            is_automated=False,
            executed_by='Manual',
            pnl=result.get('pnl', 0)
        )
        
        db.session.add(execution)
        db.session.commit()
        
        logger.info(f"Position {position_id} closed successfully")
        return True
    else:
        logger.error(f"Failed to close position {position_id}")
        return False

def get_position_details(position_id, user_id):
    """Get details for a specific position."""
    from broker_apis import get_position_details as broker_get_position_details
    return broker_get_position_details(position_id, user_id)

def update_orders_status():
    """Update the status of pending orders."""
    from broker_apis import check_order_status
    
    # Get all pending trade executions
    pending_executions = TradeExecution.query.filter_by(status='pending').all()
    
    for execution in pending_executions:
        try:
            # Check order status
            status = check_order_status(
                execution.user_id,
                execution.platform,
                execution.order_id
            )
            
            if status:
                execution.status = status
                if status == 'filled':
                    # If a signal was associated with this trade, update its status
                    if execution.signal:
                        execution.signal.status = 'executed'
                
                db.session.commit()
        except Exception as e:
            logger.error(f"Error updating order status for execution {execution.id}: {e}")
            continue
