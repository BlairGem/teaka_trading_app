import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ALERT] Telegram not configured — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        return {"ok": False, "error": "Telegram credentials not configured"}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, json=data)
    return response.json()

@app.route("/api/alert", methods=["POST"])
def receive_alert():
    data = request.get_json()
    message = data.get("message", "No message received.")
    print(f"[ALERT RECEIVED] {message}")
    result = send_telegram_alert(message)
    return jsonify({"status": "sent", "message": message, "telegram": result})

@app.route("/api/auto-exit", methods=["POST"])
def auto_exit_trigger():
    trade = request.get_json()
    asset = trade.get("asset", "Unknown")
    reason = trade.get("reason", "N/A")
    send_telegram_alert(f"Auto-exit triggered for {asset}: {reason}")
    return jsonify({"status": "auto-exit sent", "asset": asset})

if __name__ == "__main__":
    app.run(port=5051)
