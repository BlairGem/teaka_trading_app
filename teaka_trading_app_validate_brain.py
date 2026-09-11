import json
import os
import sys
from pathlib import Path

candidates = [
    Path("ev_virtual_brain.json"),
    Path(os.environ.get("TEAKA_BRAIN_FILE", "")),
    Path(os.environ.get("EV_Files", r"C:\EV_Files")) / "ev_virtual_brain.json",
    Path(r"C:\EV_Files\ev_virtual_brain.json"),
]

path = next((p for p in candidates if p and p.is_file()), Path(r"C:\EV_Files\ev_virtual_brain.json"))

try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("✅ JSON is valid. Top‐level keys:", list(data.keys())[:5])
    print("Path:", path)
except Exception as e:
    print("❌ JSON parse error:", e)
    sys.exit(1)
