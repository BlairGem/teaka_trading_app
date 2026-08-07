import logging
import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, mean_squared_error, mean_absolute_error
from models import MLModel, db
import joblib

# Import TensorFlow lazily to avoid startup errors
tf = None
Sequential = None
load_model = None
LSTM = None
Dense = None
Dropout = None

def _import_tensorflow():
    """Import TensorFlow and related modules lazily."""
    global tf, Sequential, load_model, LSTM, Dense, Dropout
    try:
        import tensorflow as tf
        from tensorflow.keras.models import Sequential, load_model
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        return True
    except ImportError as e:
        logging.error(f"TensorFlow import error: {e}")
        return False

logger = logging.getLogger(__name__)

def create_ml_model(user_id, name, model_type, target_variable, features, data, hyperparameters=None):
    """Create and train a new ML model."""
    try:
        # Create model instance
        ml_model = MLModel(
            user_id=user_id,
            name=name,
            model_type=model_type,
            target_variable=target_variable,
            training_start_date=data.index[0] if not data.empty else datetime.utcnow(),
            training_end_date=data.index[-1] if not data.empty else datetime.utcnow(),
            is_active=False
        )
        
        # Set features
        ml_model.set_features(features)
        
        # Set default hyperparameters if none provided
        if hyperparameters is None:
            hyperparameters = get_default_hyperparameters(model_type)
        
        ml_model.set_hyperparameters(hyperparameters)
        
        # Save to database to get ID
        db.session.add(ml_model)
        db.session.commit()
        
        # Prepare data
        X, y = prepare_data(data, features, target_variable)
        
        if X.empty or y.empty:
            logger.error(f"Empty dataset for ML model training")
            ml_model.set_performance_metrics({"error": "Empty dataset"})
            db.session.commit()
            return ml_model.id
        
        # Train model
        trained_model, scaler, performance_metrics = train_model(
            model_type=model_type,
            X=X,
            y=y,
            hyperparameters=hyperparameters
        )
        
        # Save trained model
        model_path = save_model(trained_model, ml_model.id, model_type)
        scaler_path = save_scaler(scaler, ml_model.id)
        
        # Update model with paths and performance metrics
        ml_model.model_path = model_path
        ml_model.set_performance_metrics(performance_metrics)
        ml_model.last_updated = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"ML model {name} created successfully with ID {ml_model.id}")
        return ml_model.id
    
    except Exception as e:
        logger.error(f"Error creating ML model: {e}")
        db.session.rollback()
        return None

def prepare_data(data, features, target_variable):
    """Prepare data for ML model training."""
    if data.empty:
        return pd.DataFrame(), pd.Series()
    
    # Make sure all features exist in the data
    available_features = [f for f in features if f in data.columns]
    if not available_features:
        logger.error("No requested features available in the data")
        return pd.DataFrame(), pd.Series()
    
    # Prepare feature data
    X = data[available_features].copy()
    
    # Handle NaN values
    X = X.dropna()
    
    # Prepare target variable
    if target_variable == 'price_direction':
        # Classification target: 1 if price goes up, 0 if down
        y = (data['close'].shift(-1) > data['close']).astype(int)
    elif target_variable == 'price_change_pct':
        # Regression target: percent change in next period
        y = data['close'].pct_change(1).shift(-1) * 100
    elif target_variable == 'next_candle_close':
        # Regression target: next candle close price
        y = data['close'].shift(-1)
    else:
        logger.error(f"Unsupported target variable: {target_variable}")
        return pd.DataFrame(), pd.Series()
    
    # Align X and y and drop NaN values
    X = X.loc[y.index]
    y = y.loc[X.index]
    
    # Drop NaN values created by shifts
    valid_indices = ~y.isna()
    X = X[valid_indices]
    y = y[valid_indices]
    
    return X, y

