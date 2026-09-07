#!/usr/bin/env bash
# Idempotent bootstrap for the TeAka Cloud Agent dev environment.
#
# Installs the minimal, paper-safe runtime dependencies (Flask, per
# requirements.txt) into the user site so `python3 connect_python.py` and the
# paper-trading tools run out of the box. Safe to re-run.
#
# The dashboard-managed Cloud Agent environment runs the equivalent command as
# its `install` step:
#     python3 -m pip install --user -r requirements.txt
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m pip install --user --upgrade-strategy only-if-needed -r requirements.txt

echo "cloud_agent_install: dependencies ready in $(python3 -m site --user-site)"
