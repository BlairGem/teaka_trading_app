import importlib
import json
import os
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


def candles():
    return pd.DataFrame({"open": [100., 100., 101., 102., 103.],
                         "high": [101., 102., 103., 104., 105.],
                         "low": [99., 99., 100., 101., 102.],
                         "close": [100., 101., 102., 103., 104.],
                         "volume": [10.] * 5},
                        index=pd.date_range("2026-01-01", periods=5, freq="h"))


class FactoryBoundaryTests(unittest.TestCase):
    def test_sqlite_guard_rejects_persistent_database(self):
        with self.assertRaisesRegex(RuntimeError, "non-memory sqlite"):
            sqlite3.connect("must-never-be-created.db")

    def test_factory_is_explicit_and_import_does_not_create_database(self):
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///must-never-be-read.db", "TEAKA_MODE": "live", "LIVE_TRADING_ENABLED": "true"}):
            module = importlib.import_module("trading_stack.app")
            self.assertTrue(callable(getattr(module, "create_app", None)))
            app = module.create_app({"TESTING": True})
            self.assertEqual(app.config["SQLALCHEMY_DATABASE_URI"], "sqlite://")
            self.assertEqual(app.config["TEAKA_MODE"], "paper")
            self.assertNotIn("unified_trading", sys.modules)
            self.assertNotIn("trading_stack.unified_trading", sys.modules)


