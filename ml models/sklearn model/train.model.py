from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier  # or your model
import pandas as pd

# Load data
data_path = os.environ.get("TEAKA_MARKET_DATA", "C:/EV_Files/teaka_trading_app/data/market_data.csv")
if not os.path.exists(data_path) and os.path.exists("market_prices.csv"):
    data_path = "market_prices.csv"
df = pd.read_csv(data_path)

features = df.drop("target", axis=1)
target = df["target"]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)

# Build model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Evaluate
accuracy = model.score(X_test, y_test)
print(f"Accuracy: {accuracy:.2f}")
