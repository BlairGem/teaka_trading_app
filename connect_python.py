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
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent
BRAIN_DIR = ROOT / "bridge" / "brain"
CROSS_DEVICE_BRAIN = BRAIN_DIR / "Cross_device_brain.json"
EVBOT_STATE = BRAIN_DIR / "evbot_runtime_state.json"
EVBOT_DIR = ROOT / "evbot"
PUBLIC_DIR = ROOT / "public"
BRAIN_CANDIDATES = [
    CROSS_DEVICE_BRAIN,
    ROOT / "ev_virtual_brain.json",
    Path(os.environ.get("TEAKA_BRAIN_FILE", "")),
    # D: Drive actual physical locations
    Path(r"D:\EV_Files\ev_viral_brain.json"),
    Path(r"D:\EV_Files\EVBot_runtime\EchoVault\daemon_brain.json"),
    Path(r"D:\EV_Files\EVBot_runtime\EchoVault\echo_cava.vlt.json"),
    Path(r"D:\EV_Files\ev_virtual_brain.json"),
    # C: Drive junction / repo locations
    Path(r"C:\EV_Files\ev_viral_brain.json"),
    Path(r"C:\EV_Files\EVBot_runtime\EchoVault\daemon_brain.json"),
    Path(r"C:\EV_Files\ev_virtual_brain.json"),
    Path(r"C:\Users\Blair\EV_Git\Ev\brain\EV_CHAT_STATE_20260607.json"),
    Path(r"C:\Users\Blair\EV_Git\Ev\brain\EV_FuzzyBrain_State.json"),
    Path(r"C:\Users\Blair\EV_Git\Ev\brain\EV_PYTHONISTA_BRAIN_MAP_MASTER_2026-06-07.json"),
    # Historical E: Drive fallback
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


def save_cross_device_brain(brain: dict) -> Path:
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    CROSS_DEVICE_BRAIN.write_text(json.dumps(brain, indent=2), encoding="utf-8")
    return CROSS_DEVICE_BRAIN


def load_json_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_evbot_profile() -> dict:
    viral = load_json_file(EVBOT_DIR / "ev_viral_brain.json")
    instructions = (EVBOT_DIR / "evbot_gpt_instructions.json.txt").read_text(
        encoding="utf-8"
    ) if (EVBOT_DIR / "evbot_gpt_instructions.json.txt").is_file() else ""
    return {
        "viral_brain_present": bool(viral),
        "gpt_instructions_present": bool(instructions),
        "identity": (viral.get("evbot.brain") or {}).get("status"),
        "flask_apps": (
            ((viral.get("viral_reflex_core") or {}).get("ev_core") or {})
            .get("modules", {})
            .get("LinkedSystems", {})
            .get("FlaskApps", [])
        ),
        "spell_route": (
            ((viral.get("evbot.brain") or {}).get("spell_engine") or {}).get(
                "api_route", "/ev_remote/command"
            )
        ),
        "runners": (viral.get("evbot.brain") or {}).get("runners", {}),
        "instructions_preview": instructions[:400],
    }


def load_evbot_state() -> dict:
    state = load_json_file(EVBOT_STATE)
    if not state:
        state = {
            "evbot_online": False,
            "started_at": None,
            "mode": os.environ.get("TEAKA_MODE", "paper"),
            "source": None,
        }
    return state


def save_evbot_state(state: dict) -> None:
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    EVBOT_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


app = Flask(__name__)


@app.get("/")
def root():
    return send_from_directory(PUBLIC_DIR, "evbot_start.html")


@app.get("/evbot")
@app.get("/evbot_start.html")
def evbot_page():
    return send_from_directory(PUBLIC_DIR, "evbot_start.html")


@app.get("/api/phone/status")
def phone_status():
    state = load_evbot_state()
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
            "cross_device_brain_present": CROSS_DEVICE_BRAIN.is_file(),
            "evbot_online": bool(state.get("evbot_online")),
            "mcp_adapter_present": (ROOT / "bridge" / "ev_mcp_adapter.py").is_file(),
            "python": sys.version.split()[0],
            "sentinel_route": "ONLINE",
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


@app.get("/api/phone/brain")
def phone_brain_get():
    return jsonify({"ok": True, "brain": load_brain(), "path": str(CROSS_DEVICE_BRAIN)})


@app.post("/api/phone/brain/sync")
def phone_brain_sync():
    data = request.get_json(silent=True) or {}
    brain = data.get("brain")
    if not isinstance(brain, dict) or not brain:
        return jsonify({"ok": False, "error": "brain object required"}), 400
    brain = dict(brain)
    brain["host_received_at"] = datetime.now(timezone.utc).isoformat()
    brain["host_service"] = "teaka-python-bridge"
    path = save_cross_device_brain(brain)
    return jsonify(
        {
            "ok": True,
            "saved": str(path),
            "source": data.get("source"),
            "shared": data.get("shared"),
            "device": data.get("device"),
            "sentinel": data.get("sentinel"),
            "route": "ONLINE",
        }
    )


@app.get("/api/ev/mesh/status")
def ev_mesh_status():
    """Probe the local EV microservice mesh endpoints."""
    endpoints = {
        "gembot": "http://127.0.0.1:5056/status",
        "roboshady_brain": "http://127.0.0.1:5060/status",
        "minerals": "http://127.0.0.1:5055/status",
        "ollama": "http://127.0.0.1:11434/api/tags",
        "memory": "http://127.0.0.1:11436/memory/stats",
        "mt_greenland": "http://127.0.0.1:5057/api/health",
        "ev_commander": "http://127.0.0.1:8080/status",
    }
    status = {}
    import urllib.request
    for name, url in endpoints.items():
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                status[name] = {"online": True, "details": data}
        except Exception as exc:
            status[name] = {"online": False, "error": str(exc)}
    return jsonify({
        "service": "teaka-ev-mesh-probe",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mesh": status,
        "mcp_adapter_present": (ROOT / "bridge" / "ev_mcp_adapter.py").is_file(),
    })


@app.get("/api/evbot/status")
def evbot_status():
    state = load_evbot_state()
    profile = load_evbot_profile()
    return jsonify(
        {
            "ok": True,
            "evbot_online": bool(state.get("evbot_online")),
            "started_at": state.get("started_at"),
            "source": state.get("source"),
            "mode": os.environ.get("TEAKA_MODE", "paper"),
            "live_trading_enabled": os.environ.get("LIVE_TRADING_ENABLED", "false"),
            "profile": profile,
            "mcp_adapter": "/bridge/ev_mcp_adapter.py",
            "mesh_probe": "/api/ev/mesh/status",
            "routes": {
                "primary": "/ev_remote/command",
                "start": "/api/evbot/start",
                "ui": "/evbot",
            },
        }
    )


@app.post("/api/evbot/start")
def evbot_start():
    """Bring EVBot online against this paper-safe bridge (no live exchange orders)."""
    data = request.get_json(silent=True) or {}
    profile = load_evbot_profile()
    now = datetime.now(timezone.utc).isoformat()
    state = {
        "evbot_online": True,
        "started_at": now,
        "source": data.get("source") or "api",
        "mode": os.environ.get("TEAKA_MODE", "paper"),
        "startup": ["Check memory", "Verify routes", "Bind cortex"],
        "modules": ["EVBot", "GEMBot", "Firemind", "TeAka"],
        "note": "Cloud/host bridge start. Full Windows Waitress stack still uses evbot/EV_Waitress_Launcher.ps1 on local CS.",
    }
    save_evbot_state(state)

    brain = load_brain()
    if not isinstance(brain, dict):
        brain = {}
    brain = dict(brain)
    brain["evbot"] = {
        "online": True,
        "started_at": now,
        "mode": state["mode"],
        "author": "Forgekeeper-Blair",
    }
    save_cross_device_brain(brain)

    return jsonify(
        {
            "ok": True,
            "message": "EVBot online on TeAka bridge",
            "state": state,
            "profile": {
                "viral_brain_present": profile["viral_brain_present"],
                "gpt_instructions_present": profile["gpt_instructions_present"],
                "flask_apps": profile["flask_apps"],
                "spell_route": profile["spell_route"],
            },
            "ui": "/evbot",
            "live_orders": False,
        }
    )


@app.post("/ev_remote/command")
@app.get("/ev_remote/command")
@app.post("/evbot/activate_cortex")
@app.post("/evbot/link_cortex")
def ev_remote_command():
    data = request.get_json(silent=True) or {}
    command = (
        data.get("command")
        or data.get("cmd")
        or request.args.get("command")
        or request.args.get("cmd")
        or "status_check"
    )
    state = load_evbot_state()
    if command in {"start", "activate", "activate_cortex", "boot"}:
        with app.test_request_context(
            "/api/evbot/start",
            method="POST",
            json={"source": "ev_remote_command"},
        ):
            return evbot_start()
    return jsonify(
        {
            "ev_status": "online" if state.get("evbot_online") else "standby",
            "evbot_online": bool(state.get("evbot_online")),
            "received_command": command,
            "brain_link": load_brain(),
            "mode": os.environ.get("TEAKA_MODE", "paper"),
            "route": request.path,
        }
    )


def main() -> None:
    os.environ.setdefault("TEAKA_MODE", "paper")
    os.environ.setdefault("LIVE_TRADING_ENABLED", "false")
    os.environ.setdefault("PRIVATE_EXCHANGE_API_ENABLED", "false")
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    host = os.environ.get("TEAKA_BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("TEAKA_BIND_PORT", "5050"))
    print(f"TeAka Python bridge on http://{host}:{port} (paper-safe)")
    print(f"EVBot start UI: http://127.0.0.1:{port}/evbot")
    print("Phone client: python phone/client.py --host http://<this-ip>:5050 status")
    print("Pythonista: run phone/pythonista_boot.py with TEAKA_HOST set for ONLINE route")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
