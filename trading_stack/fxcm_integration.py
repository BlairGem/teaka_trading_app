import fxcmpy
import logging
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class FXCMManager:
    """Manager for FXCM forex trading integration."""
    
    def __init__(self):
        self.connection = None
        self.is_connected = False
    
    def connect(self, access_token: str, log_level: str = 'error') -> bool:
        """Connect to FXCM API."""
        try:
            self.connection = fxcmpy.fxcmpy(
                access_token=access_token,
                log_level=log_level,
                server='demo'  # Use 'real' for live trading
            )
            
            if self.connection.connection_status == 'established':
                self.is_connected = True
                logger.info("Successfully connected to FXCM")
                return True
            else:
                logger.error("Failed to establish FXCM connection")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to FXCM: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from FXCM API."""
        try:
            if self.connection and self.is_connected:
                self.connection.close()
                self.is_connected = False
                logger.info("Disconnected from FXCM")
        except Exception as e:
            logger.error(f"Error disconnecting from FXCM: {e}")
    
    def get_instruments(self) -> List[str]:
        """Get available trading instruments."""
        try:
            if not self.is_connected:
                logger.error("FXCM not connected")
                return []
            
            instruments = self.connection.get_instruments()
            return instruments.tolist() if hasattr(instruments, 'tolist') else list(instruments)
        except Exception as e:
            logger.error(f"Error fetching FXCM instruments: {e}")
            return []
    
    def get_candles(self, instrument: str, period: str = 'H1', number: int = 100) -> List[Dict]:
        """Get historical candle data."""
        try:
            if not self.is_connected:
                logger.error("FXCM not connected")
                return []
            
            candles = self.connection.get_candles(instrument, period=period, number=number)
            
            formatted_data = []
            for index, row in candles.iterrows():
                formatted_data.append({
                    'timestamp': int(index.timestamp() * 1000),
                    'datetime': index,
                    'open': row['bidopen'],
                    'high': row['bidhigh'],
                    'low': row['bidlow'],
                    'close': row['bidclose'],
                    'volume': row.get('tickqty', 0)
                })
            
            return formatted_data
        except Exception as e:
            logger.error(f"Error fetching FXCM candles for {instrument}: {e}")
            return []
    
    def get_prices(self, instruments: List[str] = None) -> Dict:
        """Get current prices for instruments."""
        try:
            if not self.is_connected:
                logger.error("FXCM not connected")
                return {}
            
            if instruments is None:
                instruments = self.get_instruments()
            
            prices = {}
            for instrument in instruments:
                try:
                    price_data = self.connection.get_last_price(instrument)
                    prices[instrument] = {
                        'bid': price_data['Bid'],
                        'ask': price_data['Ask'],
                        'spread': price_data['Ask'] - price_data['Bid'],
                        'timestamp': datetime.now().timestamp() * 1000
                    }
                except Exception as e:
                    logger.warning(f"Error fetching price for {instrument}: {e}")
                    continue
            
            return prices
        except Exception as e:
            logger.error(f"Error fetching FXCM prices: {e}")
            return {}
    
    def get_account_summary(self) -> Optional[Dict]:
        """Get account summary information."""
        try:
            if not self.is_connected:
                logger.error("FXCM not connected")
                return None
            
            accounts = self.connection.get_accounts()
            if not accounts.empty:
                account = accounts.iloc[0]
                return {
                    'account_id': account['accountId'],
                    'balance': account['balance'],
                    'equity': account['equity'],
                    'margin': account['usableMargin'],
                    'currency': account['accountCurrency']
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching FXCM account summary: {e}")
            return None
    
    def get_open_positions(self) -> List[Dict]:
        """Get open positions."""
        try:
            if not self.is_connected:
                logger.error("FXCM not connected")
                return []
            
            positions = self.connection.get_open_positions()
            formatted_positions = []
            
            for index, position in positions.iterrows():
                formatted_positions.append({
                    'trade_id': position['tradeId'],
                    'account_id': position['accountId'],
                    'symbol': position['currency'],
                    'side': 'buy' if position['isBuy'] else 'sell',
                    'amount': position['amountK'] * 1000,
                    'open_rate': position['open'],
                    'close_rate': position['close'],
                    'gross_pl': position['grossPL'],
                    'pip_pl': position['pipPL'],
                    'timestamp': position['time']
                })
            
            return formatted_positions
        except Exception as e:
            logger.error(f"Error fetching FXCM open positions: {e}")
            return []
    
    def place_market_order(self, symbol: str, side: str, amount: int, 
                          stop_loss: float = None, take_profit: float = None) -> Optional[Dict]:
        """Place a market order."""
        try:
            if not self.is_connected:
                logger.error("FXCM not connected")
                return None
            
            is_buy = side.lower() == 'buy'
            
            order_params = {
                'symbol': symbol,
                'is_buy': is_buy,
                'amount': amount
            }
            
            if stop_loss:
                order_params['stop'] = stop_loss
            if take_profit:
                order_params['limit'] = take_profit
            
            order_id = self.connection.create_market_buy_order(**order_params) if is_buy else \
                      self.connection.create_market_sell_order(**order_params)
            
            return {
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'type': 'market',
                'status': 'pending',
                'timestamp': datetime.now().timestamp() * 1000
            }
        except Exception as e:
            logger.error(f"Error placing FXCM market order: {e}")
            return None
    
    def close_position(self, trade_id: str) -> bool:
        """Close an open position."""
        try:
            if not self.is_connected:
                logger.error("FXCM not connected")
                return False
            
            self.connection.close_trade(trade_id=trade_id)
            logger.info(f"Closed FXCM position {trade_id}")
            return True
        except Exception as e:
            logger.error(f"Error closing FXCM position {trade_id}: {e}")
            return False
    
    def close_all_positions(self) -> bool:
        """Close all open positions."""
        try:
            if not self.is_connected:
                logger.error("FXCM not connected")
                return False
            
            self.connection.close_all_for_symbol()
            logger.info("Closed all FXCM positions")
            return True
        except Exception as e:
            logger.error(f"Error closing all FXCM positions: {e}")
            return False

# Global FXCM manager instance
fxcm_manager = FXCMManager()

def initialize_fxcm():
    """Initialize FXCM connection if token is available."""
    fxcm_token = os.environ.get('FXCM_ACCESS_TOKEN')
    if fxcm_token:
        fxcm_manager.connect(fxcm_token)
    else:
        logger.info("FXCM access token not provided")

# Initialize FXCM on import
initialize_fxcm()