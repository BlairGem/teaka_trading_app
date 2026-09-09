from __future__ import annotations

import unittest
from ev_node import EVNodeClient, EVNodeConfig
from paper_trading.paper_broker import PaperBroker, PaperConfig
from paper_trading.ev_swarm_adapter import EVSwarmSignalAdapter, SwarmDecision


class EVSwarmAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.broker_config = PaperConfig(
            initial_cash=10_000.0,
            max_order_notional=100.0,
            max_position_pct=0.10,
            fee_bps=10.0,
            slippage_bps=5.0,
            allowed_symbols=("BTC-USDT",),
        )
        self.broker = PaperBroker(self.broker_config)
        self.node_client = EVNodeClient(EVNodeConfig(mock_mode=True))
        self.adapter = EVSwarmSignalAdapter(
            broker=self.broker,
            node_client=self.node_client,
            min_confidence=0.60,
            default_order_cap_usdt=50.0,
            qwen_model="qwen2.5:3b",
        )

    def test_ev_node_client_status_and_brain(self) -> None:
        status = self.node_client.get_status()
        self.assertEqual(status["node_status"], "online")
        self.assertEqual(status["mode"], "mock")

        brain = self.node_client.load_virtual_brain("ev_virtual_brain.json")
        self.assertEqual(brain.get("ev_identity"), "EV Cloud Core")
        self.assertTrue(brain.get("linked"))

        verify = self.node_client.verify_brain_link()
        self.assertTrue(verify["verified"])
        self.assertEqual(verify["status"], "ready")

    def test_llm_response_parsing(self) -> None:
        # Test JSON parsing
        json_resp = 'Analysis: {"signal": "BUY", "confidence": 0.85, "reason": "Moving average cross"}'
        dec1 = self.adapter.parse_llm_response(json_resp, source="qwen")
        self.assertEqual(dec1.signal, "BUY")
        self.assertEqual(dec1.confidence, 0.85)
        self.assertEqual(dec1.reason, "Moving average cross")

        # Test text keyword parsing
        dec2 = self.adapter.parse_llm_response("We should definitely BUY now with volume.", source="ollama")
        self.assertEqual(dec2.signal, "BUY")
        self.assertGreaterEqual(dec2.confidence, 0.7)

        # Test ambiguous text
        dec3 = self.adapter.parse_llm_response("The market is consolidating with mixed signals.", source="gembot")
        self.assertEqual(dec3.signal, "HOLD")

    def test_swarm_buy_and_sell_cycle(self) -> None:
        # Buy signal
        buy_dec = SwarmDecision(
            signal="BUY",
            confidence=0.90,
            reason="Qwen 30B breakout confirmation",
            source="qwen_model",
            metadata={},
        )
        fill_buy = self.adapter.evaluate_and_execute("BTC-USDT", 80_000.0, buy_dec)
        self.assertIsNotNone(fill_buy)
        self.assertEqual(fill_buy.status, "FILLED")
        self.assertEqual(fill_buy.side, "BUY")
        self.assertLessEqual(fill_buy.notional, 50.0 + 1e-4)

        # Position should exist
        pos = self.broker.positions["BTC-USDT"]
        self.assertGreater(pos.quantity, 0.0)

        # Audit receipt should be generated
        self.assertEqual(len(self.adapter.audit_log), 1)
        receipt = self.adapter.audit_log[0]
        self.assertIn("receipt_hash", receipt)
        self.assertEqual(receipt["source"], "qwen_model")

        # Low confidence signal should be ignored
        low_conf = SwarmDecision(signal="SELL", confidence=0.4, reason="low", source="qwen", metadata={})
        self.assertIsNone(self.adapter.evaluate_and_execute("BTC-USDT", 81_000.0, low_conf))
        self.assertGreater(self.broker.positions["BTC-USDT"].quantity, 0.0)

        # High confidence sell signal should close position
        sell_dec = SwarmDecision(signal="SELL", confidence=0.85, reason="Target reached", source="qwen", metadata={})
        fill_sell = self.adapter.evaluate_and_execute("BTC-USDT", 82_000.0, sell_dec)
        self.assertIsNotNone(fill_sell)
        self.assertEqual(fill_sell.status, "FILLED")
        self.assertEqual(fill_sell.side, "SELL")
        self.assertEqual(self.broker.positions["BTC-USDT"].quantity, 0.0)
        self.assertEqual(len(self.adapter.audit_log), 2)


if __name__ == "__main__":
    unittest.main()
