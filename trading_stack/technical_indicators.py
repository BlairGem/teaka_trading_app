import logging
import numpy as np
import pandas as pd
import talib
from datetime import datetime
from matlab_integration import get_matlab_indicator_values

logger = logging.getLogger(__name__)

def apply_indicators(data, indicators_config):
    """Apply technical indicators to the input data."""
    if data.empty:
        logger.warning("Empty data provided to apply_indicators")
        return data
    
    # Make a copy of the input data
    df = data.copy()
    
    # Apply each requested indicator
    for indicator_name, params in indicators_config.items():
        try:
            # Call the appropriate indicator function
            df = calculate_indicator(df, indicator_name, params)
        except Exception as e:
            logger.error(f"Error calculating indicator {indicator_name}: {e}")
            continue
    
    return df

def calculate_indicator(data, indicator_name, params):
    """Calculate a specific technical indicator."""
    if data.empty:
        return data
    
    # Make a copy of the input data
    df = data.copy()
    
    # Convert indicator name to lowercase for case-insensitive comparison
    indicator_lower = indicator_name.lower()
    
    try:
        # Moving Averages
        if indicator_lower == 'sma':
            period = params.get('period', 20)
            df[f'sma_{period}'] = talib.SMA(df['close'].values, timeperiod=period)
        
        elif indicator_lower == 'ema':
            period = params.get('period', 20)
            df[f'ema_{period}'] = talib.EMA(df['close'].values, timeperiod=period)
        
        elif indicator_lower == 'wma':
            period = params.get('period', 20)
            df[f'wma_{period}'] = talib.WMA(df['close'].values, timeperiod=period)
        
        # Oscillators
        elif indicator_lower == 'rsi':
            period = params.get('period', 14)
            df[f'rsi_{period}'] = talib.RSI(df['close'].values, timeperiod=period)
        
        elif indicator_lower == 'stochastic':
            k_period = params.get('k_period', 14)
            d_period = params.get('d_period', 3)
            slowing = params.get('slowing', 3)
            
            df['stoch_k'], df['stoch_d'] = talib.STOCH(
                df['high'].values, 
                df['low'].values, 
                df['close'].values, 
                fastk_period=k_period, 
                slowk_period=slowing, 
                slowk_matype=0, 
                slowd_period=d_period, 
                slowd_matype=0
            )
        
        elif indicator_lower == 'macd':
            fast_period = params.get('fast_period', 12)
            slow_period = params.get('slow_period', 26)
            signal_period = params.get('signal_period', 9)
            
            df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
                df['close'].values, 
                fastperiod=fast_period, 
                slowperiod=slow_period, 
                signalperiod=signal_period
            )
        
        # Volatility Indicators
        elif indicator_lower == 'bollinger bands' or indicator_lower == 'bbands':
            period = params.get('period', 20)
            dev_up = params.get('dev_up', 2)
            dev_down = params.get('dev_down', 2)
            
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(
                df['close'].values, 
                timeperiod=period, 
                nbdevup=dev_up, 
                nbdevdn=dev_down, 
                matype=0
            )
        
        elif indicator_lower == 'atr':
            period = params.get('period', 14)
            df['atr'] = talib.ATR(
                df['high'].values, 
                df['low'].values, 
                df['close'].values, 
                timeperiod=period
            )
        
        # Trend Indicators
        elif indicator_lower == 'adx':
            period = params.get('period', 14)
            df['adx'] = talib.ADX(
                df['high'].values, 
                df['low'].values, 
                df['close'].values, 
                timeperiod=period
            )
        
        # Volume Indicators
        elif indicator_lower == 'obv':
            df['obv'] = talib.OBV(df['close'].values, df['volume'].values)
        
        # Miscellaneous Indicators
        elif indicator_lower == 'cci':
            period = params.get('period', 14)
            df['cci'] = talib.CCI(
                df['high'].values, 
                df['low'].values, 
                df['close'].values, 
                timeperiod=period
            )
        
        # Ichimoku Cloud
        elif indicator_lower == 'ichimoku cloud' or indicator_lower == 'ichimoku':
            conversion_period = params.get('conversion_period', 9)
            base_period = params.get('base_period', 26)
            lagging_span_period = params.get('lagging_span_period', 52)
            displacement = params.get('displacement', 26)
            
            # Tenkan-sen (Conversion Line)
            high_9 = df['high'].rolling(window=conversion_period).max()
            low_9 = df['low'].rolling(window=conversion_period).min()
            df['ichimoku_conversion'] = (high_9 + low_9) / 2
            
            # Kijun-sen (Base Line)
            high_26 = df['high'].rolling(window=base_period).max()
            low_26 = df['low'].rolling(window=base_period).min()
            df['ichimoku_base'] = (high_26 + low_26) / 2
            
            # Senkou Span A (Leading Span A)
            df['ichimoku_senkou_a'] = ((df['ichimoku_conversion'] + df['ichimoku_base']) / 2).shift(displacement)
            
            # Senkou Span B (Leading Span B)
            high_52 = df['high'].rolling(window=lagging_span_period).max()
            low_52 = df['low'].rolling(window=lagging_span_period).min()
            df['ichimoku_senkou_b'] = ((high_52 + low_52) / 2).shift(displacement)
            
            # Chikou Span (Lagging Span)
            df['ichimoku_chikou'] = df['close'].shift(-displacement)
        
        # Price Action Patterns
        elif indicator_lower == 'engulfing':
            # Bullish Engulfing
            df['bullish_engulfing'] = (
                (df['close'] > df['open']) &  # Current candle is green
                (df['close'].shift(1) < df['open'].shift(1)) &  # Previous candle is red
                (df['close'] > df['open'].shift(1)) &  # Current close is higher than previous open
                (df['open'] < df['close'].shift(1))  # Current open is lower than previous close
            ).astype(int)
            
            # Bearish Engulfing
            df['bearish_engulfing'] = (
                (df['close'] < df['open']) &  # Current candle is red
                (df['close'].shift(1) > df['open'].shift(1)) &  # Previous candle is green
                (df['close'] < df['open'].shift(1)) &  # Current close is lower than previous open
                (df['open'] > df['close'].shift(1))  # Current open is higher than previous close
            ).astype(int)
        
        # Custom indicators
        elif indicator_lower == 'custom':
            # Try to use MATLAB for custom indicators if available
            matlab_result = get_matlab_indicator_values(df, indicator_name, params)
            
            if matlab_result is not None:
                # Merge the MATLAB results with our dataframe
                for col_name, values in matlab_result.items():
                    df[col_name] = values
            else:
                logger.warning(f"Custom indicator {indicator_name} not implemented and MATLAB calculation failed")
        
        else:
            logger.warning(f"Unsupported indicator: {indicator_name}")
        
        return df
    
    except Exception as e:
        logger.error(f"Error calculating indicator {indicator_name}: {e}")
        return data  # Return original data on error

