import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .models import TradingStrategy, TradingSignal, TradeExecution, db

from .signal_generator import generate_signals_for_strategy, ModelUnavailableError
from .risk_management import calculate_position_size, check_risk_limits, normalize_account_equity

from . import config
from .strategy_contracts import exit_conditions_with_default
from .backtesting import _intrabar_exit_price

logger = logging.getLogger(__name__)


class _CompletedCandles:
    def __init__(self, provider, cutoff):
        self.provider, self.cutoff = provider, cutoff

    def get_historical_data(self, pair, timeframe, *, start_date=None, end_date=None, limit=100):
        return self.provider.get_historical_data(pair, timeframe, start_date=start_date,
            end_date=self.cutoff if end_date is None else min(pd.Timestamp(end_date), self.cutoff), limit=limit)


def _paper_runtime(runtime=None):
    if runtime is None:
        from flask import current_app
        runtime = current_app.extensions['paper_runtime']
    if getattr(runtime, 'mode', None) != 'paper':
        raise ValueError('Only paper execution is supported')
    return runtime


def run_trading_engine(runtime=None, user_id=None, candle_time=None):
    runtime = _paper_runtime(runtime)
    with runtime.lock:
        return _run_paper_candle(runtime, user_id, candle_time)


def _run_paper_candle(runtime, user_id, candle_time):
    """Process one finite local candle through actual ORM strategies and signals."""
    from .paper_runtime import timestamp
    from .technical_indicators import IndicatorUnavailableError
    runtime = _paper_runtime(runtime)
    if user_id is None or candle_time is None:
        raise ValueError('Paper engine requires user_id and candle_time')
    runtime.user(user_id)
    current = timestamp(candle_time)
    runtime.validate_clock_advance(user_id, current)
    if (user_id, current.isoformat()) in runtime.processed_candles:
        return
    provider = runtime.provider
    rows = {pair: frame.loc[current] for pair, frame in provider.frames.items() if current in frame.index}
    if not rows:
        return
    if provider.clock is not None and current < provider.clock:
        raise ValueError('Replay clock cannot move backward')
    # At an open only earlier completed candles may inform the decision.
    prior = sorted({t for frame in provider.frames.values() for t in frame.index if t < current})
    if prior and (provider.clock is None or provider.clock < prior[-1]):
        runtime._advance_clock(user_id, prior[-1])
    broker = runtime.account(user_id)
    for pair, row in rows.items():
        broker.mark(pair.replace('/', '-'), float(row['open']))
    strategies = TradingStrategy.query.filter_by(user_id=user_id, is_active=True).order_by(TradingStrategy.id).all()
    pending = []
    for strategy in strategies:
        if strategy.timeframe != provider.timeframe:
            continue
        keys = [(user_id, strategy.id, pair, current.isoformat()) for pair in strategy.get_trading_pairs() if pair in rows]
        keys = [key for key in keys if key not in runtime.seen]
        if not keys:
            continue
        runtime.seen.update(keys)
        if not prior:
            pending.append((strategy, None, keys, 'Insufficient completed history: no prior candle'))
            continue
        # ML is explicitly unavailable here regardless of inherited live flags.
        if strategy.use_ml_model:
            pending.append((strategy, None, keys, 'ML unavailable in paper runtime'))
            continue
        try:
            completed = _CompletedCandles(provider, prior[-1])
            signals = generate_signals_for_strategy(strategy, market_provider=completed,
                pending_signal_lookup=lambda *_: None, signal_factory=TradingSignal,
                now=prior[-1].to_pydatetime())
            held_pairs = {lot['trading_pair'] for lot in runtime.positions(user_id) if lot['strategy_id'] == strategy.id}
            exits = strategy.get_exit_conditions()
            if held_pairs and exits:
                class ExitRules:
                    def __getattr__(self, name):
                        return getattr(strategy, name)

                    def get_entry_conditions(self):
                        return exit_conditions_with_default(exits)

                exit_signals = generate_signals_for_strategy(ExitRules(), market_provider=completed,
                    pending_signal_lookup=lambda *_: None, signal_factory=TradingSignal,
                    now=prior[-1].to_pydatetime())
                exit_pairs = {s.trading_pair for s in exit_signals if s.signal_type == 'SELL' and s.trading_pair in held_pairs}
                signals = [s for s in signals if s.trading_pair not in exit_pairs] + [s for s in exit_signals if s.trading_pair in exit_pairs and s.signal_type == 'SELL']
            pending.append((strategy, signals, keys, None))
        except (ModelUnavailableError, IndicatorUnavailableError, ValueError) as exc:
            pending.append((strategy, None, keys, str(exc)))
    runtime._advance_clock(user_id, current)
    for strategy, signals, keys, error in pending:
        eligible = {key[2] for key in keys}
        if error:
            for pair in eligible:
                runtime.decision(user_id, strategy.id, pair, 'unavailable', error)
            continue
        for signal in signals:
            if signal.trading_pair not in eligible:
                continue
            pair = signal.trading_pair
            signal.timestamp = current.to_pydatetime()
            signal.entry_price = float(rows[pair]['open'])
            direction = 1 if signal.signal_type == 'BUY' else -1
            signal.stop_loss = signal.entry_price * (1 - direction * strategy.stop_loss_pct / 100)
            signal.take_profit = signal.entry_price * (1 + direction * strategy.take_profit_pct / 100)
            metadata = signal.get_signal_data()
            metadata.update(data_origin=provider.data_origin, decision_candle=prior[-1].isoformat(), execution_candle=current.isoformat())
            signal.set_signal_data(metadata)
            db.session.add(signal)
            db.session.flush()
            if signal.signal_type == 'SELL':
                lot = next((p for p in runtime.positions(user_id) if p['strategy_id'] == strategy.id and p['trading_pair'] == pair), None)
                if lot:
                    runtime.submit(user_id, pair, 'SELL', lot['amount'], signal.entry_price,
                        strategy=strategy, signal=signal, lot_id=lot['id'], reason='signal_exit')
                else:
                    signal.status = 'rejected'
                    runtime.decision(user_id, strategy.id, pair, 'rejected', 'no_owned_position', signal_id=signal.id)
            else:
                quantity = runtime.automatic_quantity(user_id, strategy, signal.entry_price, signal.stop_loss)
                if quantity <= 0:
                    signal.status = 'rejected'
                    runtime.decision(user_id, strategy.id, pair, 'rejected', 'invalid_size', signal_id=signal.id)
                    continue
                runtime.submit(user_id, pair, 'BUY', quantity, signal.entry_price,
                    strategy=strategy, signal=signal, stop=signal.stop_loss, take=signal.take_profit, reason='signal_entry')
        for pair in eligible - {signal.trading_pair for signal in signals}:
            runtime.decision(user_id, strategy.id, pair, 'no_signal', 'No unambiguous rule match on the completed candle')
    # Resolve opening gaps first; remaining intrabar ambiguity chooses the stop.
    for lot in list(runtime.positions(user_id)):
        row = rows.get(lot['trading_pair'])
        if row is None:
            continue
        protection = _intrabar_exit_price(lot, row)
        if protection:
            price, reason = protection
            runtime.close(user_id, lot['id'], price, reason)
    for pair, row in rows.items():
        broker.mark(pair.replace('/', '-'), float(row['close']))
    db.session.commit()
    runtime.processed_candles.add((user_id, current.isoformat()))


