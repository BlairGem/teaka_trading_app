#!/usr/bin/env python3
"""
Connect TeAka Python surfaces for local / phone access.

Starts a paper-safe Flask bridge on 0.0.0.0:5050 that exposes:
  GET  /api/phone/status
  POST /api/phone/paper-run
  POST /api/phone/command

Live exchange order gates stay off unless env explicitly enables them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parent
BRAIN_CANDIDATES = [
    ROOT / "ev_virtual_brain.json",
    Path(os.environ.get("TEAKA_BRAIN_FILE", "")),
    Path(r"E:\EV_Files\ev_virtual_brain.json"),
]


def load_brain() -> dict:
    for path in BRAIN_CANDIDATES:
        if path and path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
    return {"status": "brain_missing", "hint": "ev_virtual_brain.json not found"}


app = Flask(__name__)


@app.get("/api/phone/status")
def phone_status():
    return jsonify(
        {
            "service": "teaka-python-bridge",
            "mode": os.environ.get("TEAKA_MODE", "paper"),
            "live_trading_enabled": os.environ.get("LIVE_TRADING_ENABLED", "false"),
            "private_exchange_api_enabled": os.environ.get(
                "PRIVATE_EXCHANGE_API_ENABLED", "false"
            ),
            "paper_trading": True,
            "trading_stack_connected": (ROOT / "trading_stack" / "trading_engine.py").is_file(),
            "brain": load_brain(),
            "python": sys.version.split()[0],
        }
    )


@app.post("/api/phone/paper-run")
def phone_paper_run():
    ticks = ROOT / "paper_trading" / "sample_ticks.csv"
    runner = ROOT / "paper_trading" / "run_paper.py"
    log = ROOT / "paper_trading" / "state" / "phone_paper_fills.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(runner), "--ticks", str(ticks), "--log", str(log)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    snapshot = {}
    if proc.stdout.strip():
        try:
            snapshot = json.loads(proc.stdout)
        except json.JSONDecodeError:
            # Runner may print trailing text; take the largest JSON object in stdout.
            text = proc.stdout.strip()
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    snapshot = json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    snapshot = {"raw_stdout": text[-2000:]}
            else:
                snapshot = {"raw_stdout": text[-2000:]}
    return jsonify(
        {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "snapshot": snapshot,
            "stderr": proc.stderr[-2000:],
            "log": str(log),
        }
    ), (200 if proc.returncode == 0 else 500)


@app.post("/api/phone/command")
@app.get("/api/phone/command")
def phone_command():
    data = request.get_json(silent=True) or {}
    command = data.get("command") or request.args.get("command") or "status_check"
    return jsonify(
        {
            "ev_status": "online",
            "received_command": command,
            "brain_link": load_brain(),
            "mode": os.environ.get("TEAKA_MODE", "paper"),
        }
    )


def main() -> None:
    os.environ.setdefault("TEAKA_MODE", "paper")
    os.environ.setdefault("LIVE_TRADING_ENABLED", "false")
    os.environ.setdefault("PRIVATE_EXCHANGE_API_ENABLED", "false")
    host = os.environ.get("TEAKA_BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("TEAKA_BIND_PORT", "5050"))
    print(f"TeAka Python bridge on http://{host}:{port} (paper-safe)")
    print("Phone client: python phone/client.py --host http://<this-ip>:5050 status")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
