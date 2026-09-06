import logging
import math
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    from .strategy_contracts import StrategyContractError, normalize_strategy_contract
    from .signal_generator import ModelUnavailableError, evaluate_condition
except ImportError:  # Preserve direct script-style imports used by the legacy app.
    from strategy_contracts import StrategyContractError, normalize_strategy_contract
    from signal_generator import ModelUnavailableError, evaluate_condition

logger = logging.getLogger(__name__)

def run_backtest(
    strategy_id,
    trading_pair,
    start_date,
    end_date,
    initial_balance=10000.0,
    market_provider=None,
    strategy_lookup=None,
    result_factory=None,
    session=None,
    fee_bps=0.0,
    slippage_bps=0.0,
    model_predictor=None,
):
    """Run a backtest for a strategy on a specific trading pair."""
    try:
        if strategy_lookup is None or result_factory is None or session is None:
            try:
                from .models import TradingStrategy, BacktestResult, db
            except ImportError:
                from models import TradingStrategy, BacktestResult, db
            strategy_lookup = strategy_lookup or TradingStrategy.query.get
            result_factory = result_factory or BacktestResult
            session = session or db.session
        try:
            from .technical_indicators import apply_indicators
        except ImportError:
            from technical_indicators import apply_indicators

        strategy = strategy_lookup(strategy_id)
        if not strategy:
            logger.error(f"Strategy with ID {strategy_id} not found")
            return None
        
        # Convert dates to datetime if they are strings
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Calculate the date range needed (adding buffer for indicators)
        date_buffer = timedelta(days=30)  # Buffer for calculating indicators
        data_start_date = start_date - date_buffer
        
        # Get historical data
        data = get_historical_data_for_backtest(
            trading_pair=trading_pair,
            timeframe=strategy.timeframe,
            start_date=data_start_date,
            end_date=end_date,
            market_provider=market_provider,
        )
        
        if data.empty:
            logger.error(f"No historical data available for {trading_pair}")
            return None
        
        # Apply technical indicators
        indicators_config = strategy.get_indicators_config()
        df_with_indicators = apply_indicators(data, indicators_config)
        
        # Run backtest simulation
        if strategy.use_ml_model and strategy.ml_model_id:
            # Backtest with ML model
            backtest_results = backtest_ml_strategy(
                strategy=strategy,
                data=df_with_indicators,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance,
                model_predictor=model_predictor,
            )
        else:
            # Backtest with technical indicators
            backtest_results = backtest_technical_strategy(
                strategy=strategy,
                data=df_with_indicators,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )
        
        # Calculate performance metrics
        performance_metrics = calculate_performance_metrics(backtest_results)
        
        # Save backtest results to database
        backtest_result = result_factory(
            user_id=strategy.user_id,
            strategy_id=strategy.id,
            trading_pair=trading_pair,
            timeframe=strategy.timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance,
            final_balance=backtest_results['final_balance'],
            total_trades=performance_metrics['total_trades'],
            winning_trades=performance_metrics['winning_trades'],
            losing_trades=performance_metrics['losing_trades'],
            profit_factor=performance_metrics['profit_factor'],
            max_drawdown_pct=performance_metrics['max_drawdown_pct'],
            sharpe_ratio=performance_metrics['sharpe_ratio']
        )
        
        # Set detailed result data
        result_data = {
            'trades': backtest_results['trades'],
            'equity_curve': backtest_results['equity_curve'],
            'drawdown_curve': backtest_results['drawdown_curve'],
            'data_origin': backtest_results.get('data_origin'),
            'time_range': backtest_results.get('time_range'),
            'assumptions': backtest_results.get('assumptions'),
            'metrics': performance_metrics
        }
        backtest_result.set_result_data(result_data)
        
        # Save to database
        session.add(backtest_result)
        session.commit()
        
        logger.info(f"Backtest completed for strategy {strategy.name} on {trading_pair}")
        return backtest_result.id
    
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return None

def get_historical_data_for_backtest(
    trading_pair, timeframe, start_date, end_date, market_provider=None
):
    """Get historical data for backtesting."""
    # This would typically call an API or database to get historical data
    # For simplicity, we're reusing the market_data function but in a real system
    # you might have a separate function for getting larger historical datasets
    
    try:
        from .market_data import get_historical_data
    except ImportError:
        from market_data import get_historical_data
    return get_historical_data(
        trading_pair,
        timeframe,
        limit=5000,
        start_date=start_date,
        end_date=end_date,
        provider=market_provider,
    )

