import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models import TradingStrategy, BacktestResult, db
from market_data import get_historical_data
from technical_indicators import apply_indicators
from ml_models import predict_with_model
import config

logger = logging.getLogger(__name__)

def run_backtest(strategy_id, trading_pair, start_date, end_date, initial_balance=10000.0):
    """Run a backtest for a strategy on a specific trading pair."""
    try:
        # Get the strategy
        strategy = TradingStrategy.query.get(strategy_id)
        if not strategy:
            logger.error(f"Strategy with ID {strategy_id} not found")
            return None
        
        # Convert dates to datetime if they are strings
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Calculate the date range needed (adding buffer for indicators)
        date_buffer = timedelta(days=30)  # Buffer for calculating indicators
        data_start_date = start_date - date_buffer
        
        # Get historical data
        data = get_historical_data_for_backtest(
            trading_pair=trading_pair,
            timeframe=strategy.timeframe,
            start_date=data_start_date,
            end_date=end_date
        )
        
        if data.empty:
            logger.error(f"No historical data available for {trading_pair}")
            return None
        
        # Apply technical indicators
        indicators_config = strategy.get_indicators_config()
        df_with_indicators = apply_indicators(data, indicators_config)
        
        # Run backtest simulation
        if strategy.use_ml_model and strategy.ml_model_id:
            # Backtest with ML model
            backtest_results = backtest_ml_strategy(
                strategy=strategy,
                data=df_with_indicators,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance
            )
        else:
            # Backtest with technical indicators
            backtest_results = backtest_technical_strategy(
                strategy=strategy,
                data=df_with_indicators,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance
            )
        
        # Calculate performance metrics
        performance_metrics = calculate_performance_metrics(backtest_results)
        
        # Save backtest results to database
        backtest_result = BacktestResult(
            user_id=strategy.user_id,
            strategy_id=strategy.id,
            trading_pair=trading_pair,
            timeframe=strategy.timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance,
            final_balance=backtest_results['final_balance'],
            total_trades=performance_metrics['total_trades'],
            winning_trades=performance_metrics['winning_trades'],
            losing_trades=performance_metrics['losing_trades'],
            profit_factor=performance_metrics['profit_factor'],
            max_drawdown_pct=performance_metrics['max_drawdown_pct'],
            sharpe_ratio=performance_metrics['sharpe_ratio']
        )
        
        # Set detailed result data
        result_data = {
            'trades': backtest_results['trades'],
            'equity_curve': backtest_results['equity_curve'],
            'drawdown_curve': backtest_results['drawdown_curve'],
            'metrics': performance_metrics
        }
        backtest_result.set_result_data(result_data)
        
        # Save to database
        db.session.add(backtest_result)
        db.session.commit()
        
        logger.info(f"Backtest completed for strategy {strategy.name} on {trading_pair}")
        return backtest_result.id
    
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return None

def get_historical_data_for_backtest(trading_pair, timeframe, start_date, end_date):
    """Get historical data for backtesting."""
    # This would typically call an API or database to get historical data
    # For simplicity, we're reusing the market_data function but in a real system
    # you might have a separate function for getting larger historical datasets
    
    # Convert dates to string format if needed by your API
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"Getting historical data for {trading_pair} from {start_str} to {end_str}")
    
    # Call market_data function (this would need to be extended to support date ranges)
    return get_historical_data(trading_pair, timeframe, limit=5000)  # Using a large limit as approximation

