"""
Pythonista3 / Sentinel AL7 phone boot + cross-device brain sync.

Matches the phone boot pattern:

    ST_BOOT: DOCUMENTS=.../Pythonista3/Documents
    ST_BOOT: MASTER=.../therruedevil7.json
    ST_BOOT: SHARED=.../Cross_device_brain.json
    ST_BOOT: ROUTE_MODE=AUTO
    ST_BOOT: SENTINEL_AL7_DAEMON_STARTED
    BRAIN_SYNCED: therruedevil7.json -> Cross_device_brain.json route=ONLINE|OFFLINE

Usage in Pythonista (Run):

    import phone.pythonista_boot as boot
    boot.main()

Or from Termux / desktop with the same files in ./phone or Documents.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


MASTER_NAME = "therruedevil7.json"
SHARED_NAME = "Cross_device_brain.json"
ROUTE_MODE = os.environ.get("ROUTE_MODE", "AUTO").upper()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"{_now()} | {msg}")


def resolve_documents() -> Path:
    """Prefer Pythonista Documents; fall back to repo phone/ or cwd."""
    env = os.environ.get("PYTHONISTA_DOCUMENTS") or os.environ.get("DOCUMENTS")
    if env:
        return Path(env)

    # Pythonista often exposes this via objc / shortcuts; allow common patterns.
    home = Path.home()
    candidates = [
        home / "Documents",
        Path(__file__).resolve().parent,
        Path.cwd() / "phone",
        Path.cwd(),
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return Path.cwd()


def default_master_brain() -> dict:
    return {
        "identity": "therruedevil7",
        "device": "pythonista3",
        "sentinel": "AL7",
        "phase": "Starforge Phase 3",
        "linked": True,
        "route_mode": ROUTE_MODE,
        "teaka": {
            "mode": "paper",
            "live_trading_enabled": False,
        },
        "runtime": {
            "sentinel_al7": True,
            "pythonista": True,
            "bridge_ready": False,
        },
        "memory": {
            "last_confirmed": datetime.now(timezone.utc).isoformat(),
            "status": "local_master",
        },
        "thoughts": [],
    }


def load_or_create_json(path: Path, fallback: dict) -> dict:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log(f"ST_BOOT: WARN bad json at {path.name}: {exc}; recreating")
    path.write_text(json.dumps(fallback, indent=2), encoding="utf-8")
    return dict(fallback)


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def teaka_host() -> str:
    return os.environ.get("TEAKA_HOST", "http://127.0.0.1:5050").rstrip("/")


def probe_online(host: str, timeout: float = 3.0) -> dict | None:
    url = host + "/api/phone/status"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def push_brain(host: str, brain: dict, timeout: float = 8.0) -> dict | None:
    url = host + "/api/phone/brain/sync"
    payload = json.dumps(
        {
            "source": MASTER_NAME,
            "shared": SHARED_NAME,
            "device": "pythonista3",
            "sentinel": "AL7",
            "brain": brain,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def sync_brains(documents: Path) -> dict:
    master_path = documents / MASTER_NAME
    shared_path = documents / SHARED_NAME

    log(f"ST_BOOT: DOCUMENTS={documents}")
    log(f"ST_BOOT: MASTER={master_path}")
    log(f"ST_BOOT: SHARED={shared_path}")
    log(f"ST_BOOT: ROUTE_MODE={ROUTE_MODE}")
    log("ST_BOOT: SENTINEL_AL7_DAEMON_STARTED")

    master = load_or_create_json(master_path, default_master_brain())
    shared = dict(master)
    shared["synced_from"] = MASTER_NAME
    shared["synced_at"] = datetime.now(timezone.utc).isoformat()
    shared["cross_device"] = True

    host = teaka_host()
    route = "OFFLINE"
    host_status = None
    push_result = None

    want_online = ROUTE_MODE in {"AUTO", "ONLINE", "ON"}
    if want_online:
        host_status = probe_online(host)
        if host_status is not None:
            shared["runtime"] = dict(shared.get("runtime") or {})
            shared["runtime"]["bridge_ready"] = True
            shared["host_status"] = {
                "mode": host_status.get("mode"),
                "paper_trading": host_status.get("paper_trading"),
                "trading_stack_connected": host_status.get("trading_stack_connected"),
            }
            push_result = push_brain(host, shared)
            if push_result and push_result.get("ok"):
                route = "ONLINE"
            else:
                route = "OFFLINE"
        else:
            route = "OFFLINE"

    shared["route"] = route
    shared["teaka_host"] = host
    write_json(shared_path, shared)
    # Keep master stamp in sync without losing local identity fields.
    master["memory"] = {
        "last_confirmed": shared["synced_at"],
        "status": f"synced_to_{SHARED_NAME}",
        "route": route,
    }
    write_json(master_path, master)

    log(f"BRAIN_SYNCED: {MASTER_NAME} -> {SHARED_NAME} route={route}")
    return {
        "documents": str(documents),
        "master": str(master_path),
        "shared": str(shared_path),
        "route": route,
        "host": host,
        "host_status": host_status,
        "push_result": push_result,
    }


def main() -> dict:
    result = sync_brains(resolve_documents())
    # Small settle so Pythonista console shows the full boot sequence.
    time.sleep(0.05)
    print(json.dumps({k: v for k, v in result.items() if k != "host_status"}, indent=2))
    return result


if __name__ == "__main__":
    main()
    sys.exit(0)
