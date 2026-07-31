import alpaca_trade_api as tradeapi
import logging
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AlpacaManager:
    """Manager for Alpaca stock and crypto trading integration."""
    
    def __init__(self):
        self.api = None
        self.is_connected = False
    
    def connect(self, api_key: str, secret_key: str, base_url: str = None) -> bool:
        """Connect to Alpaca API."""
        try:
            if base_url is None:
                base_url = 'https://paper-api.alpaca.markets'  # Paper trading by default
            
            self.api = tradeapi.REST(
                api_key,
                secret_key,
                base_url,
                api_version='v2'
            )
            
            # Test connection
            account = self.api.get_account()
            if account:
                self.is_connected = True
                logger.info(f"Successfully connected to Alpaca (Account: {account.id})")
                return True
            else:
                logger.error("Failed to get Alpaca account info")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Alpaca: {e}")
            return False
    
    def get_account(self) -> Optional[Dict]:
        """Get account information."""
        try:
            if not self.is_connected:
                logger.error("Alpaca not connected")
                return None
            
            account = self.api.get_account()
            return {
                'id': account.id,
                'account_number': account.account_number,
                'status': account.status,
                'currency': account.currency,
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power),
                'equity': float(account.equity),
                'long_market_value': float(account.long_market_value),
                'short_market_value': float(account.short_market_value),
                'day_trade_count': account.day_trade_count,
                'pattern_day_trader': account.pattern_day_trader
            }
        except Exception as e:
            logger.error(f"Error fetching Alpaca account: {e}")
            return None
    
    def get_positions(self) -> List[Dict]:
        """Get current positions."""
        try:
            if not self.is_connected:
                logger.error("Alpaca not connected")
                return []
            
            positions = self.api.list_positions()
            formatted_positions = []
            
            for position in positions:
                formatted_positions.append({
                    'symbol': position.symbol,
                    'qty': float(position.qty),
                    'side': 'long' if float(position.qty) > 0 else 'short',
                    'market_value': float(position.market_value),
                    'cost_basis': float(position.cost_basis),
                    'unrealized_pl': float(position.unrealized_pl),
                    'unrealized_plpc': float(position.unrealized_plpc),
                    'avg_entry_price': float(position.avg_entry_price),
                    'current_price': float(position.current_price)
                })
            
            return formatted_positions
        except Exception as e:
            logger.error(f"Error fetching Alpaca positions: {e}")
            return []
    
    def get_bars(self, symbols: List[str], timeframe: str = '1Hour', 
                limit: int = 100, asof: str = None) -> Dict[str, List[Dict]]:
        """Get historical bar data."""
        try:
            if not self.is_connected:
                logger.error("Alpaca not connected")
                return {}
            
            # Convert timeframe to Alpaca format
            timeframe_map = {
                '1m': '1Min', '5m': '5Min', '15m': '15Min', '30m': '30Min',
                '1h': '1Hour', '4h': '4Hour', '1d': '1Day', '1w': '1Week'
            }
            alpaca_timeframe = timeframe_map.get(timeframe, '1Hour')
            
            bars = self.api.get_bars(
                symbols,
                alpaca_timeframe,
                limit=limit,
                asof=asof
            )
            
            formatted_data = {}
            for symbol in symbols:
                formatted_data[symbol] = []
                if symbol in bars:
                    for bar in bars[symbol]:
                        formatted_data[symbol].append({
                            'timestamp': int(bar.t.timestamp() * 1000),
                            'datetime': bar.t,
                            'open': float(bar.o),
                            'high': float(bar.h),
                            'low': float(bar.l),
                            'close': float(bar.c),
                            'volume': int(bar.v)
                        })
            
            return formatted_data
        except Exception as e:
            logger.error(f"Error fetching Alpaca bars: {e}")
            return {}
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """Get latest quote for a symbol."""
        try:
            if not self.is_connected:
                logger.error("Alpaca not connected")
                return None
            
            quote = self.api.get_latest_quote(symbol)
            return {
                'symbol': symbol,
                'bid': float(quote.bid_price),
                'ask': float(quote.ask_price),
                'bid_size': int(quote.bid_size),
                'ask_size': int(quote.ask_size),
                'timestamp': int(quote.timestamp.timestamp() * 1000)
            }
        except Exception as e:
            logger.error(f"Error fetching Alpaca quote for {symbol}: {e}")
            return None
    
    def place_order(self, symbol: str, qty: float, side: str, order_type: str = 'market',
                   time_in_force: str = 'day', limit_price: float = None,
                   stop_price: float = None, trail_price: float = None) -> Optional[Dict]:
        """Place an order."""
        try:
            if not self.is_connected:
                logger.error("Alpaca not connected")
                return None
            
            order_params = {
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'type': order_type,
                'time_in_force': time_in_force
            }
            
            if limit_price:
                order_params['limit_price'] = limit_price
            if stop_price:
                order_params['stop_price'] = stop_price
            if trail_price:
                order_params['trail_price'] = trail_price
            
            order = self.api.submit_order(**order_params)
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'type': order.order_type,
                'status': order.status,
                'limit_price': float(order.limit_price) if order.limit_price else None,
                'stop_price': float(order.stop_price) if order.stop_price else None,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0
            }
        except Exception as e:
            logger.error(f"Error placing Alpaca order: {e}")
            return None
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order status."""
        try:
            if not self.is_connected:
                logger.error("Alpaca not connected")
                return None
            
            order = self.api.get_order(order_id)
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'type': order.order_type,
                'status': order.status,
                'limit_price': float(order.limit_price) if order.limit_price else None,
                'stop_price': float(order.stop_price) if order.stop_price else None,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
            }
        except Exception as e:
            logger.error(f"Error fetching Alpaca order {order_id}: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            if not self.is_connected:
                logger.error("Alpaca not connected")
                return False
            
            self.api.cancel_order(order_id)
            logger.info(f"Cancelled Alpaca order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling Alpaca order {order_id}: {e}")
            return False
    
    def close_position(self, symbol: str, qty: str = None) -> Optional[Dict]:
        """Close a position."""
        try:
            if not self.is_connected:
                logger.error("Alpaca not connected")
                return None
            
            order = self.api.close_position(symbol, qty=qty)
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'type': order.order_type,
                'status': order.status
            }
        except Exception as e:
            logger.error(f"Error closing Alpaca position for {symbol}: {e}")
            return None
    
    def close_all_positions(self) -> bool:
        """Close all positions."""
        try:
            if not self.is_connected:
                logger.error("Alpaca not connected")
                return False
            
            self.api.close_all_positions()
            logger.info("Closed all Alpaca positions")
            return True
        except Exception as e:
            logger.error(f"Error closing all Alpaca positions: {e}")
            return False
    
    def get_portfolio_history(self, period: str = '1M', timeframe: str = '1D') -> Optional[Dict]:
        """Get portfolio history."""
        try:
            if not self.is_connected:
                logger.error("Alpaca not connected")
                return None
            
            portfolio = self.api.get_portfolio_history(period=period, timeframe=timeframe)
            return {
                'timestamp': [int(t.timestamp() * 1000) for t in portfolio.timestamp],
                'equity': [float(e) for e in portfolio.equity],
                'profit_loss': [float(pl) for pl in portfolio.profit_loss],
                'profit_loss_pct': [float(plp) for plp in portfolio.profit_loss_pct],
                'base_value': float(portfolio.base_value)
            }
        except Exception as e:
            logger.error(f"Error fetching Alpaca portfolio history: {e}")
            return None

# Global Alpaca manager instance
alpaca_manager = AlpacaManager()

def initialize_alpaca():
    """Initialize Alpaca connection if credentials are available."""
    alpaca_key = os.environ.get('ALPACA_API_KEY')
    alpaca_secret = os.environ.get('ALPACA_SECRET_KEY')
    alpaca_base_url = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    
    if alpaca_key and alpaca_secret:
        alpaca_manager.connect(alpaca_key, alpaca_secret, alpaca_base_url)
    else:
        logger.info("Alpaca credentials not provided")

# Initialize Alpaca on import
initialize_alpaca()