def calculate_support_resistance(data, period=14, method='peaks'):
    """Calculate support and resistance levels."""
    if data.empty:
        return [], []
    
    # Make a copy of the input data
    df = data.copy()
    
    if method == 'peaks':
        # Use local peaks to identify support and resistance
        supports = []
        resistances = []
        
        # For support, look for local minima
        for i in range(period, len(df) - period):
            if all(df['low'].iloc[i] <= df['low'].iloc[i-j] for j in range(1, period+1)) and \
               all(df['low'].iloc[i] <= df['low'].iloc[i+j] for j in range(1, period+1)):
                supports.append((df.index[i], df['low'].iloc[i]))
        
        # For resistance, look for local maxima
        for i in range(period, len(df) - period):
            if all(df['high'].iloc[i] >= df['high'].iloc[i-j] for j in range(1, period+1)) and \
               all(df['high'].iloc[i] >= df['high'].iloc[i+j] for j in range(1, period+1)):
                resistances.append((df.index[i], df['high'].iloc[i]))
        
        return supports, resistances
    
    elif method == 'fibonacci':
        # Use Fibonacci retracement levels
        price_max = df['high'].max()
        price_min = df['low'].min()
        diff = price_max - price_min
        
        levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        retracements = [(price_max - level * diff) for level in levels]
        
        return retracements, []
    
    else:
        logger.warning(f"Unsupported support/resistance method: {method}")
        return [], []

def detect_patterns(data):
    """Detect candlestick patterns in the data."""
    if data.empty:
        return {}
    
    # Make a copy of the input data
    df = data.copy()
    
    patterns = {}
    
    # Single candlestick patterns
    patterns['doji'] = talib.CDLDOJI(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
    patterns['hammer'] = talib.CDLHAMMER(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
    patterns['hanging_man'] = talib.CDLHANGINGMAN(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
    patterns['shooting_star'] = talib.CDLSHOOTINGSTAR(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
    
    # Double candlestick patterns
    patterns['engulfing'] = talib.CDLENGULFING(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
    patterns['harami'] = talib.CDLHARAMI(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
    
    # Triple candlestick patterns
    patterns['morning_star'] = talib.CDLMORNINGSTAR(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
    patterns['evening_star'] = talib.CDLEVENINGSTAR(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
    
    return patterns

def get_indicator_description(indicator_name):
    """Get a description of a technical indicator."""
    indicator_lower = indicator_name.lower()
    
    descriptions = {
        'sma': {
            'name': 'Simple Moving Average',
            'description': 'The simple moving average is an arithmetic moving average calculated by adding recent prices and dividing by the number of time periods in the calculation average.',
            'parameters': {
                'period': 'Number of periods to average (default: 20)'
            },
            'typical_values': 'Common periods include 20, 50, 100, and 200.'
        },
        'ema': {
            'name': 'Exponential Moving Average',
            'description': 'The exponential moving average gives more weight to recent prices, reacting more quickly to price changes than a simple moving average.',
            'parameters': {
                'period': 'Number of periods to average (default: 20)'
            },
            'typical_values': 'Common periods include 12, 26, 50, and 200.'
        },
        'rsi': {
            'name': 'Relative Strength Index',
            'description': 'The RSI measures the speed and change of price movements, oscillating between 0 and 100. It is considered overbought when above 70 and oversold when below 30.',
            'parameters': {
                'period': 'Number of periods to calculate (default: 14)'
            },
            'typical_values': 'The standard period is 14, but 9 and 25 are also common.'
        },
        'macd': {
            'name': 'Moving Average Convergence Divergence',
            'description': 'MACD is a trend-following momentum indicator showing the relationship between two moving averages of a security\'s price.',
            'parameters': {
                'fast_period': 'Period for the fast EMA (default: 12)',
                'slow_period': 'Period for the slow EMA (default: 26)',
                'signal_period': 'Period for the signal line (default: 9)'
            },
            'typical_values': 'Standard settings are 12, 26, and 9.'
        }
    }
    
    return descriptions.get(indicator_lower, {
        'name': indicator_name,
        'description': 'No description available for this indicator.',
        'parameters': {},
        'typical_values': 'N/A'
    })
