from __future__ import annotations

import os
import unittest
import uuid
from pathlib import Path

from paper_broker import PaperBroker, PaperConfig


class PaperBrokerTests(unittest.TestCase):
    def setUp(self) -> None:
        artifact_root = Path(
            os.environ.get(
                "TEAKA_TEST_ARTIFACT_ROOT",
                Path(__file__).resolve().parent / "state" / "test-artifacts",
            )
        )
        self.artifact_dir = artifact_root / f"existing-{uuid.uuid4().hex}"
        self.artifact_dir.mkdir(parents=True, exist_ok=False)
        self.log = self.artifact_dir / "fills.jsonl"
        self.config = PaperConfig(
            initial_cash=10_000,
            max_order_notional=2_000,
            max_position_pct=0.50,
            max_drawdown_pct=0.10,
            fee_bps=10,
            slippage_bps=5,
            allowed_symbols=("BTC-USDT",),
        )

    def test_buy_and_sell_are_virtual(self) -> None:
        broker = PaperBroker(self.config, self.log)
        buy = broker.submit_market_order("BTC-USDT", "BUY", 0.01, 50_000, "test")
        self.assertEqual(buy.status, "FILLED")
        sell = broker.submit_market_order("BTC-USDT", "SELL", 0.01, 51_000, "test")
        self.assertEqual(sell.status, "FILLED")
        self.assertEqual(broker.positions["BTC-USDT"].quantity, 0.0)
        self.assertTrue(self.log.exists())
        self.assertFalse(broker.snapshot()["live_order_routes"])

    def test_max_order_notional_rejects(self) -> None:
        broker = PaperBroker(self.config)
        fill = broker.submit_market_order("BTC-USDT", "BUY", 1, 50_000)
        self.assertEqual((fill.status, fill.reason), ("REJECTED", "max_order_notional"))

    def test_shorting_is_disabled(self) -> None:
        broker = PaperBroker(self.config)
        fill = broker.submit_market_order("BTC-USDT", "SELL", 0.01, 50_000)
        self.assertEqual((fill.status, fill.reason), ("REJECTED", "shorting_disabled"))

    def test_drawdown_trips_kill_switch(self) -> None:
        broker = PaperBroker(self.config)
        fill = broker.submit_market_order("BTC-USDT", "BUY", 0.11, 10_000)
        self.assertEqual(fill.status, "FILLED")
        broker.mark("BTC-USDT", 1)
        self.assertTrue(broker.kill_switch)
        blocked = broker.submit_market_order("BTC-USDT", "BUY", 0.01, 1)
        self.assertEqual(
            (blocked.status, blocked.reason),
            ("REJECTED", "kill_switch_active"),
        )


if __name__ == "__main__":
    unittest.main()
