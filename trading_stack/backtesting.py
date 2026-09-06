import logging
import math
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    from .strategy_contracts import StrategyContractError, normalize_strategy_contract, exit_conditions_with_default, required_history
    from .signal_generator import ModelUnavailableError, evaluate_condition
    from .risk_management import calculate_position_size
except ImportError:  # Preserve direct script-style imports used by the legacy app.
    from strategy_contracts import StrategyContractError, normalize_strategy_contract, exit_conditions_with_default, required_history
    from signal_generator import ModelUnavailableError, evaluate_condition
    from risk_management import calculate_position_size

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
        
        # Fetch all bounded completed history to retain recursive EMA/RSI state.
        data_start_date = datetime(1970, 1, 1, tzinfo=getattr(start_date, 'tzinfo', None))
        
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
        df_with_indicators = apply_indicators(data, indicators_config, optional_backend=False)
        
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
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
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
            'coverage': backtest_results.get('coverage'),
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
    data = get_historical_data(
        trading_pair,
        timeframe,
        limit=100001,
        start_date=start_date,
        end_date=end_date,
        provider=market_provider,
    )
    if len(data) > 100000:
        raise ValueError('Backtest history exceeds the 100000 candle paper limit; use a smaller dataset')
    return data

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


def _finite_float(value, field):
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


def _replay_economics(strategy, initial_balance, fee_bps, slippage_bps):
    balance = _finite_float(initial_balance, "initial_balance")
    fee = _finite_float(fee_bps, "fee_bps")
    slippage = _finite_float(slippage_bps, "slippage_bps")
    risk = _finite_float(getattr(strategy, "risk_per_trade_pct", None), "risk_per_trade_pct")
    stop = _finite_float(getattr(strategy, "stop_loss_pct", None), "stop_loss_pct")
    take = _finite_float(getattr(strategy, "take_profit_pct", None), "take_profit_pct")
    if balance <= 0:
        raise ValueError("initial_balance must be positive")
    if not 0 <= fee < 10_000 or not 0 <= slippage < 10_000:
        raise ValueError("fee_bps and slippage_bps must be in [0, 10000)")
    if not 0 < risk <= 100:
        raise ValueError("risk_per_trade_pct must be in (0, 100]")
    if not 0 < stop < 100:
        raise ValueError("stop_loss_pct must be in (0, 100)")
    if not 0 < take <= 100:
        raise ValueError("take_profit_pct must be in (0, 100]")
    return balance, risk, stop, take, fee / 10_000, slippage / 10_000


def _validated_replay_frame(data):
    required = ["open", "high", "low", "close", "volume"]
    if data is None:
        return pd.DataFrame(columns=required)
    if not isinstance(data, pd.DataFrame):
        raise ValueError("backtest data must be a pandas DataFrame")
    if data.empty:
        return data.copy()
    if any(column not in data.columns for column in required):
        raise ValueError("backtest data must contain open/high/low/close/volume")

    frame = data.copy()
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame = frame.sort_index()
    if not frame.index.is_unique:
        raise ValueError("backtest timestamps must be unique")
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    values = frame[required]
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("backtest OHLCV values must be finite")
    prices = values[["open", "high", "low", "close"]]
    if not (prices > 0).all().all() or not (values["volume"] >= 0).all():
        raise ValueError("backtest prices must be positive and volume non-negative")
    valid_ranges = (
        (values["high"] >= values[["open", "close"]].max(axis=1)).all()
        and (values["low"] <= values[["open", "close"]].min(axis=1)).all()
        and (values["high"] >= values["low"]).all()
    )
    if not valid_ranges:
        raise ValueError("backtest candle high/low ranges are invalid")
    return frame


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


