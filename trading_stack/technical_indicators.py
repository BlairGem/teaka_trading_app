import logging
import pandas as pd

try:
    from .strategy_contracts import normalize_indicators_config
except ImportError:  # Preserve direct script-style imports used by the legacy app.
    from strategy_contracts import normalize_indicators_config

logger = logging.getLogger(__name__)


class IndicatorUnavailableError(RuntimeError):
    """Raised when a requested optional indicator backend is unavailable."""


def apply_indicators(data, indicators_config, optional_backend=None):
    """Apply normalized indicators without initializing optional runtimes."""
    if data.empty:
        return data.copy()

    df = data.copy()
    for indicator_name, params in normalize_indicators_config(indicators_config).items():
        df = calculate_indicator(df, indicator_name, params, optional_backend)
    return df


def _optional_talib(optional_backend):
    if optional_backend is False:
        raise IndicatorUnavailableError("optional TA-Lib backend is disabled")
    if optional_backend is not None:
        return optional_backend
    try:
        import talib
    except ImportError as exc:
        raise IndicatorUnavailableError(
            "this indicator requires the optional TA-Lib package"
        ) from exc
    return talib


def calculate_indicator(data, indicator_name, params, optional_backend=None):
    """Calculate one indicator; core replay indicators use pandas only."""
    if data.empty:
        return data.copy()

    df = data.copy()
    indicator_lower = indicator_name.strip().lower()
    close = pd.to_numeric(df["close"], errors="coerce")

    if indicator_lower == "sma":
        period = params.get("period", 20)
        df[f"sma_{period}"] = close.rolling(period, min_periods=period).mean()
    elif indicator_lower == "ema":
        period = params.get("period", 20)
        df[f"ema_{period}"] = close.ewm(span=period, adjust=False).mean()
    elif indicator_lower == "rsi":
        period = params.get("period", 14)
        delta = close.diff()
        average_gain = delta.clip(lower=0).ewm(
            alpha=1 / period, adjust=False, min_periods=period
        ).mean()
        average_loss = (-delta.clip(upper=0)).ewm(
            alpha=1 / period, adjust=False, min_periods=period
        ).mean()
        relative_strength = average_gain / average_loss
        rsi = 100 - (100 / (1 + relative_strength))
        df[f"rsi_{period}"] = rsi.mask(
            (average_loss == 0) & (average_gain > 0), 100.0
        )
    elif indicator_lower == "macd":
        fast = params.get("fast_period", 12)
        slow = params.get("slow_period", 26)
        signal = params.get("signal_period", 9)
        fast_ema = close.ewm(span=fast, adjust=False).mean()
        slow_ema = close.ewm(span=slow, adjust=False).mean()
        df["macd"] = fast_ema - slow_ema
        df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]
    elif indicator_lower in {"bollinger bands", "bbands"}:
        period = params.get("period", 20)
        middle = close.rolling(period, min_periods=period).mean()
        deviation = close.rolling(period, min_periods=period).std(ddof=0)
        df["bb_middle"] = middle
        df["bb_upper"] = middle + deviation * params.get("dev_up", 2)
        df["bb_lower"] = middle - deviation * params.get("dev_down", 2)
    elif indicator_lower in {"ichimoku", "ichimoku cloud"}:
        conversion = params.get("conversion_period", 9)
        base = params.get("base_period", 26)
        lagging = params.get("lagging_span_period", 52)
        displacement = params.get("displacement", 26)
        df["ichimoku_conversion"] = (
            df["high"].rolling(conversion).max() + df["low"].rolling(conversion).min()
        ) / 2
        df["ichimoku_base"] = (
            df["high"].rolling(base).max() + df["low"].rolling(base).min()
        ) / 2
        df["ichimoku_senkou_a"] = (
            (df["ichimoku_conversion"] + df["ichimoku_base"]) / 2
        ).shift(displacement)
        span_b = (
            df["high"].rolling(lagging).max() + df["low"].rolling(lagging).min()
        ) / 2
        df["ichimoku_senkou_b"] = span_b.shift(displacement)
        # A lagging-only series prevents a replay row from observing a future close.
        df["ichimoku_chikou"] = close.shift(displacement)
    elif indicator_lower == "engulfing":
        df["bullish_engulfing"] = (
            (df["close"] > df["open"])
            & (df["close"].shift(1) < df["open"].shift(1))
            & (df["close"] > df["open"].shift(1))
            & (df["open"] < df["close"].shift(1))
        ).astype(int)
        df["bearish_engulfing"] = (
            (df["close"] < df["open"])
            & (df["close"].shift(1) > df["open"].shift(1))
            & (df["close"] < df["open"].shift(1))
            & (df["open"] > df["close"].shift(1))
        ).astype(int)
    elif indicator_lower == "custom":
        if optional_backend is False:
            raise IndicatorUnavailableError("optional MATLAB backend is disabled")
        try:
            from .matlab_integration import get_matlab_indicator_values
        except (ImportError, ModuleNotFoundError) as exc:
            raise IndicatorUnavailableError(
                "custom indicators require the optional MATLAB runtime"
            ) from exc
        result = get_matlab_indicator_values(df, indicator_name, params)
        if result is None:
            raise IndicatorUnavailableError("MATLAB did not produce indicator values")
        for column, values in result.items():
            df[column] = values
    elif indicator_lower in {"wma", "stochastic", "atr", "adx", "obv", "cci"}:
        talib = _optional_talib(optional_backend)
        if indicator_lower == "wma":
            period = params.get("period", 20)
            df[f"wma_{period}"] = talib.WMA(close.to_numpy(), timeperiod=period)
        elif indicator_lower == "stochastic":
            df["stoch_k"], df["stoch_d"] = talib.STOCH(
                df["high"].to_numpy(),
                df["low"].to_numpy(),
                close.to_numpy(),
                fastk_period=params.get("k_period", 14),
                slowk_period=params.get("slowing", 3),
                slowk_matype=0,
                slowd_period=params.get("d_period", 3),
                slowd_matype=0,
            )
        elif indicator_lower == "atr":
            df["atr"] = talib.ATR(
                df["high"].to_numpy(),
                df["low"].to_numpy(),
                close.to_numpy(),
                timeperiod=params.get("period", 14),
            )
        elif indicator_lower == "adx":
            df["adx"] = talib.ADX(
                df["high"].to_numpy(),
                df["low"].to_numpy(),
                close.to_numpy(),
                timeperiod=params.get("period", 14),
            )
        elif indicator_lower == "obv":
            df["obv"] = talib.OBV(close.to_numpy(), df["volume"].to_numpy())
        else:
            df["cci"] = talib.CCI(
                df["high"].to_numpy(),
                df["low"].to_numpy(),
                close.to_numpy(),
                timeperiod=params.get("period", 14),
            )
    else:
        raise ValueError(f"unsupported indicator: {indicator_name}")
    return df

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

    talib = _optional_talib(None)
    
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