class FullPaperTests(unittest.TestCase):
    def setUp(self):
        from trading_stack.app import create_app
        from trading_stack.paper_runtime import PaperRuntime, LocalCandleProvider
        from paper_trading.paper_broker import PaperConfig
        from trading_stack.models import db, User, TradingStrategy
        self.db = db
        self.app = create_app({"TESTING": True, "SECRET_KEY": "synthetic-test-only"})
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.provider = LocalCandleProvider({"BTC/USDT": candles()}, "synthetic_test_fixture", "1h")
        self.runtime = PaperRuntime(self.provider, PaperConfig(max_order_notional=10000, max_position_pct=1, fee_bps=10, slippage_bps=5))
        self.app.extensions["paper_runtime"] = self.runtime
        self.users = []
        for i in range(2):
            user = User(username=f"fixture{i}", email=f"fixture{i}@example.invalid", password_hash="unused", max_position_size_pct=80, max_open_positions=2)
            db.session.add(user)
            self.users.append(user)
        db.session.flush()
        self.strategies = []
        for i in range(2):
            strategy = TradingStrategy(user_id=self.users[0].id, name=f"s{i}", timeframe="1h", is_active=True, risk_per_trade_pct=0.1, stop_loss_pct=2., take_profit_pct=50.)
            strategy.set_trading_pairs(["BTC/USDT"])
            strategy.set_indicators_config({"sma": {"period": 1}})
            strategy.set_entry_conditions([{"indicator": "sma_1", "operator": ">", "value": 1, "side": "BUY"}])
            db.session.add(strategy)
            self.strategies.append(strategy)
        db.session.commit()

    def tearDown(self):
        self.db.session.remove()
        self.db.engine.dispose()
        self.ctx.pop()

    def replay(self):
        return self.runtime.replay(self.users[0].id, "2026-01-01", "2026-01-01T04:00:00")

    def test_real_engine_two_strategies_shared_risk_deterministic_and_idempotent(self):
        from trading_stack.models import TradingSignal, TradeExecution, PaperRun, PaperDecision
        first = self.replay()
        self.assertGreater(first["decision_count"], 0)
        self.assertEqual(first["fill_count"], 2)
        self.assertEqual(first["mode"], "paper")
        self.assertEqual(first["data_origin"], "synthetic_test_fixture")
        self.assertEqual(TradeExecution.query.filter_by(status="filled").count(), 2)
        self.assertGreater(TradingSignal.query.count(), 1)
        self.assertEqual(PaperRun.query.count(), 1)
        self.assertGreater(PaperDecision.query.filter_by(status="rejected").count(), 0)
        again = self.replay()
        self.assertEqual(again["economic_summary"], first["economic_summary"])
        self.assertEqual(TradeExecution.query.filter_by(status="filled").count(), 2)
        from trading_stack.paper_runtime import PaperRuntime, LocalCandleProvider
        other = PaperRuntime(LocalCandleProvider({"BTC/USDT": candles()}, "synthetic_test_fixture", "1h"), self.runtime.config)
        independent = other.replay(self.users[0].id, "2026-01-01", "2026-01-01T04:00:00")
        self.assertEqual(independent["economic_summary"], first["economic_summary"])
        canonical = lambda result: [{key: value for key, value in fill.items() if key != 'order_id'} for fill in result['fills']]
        self.assertEqual(canonical(independent), canonical(first))
        self.assertEqual(first['fills'][0]['quantity'], 5)
        json.dumps(first, allow_nan=False)
        self.assertEqual(self.runtime.account(self.users[1].id).cash, 10000)

    def test_clock_hides_future_and_rejects_backward_advancement(self):
        self.assertEqual(self.provider.get_latest_prices(["BTC/USDT"]), {})
        self.provider.advance("2026-01-01T01:00:00")
        self.assertEqual(self.provider.get_latest_prices(["BTC/USDT"], as_of="2030-01-01"), {"BTC/USDT": 101})
        self.assertEqual(len(self.provider.get_historical_data("BTC/USDT", "1h", start_date=None, end_date=None, limit=100)), 2)
        with self.assertRaises(ValueError):
            self.provider.advance("2025-01-01")

    def test_exit_rules_use_prior_candle_next_open_and_simulated_fill_times(self):
        from trading_stack.models import TradeExecution
        self.strategies[1].is_active = False
        self.strategies[0].set_exit_conditions([{"indicator": "sma_1", "operator": ">", "value": 100.5}])
        self.db.session.commit()
        result = self.replay()
        fills = TradeExecution.query.filter_by(status='filled').order_by(TradeExecution.id).all()
        self.assertEqual(fills[1].timestamp.isoformat(), '2026-01-01T02:00:00')
        self.assertAlmostEqual(fills[1].price, 101 * .9995)
        self.assertEqual(result['fills'][0]['timestamp'], '2026-01-01T01:00:00')
        self.assertEqual(result['fills'][1]['timestamp'], '2026-01-01T02:00:00')

    def test_duplicate_engine_candle_preserves_positions_and_orm_counts(self):
        from trading_stack.trading_engine import run_trading_engine
        from trading_stack.models import TradeExecution, TradingSignal
        for time in ('2026-01-01', '2026-01-01T01:00:00'):
            run_trading_engine(self.runtime, self.users[0].id, time)
        before = (self.runtime.balance(self.users[0].id), self.runtime.positions(self.users[0].id), TradeExecution.query.count(), TradingSignal.query.count())
        run_trading_engine(self.runtime, self.users[0].id, '2026-01-01T01:00:00')
        self.assertEqual(before, (self.runtime.balance(self.users[0].id), self.runtime.positions(self.users[0].id), TradeExecution.query.count(), TradingSignal.query.count()))

    def test_live_flags_cannot_load_optional_provider_and_mixed_quotes_rejected(self):
        from trading_stack.paper_runtime import LocalCandleProvider
        from trading_stack.models import PaperDecision
        for strategy in self.strategies:
            strategy.use_ml_model = True
            strategy.ml_model_id = 1
        self.db.session.commit()
        with patch.dict(os.environ, {'TEAKA_MODE': 'live', 'LIVE_TRADING_ENABLED': 'true', 'PRIVATE_EXCHANGE_API_ENABLED': 'true'}):
            result = self.replay()
        self.assertEqual(result['fill_count'], 0)
        self.assertGreater(PaperDecision.query.filter_by(status='unavailable').count(), 0)
        for name in ('unified_trading', 'ml_models', 'matlab_integration', 'messaging', 'broker_apis'):
            self.assertNotIn('trading_stack.' + name, sys.modules)
            self.assertNotIn(name, sys.modules)
        with self.assertRaises(ValueError):
            LocalCandleProvider({'USD/JPY': candles()}, 'synthetic_test_fixture')

    def test_invalid_manual_values_and_user_limits_fail_closed(self):
        self.provider.advance('2026-01-01')
        for quantity in (True, float('nan'), float('inf'), 0, -1):
            with self.assertRaises(ValueError):
                self.runtime.manual_order(self.users[0].id, 'BTC/USDT', 'BUY', quantity)
        self.users[0].max_position_size_pct = float('nan')
        with self.assertRaises(ValueError):
            self.runtime.manual_order(self.users[0].id, 'BTC/USDT', 'BUY', 1)

    def test_api_foreign_signal_execution_backtest_and_cross_strategy_lot_denied(self):
        from trading_stack.models import TradingSignal, BacktestResult
        signal = TradingSignal(user_id=self.users[0].id, strategy_id=self.strategies[0].id, trading_pair='BTC/USDT', signal_type='BUY', status='pending', entry_price=100, stop_loss=98, take_profit=104)
        backtest = BacktestResult(user_id=self.users[0].id, strategy_id=self.strategies[0].id, trading_pair='BTC/USDT')
        self.db.session.add_all([signal, backtest])
        self.db.session.commit()
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(self.users[1].id)
        self.assertEqual(client.post(f'/api/signals/{signal.id}/execute', json={'amount': 1}).status_code, 404)
        self.assertEqual(client.get(f'/api/backtests/{backtest.id}').status_code, 404)
        self.provider.advance('2026-01-01')
        self.runtime.submit(self.users[0].id, 'BTC/USDT', 'BUY', 1, 100, strategy=self.strategies[0], stop=98, take=104)
        lot = self.runtime.positions(self.users[0].id)[0]
        self.assertFalse(self.runtime.submit(self.users[0].id, 'BTC/USDT', 'SELL', 1, 100, strategy=self.strategies[1], lot_id=lot['id'])['success'])

    def test_web_csv_roots_and_existing_output_preserved(self):
        from trading_stack.paper_replay import replay_csv
        root = Path(os.environ['TEAKA_TEST_ARTIFACT_ROOT'])
        source, output = root / 'web-candles.csv', root / 'existing.json'
        candles().rename_axis('timestamp').to_csv(source)
        output.write_text('preserve this exact content')
        with self.assertRaises(ValueError):
            replay_csv(self.runtime, self.users[0].id, source, 'BTC/USDT', '1h', '2026-01-01', '2026-01-02', 'synthetic_test_fixture', output)
        self.assertEqual(output.read_text(), 'preserve this exact content')
        self.app.config.update(PAPER_DATA_ROOT=str(root), PAPER_OUTPUT_ROOT=str(root))
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(self.users[0].id)
        request = dict(csv_path=str(source), output_path='C:/never-write.json', trading_pair='BTC/USDT', timeframe='1h', start='2026-01-01', end='2026-01-01T04:00:00', data_origin='synthetic_test_fixture')
        result = client.post('/api/paper/replay', json=request)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['fill_count'], 2)
        self.assertTrue(list(root.glob('paper-run-*.json')))

    def test_owned_backtest_api_uses_local_candles_and_foreign_owner_fails(self):
        self.provider.advance('2026-01-01T04:00:00')
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(self.users[0].id)
        body = dict(strategy_id=self.strategies[0].id, trading_pair='BTC/USDT', start_date='2026-01-01', end_date='2026-01-01T04:00:00')
        result = client.post('/api/backtests', json=body)
        self.assertEqual(result.status_code, 200)
        saved = client.get('/api/backtests/' + str(result.json['backtest_id'])).json
        self.assertEqual(json.loads(saved['result_data'])['data_origin'], 'synthetic_test_fixture')
        with client.session_transaction() as session:
            session['_user_id'] = str(self.users[1].id)
        # This fixture keeps an app context alive for ORM assertions. Real
        # requests have separate contexts, so clear Flask-Login's context cache.
        from flask import g
        g.pop('_login_user', None)
        self.assertEqual(client.post('/api/backtests', json=body).status_code, 404)

    def test_csv_after_balance_read_and_repeat_preserves_economics(self):
        from trading_stack.paper_replay import replay_csv
        root = Path(os.environ['TEAKA_TEST_ARTIFACT_ROOT'])
        source = root / 'repeat-fixture.csv'
        candles().rename_axis('timestamp').to_csv(source)
        self.runtime.balance(self.users[0].id)
        outputs = []
        for index in range(2):
            outputs.append(replay_csv(self.runtime, self.users[0].id, source, 'BTC/USDT', '1h', '2026-01-01', '2026-01-01T04:00:00', 'synthetic_test_fixture', root / f'repeat-{index}.json'))
        self.assertEqual(outputs[0], outputs[1])

    def test_finite_cli_uses_real_orm_and_writes_complete_report(self):
        from trading_stack.paper_replay import main
        import contextlib
        root = Path(os.environ['TEAKA_TEST_ARTIFACT_ROOT'])
        source, definition = root / 'cli-candles.csv', root / 'cli-strategies.json'
        candles().rename_axis('timestamp').to_csv(source)
        definition.write_text(json.dumps([dict(name=s.name, risk_per_trade_pct=s.risk_per_trade_pct,
            stop_loss_pct=s.stop_loss_pct, take_profit_pct=s.take_profit_pct,
            indicators_config=s.get_indicators_config(), entry_conditions=s.get_entry_conditions()) for s in self.strategies]))
        output = root / 'cli-replay.json'
        with (root / 'cli-complete-output.txt').open('x') as transcript, contextlib.redirect_stdout(transcript):
            code = main(['--csv', str(source), '--strategies', str(definition), '--pair', 'BTC/USDT', '--timeframe', '1h', '--start', '2026-01-01', '--end', '2026-01-01T04:00:00', '--data-origin', 'synthetic_test_fixture', '--output', str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.read_text())['fill_count'], 2)

    def test_shared_clock_cannot_rewind_for_later_user_or_replace_active_dataset(self):
        from trading_stack.paper_replay import replay_csv
        result = self.replay()
        before = (self.provider.clock, self.runtime.balance(self.users[0].id), self.runtime.positions(self.users[0].id))
        with self.assertRaises(ValueError):
            self.runtime.replay(self.users[1].id, '2026-01-01', '2026-01-01T04:00:00')
        root = Path(os.environ['TEAKA_TEST_ARTIFACT_ROOT'])
        source = root / 'other-user-fixture.csv'
        candles().rename_axis('timestamp').to_csv(source)
        with self.assertRaises(ValueError):
            replay_csv(self.runtime, self.users[1].id, source, 'BTC/USDT', '1h', '2026-01-01', '2026-01-01T04:00:00', 'synthetic_test_fixture', root / 'other-user.json')
        self.assertEqual(before, (self.provider.clock, self.runtime.balance(self.users[0].id), self.runtime.positions(self.users[0].id)))
        self.assertEqual(self.replay(), result)

    def test_two_distinct_same_quote_strategies_have_owned_positions_and_shared_cash(self):
        from trading_stack.paper_runtime import LocalCandleProvider
        from trading_stack.trading_engine import run_trading_engine
        self.runtime.provider = LocalCandleProvider({'BTC/USDT': candles(), 'ETH/USDT': candles()}, 'synthetic_test_fixture', '1h')
        self.strategies[1].set_trading_pairs(['ETH/USDT'])
        self.db.session.commit()
        run_trading_engine(self.runtime, self.users[0].id, '2026-01-01')
        run_trading_engine(self.runtime, self.users[0].id, '2026-01-01T01:00:00')
        positions = self.runtime.positions(self.users[0].id)
        self.assertEqual({p['strategy_id'] for p in positions}, {s.id for s in self.strategies})
        self.assertEqual(len(positions), 2)
        self.assertLess(self.runtime.account(self.users[0].id).cash, 9000)
        self.assertEqual(self.runtime.positions(self.users[1].id), [])

    def test_recovered_login_flow_accepts_only_synthetic_fixture(self):
        user = self.users[0]
        user.set_password('synthetic-fixture-only-password')
        self.db.session.commit()
        client = self.app.test_client()
        result = client.post('/auth/login', data={'username': user.username, 'password': 'synthetic-fixture-only-password'})
        self.assertEqual(result.status_code, 302)
        self.assertTrue(result.location.endswith('/dashboard'))

    def test_submit_without_replay_clock_fails_before_mutation(self):
        from trading_stack.models import TradeExecution
        with self.assertRaises(ValueError):
            self.runtime.submit(self.users[0].id, 'BTC/USDT', 'BUY', 1, 100)
        self.assertEqual(TradeExecution.query.count(), 0)
        self.assertEqual(self.runtime.accounts, {})

    def test_engine_position_and_order_status_helpers_use_paper_state(self):
        from trading_stack.trading_engine import get_position_details, update_orders_status
        self.provider.advance('2026-01-01')
        self.runtime.manual_order(self.users[0].id, 'BTC/USDT', 'BUY', 1)
        position = self.runtime.positions(self.users[0].id)[0]
        self.assertEqual(get_position_details(position['id'], self.users[0].id)['id'], position['id'])
        self.assertIsNone(get_position_details(position['id'], self.users[1].id))
        self.assertEqual(update_orders_status()['mode'], 'paper')

    def test_other_user_forward_replay_cannot_skip_held_account_events(self):
        from trading_stack.models import PaperRun, TradeExecution
        from trading_stack.trading_engine import run_trading_engine
        from trading_stack.paper_runtime import LocalCandleProvider
        data = candles()
        data.loc[data.index[2], 'low'] = 90
        self.runtime.provider = LocalCandleProvider({'BTC/USDT': data}, 'synthetic_test_fixture', '1h')
        for strategy in self.strategies:
            strategy.is_active = False
        self.db.session.commit()
        self.runtime.provider.advance('2026-01-01')
        self.runtime.manual_order(self.users[0].id, 'BTC/USDT', 'BUY', 1)
        before = (self.runtime.provider.clock, self.runtime.balance(self.users[0].id), self.runtime.positions(self.users[0].id), PaperRun.query.count(), TradeExecution.query.count(), set(self.runtime.accounts))
        with self.assertRaisesRegex(ValueError, 'held account'):
            self.runtime.replay(self.users[1].id, '2026-01-01T01:00:00', '2026-01-01T04:00:00')
        self.assertEqual(before, (self.runtime.provider.clock, self.runtime.balance(self.users[0].id), self.runtime.positions(self.users[0].id), PaperRun.query.count(), TradeExecution.query.count(), set(self.runtime.accounts)))
        for target in ('2026-01-01T01:00:00', '2026-01-01T04:00:00'):
            with self.assertRaisesRegex(ValueError, 'held account'):
                run_trading_engine(self.runtime, self.users[1].id, target)
        # The owner can still process every required event and receive the stop.
        result = self.runtime.replay(self.users[0].id, '2026-01-01T01:00:00', '2026-01-01T04:00:00')
        self.assertEqual(result['fills'][0]['timestamp'], '2026-01-01T02:00:00')
        self.assertAlmostEqual(result['fills'][0]['requested_price'], 98)
        self.assertEqual(self.runtime.positions(self.users[0].id), [])

    def test_same_user_direct_engine_and_replay_gaps_reject_before_mutation(self):
        from trading_stack.trading_engine import run_trading_engine
        from trading_stack.models import PaperRun, TradeExecution
        self.provider.advance('2026-01-01')
        self.runtime.manual_order(self.users[0].id, 'BTC/USDT', 'BUY', 1)
        before = (self.provider.clock, self.runtime.balance(self.users[0].id), self.runtime.positions(self.users[0].id), PaperRun.query.count(), TradeExecution.query.count())
        with self.assertRaisesRegex(ValueError, 'unprocessed candle'):
            run_trading_engine(self.runtime, self.users[0].id, '2026-01-01T03:00:00')
        with self.assertRaisesRegex(ValueError, 'unprocessed candle'):
            self.runtime.replay(self.users[0].id, '2026-01-01T03:00:00', '2026-01-01T04:00:00')
        self.assertEqual(before, (self.provider.clock, self.runtime.balance(self.users[0].id), self.runtime.positions(self.users[0].id), PaperRun.query.count(), TradeExecution.query.count()))

    def test_direct_provider_advancement_cannot_bypass_held_account_clock(self):
        self.provider.advance('2026-01-01')
        self.runtime.manual_order(self.users[0].id, 'BTC/USDT', 'BUY', 1)
        with self.assertRaisesRegex(ValueError, 'held account'):
            self.provider.advance('2026-01-01T04:00:00')
        self.assertEqual(self.provider.clock.isoformat(), '2026-01-01T00:00:00')

    def test_inactive_replay_prevents_dataset_replacement_and_false_provenance(self):
        from trading_stack.paper_replay import replay_csv
        root = Path(os.environ['TEAKA_TEST_ARTIFACT_ROOT'])
        first_csv, second_csv = root / 'inactive-one.csv', root / 'inactive-two.csv'
        candles().rename_axis('timestamp').to_csv(first_csv)
        (candles() * 2).rename_axis('timestamp').to_csv(second_csv)
        for strategy in self.strategies:
            strategy.is_active = False
        self.db.session.commit()
        first = replay_csv(self.runtime, self.users[0].id, first_csv, 'BTC/USDT', '1h', '2026-01-01', '2026-01-01T04:00:00', 'synthetic_one', root / 'inactive-first.json')
        self.assertEqual(first['fill_count'], 0)
        before = (self.runtime.provider, self.runtime.provider.clock, dict(self.runtime.results), set(self.runtime.processed_candles))
        with self.assertRaisesRegex(ValueError, 'fresh runtime'):
            replay_csv(self.runtime, self.users[0].id, second_csv, 'BTC/USDT', '1h', '2026-01-01', '2026-01-01T04:00:00', 'synthetic_two', root / 'inactive-second.json')
        from trading_stack.paper_runtime import LocalCandleProvider
        with self.assertRaisesRegex(ValueError, 'fresh runtime'):
            self.runtime.provider = LocalCandleProvider({'BTC/USDT': candles() * 2}, 'synthetic_two', '1h')
        self.assertEqual(before, (self.runtime.provider, self.runtime.provider.clock, dict(self.runtime.results), set(self.runtime.processed_candles)))

    def test_manual_signal_uses_requested_quantity_but_preserves_strategy_max_risk(self):
        from trading_stack.models import TradingSignal, TradeExecution
        from trading_stack.trading_engine import execute_trade_from_signal
        self.provider.advance('2026-01-01')
        strategy = self.strategies[0]
        strategy.risk_per_trade_pct = 2
        signal = TradingSignal(user_id=self.users[0].id, strategy_id=strategy.id, trading_pair='BTC/USDT', signal_type='BUY', status='pending', entry_price=100, stop_loss=98, take_profit=104)
        self.db.session.add(signal)
        self.db.session.commit()
        self.assertTrue(execute_trade_from_signal(signal, 1, self.runtime, self.users[0].id))
        self.assertEqual(TradeExecution.query.filter_by(signal_id=signal.id).one().amount, 1)
        lot = self.runtime.positions(self.users[0].id)[0]
        self.runtime.close(self.users[0].id, lot['id'])
        strategy.risk_per_trade_pct = .001
        self.db.session.commit()
        rejected = self.runtime.submit(self.users[0].id, 'BTC/USDT', 'BUY', 1, 100, strategy=strategy, stop=98, take=104)
        self.assertFalse(rejected['success'])
        self.assertEqual(rejected['error'], 'risk_per_trade_limit')

    def test_strategy_metrics_include_owned_entry_and_each_signal_less_close(self):
        from trading_stack.paper_runtime import LocalCandleProvider, PaperRuntime
        from trading_stack.models import TradingSignal, TradeExecution
        from trading_stack.trading_engine import execute_trade_from_signal, run_trading_engine
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(self.users[0].id)
        self.strategies[1].is_active = False
        strategy = self.strategies[0]
        strategy.is_active = False
        self.db.session.commit()
        for reason in ('stop_loss', 'take_profit', 'final_liquidation', 'manual_close'):
            with self.subTest(reason=reason):
                data = candles()
                if reason == 'stop_loss':
                    data.loc[data.index[1], 'low'] = 90
                if reason == 'take_profit':
                    data.loc[data.index[1], 'high'] = 110
                runtime = PaperRuntime(LocalCandleProvider({'BTC/USDT': data}, 'synthetic_test_fixture', '1h'), self.runtime.config)
                self.app.extensions['paper_runtime'] = runtime
                runtime.provider.advance('2026-01-01')
                signal = TradingSignal(user_id=self.users[0].id, strategy_id=strategy.id, trading_pair='BTC/USDT', signal_type='BUY', status='pending', entry_price=100, stop_loss=98, take_profit=104)
                self.db.session.add(signal)
                self.db.session.commit()
                self.assertTrue(execute_trade_from_signal(signal, 1, runtime, self.users[0].id))
                if reason in ('stop_loss', 'take_profit'):
                    run_trading_engine(runtime, self.users[0].id, '2026-01-01T01:00:00')
                elif reason == 'final_liquidation':
                    runtime.replay(self.users[0].id, '2026-01-01T01:00:00', '2026-01-01T01:00:00')
                else:
                    lot = runtime.positions(self.users[0].id)[0]
                    self.assertTrue(client.post(f"/api/positions/{lot['id']}/close").json['success'])
                rows = TradeExecution.query.filter_by(user_id=self.users[0].id).all()
                closing = rows[-1]
                self.assertIsNone(closing.signal_id)
                self.assertEqual(closing.strategy_id, strategy.id)
                self.assertEqual(json.loads(closing.notes)['reason'], reason)
                metrics = client.get(f'/api/strategies/{strategy.id}/risk-metrics').json['data']
                self.assertEqual(metrics['execution_count'], len(rows))
                self.assertAlmostEqual(metrics['fees'], sum(row.fee for row in rows))
        # Another user's execution/strategy must never enter these totals.
        self.db.session.add(TradeExecution(user_id=self.users[1].id, strategy_id=strategy.id,
            trading_pair='BTC/USDT', order_type='SELL', amount=1, price=100, fee=100,
            status='filled', platform='paper'))
        self.db.session.commit()
        isolated = client.get(f'/api/strategies/{strategy.id}/risk-metrics').json['data']
        self.assertEqual(isolated, metrics)
        from flask import g
        g.pop('_login_user', None)
        with client.session_transaction() as session:
            session['_user_id'] = str(self.users[1].id)
        self.assertEqual(client.get(f'/api/strategies/{strategy.id}/risk-metrics').status_code, 404)

    def test_manual_requested_quantity_risk_and_owned_close_bypass_limits(self):
        self.provider.advance("2026-01-01")
        user = self.users[0]
        rejected = self.runtime.manual_order(user.id, "BTC/USDT", "BUY", 90)
        self.assertFalse(rejected["success"])
        result = self.runtime.manual_order(user.id, "BTC/USDT", "BUY", 1)
        self.assertTrue(result["success"])
        position = self.runtime.positions(user.id)[0]
        self.assertFalse(self.runtime.close(self.users[1].id, position["id"])["success"])
        user.max_open_positions = 0
        user.max_position_size_pct = 0
        self.runtime.account(user.id).kill_switch = True
        self.assertTrue(self.runtime.close(user.id, position["id"])["success"])

    def test_stop_closes_owned_lot_and_no_reopen_on_same_candle(self):
        from trading_stack.models import TradeExecution
        data = candles()
        data.loc[data.index[1], "low"] = 90
        from trading_stack.paper_runtime import LocalCandleProvider
        self.runtime.provider = LocalCandleProvider({"BTC/USDT": data}, "synthetic_test_fixture", "1h")
        self.runtime.replay(self.users[0].id, "2026-01-01", "2026-01-01T01:00:00")
        fills = TradeExecution.query.filter_by(status="filled").order_by(TradeExecution.id).all()
        self.assertEqual([row.order_type for row in fills], ["BUY", "SELL"])
        self.assertLess(fills[1].price, 100)
        self.assertEqual(self.runtime.positions(self.users[0].id), [])

    def test_invalid_data_rejected_before_account_or_orm_mutation(self):
        from trading_stack.paper_runtime import LocalCandleProvider
        for column, value in (("close", float("nan")), ("low", -1), ("volume", -1)):
            data = candles()
            data.loc[data.index[1], column] = value
            with self.assertRaises(ValueError):
                LocalCandleProvider({"BTC/USDT": data}, "synthetic_test_fixture", "1h")

    def test_api_owner_checks_unavailable_features_and_manual_mapping(self):
        self.provider.advance("2026-01-01")
        client = self.app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(self.users[1].id)
            session["_fresh"] = True
        self.assertEqual(client.get(f"/api/strategies/{self.strategies[0].id}").status_code, 404)
        self.assertEqual(client.get(f"/api/strategies/{self.strategies[0].id}/risk-metrics").status_code, 404)
        self.assertEqual(client.post("/api/ml-models", json={}).status_code, 503)
        self.assertEqual(client.get("/api/matlab-signal").status_code, 503)
        self.assertEqual(client.post("/api/futures/order", json={}).status_code, 503)
        result = client.post("/api/execute-trade", json={"trading_pair": "BTC/USDT", "order_type": "BUY", "amount": 1})
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json["success"])
        self.assertEqual(result.json["data"]["status"], "filled")
        self.assertEqual(client.post("/api/paper/replay", json={"csv_path": "C:/EV_Brain/private.csv", "data_origin": "x", "start": "2026-01-01", "end": "2026-01-02"}).status_code, 400)

    def test_csv_finite_replay_writes_provenance_artifact(self):
        from trading_stack.paper_replay import replay_csv
        root = Path(os.environ["TEAKA_TEST_ARTIFACT_ROOT"])
        source, output = root / "integration-fixture.csv", root / "integration-replay.json"
        candles().rename_axis("timestamp").to_csv(source)
        result = replay_csv(self.runtime, self.users[0].id, source, "BTC/USDT", "1h", "2026-01-01", "2026-01-01T04:00:00", "synthetic_test_fixture", output)
        saved = json.loads(output.read_text())
        self.assertEqual(saved, result)
        self.assertEqual(saved["data_origin"], "synthetic_test_fixture")
        self.assertEqual(saved["source_path"], str(source.resolve()))
        self.assertEqual(len(saved["source_sha256"]), 64)
