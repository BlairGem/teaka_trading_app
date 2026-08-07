"""
TeAka / EVBot lore script for Pythonista (phone-first).

Add this to your lore boot so EVBot does not depend on PC-only Waitress.
PC bridge is optional: ONLINE if reachable, otherwise local lore OFFLINE.

Pythonista usage (paste into your lore script or run alone):

    import os
    os.environ["TEAKA_HOST"] = "http://<pc-lan-ip>:5050"  # optional
    os.environ["ROUTE_MODE"] = "AUTO"
    import lore_script
    lore_script.main()
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pythonista_boot as boot


LORE_NAME = "evbot_lore_state.json"


def _host() -> str:
    return os.environ.get("TEAKA_HOST", "http://127.0.0.1:5050").rstrip("/")


def _post(path: str, body: dict, timeout: float = 8.0) -> dict | None:
    req = urllib.request.Request(
        _host() + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def write_lore(documents: Path, route: str, extra: dict | None = None) -> Path:
    path = documents / LORE_NAME
    payload = {
        "script": "lore_script.py",
        "route": route,
        "teaka_host": _host(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "evbot": {
            "online": route == "ONLINE",
            "mode": "paper",
            "local_ready": True,
            "note": (
                "Synced to PC bridge"
                if route == "ONLINE"
                else "PC not required — local lore active on phone"
            ),
        },
    }
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> dict:
    # 1) Always run Sentinel brain sync (works OFFLINE).
    result = boot.sync_brains(boot.resolve_documents())
    documents = Path(result["documents"])
    route = result.get("route") or "OFFLINE"

    # 2) If ONLINE, also ask bridge to start EVBot.
    evbot_start = None
    if route == "ONLINE":
        evbot_start = _post("/api/evbot/start", {"source": "pythonista_lore"})
        boot.log(
            "EVBOT_START: "
            + ("ok" if evbot_start and evbot_start.get("ok") else "failed_or_skipped")
        )

    lore_path = write_lore(
        documents,
        route,
        {"evbot_start": evbot_start, "boot": {"shared": result.get("shared")}},
    )
    boot.log(f"LORE_READY: {lore_path.name} local_ready=true route={route}")

    out = {
        "documents": str(documents),
        "route": route,
        "lore": str(lore_path),
        "evbot_start": evbot_start,
        "scriptable": "phone/Scriptable_EVBot_Lore.js",
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
