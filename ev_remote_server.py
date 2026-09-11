from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Memory File Paths
BRAIN_CANDIDATES = [
    os.path.join("D:\\", "EV_Files", "ev_viral_brain.json"),
    os.path.join("D:\\", "EV_Files", "EVBot_runtime", "EchoVault", "daemon_brain.json"),
    os.path.join("D:\\", "EV_Files", "ev_virtual_brain.json"),
    os.path.join("C:\\", "EV_Files", "ev_viral_brain.json"),
    os.path.join("C:\\", "EV_Files", "ev_virtual_brain.json"),
    os.path.join("E:\\", "EV_Files", "ev_virtual_brain.json"),
    "ev_virtual_brain.json",
]

# Load Brain Memory (if available)
def load_brain():
    for brain_path in BRAIN_CANDIDATES:
        if os.path.exists(brain_path):
            try:
                with open(brain_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return {"error": "Brain file missing"}

@app.route("/ev_remote/command", methods=["GET", "POST"])
def remote_command():
    data = request.json or {}
    command = data.get("command", "status_check")

    brain = load_brain()

    response = {
        "ev_status": "online",
        "brain_link": brain,
        "received_command": command
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