def _open_long(
    balance,
    timestamp,
    raw_open,
    risk_pct,
    stop_pct,
    take_pct,
    fee_rate,
    slippage_rate,
    confidence=None,
):
    entry_price = _finite_float(raw_open, "entry price") * (1 + slippage_rate)
    stop_loss = entry_price * (1 - stop_pct / 100)
    take_profit = entry_price * (1 + take_pct / 100)
    if (
        not math.isfinite(entry_price)
        or not math.isfinite(stop_loss)
        or not math.isfinite(take_profit)
        or min(entry_price, stop_loss, take_profit) <= 0
    ):
        raise ValueError("derived entry, stop and take prices must be finite and positive")

    risk_quantity = calculate_position_size(
        balance, entry_price, stop_loss, risk_pct
    )
    affordable_quantity = balance / (entry_price * (1 + fee_rate))
    quantity = min(risk_quantity, affordable_quantity)
    if not math.isfinite(quantity) or quantity <= 0:
        raise ValueError("derived position quantity must be finite and positive")

    notional = quantity * entry_price
    entry_fee = notional * fee_rate
    cost_basis = notional + entry_fee
    if cost_basis > balance:
        quantity *= balance / cost_basis
        notional = quantity * entry_price
        entry_fee = notional * fee_rate
        cost_basis = notional + entry_fee
    if not all(
        math.isfinite(value) and value > 0
        for value in (quantity, notional, cost_basis)
    ):
        raise ValueError("derived position economics must be finite and positive")

    position = {
        "type": "BUY",
        "entry_time": _timestamp_text(timestamp),
        "entry_price": float(entry_price),
        "quantity": float(quantity),
        "notional": float(notional),
        "size": float(notional),
        "entry_fee": float(entry_fee),
        "cost_basis": float(cost_basis),
        "stop_loss": float(stop_loss),
        "take_profit": float(take_profit),
    }
    if confidence is not None:
        position["confidence"] = float(confidence)
    return position, float(balance - cost_basis)


def _close_long(balance, position, timestamp, raw_price, reason, fee_rate, slippage_rate, **extra):
    exit_price = _finite_float(raw_price, "exit price") * (1 - slippage_rate)
    if not math.isfinite(exit_price) or exit_price <= 0:
        raise ValueError("derived exit price must be finite and positive")
    proceeds = position["quantity"] * exit_price
    exit_fee = proceeds * fee_rate
    pnl = proceeds - exit_fee - position["cost_basis"]
    if not all(math.isfinite(value) for value in (proceeds, exit_fee, pnl)):
        raise ValueError("derived exit economics must be finite")
    trade = {
        "entry_time": position["entry_time"],
        "exit_time": _timestamp_text(timestamp),
        "type": "BUY",
        "entry_price": position["entry_price"],
        "exit_price": float(exit_price),
        "size": position["notional"],
        "quantity": position["quantity"],
        "entry_fee": position["entry_fee"],
        "exit_fee": float(exit_fee),
        "pnl": float(pnl),
        "exit_reason": reason,
    }
    if "confidence" in position:
        trade["confidence"] = position["confidence"]
    trade.update(extra)
    return float(balance + proceeds - exit_fee), trade


def _intrabar_exit_price(position, row):
    opening = float(row["open"])
    if opening <= position["stop_loss"]:
        return opening, "stop_loss"
    if opening >= position["take_profit"]:
        return opening, "take_profit"
    if float(row["low"]) <= position["stop_loss"]:
        return position["stop_loss"], "stop_loss"
    if float(row["high"]) >= position["take_profit"]:
        return position["take_profit"], "take_profit"
    return None


def _mark_equity(balance, position, close):
    equity = balance
    if position is not None:
        equity += position["quantity"] * float(close)
    if not math.isfinite(equity):
        raise ValueError("derived equity must be finite")
    return float(equity)


