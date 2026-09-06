import logging
import math
from datetime import datetime

try:
    from .strategy_contracts import (
        StrategyContractError,
        normalize_operator,
        normalize_strategy_contract,
    )
except ImportError:  # Preserve direct script-style imports used by the legacy app.
    from strategy_contracts import (
        StrategyContractError,
        normalize_operator,
        normalize_strategy_contract,
    )

logger = logging.getLogger(__name__)


class ModelUnavailableError(RuntimeError):
    """Raised when paper signal generation has no injected model predictor."""

def generate_signals_for_strategy(
    strategy,
    market_provider=None,
    pending_signal_lookup=None,
    signal_factory=None,
    model_predictor=None,
    now=None,
):
    """Generate trading signals for a specific strategy."""
    try:
        from .market_data import get_historical_data
        from .technical_indicators import IndicatorUnavailableError, apply_indicators
    except ImportError:
        from market_data import get_historical_data
        from technical_indicators import IndicatorUnavailableError, apply_indicators

    signals = []
    for trading_pair in strategy.get_trading_pairs():
        try:
            historical_data = get_historical_data(
                trading_pair=trading_pair,
                timeframe=strategy.timeframe,
                limit=200,
                provider=market_provider,
            )
            if historical_data.empty:
                continue

            df_with_indicators = apply_indicators(
                historical_data, strategy.get_indicators_config()
            )
            if strategy.use_ml_model and strategy.ml_model_id:
                signal = generate_ml_signal(
                    strategy,
                    trading_pair,
                    df_with_indicators,
                    pending_signal_lookup,
                    signal_factory,
                    model_predictor,
                    now,
                )
            else:
                signal = generate_technical_signal(
                    strategy,
                    trading_pair,
                    df_with_indicators,
                    pending_signal_lookup,
                    signal_factory,
                    now,
                )
            if signal is not None:
                signals.append(signal)
        except (ModelUnavailableError, IndicatorUnavailableError):
            raise
        except Exception as e:
            logger.error(f"Error generating signals for {trading_pair}: {e}")
    return signals


def _default_pending_signal_lookup(strategy_id, trading_pair):
    try:
        from .models import TradingSignal
    except ImportError:
        from models import TradingSignal
    return (
        TradingSignal.query.filter_by(
            strategy_id=strategy_id, trading_pair=trading_pair, status="pending"
        )
        .order_by(TradingSignal.timestamp.desc())
        .first()
    )


def _default_signal_factory(**values):
    try:
        from .models import TradingSignal
    except ImportError:
        from models import TradingSignal
    return TradingSignal(**values)


def _recent_pending_signal(strategy, trading_pair, pending_signal_lookup, now):
    lookup = pending_signal_lookup or _default_pending_signal_lookup
    recent = lookup(strategy.id, trading_pair)
    if recent is None or getattr(recent, "timestamp", None) is None:
        return False
    current_time = now() if callable(now) else (now or datetime.utcnow())
    return (current_time - recent.timestamp).total_seconds() < 3600


