import os
import subprocess
import socket
import threading
from flask import Flask, request, jsonify


def find_open_port(start=8081, max_tries=20):
    for port in range(start, start + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return None


def start_evbot_flask(port):
    app = Flask(__name__)

    @app.route('/evbot/command', methods=['POST'])
    def process_command():
        data = request.get_json()
        spell = data.get("spell", "")
        if spell == "say_hi":
            return jsonify({"message": f"EVBot online via auto-bind on port {port}"})
        return jsonify({"result": "Unknown spell"})

    app.run(host="127.0.0.1", port=port)


def start_ollama_serve(port=11434):
    """Start ollama serve (not 'ollama run' which is interactive)."""
    try:
        proc = subprocess.Popen(
            ["ollama", "serve"],
            env={**os.environ, "OLLAMA_HOST": f"0.0.0.0:{port}"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"Ollama serve started (pid {proc.pid}) on port {port}")
        return proc
    except FileNotFoundError:
        print("ollama binary not found — skipping")
        return None


def main():
    ev_port = find_open_port()
    if ev_port:
        print(f"Binding EVBot to port {ev_port}")
        flask_thread = threading.Thread(target=start_evbot_flask, args=(ev_port,), daemon=True)
        flask_thread.start()
    else:
        print("No open port found for EVBot Flask")

    start_ollama_serve()


if __name__ == "__main__":
    main()
