from __future__ import annotations

import unittest
import sys
from types import SimpleNamespace


class PositionSizingTests(unittest.TestCase):
    def test_risk_budget_divided_by_price_distance_returns_asset_units(self) -> None:
        from trading_stack.risk_management import calculate_position_size

        self.assertEqual(calculate_position_size(10_000, 100, 98, 1), 50)

    def test_invalid_or_out_of_range_sizing_inputs_fail_closed(self) -> None:
        from trading_stack.risk_management import calculate_position_size

        cases = (
            (float("nan"), 100, 98, 1),
            (10_000, float("inf"), 98, 1),
            (10_000, 100, 100, 1),
            (10_000, 100, 98, 0),
            (10_000, 100, 98, 101),
        )
        for values in cases:
            with self.subTest(values=values):
                self.assertEqual(calculate_position_size(*values), 0.0)


class StrategyNormalizationTests(unittest.TestCase):
    def test_editor_arrays_become_keyed_indicators_and_stable_conditions(self) -> None:
        from trading_stack.strategy_contracts import normalize_strategy_contract

        indicators = [
            {"type": "SMA", "parameters": {"period": 3}, "id": 101},
            {"type": "RSI", "parameters": {"period": 2}, "id": 202},
        ]
        conditions = [
            {"indicator": "sma_101", "operator": ">", "value": 2, "side": "buy"},
            {
                "indicator": "rsi_202",
                "operator": "<=",
                "value": 70,
                "signal_type": "SELL",
            },
        ]

        keyed, normalized = normalize_strategy_contract(indicators, conditions)

        self.assertEqual(keyed, {"sma": {"period": 3}, "rsi": {"period": 2}})
        self.assertEqual(
            normalized,
            [
                {
                    "indicator": "sma_3",
                    "operator": "above",
                    "value": 2.0,
                    "signal_type": "BUY",
                },
                {
                    "indicator": "rsi_2",
                    "operator": "below_or_equal",
                    "value": 70.0,
                    "signal_type": "SELL",
                },
            ],
        )

    def test_condition_without_side_is_rejected(self) -> None:
        from trading_stack.strategy_contracts import (
            StrategyContractError,
            normalize_strategy_contract,
        )

        with self.assertRaises(StrategyContractError):
            normalize_strategy_contract(
                {"sma": {"period": 3}},
                [{"indicator": "sma", "operator": ">", "value": 2}],
            )

    def test_conflicting_side_fields_are_rejected(self) -> None:
        from trading_stack.strategy_contracts import (
            StrategyContractError,
            normalize_strategy_contract,
        )

        with self.assertRaises(StrategyContractError):
            normalize_strategy_contract(
                {"sma": {"period": 3}},
                [
                    {
                        "indicator": "sma",
                        "operator": ">",
                        "value": 2,
                        "side": "BUY",
                        "signal_type": "SELL",
                    }
                ],
            )

    def test_duplicate_indicator_types_and_unknown_references_are_rejected(self) -> None:
        from trading_stack.strategy_contracts import (
            StrategyContractError,
            normalize_strategy_contract,
        )

        with self.assertRaises(StrategyContractError):
            normalize_strategy_contract(
                [
                    {"type": "SMA", "parameters": {"period": 3}, "id": 1},
                    {"type": "SMA", "parameters": {"period": 5}, "id": 2},
                ],
                [],
            )
        with self.assertRaises(StrategyContractError):
            normalize_strategy_contract(
                {"sma": {"period": 3}},
                [
                    {
                        "indicator": "ema_999",
                        "operator": ">",
                        "value": 2,
                        "side": "BUY",
                    }
                ],
            )


