import logging
import math
import pandas as pd
from datetime import datetime, timedelta
import os

try:
    from .config import CRYPTO_TRADING_PAIRS, FOREX_TRADING_PAIRS, TEAKA_MODE
except ImportError:  # Preserve direct script-style imports used by the legacy app.
    from config import CRYPTO_TRADING_PAIRS, FOREX_TRADING_PAIRS, TEAKA_MODE

logger = logging.getLogger(__name__)

# Cache for market data to reduce API calls
price_cache = {}
ohlcv_cache = {}

def _valid_price(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def get_latest_prices(provider=None, as_of=None):
    """Get the latest prices for the configured trading pairs."""
    pairs = CRYPTO_TRADING_PAIRS + FOREX_TRADING_PAIRS
    if provider is not None:
        provided = provider.get_latest_prices(pairs, as_of=as_of)
        if not isinstance(provided, dict):
            return {}
        return {
            pair: float(price)
            for pair, price in provided.items()
            if pair in pairs and _valid_price(price)
        }
    if TEAKA_MODE == "paper":
        return {}

    all_prices = {}
    
    # Get crypto prices from KuCoin (only crypto pairs)
    crypto_prices = get_crypto_prices(CRYPTO_TRADING_PAIRS)
    all_prices.update(crypto_prices)
    
    # Get forex prices from FXCM/OANDA (only forex pairs)
    # Only attempt if we have API credentials
    if os.environ.get('OANDA_API_KEY') or os.environ.get('FXCM_ACCESS_TOKEN'):
        forex_prices = get_forex_prices(FOREX_TRADING_PAIRS)
        all_prices.update(forex_prices)
    else:
        logger.info("No forex API credentials available, skipping forex price updates")
    
    # Update the price cache
    price_cache.update(all_prices)
    
    return all_prices

def get_crypto_prices(pairs):
    """Get the latest prices for crypto pairs from KuCoin."""
    prices = {}
    
    try:
        import requests

        # Convert trading pairs format from BTC/USDT to BTC-USDT for KuCoin
        formatted_pairs = [p.replace('/', '-') for p in pairs]
        
        # Make API request to KuCoin public endpoint (no auth required for prices)
        url = "https://api.kucoin.com/api/v1/market/allTickers"
        
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['code'] == '200000':
                # Process the response
                tickers = data['data']['ticker']
                for ticker in tickers:
                    symbol = ticker['symbol']
                    price = float(ticker['last'])
                    
                    # Convert back to BTC/USDT format
                    original_symbol = symbol.replace('-', '/')
                    if original_symbol in pairs:
                        prices[original_symbol] = price
            else:
                logger.error(f"KuCoin API error: {data}")
        else:
            logger.error(f"Failed to get crypto prices: {response.text}")
    
    except Exception as e:
        logger.error(f"Error fetching crypto prices: {e}")
    
    return prices

def get_forex_prices(pairs):
    """Get the latest prices for forex pairs from OANDA."""
    prices = {}
    
    try:
        import requests

        # Convert pairs to OANDA format (e.g., EUR_USD)
        formatted_pairs = [p.replace('/', '_') for p in pairs]
        instruments_param = ','.join(formatted_pairs)
        
        # Make API request to OANDA
        oanda_api_key = os.environ.get('OANDA_API_KEY')
        if not oanda_api_key:
            logger.warning("OANDA API key not found, cannot fetch forex prices")
            return prices
            
        url = f"https://api-fxpractice.oanda.com/v3/instruments/{instruments_param}/candles?count=1&price=M"
        headers = {
            'Authorization': f'Bearer {oanda_api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Process the response
            for instrument, candles_data in data.items():
                if 'candles' in candles_data and candles_data['candles']:
                    candle = candles_data['candles'][0]
                    if 'mid' in candle and 'c' in candle['mid']:
                        price = float(candle['mid']['c'])
                        
                        # Convert back to original format
                        original_symbol = instrument.replace('_', '/')
                        prices[original_symbol] = price
        else:
            logger.error(f"Failed to get forex prices: {response.text}")
    
    except Exception as e:
        logger.error(f"Error fetching forex prices: {e}")
    
    return prices

def _date_bound(value, field):
    try:
        return pd.to_datetime(value, utc=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO date or datetime") from exc


def _normalize_history(data, start_date, end_date, limit):
    if not isinstance(data, pd.DataFrame) or data.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    frame = data.copy()
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.set_index("timestamp")
    else:
        frame.index = pd.to_datetime(frame.index, utc=True)
    required = ["open", "high", "low", "close", "volume"]
    if any(column not in frame.columns for column in required):
        return pd.DataFrame(columns=required)
    frame = frame.sort_index()
    if start_date is not None:
        frame = frame.loc[_date_bound(start_date, "start_date") : _date_bound(end_date, "end_date")]
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        frame = frame.tail(limit)
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame[required]


def get_historical_data(
    trading_pair,
    timeframe,
    limit=100,
    start_date=None,
    end_date=None,
    provider=None,
):
    """Get historical OHLCV data for a trading pair."""
    if (start_date is None) != (end_date is None):
        raise ValueError("start_date and end_date must be provided together")
    if start_date is not None and _date_bound(start_date, "start_date") > _date_bound(
        end_date, "end_date"
    ):
        raise ValueError("start_date must be on or before end_date")
    if trading_pair not in CRYPTO_TRADING_PAIRS + FOREX_TRADING_PAIRS:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    if provider is not None:
        data = provider.get_historical_data(
            trading_pair,
            timeframe,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return _normalize_history(data, start_date, end_date, limit)
    if TEAKA_MODE == "paper":
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    cache_key = f"{trading_pair}_{timeframe}_{limit}_{start_date}_{end_date}"
    
    # Check if we have cached data
    if cache_key in ohlcv_cache:
        # Only use cache if it's less than 5 minutes old
        if datetime.now() - ohlcv_cache[cache_key]['timestamp'] < timedelta(minutes=5):
            return ohlcv_cache[cache_key]['data']
    
    # Determine if this is a crypto or forex pair
    if trading_pair in CRYPTO_TRADING_PAIRS:
        data = get_crypto_historical_data(trading_pair, timeframe, limit)
    elif trading_pair in FOREX_TRADING_PAIRS:
        data = get_forex_historical_data(trading_pair, timeframe, limit)
    else:
        logger.error(f"Unsupported trading pair: {trading_pair}")
        return pd.DataFrame()
    
    data = _normalize_history(data, start_date, end_date, limit)
    if not data.empty:
        ohlcv_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    return data

def get_crypto_historical_data(trading_pair, timeframe, limit=100):
    """Get historical data for a crypto pair from Binance."""
    try:
        import requests

        # Convert trading pair and timeframe to Binance format
        symbol = trading_pair.replace('/', '')
        binance_timeframe = convert_timeframe_to_binance(timeframe)
        
        # Make API request to Binance
        url = f"https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': binance_timeframe,
            'limit': limit
        }
        headers = {}
        binance_api_key = os.environ.get('BINANCE_API_KEY')
        if binance_api_key:
            headers['X-MBX-APIKEY'] = binance_api_key
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Convert to DataFrame
            if data:
                df = pd.DataFrame(data)
                # Rename columns to standard format
                df.columns = [
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ]
            else:
                return pd.DataFrame()
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            
            return df[['open', 'high', 'low', 'close', 'volume']]
        else:
            logger.error(f"Failed to get crypto historical data: {response.text}")
            return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"Error fetching crypto historical data: {e}")
        return pd.DataFrame()

def get_forex_historical_data(trading_pair, timeframe, limit=100):
    """Get historical data for a forex pair from OANDA."""
    try:
        import requests

        # Convert trading pair and timeframe to OANDA format
        instrument = trading_pair.replace('/', '_')
        oanda_timeframe = convert_timeframe_to_oanda(timeframe)
        
        # Make API request to OANDA
        oanda_api_key = os.environ.get('OANDA_API_KEY')
        if not oanda_api_key:
            logger.warning("OANDA API key not found, cannot fetch forex historical data")
            return pd.DataFrame()
            
        url = f"https://api-fxpractice.oanda.com/v3/instruments/{instrument}/candles"
        params = {
            'granularity': oanda_timeframe,
            'count': limit,
            'price': 'M'  # Midpoint candles
        }
        headers = {
            'Authorization': f'Bearer {oanda_api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Process the response
            candles = data.get('candles', [])
            records = []
            
            for candle in candles:
                if candle['complete']:
                    records.append({
                        'timestamp': candle['time'],
                        'open': float(candle['mid']['o']),
                        'high': float(candle['mid']['h']),
                        'low': float(candle['mid']['l']),
                        'close': float(candle['mid']['c']),
                        'volume': float(candle['volume'])
                    })
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            if not df.empty:
                # Convert timestamp and set as index
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                return df
            else:
                logger.warning(f"No data returned for {trading_pair} with timeframe {timeframe}")
                return pd.DataFrame()
        else:
            logger.error(f"Failed to get forex historical data: {response.text}")
            return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"Error fetching forex historical data: {e}")
        return pd.DataFrame()

def convert_timeframe_to_binance(timeframe):
    """Convert generic timeframe to Binance format."""
    mapping = {
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '1h': '1h',
        '4h': '4h',
        '1d': '1d',
        '1w': '1w'
    }
    return mapping.get(timeframe, '1h')

def convert_timeframe_to_oanda(timeframe):
    """Convert generic timeframe to OANDA format."""
    mapping = {
        '1m': 'M1',
        '5m': 'M5',
        '15m': 'M15',
        '30m': 'M30',
        '1h': 'H1',
        '4h': 'H4',
        '1d': 'D',
        '1w': 'W'
    }
    return mapping.get(timeframe, 'H1')

def get_available_pairs():
    """Get all available trading pairs."""
    return CRYPTO_TRADING_PAIRS + FOREX_TRADING_PAIRS

def setup_websocket_connection(trading_pair, callback):
    """Setup a websocket connection for real-time data."""
    # This would implement the websocket connection logic
    # For now, we'll just log the request
    logger.info(f"Setting up websocket for {trading_pair}")
    return True