def backtest_technical_strategy(
    strategy,
    data,
    start_date,
    end_date,
    initial_balance,
    fee_bps=0.0,
    slippage_bps=0.0,
):
    """Replay a long-only strategy in open, intrabar, close event order."""
    balance, risk_pct, stop_pct, take_pct, fee_rate, slippage_rate = (
        _replay_economics(
            strategy, initial_balance, fee_bps, slippage_bps
        )
    )
    start = _utc_timestamp(start_date, "start_date")
    end = _utc_timestamp(end_date, "end_date")
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    data_origin = str(
        data.attrs.get("data_origin", "provided-dataframe")
        if isinstance(data, pd.DataFrame)
        else "unavailable"
    )
    empty = _empty_backtest_result(balance, start, end, data_origin)
    indicators, entry_conditions = normalize_strategy_contract(
        strategy.get_indicators_config(), strategy.get_entry_conditions())
    _, exit_conditions = normalize_strategy_contract(
        strategy.get_indicators_config(), exit_conditions_with_default(strategy.get_exit_conditions()))
    needed = required_history(indicators, entry_conditions + exit_conditions)
    frame = _validated_replay_frame(data)
    empty['coverage'] = {'available_candles': 0, 'evaluated_candles': 0, 'first_evaluated': None, 'last_evaluated': None, 'insufficient_history_candles': 0}
    if frame.empty:
        return empty
    period = frame.loc[start:end]
    if period.empty:
        return empty

    empty['coverage']['available_candles'] = len(period)
    if not entry_conditions:
        return empty

    position = None
    trades = []
    equity_curve = [balance]
    drawdown_curve = [0.0]
    high_water = balance

    for timestamp, row in period.iterrows():
        location = frame.index.get_loc(timestamp)
        if not isinstance(location, int) or location < needed:
            empty['coverage']['insufficient_history_candles'] += 1
            continue
        coverage = empty['coverage']
        coverage['evaluated_candles'] += 1
        coverage['first_evaluated'] = coverage['first_evaluated'] or _timestamp_text(timestamp)
        coverage['last_evaluated'] = _timestamp_text(timestamp)
        signal_row = frame.iloc[location - 1]
        previous_signal_row = frame.iloc[location - 2] if location >= 2 else None
        entry_sides = _matching_rule_sides(
            entry_conditions, signal_row, previous_signal_row
        )
        exit_sides = _matching_rule_sides(
            exit_conditions, signal_row, previous_signal_row
        )
        entry_side = entry_sides[0] if len(entry_sides) == 1 else None
        exit_side = exit_sides[0] if len(exit_sides) == 1 else None
        exited_at_open = False

        if position is not None and (entry_side == "SELL" or exit_side == "SELL"):
            balance, trade = _close_long(
                balance,
                position,
                timestamp,
                row["open"],
                "signal",
                fee_rate,
                slippage_rate,
            )
            trades.append(trade)
            position = None
            exited_at_open = True
        elif position is None and entry_side == "BUY":
            position, balance = _open_long(
                balance,
                timestamp,
                row["open"],
                risk_pct,
                stop_pct,
                take_pct,
                fee_rate,
                slippage_rate,
            )

        if position is not None and not exited_at_open:
            protection = _intrabar_exit_price(position, row)
            if protection is not None:
                raw_price, reason = protection
                balance, trade = _close_long(
                    balance,
                    position,
                    timestamp,
                    raw_price,
                    reason,
                    fee_rate,
                    slippage_rate,
                )
                trades.append(trade)
                position = None

        equity = _mark_equity(balance, position, row["close"])
        high_water = max(high_water, equity)
        drawdown = (high_water - equity) / high_water * 100 if high_water > 0 else 0.0
        equity_curve.append(equity)
        drawdown_curve.append(float(drawdown))

    if position is not None:
        final_timestamp = period.index[-1]
        balance, trade = _close_long(
            balance,
            position,
            final_timestamp,
            period.iloc[-1]["close"],
            "end_of_test",
            fee_rate,
            slippage_rate,
        )
        trades.append(trade)
        equity_curve[-1] = balance
        high_water = max(high_water, balance)
        drawdown_curve[-1] = (
            (high_water - balance) / high_water * 100 if high_water > 0 else 0.0
        )

    result = _empty_backtest_result(balance if not equity_curve else initial_balance, start, end, data_origin)
    result['coverage'] = empty['coverage']
    result.update(
        {
            "final_balance": float(balance),
            "trades": trades,
            "equity_curve": equity_curve,
            "drawdown_curve": drawdown_curve,
            "assumptions": {
                "position_model": "long_only",
                "risk_sizing": "equity risk divided by entry-to-stop distance; capped by cash and entry fee",
                "event_order": "open signals, intrabar stop/take, close mark",
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
    fee_bps=0.0,
    slippage_bps=0.0,
):
    """Replay injected ML decisions with the same long-only execution economics."""
    balance, risk_pct, stop_pct, take_pct, fee_rate, slippage_rate = (
        _replay_economics(
            strategy, initial_balance, fee_bps, slippage_bps
        )
    )
    if model_predictor is None:
        raise ModelUnavailableError(
            "paper ML backtests require an explicitly injected model predictor"
        )

    start = _utc_timestamp(start_date, "start_date")
    end = _utc_timestamp(end_date, "end_date")
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    data_origin = str(
        data.attrs.get("data_origin", "provided-dataframe")
        if isinstance(data, pd.DataFrame)
        else "unavailable"
    )
    empty = _empty_backtest_result(balance, start, end, data_origin)
    frame = _validated_replay_frame(data)
    if frame.empty:
        return empty
    backtest_data = frame.loc[start:end]
    if backtest_data.empty:
        return empty

    position = None
    trades = []
    equity_curve = [balance]
    drawdown_curve = [0.0]
    high_water = balance

    for index, (timestamp, row) in enumerate(backtest_data.iterrows()):
        if index < 10:
            continue
        prediction_data = backtest_data.iloc[index - 10 : index].copy()
        prediction, confidence = model_predictor(
            model_id=strategy.ml_model_id, data=prediction_data
        )
        prediction = _finite_float(prediction, "model prediction")
        confidence = _finite_float(confidence, "model confidence")
        if not 0 <= confidence <= 1:
            raise ValueError("model confidence must be in [0, 1]")
        actionable = confidence >= 0.6
        exited_at_open = False

        if position is not None and actionable and prediction < 0:
            balance, trade = _close_long(
                balance,
                position,
                timestamp,
                row["open"],
                "signal",
                fee_rate,
                slippage_rate,
                exit_confidence=float(confidence),
            )
            trades.append(trade)
            position = None
            exited_at_open = True
        elif position is None and actionable and prediction > 0:
            position, balance = _open_long(
                balance,
                timestamp,
                row["open"],
                risk_pct,
                stop_pct,
                take_pct,
                fee_rate,
                slippage_rate,
                confidence=confidence,
            )

        if position is not None and not exited_at_open:
            protection = _intrabar_exit_price(position, row)
            if protection is not None:
                raw_price, reason = protection
                balance, trade = _close_long(
                    balance,
                    position,
                    timestamp,
                    raw_price,
                    reason,
                    fee_rate,
                    slippage_rate,
                )
                trades.append(trade)
                position = None

        equity = _mark_equity(balance, position, row["close"])
        high_water = max(high_water, equity)
        drawdown = (high_water - equity) / high_water * 100 if high_water > 0 else 0.0
        equity_curve.append(equity)
        drawdown_curve.append(float(drawdown))

    if position is not None:
        final_timestamp = backtest_data.index[-1]
        balance, trade = _close_long(
            balance,
            position,
            final_timestamp,
            backtest_data.iloc[-1]["close"],
            "end_of_test",
            fee_rate,
            slippage_rate,
        )
        trades.append(trade)
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
                "prediction_input": "ten completed candles",
                "execution": "open decision, intrabar stop/take, close mark",
                "risk_sizing": "equity risk divided by entry-to-stop distance; capped by cash and entry fee",
                "fee_bps": float(fee_bps),
                "slippage_bps": float(slippage_bps),
                "fees": "charged on entry and exit notionals",
                "slippage": "BUY adds bps; SELL subtracts bps",
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
