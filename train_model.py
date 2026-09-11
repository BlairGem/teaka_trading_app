import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense

data = pd.DataFrame({
    'feature1': [0.1, 0.2, 0.3, 0.4, 0.5],
    'feature2': [1.0, 0.9, 0.8, 0.7, 0.6],
    'target': [0, 1, 0, 1, 0]
})

features = data[['feature1', 'feature2']]
target = data['target']

X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

model = Sequential([
    Dense(16, input_shape=(X_train.shape[1],), activation='relu'),
    Dense(8, activation='relu'),
    Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model.fit(X_train, y_train, epochs=50, batch_size=2, verbose=1)
default_model_dir = "C:/EV_Files/teaka_trading_app" if os.path.exists("C:/EV_Files") else os.path.join(os.path.dirname(__file__), "model_output")
output_dir = os.environ.get("TEAKA_MODEL_DIR", default_model_dir)
os.makedirs(output_dir, exist_ok=True)
model.save(os.path.join(output_dir, "qtrader_model.h5"))
print("? Model training complete and saved.")