class TechnicalIndicatorTests(unittest.TestCase):
    @staticmethod
    def _candles():
        import pandas as pd

        return pd.DataFrame(
            {
                "open": [1, 2, 3, 4, 5],
                "high": [2, 3, 4, 5, 6],
                "low": [0, 1, 2, 3, 4],
                "close": [1, 2, 3, 4, 5],
                "volume": [10, 11, 12, 13, 14],
            }
        )

    def test_pandas_indicators_are_deterministic_without_optional_backends(self) -> None:
        from trading_stack.technical_indicators import apply_indicators

        result = apply_indicators(
            self._candles(),
            {
                "sma": {"period": 3},
                "ema": {"period": 3},
                "rsi": {"period": 3},
                "macd": {"fast_period": 2, "slow_period": 3, "signal_period": 2},
            },
        )

        self.assertAlmostEqual(result["sma_3"].iloc[-1], 4.0)
        self.assertAlmostEqual(result["ema_3"].iloc[-1], 4.0625)
        self.assertAlmostEqual(result["rsi_3"].iloc[-1], 100.0)
        self.assertAlmostEqual(result["macd"].iloc[-1], 0.4436728395)
        self.assertAlmostEqual(result["macd_signal"].iloc[-1], 0.4099794239)
        self.assertAlmostEqual(result["macd_hist"].iloc[-1], 0.0336934156)

    def test_editor_indicator_array_is_accepted_by_apply_indicators(self) -> None:
        from trading_stack.technical_indicators import apply_indicators

        result = apply_indicators(
            self._candles(),
            [{"type": "SMA", "parameters": {"period": 3}, "id": 101}],
        )

        self.assertEqual(result["sma_3"].iloc[-1], 4.0)

    def test_import_does_not_initialize_talib_or_matlab(self) -> None:
        sys.modules.pop("talib", None)
        sys.modules.pop("matlab_integration", None)
        sys.modules.pop("trading_stack.technical_indicators", None)

        __import__("trading_stack.technical_indicators")

        self.assertNotIn("talib", sys.modules)
        self.assertNotIn("matlab_integration", sys.modules)

    def test_disabled_optional_indicator_backend_fails_explicitly(self) -> None:
        from trading_stack.technical_indicators import (
            IndicatorUnavailableError,
            calculate_indicator,
        )

        with self.assertRaises(IndicatorUnavailableError):
            calculate_indicator(self._candles(), "wma", {}, optional_backend=False)


class _Strategy:
    id = 7
    user_id = 11
    timeframe = "1h"
    stop_loss_pct = 2
    take_profit_pct = 4
    use_ml_model = False
    ml_model_id = None

    def __init__(self, indicators, conditions):
        self._indicators = indicators
        self._conditions = conditions

    def get_indicators_config(self):
        return self._indicators

    def get_entry_conditions(self):
        return self._conditions

    def get_trading_pairs(self):
        return ["BTC/USDT"]


class _Signal(SimpleNamespace):
    def set_signal_data(self, value):
        self.signal_data = value


