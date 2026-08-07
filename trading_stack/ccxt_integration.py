import ccxt
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CCXTManager:
    """Manager for CCXT exchange integrations."""
    
    def __init__(self):
        self.exchanges = {}
        self.supported_exchanges = [
            'kucoin', 'binance', 'coinbase', 'kraken', 'bitfinex', 
            'huobi', 'okx', 'bybit', 'gate', 'mexc'
        ]
    
    def initialize_exchange(self, exchange_name: str, api_key: str = None, 
                          secret: str = None, password: str = None, 
                          sandbox: bool = False) -> bool:
        """Initialize a CCXT exchange connection."""
        try:
            if exchange_name not in self.supported_exchanges:
                logger.error(f"Exchange {exchange_name} not supported")
                return False
            
            exchange_class = getattr(ccxt, exchange_name)
            
            # Check if exchange supports sandbox mode
            exchanges_with_sandbox = ['binance', 'kucoin', 'kraken', 'okx', 'bybit']
            use_sandbox = sandbox and exchange_name in exchanges_with_sandbox
            
            config = {
                'enableRateLimit': True,
                'timeout': 30000,
            }
            
            # Only set sandbox if exchange supports it and we have credentials
            if use_sandbox and api_key:
                config['sandbox'] = True
            
            if api_key:
                config['apiKey'] = api_key
            if secret:
                config['secret'] = secret
            if password:  # For KuCoin passphrase
                config['password'] = password
            
            exchange = exchange_class(config)
            
            # Test connection only if we have credentials
            if api_key:
                try:
                    exchange.load_markets()
                    # Only test balance if we have full credentials
                    if secret and (not password or exchange_name != 'kucoin' or password):
                        balance = exchange.fetch_balance()
                        logger.info(f"Successfully connected to {exchange_name} with authentication")
                    else:
                        logger.info(f"Connected to {exchange_name} with API key only")
                except Exception as e:
                    logger.warning(f"Connected to {exchange_name} but authentication failed: {e}")
            else:
                # For public data only, just load markets to test connection
                try:
                    exchange.load_markets()
                    logger.info(f"Connected to {exchange_name} for public data only")
                except Exception as e:
                    logger.warning(f"Connected to {exchange_name} but market loading failed: {e}")
            
            self.exchanges[exchange_name] = exchange
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {exchange_name}: {e}")
            return False
    
    def get_exchange(self, exchange_name: str):
        """Get an initialized exchange instance."""
        return self.exchanges.get(exchange_name)
    
    def fetch_ticker(self, exchange_name: str, symbol: str) -> Optional[Dict]:
        """Fetch ticker data for a symbol from an exchange."""
        try:
            # Check if this is a forex pair being requested from a crypto exchange
            forex_pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 
                          'USD/CHF', 'NZD/USD', 'EUR/GBP', 'EUR/JPY', 'GBP/JPY', 'XAU/USD']
            crypto_exchanges = ['kucoin', 'binance', 'coinbase', 'kraken', 'bitfinex', 
                               'huobi', 'okx', 'bybit', 'gate', 'mexc']
            
            if symbol in forex_pairs and exchange_name in crypto_exchanges:
                logger.warning(f"Skipping forex pair {symbol} for crypto exchange {exchange_name}")
                return None
            
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                logger.error(f"Exchange {exchange_name} not initialized")
                return None
            
            ticker = exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'timestamp': ticker['timestamp'],
                'datetime': ticker['datetime']
            }
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol} from {exchange_name}: {e}")
            return None
    
    def fetch_ohlcv(self, exchange_name: str, symbol: str, timeframe: str = '1h', 
                    limit: int = 100) -> List:
        """Fetch OHLCV data from an exchange."""
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                logger.error(f"Exchange {exchange_name} not initialized")
                return []
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            formatted_data = []
            for candle in ohlcv:
                formatted_data.append({
                    'timestamp': candle[0],
                    'datetime': datetime.fromtimestamp(candle[0] / 1000),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                })
            
            return formatted_data
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol} from {exchange_name}: {e}")
            return []
    
    def fetch_balance(self, exchange_name: str) -> Optional[Dict]:
        """Fetch account balance from an exchange."""
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                logger.error(f"Exchange {exchange_name} not initialized")
                return None
            
            balance = exchange.fetch_balance()
            
            # Format balance data
            formatted_balance = {}
            for currency, amounts in balance.items():
                if currency not in ['info', 'free', 'used', 'total']:
                    if isinstance(amounts, dict):
                        formatted_balance[currency] = {
                            'free': amounts.get('free', 0),
                            'used': amounts.get('used', 0),
                            'total': amounts.get('total', 0)
                        }
            
            return formatted_balance
        except Exception as e:
            logger.error(f"Error fetching balance from {exchange_name}: {e}")
            return None
    
    def place_order(self, exchange_name: str, symbol: str, order_type: str, 
                   side: str, amount: float, price: float = None) -> Optional[Dict]:
        """Place an order on an exchange."""
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                logger.error(f"Exchange {exchange_name} not initialized")
                return None
            
            order = exchange.create_order(symbol, order_type, side, amount, price)
            
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'type': order['type'],
                'side': order['side'],
                'amount': order['amount'],
                'price': order['price'],
                'status': order['status'],
                'timestamp': order['timestamp']
            }
        except Exception as e:
            logger.error(f"Error placing order on {exchange_name}: {e}")
            return None
    
    def fetch_order_status(self, exchange_name: str, order_id: str, symbol: str) -> Optional[Dict]:
        """Fetch order status from an exchange."""
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                logger.error(f"Exchange {exchange_name} not initialized")
                return None
            
            order = exchange.fetch_order(order_id, symbol)
            return {
                'id': order['id'],
                'status': order['status'],
                'filled': order['filled'],
                'remaining': order['remaining'],
                'cost': order['cost']
            }
        except Exception as e:
            logger.error(f"Error fetching order status from {exchange_name}: {e}")
            return None
    
    def get_available_symbols(self, exchange_name: str) -> List[str]:
        """Get available trading symbols from an exchange."""
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                logger.error(f"Exchange {exchange_name} not initialized")
                return []
            
            markets = exchange.load_markets()
            return list(markets.keys())
        except Exception as e:
            logger.error(f"Error fetching symbols from {exchange_name}: {e}")
            return []
    
    def fetch_trades(self, exchange_name: str, symbol: str = None, limit: int = 50) -> List:
        """Fetch recent trades from an exchange."""
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                logger.error(f"Exchange {exchange_name} not initialized")
                return []
            
            if symbol:
                trades = exchange.fetch_my_trades(symbol, limit=limit)
            else:
                trades = exchange.fetch_my_trades(limit=limit)
            
            formatted_trades = []
            for trade in trades:
                formatted_trades.append({
                    'id': trade['id'],
                    'symbol': trade['symbol'],
                    'side': trade['side'],
                    'amount': trade['amount'],
                    'price': trade['price'],
                    'cost': trade['cost'],
                    'fee': trade['fee'],
                    'timestamp': trade['timestamp'],
                    'datetime': trade['datetime']
                })
            
            return formatted_trades
        except Exception as e:
            logger.error(f"Error fetching trades from {exchange_name}: {e}")
            return []

