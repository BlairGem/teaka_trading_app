from __future__ import annotations

import json
import os
import unittest
import uuid
from pathlib import Path

from paper_trading.paper_broker import PaperBroker, PaperConfig, load_config


def accounting_config(**overrides: object) -> PaperConfig:
    values: dict[str, object] = {
        "initial_cash": 10_000,
        "max_order_notional": 10_000,
        "max_position_pct": 1.0,
        "max_drawdown_pct": 0.15,
        "fee_bps": 10,
        "slippage_bps": 0,
        "allowed_symbols": ("BTC-USDT",),
    }
    values.update(overrides)
    return PaperConfig(**values)


class PaperAccountingTests(unittest.TestCase):
    def test_round_trip_charges_each_fee_once_in_cash_and_realized_pnl(self) -> None:
        broker = PaperBroker(accounting_config())

        broker.submit_market_order("BTC-USDT", "BUY", 1, 100)
        broker.submit_market_order("BTC-USDT", "SELL", 1, 100)

        self.assertAlmostEqual(broker.cash, 9_999.8)
        self.assertAlmostEqual(broker.positions["BTC-USDT"].realized_pnl, -0.2)

    def test_multiple_entries_and_partial_exits_reconcile_realized_pnl(self) -> None:
        broker = PaperBroker(accounting_config())

        broker.submit_market_order("BTC-USDT", "BUY", 1, 100)
        broker.submit_market_order("BTC-USDT", "BUY", 1, 200)
        broker.submit_market_order("BTC-USDT", "SELL", 1, 180)

        position = broker.positions["BTC-USDT"]
        self.assertAlmostEqual(position.quantity, 1)
        self.assertAlmostEqual(position.average_cost, 150.15)
        self.assertAlmostEqual(position.realized_pnl, 29.67)

        broker.submit_market_order("BTC-USDT", "SELL", 1, 150)

        self.assertAlmostEqual(broker.cash, 10_029.37)
        self.assertAlmostEqual(position.realized_pnl, 29.37)

    def test_kill_switch_blocks_new_buy(self) -> None:
        broker = self._broker_with_drawdown()

        fill = broker.submit_market_order("BTC-USDT", "BUY", 1, 1)

        self.assertEqual((fill.status, fill.reason), ("REJECTED", "kill_switch_active"))
        self.assertAlmostEqual(broker.positions["BTC-USDT"].quantity, 1)

    def test_kill_switch_permits_held_quantity_sell(self) -> None:
        broker = self._broker_with_drawdown()

        fill = broker.submit_market_order("BTC-USDT", "SELL", 1, 1)

        self.assertEqual(fill.status, "FILLED")
        self.assertAlmostEqual(broker.positions["BTC-USDT"].quantity, 0)

    def test_kill_switch_rejects_oversized_sell_without_short(self) -> None:
        broker = self._broker_with_drawdown()

        fill = broker.submit_market_order("BTC-USDT", "SELL", 2, 1)

        self.assertEqual((fill.status, fill.reason), ("REJECTED", "shorting_disabled"))
        self.assertAlmostEqual(broker.positions["BTC-USDT"].quantity, 1)

    def test_order_cap_blocks_new_exposure_but_permits_held_exit(self) -> None:
        config = accounting_config(
            max_order_notional=100,
            max_drawdown_pct=0.005,
            fee_bps=0,
        )
        broker = PaperBroker(config)
        broker.submit_market_order("BTC-USDT", "BUY", 1, 100)
        broker.mark("BTC-USDT", 200)
        broker.mark("BTC-USDT", 1)
        self.assertTrue(broker.kill_switch)

        sell = broker.submit_market_order("BTC-USDT", "SELL", 1, 200)

        self.assertEqual(sell.status, "FILLED")
        self.assertAlmostEqual(broker.positions["BTC-USDT"].quantity, 0)

        fresh_broker = PaperBroker(config)
        buy = fresh_broker.submit_market_order("BTC-USDT", "BUY", 1, 200)
        self.assertEqual((buy.status, buy.reason), ("REJECTED", "max_order_notional"))

    def test_nonfinite_config_values_are_rejected(self) -> None:
        cases = {
            "initial_cash": float("inf"),
            "max_order_notional": float("nan"),
            "max_position_pct": float("inf"),
            "max_drawdown_pct": float("nan"),
            "fee_bps": float("inf"),
            "slippage_bps": float("nan"),
        }
        for field, invalid in cases.items():
            with self.subTest(field=field):
                with self.assertRaises((TypeError, ValueError)):
                    PaperBroker(accounting_config(**{field: invalid}))

    def test_config_numeric_bounds_are_rejected(self) -> None:
        cases = (
            ("initial_cash", 0),
            ("max_order_notional", 0),
            ("max_position_pct", 0),
            ("max_position_pct", 1.01),
            ("max_drawdown_pct", 0),
            ("max_drawdown_pct", 1.01),
            ("fee_bps", -0.01),
            ("slippage_bps", -0.01),
            ("slippage_bps", 10_000),
        )
        for field, invalid in cases:
            with self.subTest(field=field, invalid=invalid):
                with self.assertRaises((TypeError, ValueError)):
                    PaperBroker(accounting_config(**{field: invalid}))

    def test_invalid_allowed_symbols_are_rejected(self) -> None:
        for symbols in ((), ("",), ("BTC-USDT", " "), ("BTC-USDT", 7)):
            with self.subTest(symbols=symbols):
                with self.assertRaises((TypeError, ValueError)):
                    PaperBroker(accounting_config(allowed_symbols=symbols))

    def test_allow_shorting_is_explicitly_rejected(self) -> None:
        with self.assertRaises((TypeError, ValueError)):
            PaperBroker(accounting_config(allow_shorting=True))

    def test_load_config_rejects_unsupported_shorting(self) -> None:
        artifact_root = Path(os.environ["TEAKA_TEST_ARTIFACT_ROOT"])
        case_dir = artifact_root / f"load-config-{uuid.uuid4().hex}"
        case_dir.mkdir(exist_ok=False)
        config_path = case_dir / "config.json"
        config_path.write_text(json.dumps({"allow_shorting": True}), encoding="utf-8")

        with self.assertRaises((TypeError, ValueError)):
            load_config(config_path)

    def test_load_config_rejects_string_allowed_symbols(self) -> None:
        artifact_root = Path(os.environ["TEAKA_TEST_ARTIFACT_ROOT"])
        case_dir = artifact_root / f"load-config-{uuid.uuid4().hex}"
        case_dir.mkdir(exist_ok=False)
        config_path = case_dir / "config.json"
        config_path.write_text(
            json.dumps({"allowed_symbols": "BTC-USDT"}),
            encoding="utf-8",
        )

        with self.assertRaises((TypeError, ValueError)):
            load_config(config_path)

    @staticmethod
    def _broker_with_drawdown() -> PaperBroker:
        broker = PaperBroker(accounting_config(max_drawdown_pct=0.005))
        buy = broker.submit_market_order("BTC-USDT", "BUY", 1, 100)
        if buy.status != "FILLED":
            raise AssertionError(f"test setup buy rejected: {buy.reason}")
        broker.mark("BTC-USDT", 1)
        if not broker.kill_switch:
            raise AssertionError("test setup did not trip kill switch")
        return broker


if __name__ == "__main__":
    unittest.main()