class SignalGenerationTests(unittest.TestCase):
    @staticmethod
    def _candles(**extra):
        import pandas as pd

        values = {
            "open": [109.0, 101.0],
            "high": [111.0, 102.0],
            "low": [108.0, 99.0],
            "close": [110.0, 100.0],
            "volume": [12.0, 13.0],
        }
        values.update(extra)
        return pd.DataFrame(values)

    @staticmethod
    def _generate(strategy, candles):
        from trading_stack.signal_generator import generate_technical_signal

        return generate_technical_signal(
            strategy,
            "BTC/USDT",
            candles,
            pending_signal_lookup=lambda strategy_id, pair: None,
            signal_factory=lambda **values: _Signal(**values),
        )

    def test_empty_rules_do_not_invent_a_buy(self) -> None:
        self.assertIsNone(self._generate(_Strategy({}, []), self._candles()))

    def test_sell_only_rules_create_sell_with_stop_above_entry(self) -> None:
        strategy = _Strategy(
            {},
            [{"indicator": "price", "operator": "<", "value": 105, "side": "SELL"}],
        )

        signal = self._generate(strategy, self._candles())

        self.assertEqual(signal.signal_type, "SELL")
        self.assertEqual(signal.entry_price, 100.0)
        self.assertEqual(signal.stop_loss, 102.0)
        self.assertEqual(signal.take_profit, 96.0)

    def test_missing_indicator_column_does_not_invent_a_signal(self) -> None:
        strategy = _Strategy(
            {"sma": {"period": 3}},
            [{"indicator": "sma", "operator": ">", "value": 1, "side": "BUY"}],
        )

        self.assertIsNone(self._generate(strategy, self._candles()))

    def test_editor_indicator_id_resolves_to_calculated_column(self) -> None:
        strategy = _Strategy(
            [{"type": "SMA", "parameters": {"period": 2}, "id": 77}],
            [{"indicator": "sma_77", "operator": ">", "value": 2, "side": "BUY"}],
        )

        signal = self._generate(strategy, self._candles(sma_2=[2.0, 3.0]))

        self.assertEqual(signal.signal_type, "BUY")

    def test_malformed_or_simultaneously_true_rules_fail_closed(self) -> None:
        malformed = _Strategy(
            {}, [{"indicator": "price", "operator": ">", "value": 1}]
        )
        ambiguous = _Strategy(
            {},
            [
                {"indicator": "price", "operator": ">", "value": 1, "side": "BUY"},
                {"indicator": "price", "operator": ">", "value": 1, "side": "SELL"},
            ],
        )

        self.assertIsNone(self._generate(malformed, self._candles()))
        self.assertIsNone(self._generate(ambiguous, self._candles()))

    def test_missing_paper_model_predictor_fails_explicitly(self) -> None:
        from trading_stack.signal_generator import (
            ModelUnavailableError,
            generate_ml_signal,
        )

        strategy = _Strategy({}, [])
        strategy.use_ml_model = True
        strategy.ml_model_id = 19
        with self.assertRaises(ModelUnavailableError):
            generate_ml_signal(
                strategy,
                "BTC/USDT",
                self._candles(),
                pending_signal_lookup=lambda strategy_id, pair: None,
                signal_factory=lambda **values: _Signal(**values),
            )

    def test_strategy_generator_uses_injected_market_and_signal_collaborators(self) -> None:
        from trading_stack.signal_generator import generate_signals_for_strategy

        provider = _MarketProvider(BacktestContractTests._candles())
        strategy = _Strategy(
            {},
            [{"indicator": "price", "operator": ">", "value": 100, "side": "BUY"}],
        )

        signals = generate_signals_for_strategy(
            strategy,
            market_provider=provider,
            pending_signal_lookup=lambda strategy_id, pair: None,
            signal_factory=lambda **values: _Signal(**values),
        )

        self.assertEqual([signal.signal_type for signal in signals], ["BUY"])
        self.assertEqual(provider.history_calls[0][0], "BTC/USDT")


class _MarketProvider:
    def __init__(self, frame):
        self.frame = frame
        self.history_calls = []

    def get_latest_prices(self, pairs, as_of=None):
        self.latest_pairs = tuple(pairs)
        self.latest_as_of = as_of
        return {"BTC/USDT": 101.5}

    def get_historical_data(
        self, trading_pair, timeframe, start_date=None, end_date=None, limit=100
    ):
        self.history_calls.append(
            (trading_pair, timeframe, start_date, end_date, limit)
        )
        return self.frame.copy()


