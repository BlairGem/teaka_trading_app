import logging
import pandas as pd
import numpy as np
from datetime import datetime
from models import TradeExecution, TradingStrategy, User, db
from config import MAX_POSITION_SIZE_PERCENTAGE, MAX_OPEN_POSITIONS

logger = logging.getLogger(__name__)

def calculate_position_size(account_balance, entry_price, stop_loss, risk_per_trade_pct=1.0):
    """Calculate position size based on risk management parameters."""
    if entry_price <= 0 or stop_loss <= 0:
        logger.error("Invalid entry price or stop loss")
        return 0
    
    # Calculate risk amount in account currency
    risk_amount = account_balance * (risk_per_trade_pct / 100)
    
    # Calculate the difference between entry and stop loss
    if entry_price > stop_loss:  # Long position
        risk_per_unit = entry_price - stop_loss
    else:  # Short position
        risk_per_unit = stop_loss - entry_price
    
    # Avoid division by zero
    if risk_per_unit <= 0:
        logger.error("Risk per unit must be greater than zero")
        return 0
    
    # Calculate position size
    position_size = risk_amount / risk_per_unit
    
    # Convert to units
    units = position_size / entry_price
    
    return units

def check_risk_limits(user, trading_pair, entry_price):
    """Check if a trade passes risk management rules."""
    try:
        # Get account balance
        from broker_apis import get_account_balance
        account_balance_data = get_account_balance(user)
        
        if not account_balance_data:
            logger.error("Failed to get account balance")
            return False
        
        # Determine platform based on trading pair (simplified approach)
        platform = 'binance' if trading_pair in trading_pair.split('/')[1] == 'USDT' else 'oanda'
        
        # Get account balance for the specific platform
        if platform not in account_balance_data:
            logger.error(f"No account balance data for platform {platform}")
            return False
        
        account_balance = account_balance_data[platform].get('balance', 0)
        if platform == 'binance':
            # For Binance, we need to sum up the balances of relevant assets
            if 'balances' in account_balance_data[platform]:
                quote_currency = trading_pair.split('/')[1]  # e.g., USDT for BTC/USDT
                account_balance = account_balance_data[platform]['balances'].get(quote_currency, {}).get('free', 0)
        
        # Get active positions
        from trading_engine import get_active_positions
        active_positions = get_active_positions(user.id)
        
        # Check max positions limit
        max_positions = user.max_open_positions if user.max_open_positions else MAX_OPEN_POSITIONS
        if len(active_positions) >= max_positions:
            logger.warning(f"Maximum number of positions ({max_positions}) already reached")
            return False
        
        # Check for existing position in the same trading pair
        for position in active_positions:
            if position['trading_pair'] == trading_pair:
                logger.warning(f"Position already exists for {trading_pair}")
                return False
        
        # Check max position size as percentage of account
        max_position_size_pct = user.max_position_size_pct if user.max_position_size_pct else MAX_POSITION_SIZE_PERCENTAGE
        max_position_value = account_balance * (max_position_size_pct / 100)
        
        # Check if the potential trade exceeds the maximum position size
        from market_data import get_latest_prices
        latest_prices = get_latest_prices()
        
        # If we can't get the current price, use the entry price
        current_price = latest_prices.get(trading_pair, entry_price)
        
        # Get strategy for this trade
        strategy = TradingStrategy.query.filter_by(user_id=user.id, is_active=True).first()
        
        if not strategy:
            logger.error("No active strategy found for user")
            return False
        
        # Calculate position size based on risk management
        position_size = calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss=entry_price * (1 - strategy.stop_loss_pct / 100),  # Simple calculation for demo
            risk_per_trade_pct=strategy.risk_per_trade_pct
        )
        
        position_value = position_size * current_price
        
        if position_value > max_position_value:
            logger.warning(f"Position value ({position_value}) exceeds maximum allowed ({max_position_value})")
            return False
        
        # All checks passed
        return True
    
    except Exception as e:
        logger.error(f"Error checking risk limits: {e}")
        return False

