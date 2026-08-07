import logging
import json
import requests
import time
import hmac
import hashlib
import base64
from datetime import datetime, timezone
import uuid
from config import (
    KUCOIN_API_KEY, KUCOIN_SECRET_KEY, KUCOIN_PASSPHRASE,
    OANDA_API_KEY, OANDA_ACCOUNT_ID,
    IB_API_KEY, IB_ACCOUNT_ID
)

logger = logging.getLogger(__name__)

def get_account_balance(user):
    """Get account balance for all connected brokers."""
    balances = {}
    
    # Check if user has KuCoin API keys
    if hasattr(user, 'kucoin_api_key') and user.kucoin_api_key and user.kucoin_api_secret:
        kucoin_balance = get_kucoin_account_balance(
            api_key=user.kucoin_api_key,
            api_secret=user.kucoin_api_secret,
            passphrase=user.kucoin_passphrase
        )
        if kucoin_balance:
            balances['kucoin'] = kucoin_balance
    
    # Check if user has OANDA API keys
    if user.oanda_api_key and user.oanda_account_id:
        oanda_balance = get_oanda_account_balance(
            api_key=user.oanda_api_key,
            account_id=user.oanda_account_id
        )
        if oanda_balance:
            balances['oanda'] = oanda_balance
    
    # Check if user has Interactive Brokers API keys
    if hasattr(user, 'ib_api_key') and user.ib_api_key and user.ib_account_id:
        ib_balance = get_ib_account_balance(
            api_key=user.ib_api_key,
            account_id=user.ib_account_id
        )
        if ib_balance:
            balances['interactive_brokers'] = ib_balance
    
    # If user has no API keys configured, use the default ones
    if not balances:
        if KUCOIN_API_KEY and KUCOIN_SECRET_KEY:
            kucoin_balance = get_kucoin_account_balance(
                api_key=KUCOIN_API_KEY,
                api_secret=KUCOIN_SECRET_KEY,
                passphrase=KUCOIN_PASSPHRASE
            )
            if kucoin_balance:
                balances['kucoin'] = kucoin_balance
        
        if OANDA_API_KEY and OANDA_ACCOUNT_ID:
            oanda_balance = get_oanda_account_balance(
                api_key=OANDA_API_KEY,
                account_id=OANDA_ACCOUNT_ID
            )
            if oanda_balance:
                balances['oanda'] = oanda_balance
    
    return balances

def get_kucoin_account_balance(api_key, api_secret, passphrase):
    """Get account balance from KuCoin."""
    try:
        # Set up the request
        endpoint = '/api/v1/accounts'
        now = int(time.time() * 1000)
        str_to_sign = str(now) + 'GET' + endpoint
        
        # Create signature for authentication
        signature = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
        ).decode()
        
        passphrase_encoded = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), passphrase.encode('utf-8'), hashlib.sha256).digest()
        ).decode()
        
        # Set up headers
        headers = {
            'KC-API-SIGN': signature,
            'KC-API-TIMESTAMP': str(now),
            'KC-API-KEY': api_key,
            'KC-API-PASSPHRASE': passphrase_encoded,
            'KC-API-KEY-VERSION': '2'
        }
        
        # Make the request
        url = f"https://api.kucoin.com{endpoint}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['code'] == '200000':
                # Extract balances with non-zero amounts
                balances = {}
                for account in data['data']:
                    if account['type'] == 'trade':  # Trading account
                        balance = float(account['balance'])
                        available = float(account['available'])
                        holds = float(account['holds'])
                        
                        if balance > 0:
                            balances[account['currency']] = {
                                'available': available,
                                'holds': holds,
                                'balance': balance
                            }
                
                return {
                    'balances': balances
                }
            else:
                logger.error(f"KuCoin API error: {data}")
                return None
        else:
            logger.error(f"Failed to get KuCoin account balance: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error fetching KuCoin account balance: {e}")
        return None

