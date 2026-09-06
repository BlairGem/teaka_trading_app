import logging
import math

try:
    from .config import MAX_POSITION_SIZE_PERCENTAGE, MAX_OPEN_POSITIONS
except ImportError:  # Preserve direct script-style imports used by the legacy app.
    from config import MAX_POSITION_SIZE_PERCENTAGE, MAX_OPEN_POSITIONS

logger = logging.getLogger(__name__)

def calculate_position_size(account_balance, entry_price, stop_loss, risk_per_trade_pct=1.0):
    """Return asset units whose stop distance risks the requested equity percent."""
    values = (account_balance, entry_price, stop_loss, risk_per_trade_pct)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in values
    ):
        return 0.0
    if account_balance <= 0 or entry_price <= 0 or stop_loss <= 0:
        return 0.0
    if not 0 < risk_per_trade_pct <= 100:
        return 0.0

    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit <= 0:
        return 0.0

    risk_amount = account_balance * (risk_per_trade_pct / 100)
    return risk_amount / risk_per_unit


def platform_for_trading_pair(trading_pair):
    if not isinstance(trading_pair, str):
        return None
    parts = trading_pair.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return "binance" if parts[1].upper() == "USDT" else "oanda"


def _positive_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def normalize_account_equity(account_balance_data, trading_pair=None):
    """Extract positive equity from paper snapshots or legacy broker balances."""
    direct = _positive_number(account_balance_data)
    if direct is not None:
        return direct
    equity_method = getattr(account_balance_data, "equity", None)
    if callable(equity_method):
        return _positive_number(equity_method()) or 0.0
    if not isinstance(account_balance_data, dict):
        return 0.0

    platform = platform_for_trading_pair(trading_pair) if trading_pair else None
    if platform and platform in account_balance_data:
        platform_data = account_balance_data[platform]
        if platform == "binance" and isinstance(platform_data, dict):
            quote = trading_pair.split("/")[1].upper()
            balances = platform_data.get("balances")
            if isinstance(balances, dict) and isinstance(balances.get(quote), dict):
                quote_data = balances[quote]
                for field in ("free", "total", "balance"):
                    value = _positive_number(quote_data.get(field))
                    if value is not None:
                        return value
        nested = normalize_account_equity(platform_data, trading_pair)
        if nested > 0:
            return nested

    for field in ("equity", "balance", "cash"):
        value = _positive_number(account_balance_data.get(field))
        if value is not None:
            return value
    for field in ("paper", "account", "snapshot"):
        if field in account_balance_data:
            nested = normalize_account_equity(account_balance_data[field], trading_pair)
            if nested > 0:
                return nested
    return 0.0


def check_risk_limits(
    user,
    trading_pair,
    entry_price,
    account_balance_provider=None,
    active_positions_provider=None,
    latest_prices_provider=None,
    strategy_provider=None,
    strategy=None,
):
    """Check if a trade passes risk management rules."""
    try:
        if _positive_number(entry_price) is None or platform_for_trading_pair(trading_pair) is None:
            return False

        if account_balance_provider is None:
            try:
                from .broker_apis import get_account_balance
            except ImportError:
                from broker_apis import get_account_balance
            account_balance_provider = get_account_balance
        if active_positions_provider is None:
            try:
                from .trading_engine import get_active_positions
            except ImportError:
                from trading_engine import get_active_positions
            active_positions_provider = get_active_positions
        if latest_prices_provider is None:
            try:
                from .market_data import get_latest_prices
            except ImportError:
                from market_data import get_latest_prices
            latest_prices_provider = get_latest_prices
        account_balance = normalize_account_equity(
            account_balance_provider(user), trading_pair
        )
        if account_balance <= 0:
            return False
        active_positions = active_positions_provider(user.id)
        if not isinstance(active_positions, (list, tuple)):
            return False

        max_positions = getattr(user, "max_open_positions", None)
        if max_positions is None:
            max_positions = MAX_OPEN_POSITIONS
        if isinstance(max_positions, bool) or not isinstance(max_positions, int) or max_positions <= 0:
            return False
        if len(active_positions) >= max_positions:
            return False
        for position in active_positions:
            if isinstance(position, dict) and position.get("trading_pair") == trading_pair:
                return False

        max_position_size_pct = getattr(user, "max_position_size_pct", None)
        if max_position_size_pct is None:
            max_position_size_pct = MAX_POSITION_SIZE_PERCENTAGE
        if (
            _positive_number(max_position_size_pct) is None
            or max_position_size_pct > 100
        ):
            return False
        max_position_value = account_balance * (max_position_size_pct / 100)

        latest_prices = latest_prices_provider()
        current_price = (
            latest_prices.get(trading_pair, entry_price)
            if isinstance(latest_prices, dict)
            else entry_price
        )
        if _positive_number(current_price) is None:
            return False

        if strategy is None and strategy_provider is not None:
            strategy = strategy_provider(user.id)
        if not strategy:
            return False
        stop_loss_pct = getattr(strategy, "stop_loss_pct", None)
        risk_pct = getattr(strategy, "risk_per_trade_pct", None)
        if (
            _positive_number(stop_loss_pct) is None
            or stop_loss_pct >= 100
            or _positive_number(risk_pct) is None
            or risk_pct > 100
        ):
            return False
        derived_stop = entry_price * (1 - stop_loss_pct / 100)
        if _positive_number(derived_stop) is None:
            return False
        position_size = calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss=derived_stop,
            risk_per_trade_pct=risk_pct,
        )
        position_value = position_size * current_price
        return (
            _positive_number(position_size) is not None
            and _positive_number(position_value) is not None
            and position_value <= max_position_value
        )
    except Exception as e:
        logger.error(f"Error checking risk limits: {e}")
        return False

def calculate_portfolio_risk(user_id):
    """Calculate overall portfolio risk metrics."""
    try:
        try:
            from .models import TradeExecution, User
            from .broker_apis import get_account_balance
            from .trading_engine import get_active_positions
        except ImportError:
            from models import TradeExecution, User
            from broker_apis import get_account_balance
            from trading_engine import get_active_positions

        # Get user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return None
        
        # Get account balance
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
        profit_factor = sum(profits) / sum(losses) if sum(losses) > 0 else None
        
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

    running_max = None
    drawdown = []
    for raw_value in equity_curve:
        value = _positive_number(raw_value)
        if value is None:
            return 0, []
        running_max = value if running_max is None else max(running_max, value)
        drawdown.append((running_max - value) / running_max)
    return max(drawdown), drawdown

def calculate_position_exposure(user_id):
    """Calculate position exposure by asset class and trading pair."""
    try:
        try:
            from .models import User
            from .broker_apis import get_account_balance
            from .trading_engine import get_active_positions
        except ImportError:
            from models import User
            from broker_apis import get_account_balance
            from trading_engine import get_active_positions

        # Get user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return None
        
        # Get account balance
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
        try:
            from .models import TradeExecution, TradingStrategy
        except ImportError:
            from models import TradeExecution, TradingStrategy

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
        profit_factor = sum(profits) / sum(losses) if sum(losses) > 0 else None
        
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
