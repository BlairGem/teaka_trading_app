#!/usr/bin/env bash
# Start the paper-safe TeAka Python bridge for the Cloud Agent dev environment.
#
# Binds 0.0.0.0:5050 and stays attached (foreground). Live exchange order gates
# stay disabled unless explicitly overridden in the environment.
#
# The dashboard-managed Cloud Agent environment runs the equivalent command as
# its `start` step:
#     python3 connect_python.py
set -euo pipefail

cd "$(dirname "$0")/.."

export TEAKA_MODE="${TEAKA_MODE:-paper}"
export LIVE_TRADING_ENABLED="${LIVE_TRADING_ENABLED:-false}"
export PRIVATE_EXCHANGE_API_ENABLED="${PRIVATE_EXCHANGE_API_ENABLED:-false}"

exec python3 connect_python.py