def backtest_technical_strategy(strategy, data, start_date, end_date, initial_balance):
    """Run a backtest simulation using technical indicators."""
    # Filter data to backtest period
    backtest_data = data.loc[start_date:end_date].copy()
    
    if backtest_data.empty:
        logger.warning("No data available for backtest period")
        return {
            'final_balance': initial_balance,
            'trades': [],
            'equity_curve': [initial_balance],
            'drawdown_curve': [0.0]
        }
    
    # Initialize backtest variables
    balance = initial_balance
    position = None
    trades = []
    equity_curve = [balance]
    max_equity = balance
    drawdown_curve = [0.0]
    
    entry_conditions = strategy.get_entry_conditions()
    exit_conditions = strategy.get_exit_conditions()
    
    # Iterate through each candle
    for idx, row in backtest_data.iterrows():
        if idx == backtest_data.index[0]:
            # Skip the first row as we need previous data for comparison
            continue
        
        # Get previous candle data
        prev_idx = backtest_data.index[backtest_data.index.get_loc(idx) - 1]
        prev_row = backtest_data.loc[prev_idx]
        
        # Check for exit if we have an open position
        if position:
            # Check stop loss and take profit
            if position['type'] == 'BUY':
                # Check if price hit stop loss
                if row['low'] <= position['stop_loss']:
                    # Stop loss hit
                    exit_price = position['stop_loss']
                    trade_result = (exit_price - position['entry_price']) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'stop_loss'
                    })
                    
                    position = None
                
                # Check if price hit take profit
                elif row['high'] >= position['take_profit']:
                    # Take profit hit
                    exit_price = position['take_profit']
                    trade_result = (exit_price - position['entry_price']) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'take_profit'
                    })
                    
                    position = None
            
            elif position['type'] == 'SELL':
                # Check if price hit stop loss
                if row['high'] >= position['stop_loss']:
                    # Stop loss hit
                    exit_price = position['stop_loss']
                    trade_result = (position['entry_price'] - exit_price) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'stop_loss'
                    })
                    
                    position = None
                
                # Check if price hit take profit
                elif row['low'] <= position['take_profit']:
                    # Take profit hit
                    exit_price = position['take_profit']
                    trade_result = (position['entry_price'] - exit_price) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'take_profit'
                    })
                    
                    position = None
            
            # Check exit conditions if position is still open
            if position:
                exit_signal = True
                for condition in exit_conditions:
                    result = evaluate_backtest_condition(
                        row=row,
                        prev_row=prev_row,
                        condition=condition
                    )
                    
                    if not result:
                        exit_signal = False
                        break
                
                if exit_signal:
                    # Exit on signal
                    exit_price = row['close']
                    
                    if position['type'] == 'BUY':
                        trade_result = (exit_price - position['entry_price']) / position['entry_price']
                    else:
                        trade_result = (position['entry_price'] - exit_price) / position['entry_price']
                    
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'signal'
                    })
                    
                    position = None
        
        # Check for entry if we don't have an open position
        if not position:
            # Check buy conditions
            buy_signal = True
            for condition in entry_conditions:
                if condition['signal_type'] != 'BUY':
                    continue
                
                result = evaluate_backtest_condition(
                    row=row,
                    prev_row=prev_row,
                    condition=condition
                )
                
                if not result:
                    buy_signal = False
                    break
            
            # Check sell conditions
            sell_signal = True
            for condition in entry_conditions:
                if condition['signal_type'] != 'SELL':
                    continue
                
                result = evaluate_backtest_condition(
                    row=row,
                    prev_row=prev_row,
                    condition=condition
                )
                
                if not result:
                    sell_signal = False
                    break
            
            # Enter position if signal is generated
            if buy_signal:
                entry_price = row['close']
                position_size = balance * (strategy.risk_per_trade_pct / 100)
                stop_loss = entry_price * (1 - strategy.stop_loss_pct / 100)
                take_profit = entry_price * (1 + strategy.take_profit_pct / 100)
                
                position = {
                    'type': 'BUY',
                    'entry_time': idx,
                    'entry_price': entry_price,
                    'size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
                
                balance -= position_size
            
            elif sell_signal:
                entry_price = row['close']
                position_size = balance * (strategy.risk_per_trade_pct / 100)
                stop_loss = entry_price * (1 + strategy.stop_loss_pct / 100)
                take_profit = entry_price * (1 - strategy.take_profit_pct / 100)
                
                position = {
                    'type': 'SELL',
                    'entry_time': idx,
                    'entry_price': entry_price,
                    'size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
                
                balance -= position_size
        
        # Update equity and drawdown
        current_equity = balance
        if position:
            # Add unrealized P&L
            if position['type'] == 'BUY':
                trade_result = (row['close'] - position['entry_price']) / position['entry_price']
            else:
                trade_result = (position['entry_price'] - row['close']) / position['entry_price']
            
            current_equity += position['size'] + (position['size'] * trade_result)
        
        equity_curve.append(current_equity)
        max_equity = max(max_equity, current_equity)
        current_drawdown = (max_equity - current_equity) / max_equity * 100 if max_equity > 0 else 0
        drawdown_curve.append(current_drawdown)
    
    # Close any open position at the end of the backtest
    if position:
        exit_price = backtest_data.iloc[-1]['close']
        
        if position['type'] == 'BUY':
            trade_result = (exit_price - position['entry_price']) / position['entry_price']
        else:
            trade_result = (position['entry_price'] - exit_price) / position['entry_price']
        
        pnl = position['size'] * trade_result
        balance += position['size'] + pnl
        
        # Record the trade
        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': backtest_data.index[-1],
            'type': position['type'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'size': position['size'],
            'pnl': pnl,
            'exit_reason': 'end_of_test'
        })
    
    return {
        'final_balance': balance,
        'trades': trades,
        'equity_curve': equity_curve,
        'drawdown_curve': drawdown_curve
    }

def backtest_ml_strategy(strategy, data, start_date, end_date, initial_balance):
    """Run a backtest simulation using ML model predictions."""
    # Filter data to backtest period
    backtest_data = data.loc[start_date:end_date].copy()
    
    if backtest_data.empty:
        logger.warning("No data available for backtest period")
        return {
            'final_balance': initial_balance,
            'trades': [],
            'equity_curve': [initial_balance],
            'drawdown_curve': [0.0]
        }
    
    # Initialize backtest variables
    balance = initial_balance
    position = None
    trades = []
    equity_curve = [balance]
    max_equity = balance
    drawdown_curve = [0.0]
    
    # Iterate through each candle
    for i, (idx, row) in enumerate(backtest_data.iterrows()):
        if i < 10:  # Skip the first few rows to ensure we have enough data for prediction
            continue
        
        # Get data for prediction (current row and some historical rows)
        prediction_data = backtest_data.iloc[i-10:i+1].copy()
        
        # Get prediction from ML model
        prediction, confidence = predict_with_model(
            model_id=strategy.ml_model_id,
            data=prediction_data
        )
        
        # Check for exit if we have an open position
        if position:
            # Check stop loss and take profit
            if position['type'] == 'BUY':
                # Check if price hit stop loss
                if row['low'] <= position['stop_loss']:
                    # Stop loss hit
                    exit_price = position['stop_loss']
                    trade_result = (exit_price - position['entry_price']) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'stop_loss',
                        'confidence': position['confidence']
                    })
                    
                    position = None
                
                # Check if price hit take profit
                elif row['high'] >= position['take_profit']:
                    # Take profit hit
                    exit_price = position['take_profit']
                    trade_result = (exit_price - position['entry_price']) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'take_profit',
                        'confidence': position['confidence']
                    })
                    
                    position = None
                
                # Check for exit signal (if prediction changes direction)
                elif prediction < 0 and confidence >= 0.6:
                    # Exit on opposite signal
                    exit_price = row['close']
                    trade_result = (exit_price - position['entry_price']) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'signal',
                        'confidence': position['confidence'],
                        'exit_confidence': confidence
                    })
                    
                    position = None
            
            elif position['type'] == 'SELL':
                # Check if price hit stop loss
                if row['high'] >= position['stop_loss']:
                    # Stop loss hit
                    exit_price = position['stop_loss']
                    trade_result = (position['entry_price'] - exit_price) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'stop_loss',
                        'confidence': position['confidence']
                    })
                    
                    position = None
                
                # Check if price hit take profit
                elif row['low'] <= position['take_profit']:
                    # Take profit hit
                    exit_price = position['take_profit']
                    trade_result = (position['entry_price'] - exit_price) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'take_profit',
                        'confidence': position['confidence']
                    })
                    
                    position = None
                
                # Check for exit signal (if prediction changes direction)
                elif prediction > 0 and confidence >= 0.6:
                    # Exit on opposite signal
                    exit_price = row['close']
                    trade_result = (position['entry_price'] - exit_price) / position['entry_price']
                    pnl = position['size'] * trade_result
                    balance += position['size'] + pnl
                    
                    # Record the trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': 'signal',
                        'confidence': position['confidence'],
                        'exit_confidence': confidence
                    })
                    
                    position = None
        
        # Check for entry if we don't have an open position
        if not position and confidence >= 0.6:  # Only enter if confidence is above threshold
            if prediction > 0:  # Buy signal
                entry_price = row['close']
                position_size = balance * (strategy.risk_per_trade_pct / 100)
                stop_loss = entry_price * (1 - strategy.stop_loss_pct / 100)
                take_profit = entry_price * (1 + strategy.take_profit_pct / 100)
                
                position = {
                    'type': 'BUY',
                    'entry_time': idx,
                    'entry_price': entry_price,
                    'size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': confidence
                }
                
                balance -= position_size
            
            elif prediction < 0:  # Sell signal
                entry_price = row['close']
                position_size = balance * (strategy.risk_per_trade_pct / 100)
                stop_loss = entry_price * (1 + strategy.stop_loss_pct / 100)
                take_profit = entry_price * (1 - strategy.take_profit_pct / 100)
                
                position = {
                    'type': 'SELL',
                    'entry_time': idx,
                    'entry_price': entry_price,
                    'size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': confidence
                }
                
                balance -= position_size
        
        # Update equity and drawdown
        current_equity = balance
        if position:
            # Add unrealized P&L
            if position['type'] == 'BUY':
                trade_result = (row['close'] - position['entry_price']) / position['entry_price']
            else:
                trade_result = (position['entry_price'] - row['close']) / position['entry_price']
            
            current_equity += position['size'] + (position['size'] * trade_result)
        
        equity_curve.append(current_equity)
        max_equity = max(max_equity, current_equity)
        current_drawdown = (max_equity - current_equity) / max_equity * 100 if max_equity > 0 else 0
        drawdown_curve.append(current_drawdown)
    
    # Close any open position at the end of the backtest
    if position:
        exit_price = backtest_data.iloc[-1]['close']
        
        if position['type'] == 'BUY':
            trade_result = (exit_price - position['entry_price']) / position['entry_price']
        else:
            trade_result = (position['entry_price'] - exit_price) / position['entry_price']
        
        pnl = position['size'] * trade_result
        balance += position['size'] + pnl
        
        # Record the trade
        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': backtest_data.index[-1],
            'type': position['type'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'size': position['size'],
            'pnl': pnl,
            'exit_reason': 'end_of_test',
            'confidence': position['confidence']
        })
    
    return {
        'final_balance': balance,
        'trades': trades,
        'equity_curve': equity_curve,
        'drawdown_curve': drawdown_curve
    }

