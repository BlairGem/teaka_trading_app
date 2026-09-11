import tensorflow as tf
import numpy as np
import os

# Sample input/output data (stubbed)
inputs = np.array([
    [30000, 1500, 31000, 0.3],
    [31000, 1550, 32000, 0.35]
], dtype=np.float32)

outputs = np.array([
    [31200],
    [32150]
], dtype=np.float32)

# Define a simple regression model
model = tf.keras.Sequential([
    tf.keras.layers.Dense(32, activation='relu', input_shape=(4,)),
    tf.keras.layers.Dense(16, activation='relu'),
    tf.keras.layers.Dense(1)
])

# Compile and train the model
model.compile(optimizer='adam', loss='mean_squared_error')
model.fit(inputs, outputs, epochs=200, verbose=1)

# Save the model
default_model_dir = "C:/EV_Files/teaka_trading_app/model_output" if os.path.exists("C:/EV_Files") else os.path.join(os.path.dirname(__file__), "model_output")
model_dir = os.environ.get("TEAKA_MODEL_DIR", default_model_dir)
os.makedirs(model_dir, exist_ok=True)
model.save(model_dir)
