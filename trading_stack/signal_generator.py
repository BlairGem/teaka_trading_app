import logging
import pandas as pd
import numpy as np
from datetime import datetime
from models import TradingSignal, db
from market_data import get_historical_data
from technical_indicators import apply_indicators
from ml_models import predict_with_model
import config

logger = logging.getLogger(__name__)

def generate_signals_for_strategy(strategy):
    """Generate trading signals for a specific strategy."""
    signals = []
    
    # Get the trading pairs for this strategy
    trading_pairs = strategy.get_trading_pairs()
    
    for trading_pair in trading_pairs:
        try:
            # Get historical data
            historical_data = get_historical_data(
                trading_pair=trading_pair,
                timeframe=strategy.timeframe,
                limit=200  # Get enough data for indicators
            )
            
            if historical_data.empty:
                logger.warning(f"No historical data for {trading_pair} with timeframe {strategy.timeframe}")
                continue
            
            # Apply technical indicators
            indicators_config = strategy.get_indicators_config()
            df_with_indicators = apply_indicators(historical_data, indicators_config)
            
            # Check if strategy uses ML model
            if strategy.use_ml_model and strategy.ml_model_id:
                # Apply ML model prediction
                signal = generate_ml_signal(
                    strategy=strategy,
                    trading_pair=trading_pair,
                    data=df_with_indicators
                )
                if signal:
                    signals.append(signal)
            else:
                # Apply traditional technical analysis
                signal = generate_technical_signal(
                    strategy=strategy,
                    trading_pair=trading_pair,
                    data=df_with_indicators
                )
                if signal:
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating signals for {trading_pair}: {e}")
            continue
    
    return signals

def generate_technical_signal(strategy, trading_pair, data):
    """Generate signals based on technical analysis rules."""
    if data.empty:
        return None
    
    # Get the entry and exit conditions
    entry_conditions = strategy.get_entry_conditions()
    
    # Check if we already have a recent signal for this pair/strategy
    recent_signal = TradingSignal.query.filter_by(
        strategy_id=strategy.id,
        trading_pair=trading_pair,
        status='pending'
    ).order_by(TradingSignal.timestamp.desc()).first()
    
    # If we have a recent pending signal, don't generate a new one
    if recent_signal and (datetime.utcnow() - recent_signal.timestamp).total_seconds() < 3600:
        return None
    
    # Get latest candle data
    latest_candle = data.iloc[-1]
    prev_candle = data.iloc[-2] if len(data) > 1 else None
    
    # Check entry conditions
    buy_signal = True
    sell_signal = True
    
    for condition in entry_conditions:
        try:
            indicator = condition['indicator']
            operator = condition['operator']
            value = condition['value']
            signal_type = condition['signal_type']
            
            # Check if the indicator exists in our data
            if indicator not in latest_candle:
                logger.warning(f"Indicator {indicator} not found in data")
                continue
            
            # Evaluate the condition
            result = evaluate_condition(
                latest_candle[indicator],
                operator,
                value,
                prev_candle[indicator] if prev_candle is not None and indicator in prev_candle else None
            )
            
            # Update signal flags
            if signal_type == 'BUY' and not result:
                buy_signal = False
            elif signal_type == 'SELL' and not result:
                sell_signal = False
        
        except Exception as e:
            logger.error(f"Error evaluating condition {condition}: {e}")
            if signal_type == 'BUY':
                buy_signal = False
            else:
                sell_signal = False
    
    # Create signal if conditions are met
    if buy_signal:
        signal_type = 'BUY'
    elif sell_signal:
        signal_type = 'SELL'
    else:
        return None
    
    # Calculate entry price, stop loss and take profit
    entry_price = latest_candle['close']
    
    # For simplicity, using a fixed percentage for stop loss and take profit
    if signal_type == 'BUY':
        stop_loss = entry_price * (1 - strategy.stop_loss_pct / 100)
        take_profit = entry_price * (1 + strategy.take_profit_pct / 100)
    else:  # SELL signal
        stop_loss = entry_price * (1 + strategy.stop_loss_pct / 100)
        take_profit = entry_price * (1 - strategy.take_profit_pct / 100)
    
    # Create and return the signal
    signal = TradingSignal(
        user_id=strategy.user_id,
        strategy_id=strategy.id,
        trading_pair=trading_pair,
        signal_type=signal_type,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        timeframe=strategy.timeframe,
        status='pending',
        confidence=1.0  # For technical signals, confidence is always 1.0
    )
    
    # Add signal data with indicator values
    signal_data = {
        'indicators': {k: float(v) for k, v in latest_candle.items() if k not in ['open', 'high', 'low', 'close', 'volume']},
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

def generate_ml_signal(strategy, trading_pair, data):
    """Generate signals based on ML model prediction."""
    if data.empty:
        return None
    
    # Check if we already have a recent signal for this pair/strategy
    recent_signal = TradingSignal.query.filter_by(
        strategy_id=strategy.id,
        trading_pair=trading_pair,
        status='pending'
    ).order_by(TradingSignal.timestamp.desc()).first()
    
    # If we have a recent pending signal, don't generate a new one
    if recent_signal and (datetime.utcnow() - recent_signal.timestamp).total_seconds() < 3600:
        return None
    
    # Get prediction from ML model
    prediction, confidence = predict_with_model(
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
    signal = TradingSignal(
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
    if operator == 'above':
        return indicator_value > comparison_value
    elif operator == 'below':
        return indicator_value < comparison_value
    elif operator == 'equals':
        return abs(indicator_value - comparison_value) < 0.0001  # For floating point comparison
    elif operator == 'crosses_above' and prev_indicator_value is not None:
        return indicator_value > comparison_value and prev_indicator_value <= comparison_value
    elif operator == 'crosses_below' and prev_indicator_value is not None:
        return indicator_value < comparison_value and prev_indicator_value >= comparison_value
    elif operator == 'increasing' and prev_indicator_value is not None:
        return indicator_value > prev_indicator_value
    elif operator == 'decreasing' and prev_indicator_value is not None:
        return indicator_value < prev_indicator_value
    else:
        logger.warning(f"Unsupported operator {operator} or missing previous value")
        return False