def execute_trade_from_signal(signal, position_size, runtime=None, user_id=None):
    runtime = _paper_runtime(runtime)
    if user_id is None or signal.user_id != user_id or signal.strategy.user_id != user_id or signal.status != 'pending':
        return False
    price = runtime.provider.get_latest_prices([signal.trading_pair]).get(signal.trading_pair)
    if price is None:
        return False
    lot = next((p for p in runtime.positions(user_id) if p['strategy_id'] == signal.strategy_id and p['trading_pair'] == signal.trading_pair), None)
    result = runtime.submit(user_id, signal.trading_pair, signal.signal_type, position_size, price,
        strategy=signal.strategy, signal=signal, stop=signal.stop_loss, take=signal.take_profit,
        lot_id=lot['id'] if lot else None, reason='manual_signal')
    return result['success']


def get_active_positions(user_id):
    return _paper_runtime().positions(user_id)


def close_position(user_id, position_id):
    return _paper_runtime().close(user_id, position_id)['success']

def _run_legacy_trading_engine():
    from .broker_apis import get_account_balance
    from .messaging import send_signal_notification
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
                    if check_risk_limits(
                        user,
                        signal.trading_pair,
                        signal.entry_price,
                        strategy=strategy,
                    ):
                        # Calculate position size based on risk parameters
                        position_size = calculate_position_size(
                            normalize_account_equity(account_balance, signal.trading_pair),
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

def _execute_legacy_trade_from_signal(signal, position_size):
    from .broker_apis import execute_trade
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

def _get_legacy_active_positions(user_id):
    """Get all active positions for a user."""
    # This would typically call the broker API to get real-time positions
    # For now, we'll use a simple mock implementation
    from broker_apis import get_open_positions
    return get_open_positions(user_id)

def get_recent_trades(user_id, limit=10):
    """Get recent trades for a user."""
    return TradeExecution.query.filter_by(user_id=user_id).order_by(
        TradeExecution.timestamp.desc()).limit(limit).all()

def _close_legacy_position(user_id, position_id):
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
    return next((position for position in _paper_runtime().positions(user_id)
                 if position['id'] == str(position_id)), None)


def _get_legacy_position_details(position_id, user_id):
    """Get details for a specific position."""
    from broker_apis import get_position_details as broker_get_position_details
    return broker_get_position_details(position_id, user_id)

def update_orders_status():
    _paper_runtime()
    return {'mode': 'paper', 'status': 'synchronous', 'pending_count':
            TradeExecution.query.filter_by(platform='paper', status='pending').count()}


def _update_legacy_orders_status():
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