def train_model(model_type, X, y, hyperparameters):
    """Train an ML model and return the trained model, scaler, and performance metrics."""
    # Scale features
    scaler = StandardScaler()
    X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns, index=X.index)
    
    # Split data into train and test sets
    train_size = int(len(X_scaled) * 0.8)
    X_train, X_test = X_scaled.iloc[:train_size], X_scaled.iloc[train_size:]
    y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]
    
    model = None
    performance_metrics = {}
    
    if model_type == 'RandomForest':
        # Training for classification
        n_estimators = hyperparameters.get('n_estimators', 100)
        max_depth = hyperparameters.get('max_depth', None)
        
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        performance_metrics = {
            'accuracy': accuracy,
            'feature_importance': dict(zip(X.columns, model.feature_importances_.tolist()))
        }
    
    elif model_type == 'GradientBoosting':
        # Training for regression
        n_estimators = hyperparameters.get('n_estimators', 100)
        learning_rate = hyperparameters.get('learning_rate', 0.1)
        max_depth = hyperparameters.get('max_depth', 3)
        
        model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        
        performance_metrics = {
            'mse': mse,
            'mae': mae,
            'feature_importance': dict(zip(X.columns, model.feature_importances_.tolist()))
        }
    
    elif model_type == 'LSTM':
        # Import TensorFlow on demand
        if not _import_tensorflow():
            logger.error("TensorFlow is not available. Cannot train LSTM model.")
            return None, scaler, {"error": "TensorFlow is not available"}
        
        # Reshape data for LSTM [samples, time steps, features]
        lookback = hyperparameters.get('lookback', 10)
        
        # Prepare sequences
        X_sequences, y_sequences = create_sequences(X_scaled.values, y.values, lookback)
        
        # Split sequences
        train_size = int(len(X_sequences) * 0.8)
        X_train_seq, X_test_seq = X_sequences[:train_size], X_sequences[train_size:]
        y_train_seq, y_test_seq = y_sequences[:train_size], y_sequences[train_size:]
        
        # Build LSTM model
        input_shape = (X_train_seq.shape[1], X_train_seq.shape[2])
        units = hyperparameters.get('units', 50)
        dropout_rate = hyperparameters.get('dropout_rate', 0.2)
        
        model = Sequential()
        model.add(LSTM(units=units, return_sequences=True, input_shape=input_shape))
        model.add(Dropout(dropout_rate))
        model.add(LSTM(units=units//2))
        model.add(Dropout(dropout_rate))
        model.add(Dense(1))
        
        model.compile(optimizer='adam', loss='mse')
        
        # Train
        epochs = hyperparameters.get('epochs', 50)
        batch_size = hyperparameters.get('batch_size', 32)
        
        model.fit(X_train_seq, y_train_seq, epochs=epochs, batch_size=batch_size, verbose=0)
        
        # Evaluate
        y_pred = model.predict(X_test_seq)
        mse = mean_squared_error(y_test_seq, y_pred)
        mae = mean_absolute_error(y_test_seq, y_pred)
        
        performance_metrics = {
            'mse': float(mse),
            'mae': float(mae)
        }
    
    else:
        logger.error(f"Unsupported model type: {model_type}")
        return None, scaler, {"error": f"Unsupported model type: {model_type}"}
    
    return model, scaler, performance_metrics

def create_sequences(X, y, lookback):
    """Create sequences for LSTM model."""
    X_sequences, y_sequences = [], []
    for i in range(len(X) - lookback):
        X_sequences.append(X[i:i + lookback])
        y_sequences.append(y[i + lookback])
    return np.array(X_sequences), np.array(y_sequences)

def get_default_hyperparameters(model_type):
    """Get default hyperparameters for a model type."""
    if model_type == 'RandomForest':
        return {
            'n_estimators': 100,
            'max_depth': 10
        }
    elif model_type == 'GradientBoosting':
        return {
            'n_estimators': 100,
            'learning_rate': 0.1,
            'max_depth': 3
        }
    elif model_type == 'LSTM':
        return {
            'lookback': 10,
            'units': 50,
            'dropout_rate': 0.2,
            'epochs': 50,
            'batch_size': 32
        }
    else:
        return {}

def save_model(model, model_id, model_type):
    """Save a trained model to disk."""
    # Create models directory if it doesn't exist
    if not os.path.exists('models'):
        os.makedirs('models')
    
    model_path = f"models/model_{model_id}.pkl"
    
    if model_type == 'LSTM':
        # Save Keras model
        model_path = f"models/model_{model_id}.h5"
        model.save(model_path)
    else:
        # Save scikit-learn model
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
    
    return model_path

def save_scaler(scaler, model_id):
    """Save a scaler to disk."""
    # Create models directory if it doesn't exist
    if not os.path.exists('models'):
        os.makedirs('models')
    
    scaler_path = f"models/scaler_{model_id}.pkl"
    
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    
    return scaler_path

def load_model_and_scaler(model_id):
    """Load a model and scaler from disk."""
    try:
        # Get model info from database
        ml_model = MLModel.query.get(model_id)
        if not ml_model:
            logger.error(f"ML model with ID {model_id} not found")
            return None, None
        
        model_path = ml_model.model_path
        model_type = ml_model.model_type
        
        # Check if model file exists
        if not model_path or not os.path.exists(model_path):
            logger.error(f"Model file {model_path} not found")
            return None, None
        
        # Load model
        model = None
        if model_type == 'LSTM':
            # Import TensorFlow on demand
            if not _import_tensorflow():
                logger.error("TensorFlow is not available. Cannot load LSTM model.")
                return None, None
            model = load_model(model_path)
        else:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
        
        # Load scaler
        scaler_path = f"models/scaler_{model_id}.pkl"
        if not os.path.exists(scaler_path):
            logger.error(f"Scaler file {scaler_path} not found")
            return model, None
        
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
        
        return model, scaler
    
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None, None

def predict_with_model(model_id, data):
    """Generate a prediction using a trained ML model."""
    try:
        # Get model info
        ml_model = MLModel.query.get(model_id)
        if not ml_model:
            logger.error(f"ML model with ID {model_id} not found")
            return 0, 0
        
        # Load model and scaler
        model, scaler = load_model_and_scaler(model_id)
        if model is None:
            logger.error(f"Could not load model with ID {model_id}")
            return 0, 0
        
        # Prepare features
        features = ml_model.get_features()
        
        # Make sure all features exist in the data
        available_features = [f for f in features if f in data.columns]
        if not available_features:
            logger.error("No requested features available in the data")
            return 0, 0
        
        # Extract features
        X = data[available_features].copy().iloc[-1:].values
        
        # Scale features
        if scaler:
            X = scaler.transform(X)
        
        # Generate prediction
        if ml_model.model_type == 'LSTM':
            # Import TensorFlow on demand if needed for prediction
            if not _import_tensorflow():
                logger.error("TensorFlow is not available. Cannot make LSTM prediction.")
                return 0, 0
                
            # Reshape data for LSTM
            hyperparameters = ml_model.get_hyperparameters()
            lookback = hyperparameters.get('lookback', 10)
            
            if len(data) < lookback:
                logger.error(f"Not enough data for LSTM prediction (need {lookback} points)")
                return 0, 0
            
            # Extract features for sequence
            X_seq = data[available_features].copy().iloc[-lookback:].values
            
            # Scale sequence
            if scaler:
                X_seq = scaler.transform(X_seq)
            
            # Reshape to [1, lookback, features]
            X_seq = X_seq.reshape(1, lookback, len(available_features))
            
            # Predict
            prediction = model.predict(X_seq)[0][0]
            
            # Calculate confidence based on historical performance
            metrics = ml_model.get_performance_metrics()
            mae = metrics.get('mae', 1.0)
            confidence = 1.0 / (1.0 + mae)  # Confidence decreases as error increases
        else:
            if ml_model.model_type == 'RandomForest':
                # Classification problem
                probabilities = model.predict_proba(X)[0]
                prediction_class = model.predict(X)[0]
                
                # Convert to a signal direction (-1 for sell, 1 for buy)
                prediction = 1 if prediction_class == 1 else -1
                
                # Confidence is the probability of the predicted class
                confidence = probabilities[prediction_class]
            else:
                # Regression problem
                prediction = model.predict(X)[0]
                
                # For regression models, normalize prediction to -1 to 1 range
                # and use feature importance as confidence
                prediction_normalized = np.clip(prediction / 5.0, -1, 1)  # Assuming typical price changes are within 5%
                
                # Calculate confidence based on historical performance
                metrics = ml_model.get_performance_metrics()
                mae = metrics.get('mae', 1.0)
                confidence = 1.0 / (1.0 + mae)  # Confidence decreases as error increases
                
                prediction = prediction_normalized
        
        return prediction, confidence
    
    except Exception as e:
        logger.error(f"Error making prediction: {e}")
        return 0, 0

def get_model_details(model_id):
    """Get details about a trained ML model."""
    ml_model = MLModel.query.get(model_id)
    if not ml_model:
        return None
    
    return {
        'id': ml_model.id,
        'name': ml_model.name,
        'model_type': ml_model.model_type,
        'target_variable': ml_model.target_variable,
        'features': ml_model.get_features(),
        'hyperparameters': ml_model.get_hyperparameters(),
        'performance_metrics': ml_model.get_performance_metrics(),
        'training_start_date': ml_model.training_start_date,
        'training_end_date': ml_model.training_end_date,
        'last_updated': ml_model.last_updated,
        'is_active': ml_model.is_active
    }

def get_user_models(user_id):
    """Get all ML models for a user."""
    models = MLModel.query.filter_by(user_id=user_id).all()
    return [get_model_details(model.id) for model in models]
