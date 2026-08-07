import logging
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime

# Import conditionally if MATLAB is enabled
if os.environ.get("MATLAB_ENABLED", "False").lower() == "true":
    try:
        import matlab.engine
    except ImportError:
        logging.error("MATLAB Engine for Python not installed. MATLAB integration will not work.")

logger = logging.getLogger(__name__)

# Global MATLAB engine instance
matlab_engine = None

def initialize_matlab():
    """Initialize MATLAB engine for Python."""
    global matlab_engine
    
    if os.environ.get("MATLAB_ENABLED", "False").lower() != "true":
        logger.info("MATLAB integration is disabled")
        return False
    
    try:
        if matlab_engine is None:
            logger.info("Starting MATLAB engine...")
            matlab_engine = matlab.engine.start_matlab()
            
            # Add the path to MATLAB scripts
            matlab_path = os.environ.get("MATLAB_SCRIPTS_PATH", "./matlab_scripts")
            if os.path.exists(matlab_path):
                matlab_engine.addpath(matlab_engine.genpath(matlab_path))
                logger.info(f"Added MATLAB scripts path: {matlab_path}")
            else:
                logger.warning(f"MATLAB scripts path not found: {matlab_path}")
            
            logger.info("MATLAB engine started successfully")
        return True
    
    except Exception as e:
        logger.error(f"Failed to initialize MATLAB engine: {e}")
        return False

def get_matlab_engine():
    """Get the MATLAB engine instance, initializing it if necessary."""
    global matlab_engine
    
    if matlab_engine is None:
        initialize_matlab()
    
    return matlab_engine

def close_matlab_engine():
    """Close the MATLAB engine."""
    global matlab_engine
    
    if matlab_engine is not None:
        try:
            matlab_engine.quit()
            matlab_engine = None
            logger.info("MATLAB engine closed")
            return True
        except Exception as e:
            logger.error(f"Error closing MATLAB engine: {e}")
            return False
    
    return True

def run_matlab_function(function_name, *args, **kwargs):
    """Run a MATLAB function with the given arguments."""
    eng = get_matlab_engine()
    
    if eng is None:
        logger.error("MATLAB engine not available")
        return None
    
    try:
        # Convert Python arguments to MATLAB compatible types
        matlab_args = []
        for arg in args:
            matlab_args.append(convert_to_matlab(eng, arg))
        
        # Call the function
        result = getattr(eng, function_name)(*matlab_args, nargout=1)
        
        # Convert result back to Python
        return convert_to_python(result)
    
    except Exception as e:
        logger.error(f"Error calling MATLAB function {function_name}: {e}")
        return None

def convert_to_matlab(eng, data):
    """Convert Python data types to MATLAB compatible types."""
    if isinstance(data, pd.DataFrame):
        # Convert DataFrame to MATLAB table
        column_names = list(data.columns)
        matlab_cell_array = eng.cell(len(column_names), 1)
        
        for i, name in enumerate(column_names):
            matlab_cell_array[i] = name
        
        # Convert data to numeric array
        numeric_data = data.values
        matlab_array = matlab.double(numeric_data.tolist())
        
        # Create table
        return eng.array2table(matlab_array, nargout=1)
    
    elif isinstance(data, np.ndarray):
        # Convert numpy array to MATLAB array
        return matlab.double(data.tolist())
    
    elif isinstance(data, list):
        # Convert list to MATLAB array
        if all(isinstance(x, (int, float)) for x in data):
            return matlab.double(data)
        else:
            matlab_cell = eng.cell(len(data), 1)
            for i, val in enumerate(data):
                matlab_cell[i] = convert_to_matlab(eng, val)
            return matlab_cell
    
    elif isinstance(data, dict):
        # Convert dict to MATLAB struct
        struct = eng.struct()
        for key, value in data.items():
            eng.setfield(struct, key, convert_to_matlab(eng, value))
        return struct
    
    elif isinstance(data, str):
        return data
    
    elif isinstance(data, (int, float)):
        return data
    
    else:
        return data

def convert_to_python(matlab_data):
    """Convert MATLAB data types to Python types."""
    if isinstance(matlab_data, matlab.double):
        # Convert to numpy array
        np_array = np.array(matlab_data)
        if np_array.shape[0] == 1 and np_array.shape[1] == 1:
            # Return scalar for 1x1 arrays
            return np_array[0, 0]
        return np_array
    
    elif hasattr(matlab_data, '_fieldnames'):
        # Convert struct to dict
        result = {}
        for field in matlab_data._fieldnames:
            result[field] = convert_to_python(getattr(matlab_data, field))
        return result
    
    elif isinstance(matlab_data, list):
        # Convert cell array to list
        return [convert_to_python(item) for item in matlab_data]
    
    else:
        # Return as is for other types
        return matlab_data

