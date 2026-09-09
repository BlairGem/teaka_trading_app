"""EV Node and EV Stack adapter for TeAka trading application.

Provides interface to EV Node / EV Stack framework RPC, EV Virtual Brain,
and verifiable cryptographic audit receipts for paper trading.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import urllib.request
import urllib.error


@dataclass(frozen=True)
class EVNodeConfig:
    rpc_url: str = "http://127.0.0.1:26657"
    brain_path: str = "ev_virtual_brain.json"
    timeout_seconds: float = 3.0
    mock_mode: bool = False
    chain_id: str = "ev-stack-main-1"


class EVNodeClient:
    """Client for interacting with EV Node / EV Stack framework and EV Brain."""

    def __init__(
        self,
        config: Optional[EVNodeConfig] = None,
        http_get: Optional[Callable[[str], dict]] = None,
    ) -> None:
        self.config = config or EVNodeConfig()
        self._http_get = http_get or self._default_http_get
        self._brain_cache: Optional[Dict[str, Any]] = None

    def _default_http_get(self, url: str) -> dict:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "TeAka-EVNode-Client/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)

    def get_status(self) -> dict:
        """Query EV Node RPC status, or return mock/fallback status when unreachable."""
        if self.config.mock_mode:
            return {
                "node_status": "online",
                "mode": "mock",
                "chain_id": self.config.chain_id,
                "latest_block_height": 104250,
                "syncing": False,
                "da_layer": "active",
            }
        try:
            status_url = f"{self.config.rpc_url.rstrip('/')}/status"
            res = self._http_get(status_url)
            return {
                "node_status": "online",
                "mode": "live_rpc",
                "raw": res,
                "chain_id": res.get("result", {}).get("node_info", {}).get("network", self.config.chain_id),
                "syncing": res.get("result", {}).get("sync_info", {}).get("catching_up", False),
            }
        except Exception as err:
            return {
                "node_status": "unreachable",
                "mode": "disconnected",
                "error": str(err),
                "chain_id": self.config.chain_id,
                "syncing": False,
            }

    def load_virtual_brain(self, custom_path: Optional[str] = None) -> dict:
        """Load and parse the EV Virtual Brain specification."""
        path_str = custom_path or self.config.brain_path
        path = Path(path_str)
        if not path.is_file():
            # Try looking relative to workspace or repository root
            candidate = Path(__file__).resolve().parent / path_str
            if candidate.is_file():
                path = candidate
            else:
                return {
                    "error": f"Brain file not found at {path_str}",
                    "linked": False,
                    "ev_identity": "EV Virtual Brain (Offline)",
                }

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self._brain_cache = data
                return data
        except Exception as err:
            return {
                "error": f"Failed to parse brain file: {err}",
                "linked": False,
                "ev_identity": "EV Virtual Brain (Corrupted)",
            }

    def verify_brain_link(self) -> dict:
        """Verify the health and linkage of EV Virtual Brain."""
        brain = self.load_virtual_brain()
        is_linked = brain.get("linked", False)
        phase = brain.get("phase", "Unknown")
        identity = brain.get("ev_identity", "EV Cloud Core")
        runtime = brain.get("runtime", {})

        return {
            "verified": is_linked,
            "identity": identity,
            "phase": phase,
            "runtime_flags": runtime,
            "status": "ready" if is_linked else "degraded",
        }

    @staticmethod
    def generate_receipt_hash(receipt_data: dict) -> str:
        """Compute SHA-256 fingerprint for a trade execution receipt."""
        serialized = json.dumps(receipt_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def record_trade_audit(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        strategy: str,
        order_id: str,
        source: str = "ev_swarm",
    ) -> dict:
        """Generate a cryptographically stamped audit receipt for paper trading."""
        receipt = {
            "chain_id": self.config.chain_id,
            "timestamp": time.time(),
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "strategy": strategy,
            "source": source,
            "brain_identity": (self._brain_cache or {}).get("ev_identity", "EV Cloud Core"),
        }
        receipt["receipt_hash"] = self.generate_receipt_hash(receipt)
        return receipt
