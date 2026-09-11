import json
import os
import sys
from pathlib import Path

candidates = [
    Path("ev_virtual_brain.json"),
    Path(r"D:\EV_Files\ev_viral_brain.json"),
    Path(r"D:\EV_Files\EVBot_runtime\EchoVault\daemon_brain.json"),
    Path(r"D:\EV_Files\ev_virtual_brain.json"),
    Path(r"C:\EV_Files\ev_viral_brain.json"),
    Path(r"C:\EV_Files\EVBot_runtime\EchoVault\daemon_brain.json"),
    Path(r"C:\EV_Files\ev_virtual_brain.json"),
    Path(r"C:\Users\Blair\EV_Git\Ev\brain\EV_CHAT_STATE_20260607.json"),
    Path(r"C:\Users\Blair\EV_Git\Ev\brain\EV_FuzzyBrain_State.json"),
    Path(r"E:\EV_Files\ev_virtual_brain.json"),
]

target_path = next((p for p in candidates if p.is_file()), None)

if not target_path:
    print("❌ No EV Brain candidate file found on disk.")
    sys.exit(1)

try:
    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("✅ JSON is valid from:", target_path)
    print("   Top-level keys:", list(data.keys())[:7])
except Exception as e:
    print(f"❌ JSON parse error for {target_path}:", e)
    sys.exit(1)