class MarketDataContractTests(unittest.TestCase):
    @staticmethod
    def _dated_candles():
        import pandas as pd

        index = pd.date_range("2026-01-01", periods=5, freq="D", tz="UTC")
        return pd.DataFrame(
            {
                "open": [1, 2, 3, 4, 5],
                "high": [2, 3, 4, 5, 6],
                "low": [0, 1, 2, 3, 4],
                "close": [1, 2, 3, 4, 5],
                "volume": [10, 11, 12, 13, 14],
            },
            index=index,
        )

    def test_injected_provider_receives_pair_and_dates_and_range_is_enforced(self) -> None:
        from trading_stack.market_data import get_historical_data

        provider = _MarketProvider(self._dated_candles())
        result = get_historical_data(
            "BTC/USDT",
            "1d",
            limit=100,
            start_date="2026-01-02T00:00:00Z",
            end_date="2026-01-04T00:00:00Z",
            provider=provider,
        )

        self.assertEqual(
            provider.history_calls,
            [
                (
                    "BTC/USDT",
                    "1d",
                    "2026-01-02T00:00:00Z",
                    "2026-01-04T00:00:00Z",
                    100,
                )
            ],
        )
        self.assertEqual(
            [stamp.isoformat() for stamp in result.index],
            [
                "2026-01-02T00:00:00+00:00",
                "2026-01-03T00:00:00+00:00",
                "2026-01-04T00:00:00+00:00",
            ],
        )

    def test_latest_prices_use_injected_pair_routing(self) -> None:
        from trading_stack.market_data import get_latest_prices

        provider = _MarketProvider(self._dated_candles())

        prices = get_latest_prices(provider=provider, as_of="2026-01-03T00:00:00Z")

        self.assertEqual(prices["BTC/USDT"], 101.5)
        self.assertIn("BTC/USDT", provider.latest_pairs)
        self.assertEqual(provider.latest_as_of, "2026-01-03T00:00:00Z")

    def test_paper_mode_without_provider_returns_unavailable_data(self) -> None:
        from trading_stack.market_data import get_historical_data, get_latest_prices

        self.assertEqual(get_latest_prices(), {})
        self.assertTrue(get_historical_data("BTC/USDT", "1d").empty)

    def test_reversed_or_incomplete_date_range_is_rejected(self) -> None:
        from trading_stack.market_data import get_historical_data

        provider = _MarketProvider(self._dated_candles())
        with self.assertRaises(ValueError):
            get_historical_data(
                "BTC/USDT",
                "1d",
                start_date="2026-01-05",
                end_date="2026-01-01",
                provider=provider,
            )
        with self.assertRaises(ValueError):
            get_historical_data(
                "BTC/USDT", "1d", start_date="2026-01-01", provider=provider
            )


class RiskLimitContractTests(unittest.TestCase):
    def test_nested_paper_and_exchange_balances_normalize_to_equity(self) -> None:
        from trading_stack.risk_management import normalize_account_equity

        self.assertEqual(
            normalize_account_equity(
                {"binance": {"balances": {"USDT": {"free": "10000"}}}},
                "BTC/USDT",
            ),
            10_000.0,
        )
        self.assertEqual(
            normalize_account_equity(
                {"paper": {"account": {"equity": 7_500}}}, "BTC/USDT"
            ),
            7_500.0,
        )

    def test_pair_platform_routing_recognizes_usdt_quote(self) -> None:
        from trading_stack.risk_management import platform_for_trading_pair

        self.assertEqual(platform_for_trading_pair("BTC/USDT"), "binance")
        self.assertEqual(platform_for_trading_pair("EUR/USD"), "oanda")

    def test_injected_risk_collaborators_preserve_limits_and_strategy_risk(self) -> None:
        from trading_stack.risk_management import check_risk_limits

        user = SimpleNamespace(
            id=3, max_open_positions=3, max_position_size_pct=60
        )
        strategy = SimpleNamespace(
            risk_per_trade_pct=1, stop_loss_pct=2
        )
        collaborators = {
            "account_balance_provider": lambda user: {
                "binance": {"balances": {"USDT": {"free": "10000"}}}
            },
            "active_positions_provider": lambda user_id: [],
            "latest_prices_provider": lambda: {"BTC/USDT": 100.0},
            "strategy_provider": lambda user_id: strategy,
        }

        self.assertTrue(check_risk_limits(user, "BTC/USDT", 100, **collaborators))

        user.max_position_size_pct = 10
        self.assertFalse(check_risk_limits(user, "BTC/USDT", 100, **collaborators))

    def test_existing_or_excess_shared_positions_fail_closed(self) -> None:
        from trading_stack.risk_management import check_risk_limits

        user = SimpleNamespace(
            id=3, max_open_positions=2, max_position_size_pct=100
        )
        strategy = SimpleNamespace(risk_per_trade_pct=1, stop_loss_pct=2)
        common = {
            "account_balance_provider": lambda user: {"equity": 10_000},
            "latest_prices_provider": lambda: {"BTC/USDT": 100.0},
            "strategy_provider": lambda user_id: strategy,
        }

        duplicate = dict(
            common,
            active_positions_provider=lambda user_id: [
                {"trading_pair": "BTC/USDT"}
            ],
        )
        full = dict(
            common,
            active_positions_provider=lambda user_id: [
                {"trading_pair": "ETH/USDT"},
                {"trading_pair": "SOL/USDT"},
            ],
        )

        self.assertFalse(check_risk_limits(user, "BTC/USDT", 100, **duplicate))
        self.assertFalse(check_risk_limits(user, "BTC/USDT", 100, **full))

    def test_explicit_zero_user_limits_are_not_replaced_by_defaults(self) -> None:
        from trading_stack.risk_management import check_risk_limits

        user = SimpleNamespace(
            id=3, max_open_positions=0, max_position_size_pct=0
        )
        collaborators = {
            "account_balance_provider": lambda user: {"equity": 10_000},
            "active_positions_provider": lambda user_id: [],
            "latest_prices_provider": lambda: {"BTC/USDT": 100.0},
            "strategy_provider": lambda user_id: SimpleNamespace(
                risk_per_trade_pct=0.1, stop_loss_pct=2
            ),
        }

        self.assertFalse(
            check_risk_limits(user, "BTC/USDT", 100, **collaborators)
        )