def _utc_timestamp(value, field):
    try:
        return pd.to_datetime(value, utc=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO date or datetime") from exc


def _timestamp_text(value):
    return _utc_timestamp(value, "timestamp").isoformat()


def _empty_backtest_result(initial_balance, start_date, end_date, data_origin):
    return {
        "final_balance": float(initial_balance),
        "trades": [],
        "equity_curve": [float(initial_balance)],
        "drawdown_curve": [0.0],
        "data_origin": data_origin,
        "time_range": {
            "start": _timestamp_text(start_date),
            "end": _timestamp_text(end_date),
        },
        "assumptions": {
            "position_model": "long_only",
            "fees": "charged on entry and exit notionals",
            "slippage": "BUY adds bps; SELL subtracts bps",
        },
    }


def _matching_rule_sides(conditions, row, previous_row):
    matches = []
    for side in ("BUY", "SELL"):
        rules = [rule for rule in conditions if rule["signal_type"] == side]
        if rules and all(
            rule["indicator"] in row
            and evaluate_condition(
                row[rule["indicator"]],
                rule["operator"],
                rule["value"],
                previous_row[rule["indicator"]]
                if previous_row is not None and rule["indicator"] in previous_row
                else None,
            )
            for rule in rules
        ):
            matches.append(side)
    return matches


def backtest_technical_strategy(
    strategy,
    data,
    start_date,
    end_date,
    initial_balance,
    fee_bps=0.0,
    slippage_bps=0.0,
):
    """Replay a long-only strategy using completed candles and next-open fills."""
    numbers = (initial_balance, fee_bps, slippage_bps)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in numbers
    ):
        raise ValueError("balance, fees and slippage must be finite numbers")
    if initial_balance <= 0 or not 0 <= fee_bps < 10_000 or not 0 <= slippage_bps < 10_000:
        raise ValueError("invalid balance, fee or slippage bounds")
    start = _utc_timestamp(start_date, "start_date")
    end = _utc_timestamp(end_date, "end_date")
    if start > end:
        raise ValueError("start_date must be on or before end_date")

    data_origin = str(
        data.attrs.get("data_origin", "provided-dataframe")
        if isinstance(data, pd.DataFrame)
        else "unavailable"
    )
    empty = _empty_backtest_result(initial_balance, start, end, data_origin)
    if not isinstance(data, pd.DataFrame) or data.empty:
        return empty
    frame = data.copy()
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame = frame.sort_index()
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns):
        return empty
    period = frame.loc[start:end]
    if period.empty:
        return empty

    try:
        _, entry_conditions = normalize_strategy_contract(
            strategy.get_indicators_config(), strategy.get_entry_conditions()
        )
        _, exit_conditions = normalize_strategy_contract(
            strategy.get_indicators_config(), strategy.get_exit_conditions()
        )
    except (StrategyContractError, TypeError, ValueError):
        return empty
    if not entry_conditions:
        return empty

    risk_pct = getattr(strategy, "risk_per_trade_pct", None)
    stop_pct = getattr(strategy, "stop_loss_pct", None)
    take_pct = getattr(strategy, "take_profit_pct", None)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 < value <= 100
        for value in (risk_pct, stop_pct, take_pct)
    ):
        return empty

    fee_rate = fee_bps / 10_000
    slippage_rate = slippage_bps / 10_000
    balance = float(initial_balance)
    position = None
    trades = []
    equity_curve = [balance]
    drawdown_curve = [0.0]
    high_water = balance

    def close_position(timestamp, raw_price, reason):
        nonlocal balance, position
        fill_price = float(raw_price) * (1 - slippage_rate)
        proceeds = position["quantity"] * fill_price
        exit_fee = proceeds * fee_rate
        pnl = proceeds - exit_fee - position["cost_basis"]
        balance += proceeds - exit_fee
        trades.append(
            {
                "entry_time": position["entry_time"],
                "exit_time": _timestamp_text(timestamp),
                "type": "BUY",
                "entry_price": position["entry_price"],
                "exit_price": fill_price,
                "size": position["notional"],
                "quantity": position["quantity"],
                "entry_fee": position["entry_fee"],
                "exit_fee": exit_fee,
                "pnl": pnl,
                "exit_reason": reason,
            }
        )
        position = None

    for timestamp, execution_row in period.iterrows():
        full_location = frame.index.get_loc(timestamp)
        if not isinstance(full_location, int) or full_location == 0:
            continue
        signal_row = frame.iloc[full_location - 1]
        previous_signal_row = frame.iloc[full_location - 2] if full_location >= 2 else None
        closed_this_candle = False

        if position is not None:
            if float(execution_row["low"]) <= position["stop_loss"]:
                close_position(timestamp, position["stop_loss"], "stop_loss")
                closed_this_candle = True
            elif float(execution_row["high"]) >= position["take_profit"]:
                close_position(timestamp, position["take_profit"], "take_profit")
                closed_this_candle = True

        entry_sides = _matching_rule_sides(
            entry_conditions, signal_row, previous_signal_row
        )
        exit_sides = _matching_rule_sides(
            exit_conditions, signal_row, previous_signal_row
        )
        unambiguous_entry = entry_sides[0] if len(entry_sides) == 1 else None
        unambiguous_exit = exit_sides[0] if len(exit_sides) == 1 else None

        if position is not None and (
            unambiguous_entry == "SELL" or unambiguous_exit == "SELL"
        ):
            close_position(timestamp, execution_row["open"], "signal")
            closed_this_candle = True
        elif position is None and not closed_this_candle and unambiguous_entry == "BUY":
            entry_price = float(execution_row["open"]) * (1 + slippage_rate)
            if math.isfinite(entry_price) and entry_price > 0:
                notional = balance * (risk_pct / 100)
                entry_fee = notional * fee_rate
                if notional > 0 and notional + entry_fee <= balance:
                    quantity = notional / entry_price
                    balance -= notional + entry_fee
                    position = {
                        "entry_time": _timestamp_text(timestamp),
                        "entry_price": entry_price,
                        "notional": notional,
                        "quantity": quantity,
                        "entry_fee": entry_fee,
                        "cost_basis": notional + entry_fee,
                        "stop_loss": entry_price * (1 - stop_pct / 100),
                        "take_profit": entry_price * (1 + take_pct / 100),
                    }

        equity = balance
        if position is not None:
            equity += position["quantity"] * float(execution_row["close"])
        high_water = max(high_water, equity)
        drawdown = (high_water - equity) / high_water * 100 if high_water > 0 else 0.0
        equity_curve.append(float(equity))
        drawdown_curve.append(float(drawdown))

    if position is not None:
        final_timestamp = period.index[-1]
        close_position(final_timestamp, period.iloc[-1]["close"], "end_of_test")
        equity_curve[-1] = balance
        high_water = max(high_water, balance)
        drawdown_curve[-1] = (
            (high_water - balance) / high_water * 100 if high_water > 0 else 0.0
        )

    result = _empty_backtest_result(initial_balance, start, end, data_origin)
    result.update(
        {
            "final_balance": float(balance),
            "trades": trades,
            "equity_curve": equity_curve,
            "drawdown_curve": drawdown_curve,
            "assumptions": {
                "position_model": "long_only",
                "fee_bps": float(fee_bps),
                "slippage_bps": float(slippage_bps),
                "fees": "charged on entry and exit notionals",
                "slippage": "BUY adds bps; SELL subtracts bps",
            },
        }
    )
    return result