def get_ib_account_balance(api_key, account_id):
    """Get account balance from Interactive Brokers."""
    try:
        # Interactive Brokers CP Web API endpoint
        base_url = "https://localhost:5000/v1/api"
        endpoint = f"/portfolio/{account_id}/summary"
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Make the request
        url = f"{base_url}{endpoint}"
        # Use timeout and enable certificate verification
        # For production, configure proper SSL certificates or certificate bundle
        try:
            response = requests.get(url, headers=headers, verify=True, timeout=30)
        except requests.exceptions.SSLError:
            # If SSL verification fails, log the error and return None for security
            logger.error(f"SSL certificate verification failed for {url}. Configure proper certificates.")
            return None
        
        if response.status_code == 200:
            data = response.json()
            
            balances = {}
            for currency, balance_info in data.items():
                if isinstance(balance_info, dict) and 'amount' in balance_info:
                    balances[currency] = {
                        'amount': float(balance_info['amount']),
                        'currency': currency
                    }
            
            return {
                'balances': balances,
                'account_id': account_id
            }
        else:
            logger.error(f"Failed to get Interactive Brokers account balance: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error fetching Interactive Brokers account balance: {e}")
        return None

def get_oanda_account_balance(api_key, account_id):
    """Get account balance from OANDA."""
    try:
        # Set up the request
        endpoint = f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}'
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Make the request
        response = requests.get(endpoint, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract account details
            account = data['account']
            
            return {
                'balance': float(account['balance']),
                'currency': account['currency'],
                'margin_available': float(account['marginAvailable']),
                'margin_used': float(account['marginUsed']),
                'margin_rate': float(account['marginRate']),
                'unrealized_pl': float(account['unrealizedPL']),
                'net_asset_value': float(account['NAV']),
                'positions': len(account['positions'])
            }
        else:
            logger.error(f"Failed to get OANDA account balance: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error fetching OANDA account balance: {e}")
        return None

def execute_trade(user, platform, trading_pair, order_type, amount, price=None, stop_loss=None, take_profit=None):
    """Execute a trade on the specified platform."""
    if platform.lower() == 'binance':
        # Get user API keys or use default ones
        api_key = user.binance_api_key if user.binance_api_key else BINANCE_API_KEY
        api_secret = user.binance_api_secret if user.binance_api_secret else BINANCE_SECRET_KEY
        
        if not api_key or not api_secret:
            logger.error("Binance API keys not configured")
            return None
        
        return execute_binance_trade(
            api_key=api_key,
            api_secret=api_secret,
            trading_pair=trading_pair.replace('/', ''),  # Remove / from BTC/USDT to get BTCUSDT
            side=order_type,
            quantity=amount,
            price=price
        )
    
    elif platform.lower() == 'oanda':
        # Get user API keys or use default ones
        api_key = user.oanda_api_key if user.oanda_api_key else OANDA_API_KEY
        account_id = user.oanda_account_id if user.oanda_account_id else OANDA_ACCOUNT_ID
        
        if not api_key or not account_id:
            logger.error("OANDA API keys not configured")
            return None
        
        # For OANDA, we need to format the instrument properly (e.g. EUR_USD)
        instrument = trading_pair.replace('/', '_')
        
        return execute_oanda_trade(
            api_key=api_key,
            account_id=account_id,
            instrument=instrument,
            side=order_type,
            units=amount,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
    
    else:
        logger.error(f"Unsupported platform: {platform}")
        return None

def execute_binance_trade(api_key, api_secret, trading_pair, side, quantity, price=None):
    """Execute a trade on Binance."""
    try:
        # Set up the request
        endpoint = 'https://api.binance.com/api/v3/order'
        
        # Prepare parameters
        params = {
            'symbol': trading_pair,
            'side': side,
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }
        
        # Set order type and price
        if price:
            params['type'] = 'LIMIT'
            params['price'] = price
            params['timeInForce'] = 'GTC'  # Good Till Canceled
        else:
            params['type'] = 'MARKET'
        
        # Create signature for authentication
        query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params.keys())])
        signature = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Add signature to parameters
        params['signature'] = signature
        
        # Set up headers
        headers = {
            'X-MBX-APIKEY': api_key
        }
        
        # Make the request
        response = requests.post(endpoint, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            return {
                'order_id': str(data['orderId']),
                'status': data['status'],
                'price': float(data['price']) if data['price'] != '0' else None,
                'quantity': float(data['origQty']),
                'executed_quantity': float(data['executedQty']),
                'trading_pair': data['symbol'],
                'side': data['side']
            }
        else:
            logger.error(f"Failed to execute Binance trade: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error executing Binance trade: {e}")
        return None

def execute_oanda_trade(api_key, account_id, instrument, side, units, price=None, stop_loss=None, take_profit=None):
    """Execute a trade on OANDA."""
    try:
        # Set up the request
        endpoint = f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/orders'
        
        # Prepare order body
        order = {
            'order': {
                'type': 'MARKET' if price is None else 'LIMIT',
                'instrument': instrument,
                'units': units if side == 'BUY' else -units,  # Negative units for SELL
                'timeInForce': 'GTC'  # Good Till Canceled
            }
        }
        
        # Add price for limit orders
        if price:
            order['order']['price'] = str(price)
        
        # Add stop loss if provided
        if stop_loss:
            order['order']['stopLossOnFill'] = {
                'price': str(stop_loss)
            }
        
        # Add take profit if provided
        if take_profit:
            order['order']['takeProfitOnFill'] = {
                'price': str(take_profit)
            }
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Make the request
        response = requests.post(endpoint, headers=headers, json=order)
        
        if response.status_code == 201:
            data = response.json()
            
            # Extract order details
            order_data = data['orderCreateTransaction']
            
            return {
                'order_id': order_data['id'],
                'status': 'pending',  # OANDA doesn't return immediate execution status
                'price': float(order_data['price']) if 'price' in order_data else None,
                'units': abs(float(order_data['units'])),
                'instrument': order_data['instrument'],
                'side': 'BUY' if float(order_data['units']) > 0 else 'SELL'
            }
        else:
            logger.error(f"Failed to execute OANDA trade: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error executing OANDA trade: {e}")
        return None

def check_order_status(user_id, platform, order_id):
    """Check the status of an order."""
    from models import User
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        return None
    
    if platform.lower() == 'binance':
        # Get user API keys or use default ones
        api_key = user.binance_api_key if user.binance_api_key else BINANCE_API_KEY
        api_secret = user.binance_api_secret if user.binance_api_secret else BINANCE_SECRET_KEY
        
        if not api_key or not api_secret:
            logger.error("Binance API keys not configured")
            return None
        
        return check_binance_order_status(api_key, api_secret, order_id)
    
    elif platform.lower() == 'oanda':
        # Get user API keys or use default ones
        api_key = user.oanda_api_key if user.oanda_api_key else OANDA_API_KEY
        account_id = user.oanda_account_id if user.oanda_account_id else OANDA_ACCOUNT_ID
        
        if not api_key or not account_id:
            logger.error("OANDA API keys not configured")
            return None
        
        return check_oanda_order_status(api_key, account_id, order_id)
    
    else:
        logger.error(f"Unsupported platform: {platform}")
        return None

def check_binance_order_status(api_key, api_secret, order_id):
    """Check the status of an order on Binance."""
    try:
        # Set up the request
        endpoint = 'https://api.binance.com/api/v3/order'
        
        # Create signature for authentication
        timestamp = int(time.time() * 1000)
        query_string = f'orderId={order_id}&timestamp={timestamp}'
        signature = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Build full URL
        url = f"{endpoint}?{query_string}&signature={signature}"
        
        # Set up headers
        headers = {
            'X-MBX-APIKEY': api_key
        }
        
        # Make the request
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data['status'].lower()
        else:
            logger.error(f"Failed to check Binance order status: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error checking Binance order status: {e}")
        return None

def check_oanda_order_status(api_key, account_id, order_id):
    """Check the status of an order on OANDA."""
    try:
        # Set up the request to get order details
        endpoint = f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/orders/{order_id}'
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Make the request
        response = requests.get(endpoint, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract order status
            order = data['order']
            
            if order['state'] == 'FILLED':
                return 'filled'
            elif order['state'] == 'CANCELLED':
                return 'canceled'
            elif order['state'] == 'PENDING':
                return 'pending'
            else:
                return order['state'].lower()
        else:
            logger.error(f"Failed to check OANDA order status: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error checking OANDA order status: {e}")
        return None

def get_open_positions(user_id):
    """Get all open positions for a user."""
    from models import User, TradeExecution
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        return []
    
    positions = []
    
    # Check if user has Binance API keys
    if user.binance_api_key and user.binance_api_secret:
        binance_positions = get_binance_open_positions(
            api_key=user.binance_api_key,
            api_secret=user.binance_api_secret
        )
        positions.extend(binance_positions)
    
    # Check if user has OANDA API keys
    if user.oanda_api_key and user.oanda_account_id:
        oanda_positions = get_oanda_open_positions(
            api_key=user.oanda_api_key,
            account_id=user.oanda_account_id
        )
        positions.extend(oanda_positions)
    
    # If user has no API keys configured, use the default ones
    if not positions:
        if BINANCE_API_KEY and BINANCE_SECRET_KEY:
            binance_positions = get_binance_open_positions(
                api_key=BINANCE_API_KEY,
                api_secret=BINANCE_SECRET_KEY
            )
            positions.extend(binance_positions)
        
        if OANDA_API_KEY and OANDA_ACCOUNT_ID:
            oanda_positions = get_oanda_open_positions(
                api_key=OANDA_API_KEY,
                account_id=OANDA_ACCOUNT_ID
            )
            positions.extend(oanda_positions)
    
    return positions

def get_binance_open_positions(api_key, api_secret):
    """Get open positions from Binance."""
    try:
        # Set up the request
        endpoint = 'https://api.binance.com/api/v3/openOrders'
        
        # Create signature for authentication
        timestamp = int(time.time() * 1000)
        query_string = f'timestamp={timestamp}'
        signature = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Build full URL
        url = f"{endpoint}?{query_string}&signature={signature}"
        
        # Set up headers
        headers = {
            'X-MBX-APIKEY': api_key
        }
        
        # Make the request
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            orders = response.json()
            
            # Format the response
            positions = []
            for order in orders:
                position_id = str(order['orderId'])
                
                # Format the trading pair
                symbol = order['symbol']
                if symbol.endswith('USDT'):
                    formatted_pair = f"{symbol[:-4]}/USDT"
                else:
                    formatted_pair = symbol
                
                positions.append({
                    'id': position_id,
                    'trading_pair': formatted_pair,
                    'type': order['side'],
                    'amount': float(order['origQty']),
                    'entry_price': float(order['price']) if order['price'] != '0' else None,
                    'current_price': None,  # Need to fetch current price separately
                    'pnl': None,  # Need to calculate based on current price
                    'timestamp': datetime.fromtimestamp(order['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                    'platform': 'binance'
                })
            
            return positions
        else:
            logger.error(f"Failed to get Binance open positions: {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"Error fetching Binance open positions: {e}")
        return []

def get_oanda_open_positions(api_key, account_id):
    """Get open positions from OANDA."""
    try:
        # Set up the request
        endpoint = f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/openPositions'
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Make the request
        response = requests.get(endpoint, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            positions = data.get('positions', [])
            
            # Format the response
            formatted_positions = []
            for position in positions:
                # Get position details
                position_id = position['id'] if 'id' in position else position['instrument']
                instrument = position['instrument']
                formatted_pair = instrument.replace('_', '/')
                
                # Get long or short position
                long_units = int(position['long']['units']) if 'long' in position else 0
                short_units = abs(int(position['short']['units'])) if 'short' in position else 0
                
                if long_units > 0:
                    position_type = 'BUY'
                    amount = long_units
                    entry_price = float(position['long']['averagePrice'])
                    pnl = float(position['long']['unrealizedPL'])
                else:
                    position_type = 'SELL'
                    amount = short_units
                    entry_price = float(position['short']['averagePrice'])
                    pnl = float(position['short']['unrealizedPL'])
                
                formatted_positions.append({
                    'id': position_id,
                    'trading_pair': formatted_pair,
                    'type': position_type,
                    'amount': amount,
                    'entry_price': entry_price,
                    'current_price': None,  # Need to fetch current price separately
                    'pnl': pnl,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # OANDA doesn't provide timestamp
                    'platform': 'oanda'
                })
            
            return formatted_positions
        else:
            logger.error(f"Failed to get OANDA open positions: {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"Error fetching OANDA open positions: {e}")
        return []

def close_position(user_id, position_id):
    """Close a position."""
    from models import User
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        return None
    
    # Get position details
    position = get_position_details(position_id, user_id)
    if not position:
        logger.error(f"Position {position_id} not found")
        return None
    
    platform = position['platform']
    
    if platform.lower() == 'binance':
        # Get user API keys or use default ones
        api_key = user.binance_api_key if user.binance_api_key else BINANCE_API_KEY
        api_secret = user.binance_api_secret if user.binance_api_secret else BINANCE_SECRET_KEY
        
        if not api_key or not api_secret:
            logger.error("Binance API keys not configured")
            return None
        
        return close_binance_position(api_key, api_secret, position)
    
    elif platform.lower() == 'oanda':
        # Get user API keys or use default ones
        api_key = user.oanda_api_key if user.oanda_api_key else OANDA_API_KEY
        account_id = user.oanda_account_id if user.oanda_account_id else OANDA_ACCOUNT_ID
        
        if not api_key or not account_id:
            logger.error("OANDA API keys not configured")
            return None
        
        return close_oanda_position(api_key, account_id, position)
    
    else:
        logger.error(f"Unsupported platform: {platform}")
        return None

def close_binance_position(api_key, api_secret, position):
    """Close a position on Binance."""
    try:
        # Set up the request
        endpoint = 'https://api.binance.com/api/v3/order'
        
        # Prepare parameters
        trading_pair = position['trading_pair'].replace('/', '')  # Remove / from BTC/USDT to get BTCUSDT
        side = 'SELL' if position['type'] == 'BUY' else 'BUY'  # Opposite of position type
        
        params = {
            'symbol': trading_pair,
            'side': side,
            'type': 'MARKET',
            'quantity': position['amount'],
            'timestamp': int(time.time() * 1000)
        }
        
        # Create signature for authentication
        query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params.keys())])
        signature = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Add signature to parameters
        params['signature'] = signature
        
        # Set up headers
        headers = {
            'X-MBX-APIKEY': api_key
        }
        
        # Make the request
        response = requests.post(endpoint, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Calculate PnL
            entry_price = position['entry_price'] or 0
            exit_price = float(data['price']) if 'price' in data and data['price'] != '0' else 0
            
            if exit_price == 0:
                # If price is not available, make a separate request to get the market price
                price_response = requests.get(
                    f'https://api.binance.com/api/v3/ticker/price?symbol={trading_pair}',
                    headers={'X-MBX-APIKEY': api_key}
                )
                
                if price_response.status_code == 200:
                    price_data = price_response.json()
                    exit_price = float(price_data['price'])
            
            if side == 'SELL':
                pnl = (exit_price - entry_price) * position['amount']
            else:
                pnl = (entry_price - exit_price) * position['amount']
            
            return {
                'order_id': str(data['orderId']),
                'status': data['status'],
                'price': exit_price,
                'pnl': pnl
            }
        else:
            logger.error(f"Failed to close Binance position: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error closing Binance position: {e}")
        return None

def close_oanda_position(api_key, account_id, position):
    """Close a position on OANDA."""
    try:
        # Set up the request
        instrument = position['trading_pair'].replace('/', '_')  # Convert EUR/USD to EUR_USD
        endpoint = f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/positions/{instrument}/close'
        
        # Prepare request body
        body = {
            'longUnits': 'ALL' if position['type'] == 'BUY' else 'NONE',
            'shortUnits': 'ALL' if position['type'] == 'SELL' else 'NONE'
        }
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Make the request
        response = requests.put(endpoint, headers=headers, json=body)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract order details
            if 'longOrderFillTransaction' in data:
                fill = data['longOrderFillTransaction']
            elif 'shortOrderFillTransaction' in data:
                fill = data['shortOrderFillTransaction']
            else:
                logger.error(f"No fill transaction found in response: {data}")
                return None
            
            # Extract PnL
            pnl = float(fill['pl']) if 'pl' in fill else None
            price = float(fill['price']) if 'price' in fill else None
            
            return {
                'order_id': fill['id'],
                'status': 'filled',
                'price': price,
                'pnl': pnl
            }
        else:
            logger.error(f"Failed to close OANDA position: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error closing OANDA position: {e}")
        return None

def get_position_details(position_id, user_id):
    """Get details for a specific position."""
    # First try to find the position in the list of open positions
    positions = get_open_positions(user_id)
    for position in positions:
        if position['id'] == position_id:
            return position
    
    # If not found, position might have been closed
    logger.warning(f"Position {position_id} not found in open positions")
    return None