class _BacktestStrategy(_Strategy):
    risk_per_trade_pct = 10
    stop_loss_pct = 20
    take_profit_pct = 50

    def __init__(self, conditions, exit_conditions=None):
        super().__init__({}, conditions)
        self._exit_conditions = exit_conditions or []

    def get_exit_conditions(self):
        return self._exit_conditions


class BacktestContractTests(unittest.TestCase):
    @staticmethod
    def _candles():
        import pandas as pd

        frame = pd.DataFrame(
            {
                "open": [90.0, 101.0, 100.0, 110.0],
                "high": [90.0, 101.0, 100.0, 110.0],
                "low": [90.0, 101.0, 100.0, 110.0],
                "close": [90.0, 101.0, 100.0, 110.0],
                "volume": [1.0, 1.0, 1.0, 1.0],
            },
            index=pd.date_range("2026-01-01", periods=4, freq="D", tz="UTC"),
        )
        frame.attrs["data_origin"] = "synthetic-test-fixture"
        return frame

    def test_backtest_uses_completed_signal_candle_and_preserves_empty_exit(self) -> None:
        from trading_stack.backtesting import backtest_technical_strategy

        strategy = _BacktestStrategy(
            [{"indicator": "price", "operator": ">", "value": 100, "side": "BUY"}]
        )

        result = backtest_technical_strategy(
            strategy,
            self._candles(),
            "2026-01-02T00:00:00Z",
            "2026-01-04T00:00:00Z",
            10_000,
            fee_bps=100,
            slippage_bps=0,
        )

        self.assertEqual(len(result["trades"]), 1)
        trade = result["trades"][0]
        self.assertEqual(trade["entry_time"], "2026-01-03T00:00:00+00:00")
        self.assertEqual(trade["exit_time"], "2026-01-04T00:00:00+00:00")
        self.assertEqual(trade["exit_reason"], "end_of_test")
        self.assertEqual(trade["entry_price"], 100.0)
        self.assertEqual(result["final_balance"], 10_079.0)
        self.assertEqual(result["data_origin"], "synthetic-test-fixture")
        self.assertEqual(
            result["time_range"],
            {
                "start": "2026-01-02T00:00:00+00:00",
                "end": "2026-01-04T00:00:00+00:00",
            },
        )

    def test_sell_only_rule_does_not_open_a_short_position(self) -> None:
        from trading_stack.backtesting import backtest_technical_strategy

        strategy = _BacktestStrategy(
            [{"indicator": "price", "operator": ">", "value": 1, "side": "SELL"}]
        )
        result = backtest_technical_strategy(
            strategy,
            self._candles(),
            "2026-01-01",
            "2026-01-04",
            10_000,
        )

        self.assertEqual(result["trades"], [])
        self.assertEqual(result["final_balance"], 10_000.0)

    def test_ml_backtest_uses_completed_candles_and_does_not_open_shorts(self) -> None:
        import pandas as pd
        from trading_stack.backtesting import backtest_ml_strategy

        index = pd.date_range("2026-01-01", periods=12, freq="D", tz="UTC")
        candles = pd.DataFrame(
            {
                "open": [100.0] * 12,
                "high": [101.0] * 12,
                "low": [99.0] * 12,
                "close": [100.0] * 12,
                "volume": [1.0] * 12,
            },
            index=index,
        )
        strategy = _BacktestStrategy([])
        strategy.ml_model_id = 19
        windows = []

        def predictor(*, model_id, data):
            self.assertEqual(model_id, 19)
            windows.append(data.copy())
            return -1.0, 0.9

        result = backtest_ml_strategy(
            strategy,
            candles,
            index[0],
            index[-1],
            10_000.0,
            model_predictor=predictor,
        )

        self.assertEqual(result["trades"], [])
        self.assertEqual(result["final_balance"], 10_000.0)
        self.assertEqual([len(window) for window in windows], [10, 10])
        self.assertLess(windows[0].index[-1], index[10])

    def test_ml_backtest_serializes_trade_timestamps(self) -> None:
        import pandas as pd
        from trading_stack.backtesting import backtest_ml_strategy

        index = pd.date_range("2026-01-01", periods=11, freq="D", tz="UTC")
        candles = pd.DataFrame(
            {
                "open": [100.0] * 11,
                "high": [101.0] * 11,
                "low": [99.0] * 11,
                "close": [100.0] * 11,
                "volume": [1.0] * 11,
            },
            index=index,
        )
        strategy = _BacktestStrategy([])
        strategy.ml_model_id = 19

        result = backtest_ml_strategy(
            strategy,
            candles,
            index[0],
            index[-1],
            10_000.0,
            model_predictor=lambda **kwargs: (1.0, 0.9),
        )

        self.assertEqual(result["trades"][0]["entry_time"], index[-1].isoformat())
        self.assertEqual(result["trades"][0]["exit_time"], index[-1].isoformat())
        self.assertEqual(result["data_origin"], "provided-dataframe")
        self.assertEqual(result["time_range"]["start"], index[0].isoformat())
        self.assertEqual(result["time_range"]["end"], index[-1].isoformat())
        self.assertEqual(result["assumptions"]["position_model"], "long_only")

    def test_backtest_condition_accepts_symbolic_operator_and_fails_closed(self) -> None:
        import pandas as pd
        from trading_stack.backtesting import evaluate_backtest_condition

        row = pd.Series({"sma_3": 4.0})
        previous = pd.Series({"sma_3": 3.0})

        self.assertTrue(
            evaluate_backtest_condition(
                row,
                previous,
                {"indicator": "sma_3", "operator": ">", "value": 3.5},
            )
        )
        self.assertFalse(
            evaluate_backtest_condition(
                row,
                previous,
                {"indicator": "missing", "operator": ">", "value": 0},
            )
        )

    def test_backtest_data_helper_forwards_both_dates(self) -> None:
        from trading_stack.backtesting import get_historical_data_for_backtest

        provider = _MarketProvider(self._candles())
        result = get_historical_data_for_backtest(
            "BTC/USDT",
            "1d",
            "2026-01-02T00:00:00Z",
            "2026-01-04T00:00:00Z",
            market_provider=provider,
        )

        self.assertEqual(
            provider.history_calls[0][0:4],
            (
                "BTC/USDT",
                "1d",
                "2026-01-02T00:00:00Z",
                "2026-01-04T00:00:00Z",
            ),
        )
        self.assertEqual(len(result), 3)

    def test_performance_metrics_are_finite_when_there_are_no_losses(self) -> None:
        import math
        from trading_stack.backtesting import calculate_performance_metrics

        metrics = calculate_performance_metrics(
            {
                "final_balance": 10_100.0,
                "trades": [{"pnl": 100.0}],
                "equity_curve": [10_000.0, 10_100.0],
                "drawdown_curve": [0.0, 0.0],
            }
        )

        self.assertTrue(
            all(
                math.isfinite(float(value))
                for value in metrics.values()
                if isinstance(value, (int, float))
            )
        )
        self.assertIsNone(metrics["profit_factor"])

        empty_metrics = calculate_performance_metrics(
            {
                "final_balance": 10_000.0,
                "trades": [],
                "equity_curve": [10_000.0],
                "drawdown_curve": [0.0],
            }
        )
        self.assertIsNone(empty_metrics["profit_factor"])

if __name__ == "__main__":
    unittest.main()