def evaluate_backtest_condition(row, prev_row, condition):
    """Evaluate a condition for backtest signal generation."""
    try:
        indicator = condition['indicator']
        operator = condition['operator']
        value = condition['value']
        
        # Check if indicators exist in data
        if indicator not in row or indicator not in prev_row:
            logger.warning(f"Indicator {indicator} not found in backtest data")
            return False
        
        # Get indicator values
        current_value = row[indicator]
        previous_value = prev_row[indicator]
        
        # Evaluate the condition
        if operator == 'above':
            return current_value > value
        elif operator == 'below':
            return current_value < value
        elif operator == 'equals':
            return abs(current_value - value) < 0.0001
        elif operator == 'crosses_above':
            return current_value > value and previous_value <= value
        elif operator == 'crosses_below':
            return current_value < value and previous_value >= value
        elif operator == 'increasing':
            return current_value > previous_value
        elif operator == 'decreasing':
            return current_value < previous_value
        else:
            logger.warning(f"Unsupported operator {operator}")
            return False
    
    except Exception as e:
        logger.error(f"Error evaluating backtest condition: {e}")
        return False

def calculate_performance_metrics(backtest_results):
    """Calculate performance metrics from backtest results."""
    trades = backtest_results['trades']
    equity_curve = backtest_results['equity_curve']
    drawdown_curve = backtest_results['drawdown_curve']
    
    # Basic metrics
    total_trades = len(trades)
    if total_trades == 0:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'average_profit': 0.0,
            'average_loss': 0.0,
            'max_drawdown_pct': 0.0,
            'sharpe_ratio': 0.0,
            'return_pct': 0.0
        }
    
    winning_trades = sum(1 for trade in trades if trade['pnl'] > 0)
    losing_trades = sum(1 for trade in trades if trade['pnl'] <= 0)
    
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    # Profit and loss metrics
    total_profit = sum(trade['pnl'] for trade in trades if trade['pnl'] > 0)
    total_loss = abs(sum(trade['pnl'] for trade in trades if trade['pnl'] <= 0))
    
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    
    average_profit = total_profit / winning_trades if winning_trades > 0 else 0
    average_loss = total_loss / losing_trades if losing_trades > 0 else 0
    
    # Drawdown
    max_drawdown_pct = max(drawdown_curve) if drawdown_curve else 0
    
    # Return
    initial_balance = backtest_results['equity_curve'][0]
    final_balance = backtest_results['final_balance']
    return_pct = (final_balance - initial_balance) / initial_balance * 100
    
    # Sharpe ratio (simplified)
    if len(equity_curve) > 1:
        # Calculate daily returns
        daily_returns = [(equity_curve[i] / equity_curve[i-1]) - 1 for i in range(1, len(equity_curve))]
        avg_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)
        sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0  # Annualized
    else:
        sharpe_ratio = 0
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'average_profit': average_profit,
        'average_loss': average_loss,
        'max_drawdown_pct': max_drawdown_pct,
        'sharpe_ratio': sharpe_ratio,
        'return_pct': return_pct
    }

def get_available_strategies(user_id):
    """Get available strategies for backtesting."""
    return TradingStrategy.query.filter_by(user_id=user_id).all()

def get_backtest_result(backtest_id):
    """Get a specific backtest result."""
    result = BacktestResult.query.get(backtest_id)
    if result:
        return {
            'id': result.id,
            'strategy_name': result.strategy.name,
            'trading_pair': result.trading_pair,
            'timeframe': result.timeframe,
            'start_date': result.start_date,
            'end_date': result.end_date,
            'initial_balance': result.initial_balance,
            'final_balance': result.final_balance,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'profit_factor': result.profit_factor,
            'max_drawdown_pct': result.max_drawdown_pct,
            'sharpe_ratio': result.sharpe_ratio,
            'result_data': result.get_result_data()
        }
    return None
