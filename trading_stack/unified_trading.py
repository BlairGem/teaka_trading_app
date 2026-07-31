import logging
import os
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta

# Import our integration modules
from ccxt_integration import ccxt_manager
from fxcm_integration import fxcm_manager
from alpaca_integration import alpaca_manager

logger = logging.getLogger(__name__)

class UnifiedTradingManager:
    """Unified interface for all trading platforms (CCXT, FXCM, Alpaca)."""
    
    def __init__(self):
        self.platforms = {
            'crypto': ccxt_manager,
            'forex': fxcm_manager,
            'stocks': alpaca_manager
        }
    
    def get_account_balance(self, user=None) -> Dict:
        """Get account balances from all connected platforms."""
        balances = {}
        
        try:
            # CCXT crypto exchanges
            for exchange_name in ['kucoin', 'binance', 'coinbase']:
                try:
                    balance = ccxt_manager.fetch_balance(exchange_name)
                    if balance:
                        balances[exchange_name] = balance
                except Exception as e:
                    logger.debug(f"Could not fetch {exchange_name} balance: {e}")
            
            # FXCM forex
            try:
                if fxcm_manager.is_connected:
                    fxcm_account = fxcm_manager.get_account_summary()
                    if fxcm_account:
                        balances['fxcm'] = {
                            'USD': {
                                'free': fxcm_account['balance'],
                                'used': fxcm_account['balance'] - fxcm_account['margin'],
                                'total': fxcm_account['balance']
                            }
                        }
            except Exception as e:
                logger.debug(f"Could not fetch FXCM balance: {e}")
            
            # Alpaca stocks
            try:
                if alpaca_manager.is_connected:
                    alpaca_account = alpaca_manager.get_account()
                    if alpaca_account:
                        balances['alpaca'] = {
                            'USD': {
                                'free': alpaca_account['cash'],
                                'used': alpaca_account['portfolio_value'] - alpaca_account['cash'],
                                'total': alpaca_account['portfolio_value']
                            }
                        }
            except Exception as e:
                logger.debug(f"Could not fetch Alpaca balance: {e}")
            
        except Exception as e:
            logger.error(f"Error fetching account balances: {e}")
        
        return balances
    
    def get_latest_prices(self, pairs: List[str] = None) -> Dict:
        """Get latest prices from all platforms."""
        if pairs is None:
            pairs = [
                'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'XRP/USDT',
                'EUR/USD', 'GBP/USD', 'USD/JPY', 'XAU/USD',
                'AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA'
            ]
        
        all_prices = {}
        
        # Crypto prices from KuCoin
        crypto_pairs = [pair for pair in pairs if '/' in pair and 'USD' in pair]
        for pair in crypto_pairs:
            try:
                ticker = ccxt_manager.fetch_ticker('kucoin', pair)
                if ticker:
                    all_prices[pair] = ticker['price']
            except Exception as e:
                logger.debug(f"Could not fetch {pair} from KuCoin: {e}")
        
        # Forex prices from FXCM
        forex_pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'XAU/USD']
        if fxcm_manager.is_connected:
            try:
                fxcm_prices = fxcm_manager.get_prices(forex_pairs)
                for pair, data in fxcm_prices.items():
                    if 'bid' in data and 'ask' in data:
                        all_prices[pair] = (data['bid'] + data['ask']) / 2
            except Exception as e:
                logger.debug(f"Could not fetch forex prices: {e}")
        
        # Stock prices from Alpaca
        stock_symbols = [pair for pair in pairs if '/' not in pair]
        for symbol in stock_symbols:
            try:
                if alpaca_manager.is_connected:
                    quote = alpaca_manager.get_latest_quote(symbol)
                    if quote:
                        all_prices[symbol] = (quote['bid'] + quote['ask']) / 2
            except Exception as e:
                logger.debug(f"Could not fetch {symbol} from Alpaca: {e}")
        
        return all_prices
    
    def get_historical_data(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[Dict]:
        """Get historical data for a symbol."""
        try:
            # Determine platform based on symbol
            if '/' in symbol and any(crypto in symbol for crypto in ['USDT', 'BTC', 'ETH']):
                # Crypto
                return ccxt_manager.fetch_ohlcv('kucoin', symbol, timeframe, limit)
            elif symbol in ['EUR/USD', 'GBP/USD', 'USD/JPY', 'XAU/USD'] and fxcm_manager.is_connected:
                # Forex
                period_map = {'1m': 'm1', '5m': 'm5', '15m': 'm15', '30m': 'm30', '1h': 'H1', '4h': 'H4', '1d': 'D1'}
                fxcm_period = period_map.get(timeframe, 'H1')
                return fxcm_manager.get_candles(symbol, fxcm_period, limit)
            else:
                # Stocks
                if alpaca_manager.is_connected:
                    bars = alpaca_manager.get_bars([symbol], timeframe, limit)
                    return bars.get(symbol, [])
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
        
        return []
    
    def get_open_positions(self, user=None) -> List[Dict]:
        """Get open positions from all platforms."""
        all_positions = []
        
        try:
            # FXCM positions
            if fxcm_manager.is_connected:
                fxcm_positions = fxcm_manager.get_open_positions()
                for pos in fxcm_positions:
                    all_positions.append({
                        'platform': 'fxcm',
                        'symbol': pos['symbol'],
                        'side': pos['side'],
                        'size': pos['amount'],
                        'entry_price': pos['open_rate'],
                        'current_price': pos['close_rate'],
                        'pnl': pos['gross_pl'],
                        'timestamp': pos['timestamp']
                    })
            
            # Alpaca positions
            if alpaca_manager.is_connected:
                alpaca_positions = alpaca_manager.get_positions()
                for pos in alpaca_positions:
                    all_positions.append({
                        'platform': 'alpaca',
                        'symbol': pos['symbol'],
                        'side': pos['side'],
                        'size': abs(pos['qty']),
                        'entry_price': pos['avg_entry_price'],
                        'current_price': pos['current_price'],
                        'pnl': pos['unrealized_pl'],
                        'timestamp': datetime.now().timestamp() * 1000
                    })
        
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
        
        return all_positions
    
    def place_order(self, platform: str, symbol: str, side: str, size: float, 
                   order_type: str = 'market', price: float = None) -> Optional[Dict]:
        """Place an order on the specified platform."""
        try:
            if platform == 'fxcm' and fxcm_manager.is_connected:
                return fxcm_manager.place_market_order(symbol, side, int(size))
            elif platform == 'alpaca' and alpaca_manager.is_connected:
                return alpaca_manager.place_order(symbol, size, side, order_type, limit_price=price)
            elif platform in ['kucoin', 'binance'] and ccxt_manager.get_exchange(platform):
                return ccxt_manager.place_order(platform, symbol, order_type, side, size, price)
            else:
                logger.error(f"Platform {platform} not available or not connected")
                return None
        except Exception as e:
            logger.error(f"Error placing order on {platform}: {e}")
            return None
    
    def close_position(self, platform: str, symbol: str, position_id: str = None) -> bool:
        """Close a position on the specified platform."""
        try:
            if platform == 'fxcm' and fxcm_manager.is_connected:
                if position_id:
                    return fxcm_manager.close_position(position_id)
                else:
                    logger.error("Position ID required for FXCM")
                    return False
            elif platform == 'alpaca' and alpaca_manager.is_connected:
                result = alpaca_manager.close_position(symbol)
                return result is not None
            else:
                logger.error(f"Platform {platform} not supported for position closing")
                return False
        except Exception as e:
            logger.error(f"Error closing position on {platform}: {e}")
            return False
    
    def get_available_symbols(self, platform: str) -> List[str]:
        """Get available symbols for a platform."""
        try:
            if platform in ['kucoin', 'binance'] and ccxt_manager.get_exchange(platform):
                return ccxt_manager.get_available_symbols(platform)
            elif platform == 'fxcm' and fxcm_manager.is_connected:
                return fxcm_manager.get_instruments()
            else:
                # Return common symbols for demo purposes
                if platform == 'alpaca':
                    return ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'SPY', 'QQQ']
                elif platform == 'fxcm':
                    return ['EUR/USD', 'GBP/USD', 'USD/JPY', 'XAU/USD', 'AUD/USD']
                elif platform in ['kucoin', 'binance']:
                    return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'XRP/USDT']
        except Exception as e:
            logger.error(f"Error fetching symbols for {platform}: {e}")
        
        return []

# Global unified trading manager
unified_trading = UnifiedTradingManager()

def initialize_all_platforms():
    """Initialize all trading platforms with available credentials."""
    # This will be called when the module is imported
    logger.info("Unified trading manager initialized")

# Initialize on import
initialize_all_platforms()