# Global CCXT manager instance
ccxt_manager = CCXTManager()

# Initialize supported exchanges
def initialize_exchanges():
    """Initialize all supported exchanges."""
    logger.info("Initializing exchange connections...")
    
    # KuCoin
    kucoin_key = os.environ.get('KUCOIN_API_KEY')
    kucoin_secret = os.environ.get('KUCOIN_SECRET_KEY')
    kucoin_passphrase = os.environ.get('KUCOIN_PASSPHRASE')
    
    if kucoin_key and kucoin_secret and kucoin_passphrase:
        ccxt_manager.initialize_exchange('kucoin', kucoin_key, kucoin_secret, kucoin_passphrase, sandbox=False)
    else:
        # Initialize without credentials for public data
        ccxt_manager.initialize_exchange('kucoin', sandbox=False)
    
    # Binance (backup)
    binance_key = os.environ.get('BINANCE_API_KEY')
    binance_secret = os.environ.get('BINANCE_SECRET_KEY')
    
    if binance_key and binance_secret:
        ccxt_manager.initialize_exchange('binance', binance_key, binance_secret, sandbox=False)
    else:
        ccxt_manager.initialize_exchange('binance', sandbox=False)
    
    # Only initialize exchanges that are likely to work without credentials
    # Skip Coinbase for now as it often requires special setup
    logger.info("Exchange initialization completed")

# Initialize exchanges on import
initialize_exchanges()