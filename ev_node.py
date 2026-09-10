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
    brain_path: str = "C:/EV_AI/Cursor/Memory/EV_MEMORY.json"
    fallback_brain_paths: tuple[str, ...] = (
        "C:/EV_AI/Cursor/Memory/EV_MEMORY.json",
        "E:/EV_Files/ev_virtual_brain.json",
        "D:/EV_Files/ev_virtual_brain.json",
        "ev_virtual_brain.json",
    )
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
        """Load and parse the active EV Memory / Virtual Brain specification."""
        paths_to_try = [custom_path] if custom_path else [self.config.brain_path, *self.config.fallback_brain_paths]

        for p_str in paths_to_try:
            if not p_str:
                continue
            path = Path(p_str)
            if not path.is_file():
                candidate = Path(__file__).resolve().parent / p_str
                if candidate.is_file():
                    path = candidate
                else:
                    continue

            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._brain_cache = data
                    return data
            except Exception as err:
                return {
                    "error": f"Failed to parse brain file at {path}: {err}",
                    "linked": False,
                    "ev_identity": "EV Virtual Brain (Corrupted)",
                }

        return {
            "error": "No brain/memory file found across configured paths",
            "linked": False,
            "ev_identity": "EV Virtual Brain (Offline)",
        }

    def verify_brain_link(self) -> dict:
        """Verify the health and linkage of EV Virtual Brain / EV Memory."""
        brain = self.load_virtual_brain()
        # Support both ev_virtual_brain.json and EV_MEMORY.json schemas
        is_linked = brain.get("linked", False) or "error" not in brain
        phase = brain.get("phase", brain.get("version", "Active"))
        identity = brain.get("ev_identity", brain.get("system", "EV Cloud Core / Memory"))
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
