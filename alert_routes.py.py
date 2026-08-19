import os
from flask import Blueprint, request, jsonify
import requests

alert_bp = Blueprint('alert_bp', __name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

@alert_bp.route('/api/alert/send', methods=['POST'])
def send_alert():
    data = request.json
    message = data.get("message", "No message provided.")
    if not message:
        return jsonify({"error": "Message is required"}), 400

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return jsonify({"error": "Telegram credentials not configured"}), 500

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    resp = requests.post(url, json=payload)
    if resp.status_code == 200:
        return jsonify({"status": "sent"})
    else:
        return jsonify({"error": resp.text}), 500