def calculate_portfolio_risk(user_id):
    """Calculate overall portfolio risk metrics."""
    try:
        # Get user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return None
        
        # Get account balance
        from broker_apis import get_account_balance
        account_balance_data = get_account_balance(user)
        
        if not account_balance_data:
            logger.error("Failed to get account balance")
            return None
        
        # Calculate total account value across all platforms
        total_account_value = 0
        for platform, balance in account_balance_data.items():
            if platform == 'binance':
                # For Binance, sum up USDT and other stablecoin balances
                stablecoins = ['USDT', 'USDC', 'BUSD', 'DAI']
                for coin in stablecoins:
                    if 'balances' in balance and coin in balance['balances']:
                        total_account_value += balance['balances'][coin].get('total', 0)
            else:
                # For other platforms like OANDA
                total_account_value += balance.get('balance', 0)
        
        # Get active positions
        from trading_engine import get_active_positions
        active_positions = get_active_positions(user_id)
        
        # Calculate total position value
        total_position_value = 0
        for position in active_positions:
            amount = position.get('amount', 0)
            price = position.get('current_price') or position.get('entry_price', 0)
            position_value = amount * price
            total_position_value += position_value
        
        # Calculate exposure ratio
        exposure_ratio = total_position_value / total_account_value if total_account_value > 0 else 0
        
        # Get all recent trades
        recent_trades = TradeExecution.query.filter_by(user_id=user_id).order_by(
            TradeExecution.timestamp.desc()).limit(50).all()
        
        # Calculate win rate
        winning_trades = sum(1 for trade in recent_trades if trade.pnl and trade.pnl > 0)
        total_trades = len(recent_trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate average profit/loss
        profits = [trade.pnl for trade in recent_trades if trade.pnl and trade.pnl > 0]
        losses = [abs(trade.pnl) for trade in recent_trades if trade.pnl and trade.pnl <= 0]
        
        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # Calculate profit factor
        profit_factor = sum(profits) / sum(losses) if sum(losses) > 0 else float('inf')
        
        # Calculate expected value
        expected_value = (win_rate * avg_profit) - ((1 - win_rate) * avg_loss)
        
        # Calculate maximum drawdown
        balance_history = []
        cumulative_pnl = 0
        for trade in sorted(recent_trades, key=lambda x: x.timestamp):
            if trade.pnl:
                cumulative_pnl += trade.pnl
                balance_history.append(cumulative_pnl)
        
        max_drawdown = 0
        peak = 0
        
        for balance in balance_history:
            if balance > peak:
                peak = balance
            else:
                drawdown = (peak - balance) / peak if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'total_account_value': total_account_value,
            'total_position_value': total_position_value,
            'exposure_ratio': exposure_ratio,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expected_value': expected_value,
            'max_drawdown': max_drawdown
        }
    
    except Exception as e:
        logger.error(f"Error calculating portfolio risk: {e}")
        return None

def calculate_drawdown(equity_curve):
    """Calculate drawdown from an equity curve."""
    if not equity_curve:
        return 0, []
    
    # Calculate running maximum
    running_max = pd.Series(equity_curve).cummax()
    
    # Calculate drawdown
    drawdown = (running_max - equity_curve) / running_max
    
    # Calculate maximum drawdown
    max_drawdown = drawdown.max()
    
    return max_drawdown, drawdown.tolist()

