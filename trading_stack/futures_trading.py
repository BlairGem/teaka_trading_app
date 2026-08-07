import logging
import json
import requests
import time
import hmac
import hashlib
import base64
from datetime import datetime
from config import KUCOIN_API_KEY, KUCOIN_SECRET_KEY, KUCOIN_PASSPHRASE

logger = logging.getLogger(__name__)

def get_kucoin_futures_balance(api_key, api_secret, passphrase):
    """Get futures account balance from KuCoin."""
    try:
        endpoint = '/api/v1/account-overview'
        now = int(time.time() * 1000)
        str_to_sign = str(now) + 'GET' + endpoint + ''
        
        # Create signature for authentication
        signature = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
        ).decode()
        
        passphrase_encoded = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), passphrase.encode('utf-8'), hashlib.sha256).digest()
        ).decode()
        
        headers = {
            'KC-API-SIGN': signature,
            'KC-API-TIMESTAMP': str(now),
            'KC-API-KEY': api_key,
            'KC-API-PASSPHRASE': passphrase_encoded,
            'KC-API-KEY-VERSION': '2'
        }
        
        url = f"https://api-futures.kucoin.com{endpoint}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data['code'] == '200000':
                return data['data']
            else:
                logger.error(f"KuCoin Futures API error: {data}")
                return None
        else:
            logger.error(f"Failed to get KuCoin futures balance: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error fetching KuCoin futures balance: {e}")
        return None

def get_kucoin_futures_positions(api_key, api_secret, passphrase):
    """Get futures positions from KuCoin."""
    try:
        endpoint = '/api/v1/positions'
        now = int(time.time() * 1000)
        str_to_sign = str(now) + 'GET' + endpoint
        
        signature = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
        ).decode()
        
        passphrase_encoded = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), passphrase.encode('utf-8'), hashlib.sha256).digest()
        ).decode()
        
        headers = {
            'KC-API-SIGN': signature,
            'KC-API-TIMESTAMP': str(now),
            'KC-API-KEY': api_key,
            'KC-API-PASSPHRASE': passphrase_encoded,
            'KC-API-KEY-VERSION': '2'
        }
        
        url = f"https://api-futures.kucoin.com{endpoint}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data['code'] == '200000':
                return data['data']
            else:
                logger.error(f"KuCoin Futures API error: {data}")
                return []
        else:
            logger.error(f"Failed to get KuCoin futures positions: {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"Error fetching KuCoin futures positions: {e}")
        return []

def place_kucoin_futures_order(api_key, api_secret, passphrase, symbol, side, size, order_type='market', price=None, leverage=1):
    """Place a futures order on KuCoin."""
    try:
        endpoint = '/api/v1/orders'
        now = int(time.time() * 1000)
        
        # Build order data
        order_data = {
            'clientOid': str(int(time.time() * 1000)),
            'symbol': symbol,
            'side': side,  # 'buy' or 'sell'
            'type': order_type,  # 'market' or 'limit'
            'size': size,
            'leverage': leverage
        }
        
        if order_type == 'limit' and price:
            order_data['price'] = price
        
        body = json.dumps(order_data)
        str_to_sign = str(now) + 'POST' + endpoint + body
        
        signature = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
        ).decode()
        
        passphrase_encoded = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), passphrase.encode('utf-8'), hashlib.sha256).digest()
        ).decode()
        
        headers = {
            'KC-API-SIGN': signature,
            'KC-API-TIMESTAMP': str(now),
            'KC-API-KEY': api_key,
            'KC-API-PASSPHRASE': passphrase_encoded,
            'KC-API-KEY-VERSION': '2',
            'Content-Type': 'application/json'
        }
        
        url = f"https://api-futures.kucoin.com{endpoint}"
        response = requests.post(url, headers=headers, data=body)
        
        if response.status_code == 200:
            data = response.json()
            if data['code'] == '200000':
                return data['data']
            else:
                logger.error(f"KuCoin Futures order error: {data}")
                return None
        else:
            logger.error(f"Failed to place KuCoin futures order: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error placing KuCoin futures order: {e}")
        return None

def get_kucoin_futures_symbols():
    """Get available futures symbols from KuCoin."""
    try:
        url = "https://api-futures.kucoin.com/api/v1/contracts/active"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data['code'] == '200000':
                return data['data']
            else:
                logger.error(f"KuCoin Futures API error: {data}")
                return []
        else:
            logger.error(f"Failed to get KuCoin futures symbols: {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"Error fetching KuCoin futures symbols: {e}")
        return []

def get_kucoin_futures_klines(symbol, granularity, start_at=None, end_at=None):
    """Get futures candlestick data from KuCoin."""
    try:
        endpoint = f"/api/v1/kline/query"
        params = {
            'symbol': symbol,
            'granularity': granularity  # 1min, 5min, 15min, 30min, 1hour, 2hour, 4hour, 6hour, 8hour, 12hour, 1day, 1week
        }
        
        if start_at:
            params['from'] = start_at
        if end_at:
            params['to'] = end_at
        
        url = f"https://api-futures.kucoin.com{endpoint}"
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data['code'] == '200000':
                return data['data']
            else:
                logger.error(f"KuCoin Futures API error: {data}")
                return []
        else:
            logger.error(f"Failed to get KuCoin futures klines: {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"Error fetching KuCoin futures klines: {e}")
        return []

def close_kucoin_futures_position(api_key, api_secret, passphrase, symbol):
    """Close a futures position on KuCoin."""
    try:
        # First get the current position
        positions = get_kucoin_futures_positions(api_key, api_secret, passphrase)
        target_position = None
        
        for position in positions:
            if position['symbol'] == symbol:
                target_position = position
                break
        
        if not target_position:
            logger.error(f"No position found for symbol {symbol}")
            return None
        
        # Determine the opposite side to close the position
        current_side = target_position['side']
        close_side = 'sell' if current_side == 'long' else 'buy'
        size = abs(float(target_position['currentQty']))
        
        # Place market order to close position
        return place_kucoin_futures_order(
            api_key, api_secret, passphrase, 
            symbol, close_side, size, 'market'
        )
    
    except Exception as e:
        logger.error(f"Error closing KuCoin futures position: {e}")
        return None

def get_ib_futures_contracts():
    """Get available futures contracts from Interactive Brokers."""
    try:
        # Interactive Brokers CP Web API endpoint
        base_url = "https://localhost:5000/v1/api"
        endpoint = "/trsrv/futures"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, verify=True)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            logger.error(f"Failed to get IB futures contracts: {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"Error fetching IB futures contracts: {e}")
        return []

def place_ib_futures_order(account_id, contract_id, side, quantity, order_type='MKT', price=None):
    """Place a futures order through Interactive Brokers."""
    try:
        base_url = "https://localhost:5000/v1/api"
        endpoint = f"/iserver/account/{account_id}/orders"
        
        order_data = {
            "orders": [{
                "conid": contract_id,
                "orderType": order_type,
                "side": side.upper(),  # BUY or SELL
                "quantity": quantity,
                "tif": "DAY"
            }]
        }
        
        if order_type == 'LMT' and price:
            order_data["orders"][0]["price"] = price
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        url = f"{base_url}{endpoint}"
        response = requests.post(url, headers=headers, json=order_data, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            logger.error(f"Failed to place IB futures order: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error placing IB futures order: {e}")
        return None