def backtest_ml_strategy(
    strategy,
    data,
    start_date,
    end_date,
    initial_balance,
    model_predictor=None,
):
    """Run a backtest simulation using ML model predictions."""
    if model_predictor is None:
        import os

        if os.environ.get("TEAKA_MODE", "paper").lower() == "paper":
            raise ModelUnavailableError(
                "paper ML backtests require an explicitly injected model predictor"
            )
        try:
            from .ml_models import predict_with_model
        except ImportError:
            try:
                from ml_models import predict_with_model
            except ImportError as exc:
                raise ModelUnavailableError("ML model implementation is unavailable") from exc
        model_predictor = predict_with_model
    start = _utc_timestamp(start_date, "start_date")
    end = _utc_timestamp(end_date, "end_date")
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    data_origin = str(
        data.attrs.get("data_origin", "provided-dataframe")
        if isinstance(data, pd.DataFrame)
        else "unavailable"
    )
    empty = _empty_backtest_result(initial_balance, start, end, data_origin)
    if not isinstance(data, pd.DataFrame) or data.empty:
        return empty
    frame = data.copy()
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame = frame.sort_index()
    backtest_data = frame.loc[start:end]

    if backtest_data.empty:
        logger.warning("No data available for backtest period")
        return empty
    
    # Initialize backtest variables
    balance = initial_balance
    position = None
    trades = []
    equity_curve = [balance]
    max_equity = balance
    drawdown_curve = [0.0]
    
    # Iterate through each candle
    for i, (idx, row) in enumerate(backtest_data.iterrows()):
        if i < 10:  # Skip the first few rows to ensure we have enough data for prediction
            continue
        
        # Generate the decision from completed candles, then execute at this
        # candle's open. The execution candle is never model input.
        prediction_data = backtest_data.iloc[i-10:i].copy()
        
        # Get prediction from ML model
        prediction, confidence = model_predictor(
            model_id=strategy.ml_model_id,
            data=prediction_data
        )
        
        # Check for exit if we have an open position
        if position:
            # Check stop loss and take profit
            if position['type'] == 'BUY':
                # Check if price hit stop loss
                if row['low'] <= position['stop_loss']:
                    # Stop loss hit
                    exit_price = position['stop_loss']
                    trade_result = (exit_price - position['entry_price']) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': _timestamp_text(idx),
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'stop_loss',
                        'confidence': position['confidence']
                    })
                    
                    position = None
                
                # Check if price hit take profit
                elif row['high'] >= position['take_profit']:
                    # Take profit hit
                    exit_price = position['take_profit']
                    trade_result = (exit_price - position['entry_price']) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': _timestamp_text(idx),
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'take_profit',
                        'confidence': position['confidence']
                    })
                    
                    position = None
                
                # Check for exit signal (if prediction changes direction)
                elif prediction < 0 and confidence >= 0.6:
                    # Exit on opposite signal
                    exit_price = row['open']
                    trade_result = (exit_price - position['entry_price']) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': _timestamp_text(idx),
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'signal',
                        'confidence': position['confidence'],
                        'exit_confidence': confidence
                    })
                    
                    position = None
            
            elif position['type'] == 'SELL':
                # Check if price hit stop loss
                if row['high'] >= position['stop_loss']:
                    # Stop loss hit
                    exit_price = position['stop_loss']
                    trade_result = (position['entry_price'] - exit_price) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': _timestamp_text(idx),
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'stop_loss',
                        'confidence': position['confidence']
                    })
                    
                    position = None
                
                # Check if price hit take profit
                elif row['low'] <= position['take_profit']:
                    # Take profit hit
                    exit_price = position['take_profit']
                    trade_result = (position['entry_price'] - exit_price) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': _timestamp_text(idx),
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'take_profit',
                        'confidence': position['confidence']
                    })
                    
                    position = None
                
                # Check for exit signal (if prediction changes direction)
                elif prediction > 0 and confidence >= 0.6:
                    # Exit on opposite signal
                    exit_price = row['open']
                    trade_result = (position['entry_price'] - exit_price) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': _timestamp_text(idx),
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'signal',
                        'confidence': position['confidence'],
                        'exit_confidence': confidence
                    })
                    
                    position = None
        
        # Check for entry if we don't have an open position
        if not position and confidence >= 0.6:  # Only enter if confidence is above threshold
            if prediction > 0:  # Buy signal
                entry_price = row['open']
                position_size = balance * (strategy.risk_per_trade_pct / 100)
                stop_loss = entry_price * (1 - strategy.stop_loss_pct / 100)
                take_profit = entry_price * (1 + strategy.take_profit_pct / 100)
                
                position = {
                    'type': 'BUY',
                    'entry_time': _timestamp_text(idx),
                    'entry_price': entry_price,
                    'size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': confidence
                }
                
                balance -= position_size
            
            # Negative predictions are exit-only in the paper contract. They
            # never open a short position.
        
        # Update equity and drawdown
        current_equity = balance
        if position:
            # Add unrealized P&L
            if position['type'] == 'BUY':
                trade_result = (row['close'] - position['entry_price']) / position['entry_price']
            else:
                trade_result = (position['entry_price'] - row['close']) / position['entry_price']
            
            current_equity += position['size'] + (position['size'] * trade_result)
        
        equity_curve.append(current_equity)
        max_equity = max(max_equity, current_equity)
        current_drawdown = (max_equity - current_equity) / max_equity * 100 if max_equity > 0 else 0
        drawdown_curve.append(current_drawdown)
    
    # Close any open position at the end of the backtest
    if position:
        exit_price = backtest_data.iloc[-1]['close']
        
        if position['type'] == 'BUY':
            trade_result = (exit_price - position['entry_price']) / position['entry_price']
        else:
            trade_result = (position['entry_price'] - exit_price) / position['entry_price']
        
        pnl = position['size'] * trade_result
        balance += position['size'] + pnl
        
        # Record the trade
        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': _timestamp_text(backtest_data.index[-1]),
            'type': position['type'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'size': position['size'],
            'pnl': pnl,
            'exit_reason': 'end_of_test',
            'confidence': position['confidence']
        })
    
    result = _empty_backtest_result(initial_balance, start, end, data_origin)
    result.update(
        {
            'final_balance': float(balance),
            'trades': trades,
            'equity_curve': [float(value) for value in equity_curve],
            'drawdown_curve': [float(value) for value in drawdown_curve],
            'assumptions': {
                'position_model': 'long_only',
                'prediction_input': 'ten completed candles',
                'execution': 'next candle open; final open position closes at final close',
            },
        }
    )
    return result

