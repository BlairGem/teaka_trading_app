# Creates / updates validate_brain.py against the EV virtual brain JSON.
$target = Join-Path $PSScriptRoot "..\teaka_trading_app_validate_brain.py"
if (-not (Test-Path (Split-Path $target -Parent))) {
  $target = "C:\EV_Files\teaka_trading_app\teaka_trading_app_validate_brain.py"
}

@'
import json
import os
import sys
from pathlib import Path

candidates = [
    Path("ev_virtual_brain.json"),
    Path(os.environ.get("TEAKA_BRAIN_FILE", "")),
    Path(os.environ.get("EV_Files", r"C:\EV_Files")) / "ev_virtual_brain.json",
    Path(r"C:\EV_Files\ev_virtual_brain.json"),
    Path.home() / "EV_Link" / "ev_virtual_brain.json",
]

path = next((p for p in candidates if p.is_file()), None)
if path is None:
    print("Brain file not found")
    sys.exit(1)

try:
    data = json.loads(path.read_text(encoding="utf-8"))
    print("JSON is valid. Top-level keys:", list(data.keys())[:5])
    print("Path:", path)
except Exception as exc:
    print("JSON parse error:", exc)
    sys.exit(1)
'@ | Set-Content -LiteralPath $target -Encoding UTF8

Write-Host "Created or updated: $target" -ForegroundColor Green