def _finite_positive(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def _matching_sides(conditions, latest, previous):
    matches = []
    for side in ("BUY", "SELL"):
        rules = [condition for condition in conditions if condition["signal_type"] == side]
        if rules and all(
            condition["indicator"] in latest
            and evaluate_condition(
                latest[condition["indicator"]],
                condition["operator"],
                condition["value"],
                previous[condition["indicator"]]
                if previous is not None and condition["indicator"] in previous
                else None,
            )
            for condition in rules
        ):
            matches.append(side)
    return matches


def generate_technical_signal(
    strategy,
    trading_pair,
    data,
    pending_signal_lookup=None,
    signal_factory=None,
    now=None,
):
    """Generate signals based on technical analysis rules."""
    if data is None or data.empty:
        return None
    try:
        _, entry_conditions = normalize_strategy_contract(
            strategy.get_indicators_config(), strategy.get_entry_conditions()
        )
    except (StrategyContractError, TypeError, ValueError):
        return None
    if not entry_conditions:
        return None
    if _recent_pending_signal(strategy, trading_pair, pending_signal_lookup, now):
        return None

    latest_candle = data.iloc[-1]
    prev_candle = data.iloc[-2] if len(data) > 1 else None
    matching_sides = _matching_sides(entry_conditions, latest_candle, prev_candle)
    if len(matching_sides) != 1:
        return None

    signal_type = matching_sides[0]
    entry_price = latest_candle.get("close")
    if not _finite_positive(entry_price):
        return None
    stop_pct = getattr(strategy, "stop_loss_pct", None)
    take_pct = getattr(strategy, "take_profit_pct", None)
    if not _finite_positive(stop_pct) or not _finite_positive(take_pct):
        return None
    if stop_pct > 100 or take_pct > 100:
        return None

    if signal_type == "BUY":
        stop_loss = entry_price * (1 - strategy.stop_loss_pct / 100)
        take_profit = entry_price * (1 + strategy.take_profit_pct / 100)
    else:
        stop_loss = entry_price * (1 + strategy.stop_loss_pct / 100)
        take_profit = entry_price * (1 - strategy.take_profit_pct / 100)

    factory = signal_factory or _default_signal_factory
    signal = factory(
        user_id=strategy.user_id,
        strategy_id=strategy.id,
        trading_pair=trading_pair,
        signal_type=signal_type,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        timeframe=strategy.timeframe,
        status='pending',
        confidence=1.0,
    )
    signal_data = {
        'indicators': {
            key: float(value)
            for key, value in latest_candle.items()
            if key not in ['open', 'high', 'low', 'close', 'volume']
            and isinstance(value, (int, float))
            and math.isfinite(value)
        },
        'candle': {
            'open': float(latest_candle['open']),
            'high': float(latest_candle['high']),
            'low': float(latest_candle['low']),
            'close': float(latest_candle['close']),
            'volume': float(latest_candle['volume'])
        }
    }
    signal.set_signal_data(signal_data)
    return signal


def generate_ml_signal(
    strategy,
    trading_pair,
    data,
    pending_signal_lookup=None,
    signal_factory=None,
    model_predictor=None,
    now=None,
):
    """Generate signals based on ML model prediction."""
    if data.empty:
        return None
    
    if _recent_pending_signal(strategy, trading_pair, pending_signal_lookup, now):
        return None
    if model_predictor is None:
        import os

        if os.environ.get("TEAKA_MODE", "paper").lower() == "paper":
            raise ModelUnavailableError(
                "paper ML signals require an explicitly injected model predictor"
            )
        try:
            from .ml_models import predict_with_model
        except ImportError:
            try:
                from ml_models import predict_with_model
            except ImportError as exc:
                raise ModelUnavailableError("ML model implementation is unavailable") from exc
        model_predictor = predict_with_model
    prediction, confidence = model_predictor(
        model_id=strategy.ml_model_id,
        data=data
    )
    
    # Only generate a signal if confidence is above threshold
    confidence_threshold = 0.6  # 60% confidence minimum
    if confidence < confidence_threshold:
        return None
    
    # Determine signal type based on prediction
    if prediction > 0:
        signal_type = 'BUY'
    elif prediction < 0:
        signal_type = 'SELL'
    else:
        return None  # No signal if prediction is exactly 0
    
    # Get latest candle data for prices
    latest_candle = data.iloc[-1]
    entry_price = latest_candle['close']
    
    # Calculate stop loss and take profit
    if signal_type == 'BUY':
        stop_loss = entry_price * (1 - strategy.stop_loss_pct / 100)
        take_profit = entry_price * (1 + strategy.take_profit_pct / 100)
    else:  # SELL signal
        stop_loss = entry_price * (1 + strategy.stop_loss_pct / 100)
        take_profit = entry_price * (1 - strategy.take_profit_pct / 100)
    
    # Create and return the signal
    factory = signal_factory or _default_signal_factory
    signal = factory(
        user_id=strategy.user_id,
        strategy_id=strategy.id,
        trading_pair=trading_pair,
        signal_type=signal_type,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        timeframe=strategy.timeframe,
        status='pending',
        confidence=float(confidence)
    )
    
    # Add signal data with ML info
    signal_data = {
        'ml_prediction': float(prediction),
        'ml_confidence': float(confidence),
        'candle': {
            'open': float(latest_candle['open']),
            'high': float(latest_candle['high']),
            'low': float(latest_candle['low']),
            'close': float(latest_candle['close']),
            'volume': float(latest_candle['volume'])
        }
    }
    signal.set_signal_data(signal_data)
    
    return signal

def evaluate_condition(indicator_value, operator, comparison_value, prev_indicator_value=None):
    """Evaluate a condition for signal generation."""
    try:
        operator = normalize_operator(operator)
        current = float(indicator_value)
        target = float(comparison_value)
    except (StrategyContractError, TypeError, ValueError):
        return False
    if not math.isfinite(current) or not math.isfinite(target):
        return False
    previous = None
    if prev_indicator_value is not None:
        try:
            previous = float(prev_indicator_value)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(previous):
            return False

    if operator == 'above':
        return current > target
    elif operator == 'below':
        return current < target
    elif operator == 'equals':
        return abs(current - target) < 0.0001
    elif operator == 'above_or_equal':
        return current >= target
    elif operator == 'below_or_equal':
        return current <= target
    elif operator == 'crosses_above' and previous is not None:
        return current > target and previous <= target
    elif operator == 'crosses_below' and previous is not None:
        return current < target and previous >= target
    elif operator == 'increasing' and previous is not None:
        return current > previous
    elif operator == 'decreasing' and previous is not None:
        return current < previous
    return False