def evaluate_backtest_condition(row, prev_row, condition):
    """Evaluate a condition for backtest signal generation."""
    try:
        indicator = condition['indicator']
        if indicator not in row or indicator not in prev_row:
            logger.warning(f"Indicator {indicator} not found in backtest data")
            return False
        return evaluate_condition(
            row[indicator],
            condition['operator'],
            condition['value'],
            prev_row[indicator],
        )
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error evaluating backtest condition: {e}")
        return False

def calculate_performance_metrics(backtest_results):
    """Calculate performance metrics from backtest results."""
    trades = backtest_results['trades']
    equity_curve = backtest_results['equity_curve']
    drawdown_curve = backtest_results['drawdown_curve']
    
    # Basic metrics
    total_trades = len(trades)
    if total_trades == 0:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'profit_factor': None,
            'average_profit': 0.0,
            'average_loss': 0.0,
            'max_drawdown_pct': 0.0,
            'sharpe_ratio': 0.0,
            'return_pct': 0.0
        }
    
    winning_trades = sum(1 for trade in trades if trade['pnl'] > 0)
    losing_trades = sum(1 for trade in trades if trade['pnl'] <= 0)
    
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    # Profit and loss metrics
    total_profit = sum(trade['pnl'] for trade in trades if trade['pnl'] > 0)
    total_loss = abs(sum(trade['pnl'] for trade in trades if trade['pnl'] <= 0))
    
    # No-loss samples have no profit-factor denominator. None serializes as JSON
    # null and states that the ratio is unavailable without inventing a value.
    profit_factor = total_profit / total_loss if total_loss > 0 else None
    
    average_profit = total_profit / winning_trades if winning_trades > 0 else 0
    average_loss = total_loss / losing_trades if losing_trades > 0 else 0
    
    # Drawdown
    max_drawdown_pct = max(drawdown_curve) if drawdown_curve else 0
    
    # Return
    initial_balance = backtest_results['equity_curve'][0]
    final_balance = backtest_results['final_balance']
    return_pct = (
        (final_balance - initial_balance) / initial_balance * 100
        if initial_balance and math.isfinite(initial_balance)
        else 0.0
    )
    
    # Sharpe ratio (simplified)
    if len(equity_curve) > 1:
        # Calculate daily returns
        daily_returns = [
            (equity_curve[i] / equity_curve[i-1]) - 1
            for i in range(1, len(equity_curve))
            if equity_curve[i - 1]
            and math.isfinite(equity_curve[i - 1])
            and math.isfinite(equity_curve[i])
        ]
        if not daily_returns:
            daily_returns = [0.0]
        avg_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)
        sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0  # Annualized
    else:
        sharpe_ratio = 0
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'average_profit': average_profit,
        'average_loss': average_loss,
        'max_drawdown_pct': max_drawdown_pct,
        'sharpe_ratio': sharpe_ratio,
        'return_pct': return_pct
    }

def get_available_strategies(user_id, strategy_model=None):
    """Get available strategies for backtesting."""
    if strategy_model is None:
        try:
            from .models import TradingStrategy as strategy_model
        except ImportError:
            from models import TradingStrategy as strategy_model
    return strategy_model.query.filter_by(user_id=user_id).all()

def get_backtest_result(backtest_id, result_model=None):
    """Get a specific backtest result."""
    if result_model is None:
        try:
            from .models import BacktestResult as result_model
        except ImportError:
            from models import BacktestResult as result_model
    result = result_model.query.get(backtest_id)
    if result:
        return {
            'id': result.id,
            'strategy_name': result.strategy.name,
            'trading_pair': result.trading_pair,
            'timeframe': result.timeframe,
            'start_date': result.start_date,
            'end_date': result.end_date,
            'initial_balance': result.initial_balance,
            'final_balance': result.final_balance,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'profit_factor': result.profit_factor,
            'max_drawdown_pct': result.max_drawdown_pct,
            'sharpe_ratio': result.sharpe_ratio,
            'result_data': result.get_result_data()
        }
    return None