def get_matlab_signal(trading_pair, timeframe, indicators_config):
    """Get trading signal from MATLAB."""
    try:
        # Initialize MATLAB engine if not already done
        if not initialize_matlab():
            return None, 0.0
        
        # Prepare parameters
        params = {
            'trading_pair': trading_pair,
            'timeframe': timeframe,
            'indicators': indicators_config
        }
        
        # Call MATLAB function
        result = run_matlab_function('getSignal', params)
        
        if result is None or not isinstance(result, dict):
            logger.error("Invalid result from MATLAB signal function")
            return None, 0.0
        
        signal_type = result.get('signal')
        confidence = result.get('confidence', 0.0)
        
        return signal_type, confidence
    
    except Exception as e:
        logger.error(f"Error getting MATLAB signal: {e}")
        return None, 0.0

def run_matlab_backtest(strategy, trading_pair, timeframe, start_date, end_date):
    """Run a backtest using MATLAB."""
    try:
        # Initialize MATLAB engine if not already done
        if not initialize_matlab():
            return None
        
        # Prepare parameters
        params = {
            'strategy': {
                'name': strategy.name,
                'indicators': strategy.get_indicators_config(),
                'entry_conditions': strategy.get_entry_conditions(),
                'exit_conditions': strategy.get_exit_conditions(),
                'stop_loss_pct': strategy.stop_loss_pct,
                'take_profit_pct': strategy.take_profit_pct,
                'risk_per_trade_pct': strategy.risk_per_trade_pct
            },
            'trading_pair': trading_pair,
            'timeframe': timeframe,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
        # Call MATLAB function
        result = run_matlab_function('runBacktest', params)
        
        if result is None or not isinstance(result, dict):
            logger.error("Invalid result from MATLAB backtest function")
            return None
        
        return result
    
    except Exception as e:
        logger.error(f"Error running MATLAB backtest: {e}")
        return None

def get_matlab_indicator_values(data, indicator_name, parameters):
    """Calculate indicator values using MATLAB."""
    try:
        # Initialize MATLAB engine if not already done
        if not initialize_matlab():
            return None
        
        # Prepare parameters
        params = {
            'data': data,
            'indicator': indicator_name,
            'parameters': parameters
        }
        
        # Call MATLAB function
        result = run_matlab_function('calculateIndicator', params)
        
        if result is None:
            logger.error(f"Invalid result from MATLAB indicator function for {indicator_name}")
            return None
        
        return result
    
    except Exception as e:
        logger.error(f"Error calculating indicator {indicator_name} with MATLAB: {e}")
        return None

def generate_matlab_dashboard_data(user_id):
    """Generate dashboard data using MATLAB."""
    try:
        # Initialize MATLAB engine if not already done
        if not initialize_matlab():
            return None
        
        # Call MATLAB function
        result = run_matlab_function('getDashboardData', user_id)
        
        if result is None:
            logger.error("Invalid result from MATLAB dashboard function")
            return None
        
        return result
    
    except Exception as e:
        logger.error(f"Error generating MATLAB dashboard data: {e}")
        return None

def optimize_strategy_parameters(strategy_id, trading_pair, timeframe, start_date, end_date, parameters_to_optimize):
    """Optimize strategy parameters using MATLAB."""
    from models import TradingStrategy
    
    try:
        # Get the strategy
        strategy = TradingStrategy.query.get(strategy_id)
        if not strategy:
            logger.error(f"Strategy with ID {strategy_id} not found")
            return None
        
        # Initialize MATLAB engine if not already done
        if not initialize_matlab():
            return None
        
        # Prepare parameters
        params = {
            'strategy': {
                'name': strategy.name,
                'indicators': strategy.get_indicators_config(),
                'entry_conditions': strategy.get_entry_conditions(),
                'exit_conditions': strategy.get_exit_conditions(),
                'stop_loss_pct': strategy.stop_loss_pct,
                'take_profit_pct': strategy.take_profit_pct,
                'risk_per_trade_pct': strategy.risk_per_trade_pct
            },
            'trading_pair': trading_pair,
            'timeframe': timeframe,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'parameters_to_optimize': parameters_to_optimize
        }
        
        # Call MATLAB function
        result = run_matlab_function('optimizeStrategyParameters', params)
        
        if result is None:
            logger.error("Invalid result from MATLAB optimization function")
            return None
        
        return result
    
    except Exception as e:
        logger.error(f"Error optimizing strategy with MATLAB: {e}")
        return None