def calculate_position_exposure(user_id):
    """Calculate position exposure by asset class and trading pair."""
    try:
        # Get user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return None
        
        # Get account balance
        from broker_apis import get_account_balance
        account_balance_data = get_account_balance(user)
        
        if not account_balance_data:
            logger.error("Failed to get account balance")
            return None
        
        # Calculate total account value
        total_account_value = 0
        for platform, balance in account_balance_data.items():
            if platform == 'binance':
                # For Binance, sum up USDT and other stablecoin balances
                stablecoins = ['USDT', 'USDC', 'BUSD', 'DAI']
                for coin in stablecoins:
                    if 'balances' in balance and coin in balance['balances']:
                        total_account_value += balance['balances'][coin].get('total', 0)
            else:
                # For other platforms like OANDA
                total_account_value += balance.get('balance', 0)
        
        # Get active positions
        from trading_engine import get_active_positions
        active_positions = get_active_positions(user_id)
        
        # Calculate exposure by asset class
        forex_exposure = 0
        crypto_exposure = 0
        
        # Calculate exposure by trading pair
        pair_exposure = {}
        
        for position in active_positions:
            amount = position.get('amount', 0)
            price = position.get('current_price') or position.get('entry_price', 0)
            position_value = amount * price
            
            # Add to trading pair exposure
            pair = position.get('trading_pair', '')
            if pair not in pair_exposure:
                pair_exposure[pair] = 0
            pair_exposure[pair] += position_value
            
            # Add to asset class exposure
            if '/' in pair:
                quote_currency = pair.split('/')[1]
                if quote_currency == 'USDT' or quote_currency == 'BTC':
                    crypto_exposure += position_value
                else:
                    forex_exposure += position_value
        
        # Calculate exposure ratios
        forex_exposure_ratio = forex_exposure / total_account_value if total_account_value > 0 else 0
        crypto_exposure_ratio = crypto_exposure / total_account_value if total_account_value > 0 else 0
        
        pair_exposure_ratio = {}
        for pair, value in pair_exposure.items():
            pair_exposure_ratio[pair] = value / total_account_value if total_account_value > 0 else 0
        
        return {
            'total_account_value': total_account_value,
            'forex_exposure': forex_exposure,
            'crypto_exposure': crypto_exposure,
            'forex_exposure_ratio': forex_exposure_ratio,
            'crypto_exposure_ratio': crypto_exposure_ratio,
            'pair_exposure': pair_exposure,
            'pair_exposure_ratio': pair_exposure_ratio
        }
    
    except Exception as e:
        logger.error(f"Error calculating position exposure: {e}")
        return None

def get_risk_metrics_for_strategy(strategy_id):
    """Get risk metrics for a specific strategy."""
    try:
        # Get strategy
        strategy = TradingStrategy.query.get(strategy_id)
        if not strategy:
            logger.error(f"Strategy {strategy_id} not found")
            return None
        
        # Get recent trade executions for this strategy
        trade_executions = TradeExecution.query.filter_by(
            user_id=strategy.user_id, 
            executed_by=strategy.name
        ).order_by(TradeExecution.timestamp.desc()).limit(100).all()
        
        # Calculate win rate
        winning_trades = sum(1 for trade in trade_executions if trade.pnl and trade.pnl > 0)
        total_trades = len(trade_executions)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate average profit/loss
        profits = [trade.pnl for trade in trade_executions if trade.pnl and trade.pnl > 0]
        losses = [abs(trade.pnl) for trade in trade_executions if trade.pnl and trade.pnl <= 0]
        
        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # Calculate profit factor
        profit_factor = sum(profits) / sum(losses) if sum(losses) > 0 else float('inf')
        
        # Calculate expected value
        expected_value = (win_rate * avg_profit) - ((1 - win_rate) * avg_loss)
        
        # Calculate returns by trading pair
        pair_returns = {}
        for trade in trade_executions:
            if trade.trading_pair not in pair_returns:
                pair_returns[trade.trading_pair] = []
            
            if trade.pnl:
                pair_returns[trade.trading_pair].append(trade.pnl)
        
        # Calculate metrics by pair
        pair_metrics = {}
        for pair, returns in pair_returns.items():
            pair_metrics[pair] = {
                'total_trades': len(returns),
                'avg_return': sum(returns) / len(returns) if returns else 0,
                'total_pnl': sum(returns)
            }
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expected_value': expected_value,
            'pair_metrics': pair_metrics
        }
    
    except Exception as e:
        logger.error(f"Error getting risk metrics for strategy: {e}")
        return None
