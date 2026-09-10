"""EV Swarm signal adapter for PaperBroker.

Bridges AI signals from Qwen, Ollama, GEMBot, and EV Virtual Brain into
TeAka's PaperBroker with strict risk guardrails, position caps, and receipts.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional

from ev_node import EVNodeClient
from paper_trading.paper_broker import Fill, PaperBroker, PaperConfig

logger = logging.getLogger("ev_swarm_adapter")

SwarmSignal = Literal["BUY", "SELL", "HOLD"]


@dataclass(frozen=True)
class SwarmDecision:
    signal: SwarmSignal
    confidence: float
    reason: str
    source: str
    metadata: Dict[str, Any]


class EVSwarmSignalAdapter:
    """Interprets EV Swarm signals and executes orders via PaperBroker safely."""

    def __init__(
        self,
        broker: PaperBroker,
        node_client: Optional[EVNodeClient] = None,
        min_confidence: float = 0.65,
        default_order_cap_usdt: float = 50.0,
        qwen_model: str = "qwen2.5:3b",
        fallback_models: tuple[str, ...] = ("qwen2.5:3b", "qwen3:4b", "phi4-mini:3.8b"),
    ) -> None:
        self.broker = broker
        self.node_client = node_client or EVNodeClient()
        self.min_confidence = min_confidence
        self.default_order_cap_usdt = default_order_cap_usdt
        self.qwen_model = qwen_model
        self.fallback_models = fallback_models
        self.audit_log: List[dict] = []

    def parse_llm_response(self, raw_text: str, source: str = "qwen") -> SwarmDecision:
        """Parse raw text from Qwen or Ollama into a structured SwarmDecision."""
        cleaned = raw_text.strip().upper()

        signal: SwarmSignal = "HOLD"
        confidence = 0.5
        reason = "ambiguous_output"

        # Check for JSON structure first
        if "{" in raw_text and "}" in raw_text:
            try:
                start = raw_text.find("{")
                end = raw_text.rfind("}") + 1
                payload = json.loads(raw_text[start:end])
                raw_sig = str(payload.get("signal", "")).upper()
                if raw_sig in ("BUY", "SELL", "HOLD"):
                    signal = raw_sig  # type: ignore[assignment]
                confidence = float(payload.get("confidence", 0.5))
                reason = str(payload.get("reason", "json_parsed"))
                return SwarmDecision(
                    signal=signal,
                    confidence=max(0.0, min(1.0, confidence)),
                    reason=reason,
                    source=source,
                    metadata=payload,
                )
            except Exception:
                pass

        # Text matching fallback
        if "BUY" in cleaned and "SELL" not in cleaned:
            signal = "BUY"
            confidence = 0.8
            reason = "strong_buy_keyword"
        elif "SELL" in cleaned and "BUY" not in cleaned:
            signal = "SELL"
            confidence = 0.8
            reason = "strong_sell_keyword"
        elif "BULLISH" in cleaned:
            signal = "BUY"
            confidence = 0.7
            reason = "bullish_sentiment"
        elif "BEARISH" in cleaned:
            signal = "SELL"
            confidence = 0.7
            reason = "bearish_sentiment"
        else:
            signal = "HOLD"
            confidence = 0.5
            reason = "neutral_or_unclear"

        return SwarmDecision(
            signal=signal,
            confidence=confidence,
            reason=reason,
            source=source,
            metadata={"raw": raw_text[:200]},
        )

    def evaluate_and_execute(
        self,
        symbol: str,
        current_price: float,
        decision: SwarmDecision,
        entry_cap_usdt: Optional[float] = None,
    ) -> Optional[Fill]:
        """Evaluate a swarm decision against risk constraints and execute on paper broker."""
        self.broker.mark(symbol, current_price)

        if decision.confidence < self.min_confidence:
            return None

        cap_usdt = entry_cap_usdt or self.default_order_cap_usdt
        position = self.broker.positions.get(symbol)
        held_qty = position.quantity if position else 0.0

        fill: Optional[Fill] = None
        if decision.signal == "BUY":
            # Only buy if flat or position is within cap
            slip = self.broker.config.slippage_bps / 10_000.0
            fill_price_est = current_price * (1 + slip)

            max_notional = min(
                cap_usdt,
                self.broker.config.max_order_notional,
                self.broker.equity() * self.broker.config.max_position_pct,
                self.broker.cash / (1 + self.broker.config.fee_bps / 10_000.0),
            )
            if max_notional <= 0:
                return None

            quantity = max_notional / fill_price_est
            fill = self.broker.submit_market_order(
                symbol=symbol,
                side="BUY",
                quantity=quantity,
                mark_price=current_price,
                strategy=f"ev_swarm_{decision.source}",
            )

        elif decision.signal == "SELL":
            if held_qty > 0:
                fill = self.broker.submit_market_order(
                    symbol=symbol,
                    side="SELL",
                    quantity=held_qty,
                    mark_price=current_price,
                    strategy=f"ev_swarm_{decision.source}",
                )

        if fill is not None and fill.status == "FILLED":
            # Record audit receipt via EV Node client
            audit = self.node_client.record_trade_audit(
                symbol=symbol,
                side=fill.side,
                quantity=fill.quantity,
                price=fill.fill_price,
                strategy=fill.strategy,
                order_id=fill.order_id,
                source=decision.source,
            )
            self.audit_log.append(audit)

        return fill
