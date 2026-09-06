import logging
import json
from datetime import datetime, timedelta
from flask import request, jsonify, Blueprint
from flask_login import login_required, current_user
import pandas as pd

logger = logging.getLogger(__name__)

def init_legacy_app(app):
    from models import (
        User, TradingStrategy, TradingSignal, TradeExecution,
        BacktestResult, MLModel, db
    )
    from market_data import (
        get_latest_prices, get_historical_data,
        setup_websocket_connection
    )
    from technical_indicators import apply_indicators, calculate_support_resistance, detect_patterns
    from backtesting import run_backtest, get_backtest_result
    from trading_engine import (
        get_active_positions, get_recent_trades,
        close_position, execute_trade_from_signal
    )
    from unified_trading import unified_trading
    from ml_models import (
        create_ml_model, get_model_details,
        get_user_models, predict_with_model
    )
    from risk_management import (
        calculate_portfolio_risk, calculate_position_exposure,
        get_risk_metrics_for_strategy
    )
    from matlab_integration import (
        get_matlab_signal, run_matlab_backtest,
        optimize_strategy_parameters
    )
    from messaging import (
        send_signal_notification, send_trade_execution_notification,
        send_error_notification
    )


    """Initialize API routes for the Flask app."""
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    
    @api_bp.route('/prices', methods=['GET'])
    @login_required
    def get_prices():
        """Get the latest prices for all trading pairs."""
        try:
            prices = unified_trading.get_latest_prices()
            return jsonify({'success': True, 'data': prices})
        except Exception as e:
            logger.error(f"Error getting prices: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @api_bp.route('/chart-data', methods=['GET'])
    @login_required
    def get_chart_data():
        """Get historical data for a trading pair."""
        try:
            trading_pair = request.args.get('pair', 'BTC/USDT')
            timeframe = request.args.get('timeframe', '1h')
            limit = int(request.args.get('limit', 100))
            
            data = unified_trading.get_historical_data(trading_pair, timeframe, limit)
            
            if not data:
                return jsonify({'success': False, 'error': 'No data available'}), 404
            
            # Data is already in the correct format from unified_trading
            return jsonify({'success': True, 'data': data})
        
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/indicators', methods=['GET'])
    @login_required
    def get_indicators():
        """Get indicator values for a trading pair."""
        try:
            trading_pair = request.args.get('pair', 'BTC/USDT')
            timeframe = request.args.get('timeframe', '1h')
            limit = int(request.args.get('limit', 100))
            indicators = request.args.get('indicators', '{}')
            
            # Parse indicators JSON
            indicators_config = json.loads(indicators)
            
            # Get historical data
            data = get_historical_data(trading_pair, timeframe, limit)
            
            if data.empty:
                return jsonify({'error': 'No data available'}), 404
            
            # Apply indicators
            data_with_indicators = apply_indicators(data, indicators_config)
            
            # Convert DataFrame to list of dictionaries
            indicator_data = []
            for idx, row in data_with_indicators.iterrows():
                # Handle different index types
                if hasattr(idx, 'timestamp'):
                    timestamp = idx.timestamp() * 1000
                elif isinstance(idx, (int, float)):
                    timestamp = idx
                else:
                    timestamp = datetime.now().timestamp() * 1000
                
                point = {
                    'timestamp': timestamp
                }
                
                # Add all indicator columns
                for col in data_with_indicators.columns:
                    if col in ['open', 'high', 'low', 'close', 'volume']:
                        continue
                    
                    value = row[col]
                    if pd.isna(value):
                        point[col] = None
                    else:
                        point[col] = float(value) if isinstance(value, (int, float)) else value
                
                if len(point) > 1:  # Only add if we have at least one indicator besides timestamp
                    indicator_data.append(point)
            
            return jsonify(indicator_data)
        
        except Exception as e:
            logger.error(f"Error getting indicators: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/support-resistance', methods=['GET'])
    @login_required
    def get_support_resistance():
        """Get support and resistance levels for a trading pair."""
        try:
            trading_pair = request.args.get('pair', 'BTC/USDT')
            timeframe = request.args.get('timeframe', '1h')
            period = int(request.args.get('period', 14))
            method = request.args.get('method', 'peaks')
            
            # Get historical data
            data = get_historical_data(trading_pair, timeframe, 200)  # Get more data for better S&R detection
            
            if data.empty:
                return jsonify({'error': 'No data available'}), 404
            
            # Calculate support and resistance
            supports, resistances = calculate_support_resistance(data, period, method)
            
            # Format the response
            result = {
                'supports': [{'timestamp': ts.timestamp() * 1000, 'value': val} for ts, val in supports],
                'resistances': [{'timestamp': ts.timestamp() * 1000, 'value': val} for ts, val in resistances]
            }
            
            return jsonify(result)
        
        except Exception as e:
            logger.error(f"Error getting support and resistance: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/patterns', methods=['GET'])
    @login_required
    def get_patterns():
        """Get candlestick patterns for a trading pair."""
        try:
            trading_pair = request.args.get('pair', 'BTC/USDT')
            timeframe = request.args.get('timeframe', '1h')
            
            # Get historical data
            data = get_historical_data(trading_pair, timeframe, 100)
            
            if data.empty:
                return jsonify({'error': 'No data available'}), 404
            
            # Detect patterns
            patterns = detect_patterns(data)
            
            # Format the response
            result = []
            for pattern_name, pattern_values in patterns.items():
                for i, value in enumerate(pattern_values):
                    if value != 0:  # 0 means no pattern
                        idx = data.index[i]
                        # Handle different index types
                        if hasattr(idx, 'timestamp'):
                            timestamp = idx.timestamp() * 1000
                        else:
                            timestamp = datetime.now().timestamp() * 1000
                        
                        result.append({
                            'pattern': pattern_name,
                            'timestamp': timestamp,
                            'value': value,  # Positive for bullish, negative for bearish
                            'price': float(data['close'].iloc[i]) if hasattr(data['close'], 'iloc') else float(data['close'][i])
                        })
            
            return jsonify(result)
        
        except Exception as e:
            logger.error(f"Error getting patterns: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/account-balance', methods=['GET'])
    @login_required
    def get_api_account_balance():
        """Get account balance for the current user."""
        try:
            balance = unified_trading.get_account_balance(current_user)
            return jsonify({'success': True, 'data': balance})
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @api_bp.route('/positions', methods=['GET'])
    @login_required
    def get_positions():
        """Get active positions for the current user."""
        try:
            positions = unified_trading.get_open_positions(current_user)
            return jsonify({'success': True, 'data': positions})
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @api_bp.route('/positions/<position_id>/close', methods=['POST'])
    @login_required
    def close_api_position(position_id):
        """Close a position."""
        try:
            result = close_position(current_user.id, position_id)
            
            if result:
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Failed to close position'}), 400
        
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/trades', methods=['GET'])
    @login_required
    def get_trades():
        """Get recent trades for the current user."""
        try:
            limit = int(request.args.get('limit', 10))
            trades = get_recent_trades(current_user.id, limit)
            
            # Format the response
            formatted_trades = []
            for trade in trades:
                formatted_trades.append({
                    'id': trade.id,
                    'trading_pair': trade.trading_pair,
                    'order_type': trade.order_type,
                    'amount': trade.amount,
                    'price': trade.price,
                    'timestamp': trade.timestamp.timestamp() * 1000,
                    'status': trade.status,
                    'platform': trade.platform,
                    'pnl': trade.pnl,
                    'is_automated': trade.is_automated,
                    'executed_by': trade.executed_by
                })
            
            return jsonify(formatted_trades)
        
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/execute-trade', methods=['POST'])
    @login_required
    def execute_api_trade():
        """Execute a manual trade."""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['trading_pair', 'order_type', 'amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Get parameters
            trading_pair = data['trading_pair']
            order_type = data['order_type']
            amount = float(data['amount'])
            price = float(data['price']) if 'price' in data and data['price'] else None
            platform = data.get('platform', 'binance')
            
            # Get stop loss and take profit
            stop_loss = float(data['stop_loss']) if 'stop_loss' in data and data['stop_loss'] else None
            take_profit = float(data['take_profit']) if 'take_profit' in data and data['take_profit'] else None
            
            # Execute the trade
            result = unified_trading.place_order(
                platform=platform,
                symbol=trading_pair,
                side=order_type,
                size=amount,
                order_type='market' if not price else 'limit',
                price=price
            )
            
            if result and 'order_id' in result:
                # Create a trade execution record
                execution = TradeExecution(
                    user_id=current_user.id,
                    trading_pair=trading_pair,
                    order_type=order_type,
                    order_id=result['order_id'],
                    amount=amount,
                    price=price or result.get('price', 0),
                    status=result.get('status', 'pending'),
                    platform=platform,
                    is_automated=False,
                    executed_by="Manual"
                )
                
                # Save to database
                db.session.add(execution)
                db.session.commit()
                
                # Send notification
                send_trade_execution_notification(execution)
                
                return jsonify({'success': True, 'trade_id': execution.id})
            else:
                return jsonify({'error': 'Failed to execute trade'}), 400
        
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/strategies', methods=['GET'])
    @login_required
    def get_strategies():
        """Get all trading strategies for the current user."""
        try:
            strategies = TradingStrategy.query.filter_by(user_id=current_user.id).all()
            
            # Format the response
            formatted_strategies = []
            for strategy in strategies:
                formatted_strategies.append({
                    'id': strategy.id,
                    'name': strategy.name,
                    'description': strategy.description,
                    'trading_pairs': strategy.get_trading_pairs(),
                    'timeframe': strategy.timeframe,
                    'is_active': strategy.is_active,
                    'created_at': strategy.created_at.timestamp() * 1000,
                    'updated_at': strategy.updated_at.timestamp() * 1000,
                    'use_ml_model': strategy.use_ml_model,
                    'ml_model_id': strategy.ml_model_id
                })
            
            return jsonify(formatted_strategies)
        
        except Exception as e:
            logger.error(f"Error getting strategies: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/strategies', methods=['POST'])
    @login_required
    def create_strategy():
        """Create a new trading strategy."""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['name', 'trading_pairs', 'timeframe']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Create new strategy
            strategy = TradingStrategy(
                user_id=current_user.id,
                name=data['name'],
                description=data.get('description', ''),
                timeframe=data['timeframe'],
                risk_per_trade_pct=data.get('risk_per_trade_pct', 1.0),
                stop_loss_pct=data.get('stop_loss_pct', 2.0),
                take_profit_pct=data.get('take_profit_pct', 4.0),
                is_active=data.get('is_active', False),
                use_ml_model=data.get('use_ml_model', False),
                ml_model_id=data.get('ml_model_id')
            )
            
            # Set trading pairs
            strategy.set_trading_pairs(data['trading_pairs'])
            
            # Set indicators config
            if 'indicators_config' in data:
                strategy.set_indicators_config(data['indicators_config'])
            
            # Set entry conditions
            if 'entry_conditions' in data:
                strategy.set_entry_conditions(data['entry_conditions'])
            
            # Set exit conditions
            if 'exit_conditions' in data:
                strategy.set_exit_conditions(data['exit_conditions'])
            
            # Save to database
            db.session.add(strategy)
            db.session.commit()
            
            return jsonify({'success': True, 'strategy_id': strategy.id})
        
        except Exception as e:
            logger.error(f"Error creating strategy: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/strategies/<int:strategy_id>', methods=['GET'])
    @login_required
    def get_strategy(strategy_id):
        """Get a specific trading strategy."""
        try:
            strategy = TradingStrategy.query.filter_by(id=strategy_id, user_id=current_user.id).first()
            
            if not strategy:
                return jsonify({'error': 'Strategy not found'}), 404
            
            # Format the response
            formatted_strategy = {
                'id': strategy.id,
                'name': strategy.name,
                'description': strategy.description,
                'trading_pairs': strategy.get_trading_pairs(),
                'timeframe': strategy.timeframe,
                'indicators_config': strategy.get_indicators_config(),
                'entry_conditions': strategy.get_entry_conditions(),
                'exit_conditions': strategy.get_exit_conditions(),
                'risk_per_trade_pct': strategy.risk_per_trade_pct,
                'stop_loss_pct': strategy.stop_loss_pct,
                'take_profit_pct': strategy.take_profit_pct,
                'is_active': strategy.is_active,
                'created_at': strategy.created_at.timestamp() * 1000,
                'updated_at': strategy.updated_at.timestamp() * 1000,
                'use_ml_model': strategy.use_ml_model,
                'ml_model_id': strategy.ml_model_id
            }
            
            return jsonify(formatted_strategy)
        
        except Exception as e:
            logger.error(f"Error getting strategy: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/strategies/<int:strategy_id>', methods=['PUT'])
    @login_required
    def update_strategy(strategy_id):
        """Update a trading strategy."""
        try:
            strategy = TradingStrategy.query.filter_by(id=strategy_id, user_id=current_user.id).first()
            
            if not strategy:
                return jsonify({'error': 'Strategy not found'}), 404
            
            data = request.get_json()
            
            # Update strategy fields
            if 'name' in data:
                strategy.name = data['name']
            
            if 'description' in data:
                strategy.description = data['description']
            
            if 'trading_pairs' in data:
                strategy.set_trading_pairs(data['trading_pairs'])
            
            if 'timeframe' in data:
                strategy.timeframe = data['timeframe']
            
            if 'indicators_config' in data:
                strategy.set_indicators_config(data['indicators_config'])
            
            if 'entry_conditions' in data:
                strategy.set_entry_conditions(data['entry_conditions'])
            
            if 'exit_conditions' in data:
                strategy.set_exit_conditions(data['exit_conditions'])
            
            if 'risk_per_trade_pct' in data:
                strategy.risk_per_trade_pct = data['risk_per_trade_pct']
            
            if 'stop_loss_pct' in data:
                strategy.stop_loss_pct = data['stop_loss_pct']
            
            if 'take_profit_pct' in data:
                strategy.take_profit_pct = data['take_profit_pct']
            
            if 'is_active' in data:
                strategy.is_active = data['is_active']
            
            if 'use_ml_model' in data:
                strategy.use_ml_model = data['use_ml_model']
            
            if 'ml_model_id' in data:
                strategy.ml_model_id = data['ml_model_id']
            
            # Update timestamp
            strategy.updated_at = datetime.utcnow()
            
            # Save to database
            db.session.commit()
            
            return jsonify({'success': True})
        
        except Exception as e:
            logger.error(f"Error updating strategy: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/strategies/<int:strategy_id>', methods=['DELETE'])
    @login_required
    def delete_strategy(strategy_id):
        """Delete a trading strategy."""
        try:
            strategy = TradingStrategy.query.filter_by(id=strategy_id, user_id=current_user.id).first()
            
            if not strategy:
                return jsonify({'error': 'Strategy not found'}), 404
            
            # Delete the strategy
            db.session.delete(strategy)
            db.session.commit()
            
            return jsonify({'success': True})
        
        except Exception as e:
            logger.error(f"Error deleting strategy: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/signals', methods=['GET'])
    @login_required
    def get_signals():
        """Get recent trading signals for the current user."""
        try:
            limit = int(request.args.get('limit', 10))
            signals = TradingSignal.query.filter_by(user_id=current_user.id).order_by(
                TradingSignal.timestamp.desc()).limit(limit).all()
            
            # Format the response
            formatted_signals = []
            for signal in signals:
                formatted_signals.append({
                    'id': signal.id,
                    'trading_pair': signal.trading_pair,
                    'signal_type': signal.signal_type,
                    'entry_price': signal.entry_price,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'timestamp': signal.timestamp.timestamp() * 1000,
                    'status': signal.status,
                    'timeframe': signal.timeframe,
                    'confidence': signal.confidence,
                    'strategy_name': signal.strategy.name if signal.strategy else 'Manual',
                    'signal_data': signal.get_signal_data()
                })
            
            return jsonify(formatted_signals)
        
        except Exception as e:
            logger.error(f"Error getting signals: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/signals/<int:signal_id>/execute', methods=['POST'])
    @login_required
    def execute_signal(signal_id):
        """Execute a trade based on a signal."""
        try:
            signal = TradingSignal.query.filter_by(id=signal_id, user_id=current_user.id).first()
            
            if not signal:
                return jsonify({'error': 'Signal not found'}), 404
            
            # Check if signal is still valid
            if signal.status != 'pending':
                return jsonify({'error': 'Signal is no longer pending'}), 400
            
            # Calculate position size
            position_size_str = request.args.get('position_size', '0')
            
            # Validate against NaN injection
            if position_size_str.lower() in ['nan', 'inf', '-inf']:
                return jsonify({'error': 'Invalid position size value'}), 400
            
            try:
                position_size = float(position_size_str)
            except ValueError:
                return jsonify({'error': 'Invalid position size format'}), 400
            
            if position_size <= 0:
                # Calculate position size based on risk management
                from risk_management import calculate_position_size
                
                # Get account balance
                account_data = unified_trading.get_account_balance(current_user)
                
                # Determine platform based on trading pair
                platform = 'binance' if '/' in signal.trading_pair and signal.trading_pair.split('/')[1] == 'USDT' else 'oanda'
                
                # Get account balance for the specific platform
                if platform not in account_data:
                    return jsonify({'error': f'No account data for platform {platform}'}), 400
                
                account_balance = account_data[platform].get('balance', 0)
                
                if platform == 'binance':
                    # For Binance, we need to get the balance of the quote currency
                    if 'balances' in account_data[platform]:
                        quote_currency = signal.trading_pair.split('/')[1]  # e.g., USDT for BTC/USDT
                        account_balance = account_data[platform]['balances'].get(quote_currency, {}).get('free', 0)
                
                # Calculate position size
                strategy = signal.strategy
                risk_per_trade_pct = strategy.risk_per_trade_pct if strategy else 1.0
                
                position_size = calculate_position_size(
                    account_balance=account_balance,
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    risk_per_trade_pct=risk_per_trade_pct
                )
            
            # Execute the trade
            result = execute_trade_from_signal(signal, position_size)
            
            if result:
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Failed to execute trade from signal'}), 400
        
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/backtests', methods=['POST'])
    @login_required
    def run_api_backtest():
        """Run a backtest for a strategy."""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['strategy_id', 'trading_pair', 'start_date', 'end_date']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Get parameters
            strategy_id = data['strategy_id']
            trading_pair = data['trading_pair']
            
            # Parse dates
            try:
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
            
            # Get initial balance
            initial_balance = float(data.get('initial_balance', 10000.0))
            
            # Run the backtest
            backtest_id = run_backtest(
                strategy_id=strategy_id,
                trading_pair=trading_pair,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance
            )
            
            if backtest_id:
                return jsonify({'success': True, 'backtest_id': backtest_id})
            else:
                return jsonify({'error': 'Failed to run backtest'}), 400
        
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/backtests/<int:backtest_id>', methods=['GET'])
    @login_required
    def get_api_backtest_result(backtest_id):
        """Get the results of a backtest."""
        try:
            result = get_backtest_result(backtest_id)
            
            if not result:
                return jsonify({'error': 'Backtest result not found'}), 404
            
            return jsonify(result)
        
        except Exception as e:
            logger.error(f"Error getting backtest result: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/ml-models', methods=['GET'])
    @login_required
    def get_api_ml_models():
        """Get all ML models for the current user."""
        try:
            models = get_user_models(current_user.id)
            return jsonify(models)
        
        except Exception as e:
            logger.error(f"Error getting ML models: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/ml-models', methods=['POST'])
    @login_required
    def create_api_ml_model():
        """Create and train a new ML model."""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['name', 'model_type', 'target_variable', 'features', 'trading_pair', 'timeframe']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Get historical data for training
            trading_pair = data['trading_pair']
            timeframe = data['timeframe']
            
            # Default to 6 months of training data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=180)
            
            # Override dates if provided
            if 'start_date' in data:
                try:
                    start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
                except ValueError:
                    return jsonify({'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
            
            if 'end_date' in data:
                try:
                    end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
                except ValueError:
                    return jsonify({'error': 'Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
            
            # Get training data
            from market_data import get_historical_data_for_backtest
            training_data = get_historical_data_for_backtest(
                trading_pair=trading_pair,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if training_data.empty:
                return jsonify({'error': 'No training data available'}), 400
            
            # Apply indicators
            indicators_config = data.get('indicators_config', {})
            if not indicators_config:
                # Use default indicators if none provided
                indicators_config = {
                    'sma': {'period': 20},
                    'ema': {'period': 50},
                    'rsi': {'period': 14},
                    'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                    'bbands': {'period': 20, 'dev_up': 2, 'dev_down': 2}
                }
            
            training_data = apply_indicators(training_data, indicators_config)
            
            # Get hyperparameters
            hyperparameters = data.get('hyperparameters')
            
            # Create and train the model
            model_id = create_ml_model(
                user_id=current_user.id,
                name=data['name'],
                model_type=data['model_type'],
                target_variable=data['target_variable'],
                features=data['features'],
                data=training_data,
                hyperparameters=hyperparameters
            )
            
            if model_id:
                return jsonify({'success': True, 'model_id': model_id})
            else:
                return jsonify({'error': 'Failed to create ML model'}), 400
        
        except Exception as e:
            logger.error(f"Error creating ML model: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/ml-models/<int:model_id>', methods=['GET'])
    @login_required
    def get_api_ml_model(model_id):
        """Get details of a specific ML model."""
        try:
            model = get_model_details(model_id)
            
            if not model:
                return jsonify({'error': 'ML model not found'}), 404
            
            return jsonify(model)
        
        except Exception as e:
            logger.error(f"Error getting ML model: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/ml-models/<int:model_id>/predict', methods=['POST'])
    @login_required
    def predict_with_api_model(model_id):
        """Make a prediction using an ML model."""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['trading_pair', 'timeframe']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Get recent data for prediction
            trading_pair = data['trading_pair']
            timeframe = data['timeframe']
            
            # Get data
            prediction_data = get_historical_data(
                trading_pair=trading_pair,
                timeframe=timeframe,
                limit=50  # Get enough data for indicators and model input
            )
            
            if prediction_data.empty:
                return jsonify({'error': 'No data available for prediction'}), 400
            
            # Get model to see required features
            model_details = get_model_details(model_id)
            if not model_details:
                return jsonify({'error': 'ML model not found'}), 404
            
            # Apply indicators if needed for features
            indicators_needed = []
            for feature in model_details['features']:
                if feature not in ['open', 'high', 'low', 'close', 'volume']:
                    # This is an indicator, extract the base indicator name
                    indicator_parts = feature.split('_')
                    indicator_name = indicator_parts[0]
                    
                    if indicator_name not in indicators_needed:
                        indicators_needed.append(indicator_name)
            
            # Build indicators config
            indicators_config = {}
            for indicator in indicators_needed:
                # Use default parameters for common indicators
                if indicator == 'sma':
                    indicators_config[indicator] = {'period': 20}
                elif indicator == 'ema':
                    indicators_config[indicator] = {'period': 50}
                elif indicator == 'rsi':
                    indicators_config[indicator] = {'period': 14}
                elif indicator == 'macd':
                    indicators_config[indicator] = {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
                elif indicator == 'bbands' or indicator == 'bb':
                    indicators_config['bollinger bands'] = {'period': 20, 'dev_up': 2, 'dev_down': 2}
            
            # Apply indicators
            prediction_data = apply_indicators(prediction_data, indicators_config)
            
            # Make prediction
            prediction, confidence = predict_with_model(model_id, prediction_data)
            
            return jsonify({
                'prediction': float(prediction),
                'confidence': float(confidence),
                'timestamp': datetime.utcnow().timestamp() * 1000
            })
        
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/portfolio-risk', methods=['GET'])
    @login_required
    def get_portfolio_risk():
        """Get portfolio risk metrics for the current user."""
        try:
            risk_metrics = calculate_portfolio_risk(current_user.id)
            
            if not risk_metrics:
                return jsonify({'error': 'Failed to calculate portfolio risk'}), 400
            
            return jsonify(risk_metrics)
        
        except Exception as e:
            logger.error(f"Error getting portfolio risk: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/position-exposure', methods=['GET'])
    @login_required
    def get_position_exposure():
        """Get position exposure by asset class and trading pair."""
        try:
            exposure = calculate_position_exposure(current_user.id)
            
            if not exposure:
                return jsonify({'error': 'Failed to calculate position exposure'}), 400
            
            return jsonify(exposure)
        
        except Exception as e:
            logger.error(f"Error getting position exposure: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/strategies/<int:strategy_id>/risk-metrics', methods=['GET'])
    @login_required
    def get_api_risk_metrics_for_strategy(strategy_id):
        """Get risk metrics for a specific strategy."""
        try:
            metrics = get_risk_metrics_for_strategy(strategy_id)
            
            if not metrics:
                return jsonify({'error': 'Failed to get risk metrics for strategy'}), 400
            
            return jsonify(metrics)
        
        except Exception as e:
            logger.error(f"Error getting risk metrics for strategy: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/matlab-signal', methods=['GET'])
    @login_required
    def get_api_matlab_signal():
        """Get a trading signal from MATLAB."""
        try:
            trading_pair = request.args.get('pair', 'BTC/USDT')
            timeframe = request.args.get('timeframe', '1h')
            indicators = request.args.get('indicators', '{}')
            
            # Parse indicators JSON
            indicators_config = json.loads(indicators)
            
            # Get signal from MATLAB
            signal_type, confidence = get_matlab_signal(
                trading_pair=trading_pair,
                timeframe=timeframe,
                indicators_config=indicators_config
            )
            
            if signal_type is None:
                return jsonify({'error': 'Failed to get MATLAB signal'}), 400
            
            return jsonify({
                'signal_type': signal_type,
                'confidence': confidence,
                'timestamp': datetime.utcnow().timestamp() * 1000
            })
        
        except Exception as e:
            logger.error(f"Error getting MATLAB signal: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/strategies/<int:strategy_id>/optimize', methods=['POST'])
    @login_required
    def optimize_api_strategy_parameters(strategy_id):
        """Optimize strategy parameters using MATLAB."""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['trading_pair', 'start_date', 'end_date', 'parameters_to_optimize']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Get parameters
            trading_pair = data['trading_pair']
            parameters_to_optimize = data['parameters_to_optimize']
            
            # Parse dates
            try:
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
            
            # Get timeframe
            strategy = TradingStrategy.query.get(strategy_id)
            if not strategy:
                return jsonify({'error': 'Strategy not found'}), 404
            
            timeframe = strategy.timeframe
            
            # Run optimization
            result = optimize_strategy_parameters(
                strategy_id=strategy_id,
                trading_pair=trading_pair,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                parameters_to_optimize=parameters_to_optimize
            )
            
            if not result:
                return jsonify({'error': 'Failed to optimize strategy parameters'}), 400
            
            return jsonify(result)
        
        except Exception as e:
            logger.error(f"Error optimizing strategy parameters: {e}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/websocket', methods=['POST'])
    @login_required
    def setup_api_websocket():
        """Set up a websocket connection for real-time data."""
        try:
            data = request.get_json()
            
            # Validate required fields
            if 'trading_pair' not in data:
                return jsonify({'error': 'Missing required field: trading_pair'}), 400
            
            trading_pair = data['trading_pair']
            
            # Set up the websocket
            result = setup_websocket_connection(trading_pair, None)  # The callback will be handled client-side
            
            if result:
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Failed to set up websocket connection'}), 400
        
        except Exception as e:
            logger.error(f"Error setting up websocket: {e}")
            return jsonify({'error': str(e)}), 500
    
    # Register the blueprint with the app
    app.register_blueprint(api_bp)
    
    logger.info("API routes initialized")


def init_app(app):
    if app.config.get('TEAKA_MODE') != 'paper':
        raise ValueError('This application factory supports paper mode only')
    from .paper_routes import init_app as init_paper
    init_paper(app)
