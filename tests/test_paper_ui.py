"""Rendered paper workspace and offline full-session contracts."""
import json
import os
import unittest
from pathlib import Path
from tests import test_full_paper_integration as integration


class PaperUITests(unittest.TestCase):
    def setUp(self):
        integration.FullPaperTests.setUp(self)
        # Tests retain an app context for ORM assertions; emulate fresh request g.
        @self.app.before_request
        def reset_test_login_cache():
            from flask import g
            g.pop('_login_user', None)

    tearDown = integration.FullPaperTests.tearDown

    def client(self, user=0):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(self.users[user].id)
            session['_fresh'] = True
        return client

    def test_pages_local_assets_and_truthful_disabled_features(self):
        client = self.client()
        for path in ['/', '/dashboard', '/strategy-editor', '/market-data', '/backtesting', '/signals', '/settings', '/profile', '/auth/profile']:
            with self.subTest(path=path):
                response = client.get(path, follow_redirects=True)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn('Memory-only paper session', html)
                self.assertNotIn('cdn.', html)
                self.assertNotIn('/api/market-data/', html)
                self.assertNotIn('/api/trade/manual', html)
        settings = client.get('/settings').get_data(as_text=True)
        self.assertIn('Notifications unavailable', settings)
        self.assertIn('Broker connections unavailable', settings)
        self.assertEqual(client.get('/static/js/paper.js').status_code, 200)

    def test_credential_and_notification_mutations_are_disabled(self):
        client = self.client()
        for path in ['/update_kucoin_api', '/update_ib_api', '/update_oanda_api', '/update_notification_settings', '/auth/profile']:
            self.assertEqual(client.post(path, data={'enable_email_notifications': 'on'}).status_code, 503)
        self.assertFalse(self.users[0].enable_email_notifications)

    def test_risk_settings_reject_invalid_values_atomically(self):
        client = self.client()
        for value in ['nan', 'inf', '-1', '101']:
            response = client.post('/update_risk_settings', data={'max_position_size_pct': value, 'max_open_positions': '2', 'default_stop_loss_pct': '2', 'default_take_profit_pct': '4'})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.users[0].max_position_size_pct, 80)

    def test_status_and_full_session_with_editor_contract(self):
        client, foreign = self.client(), self.client(1)
        root = Path(os.environ['TEAKA_TEST_ARTIFACT_ROOT'])
        self.app.config.update(PAPER_DATA_ROOT=str(root), PAPER_OUTPUT_ROOT=str(root))
        source = root / 'ui-candles.csv'
        source.write_text((Path(__file__).parent / 'fixtures/paper-session/candles.csv').read_text(), encoding='utf-8')
        self.assertEqual(client.get('/api/paper/status').json['state'], 'unavailable')
        definition = json.loads((Path(__file__).parent / 'fixtures/paper-session/strategies.json').read_text())[0]
        created = client.post('/api/strategies', json=definition)
        self.assertEqual(created.status_code, 200, created.json)
        strategy_id = created.json['strategy_id']
        self.assertEqual(foreign.get(f'/api/strategies/{strategy_id}').status_code, 404)
        result = client.post('/api/paper/replay', json={'csv_path': str(source), 'trading_pair': 'BTC/USDT', 'timeframe': '1h', 'start': '2026-01-01T00:00:00', 'end': '2026-01-01T04:00:00', 'data_origin': 'synthetic_ui_fixture'})
        self.assertEqual(result.status_code, 200, result.json)
        self.assertGreater(result.json['fill_count'], 0)
        self.assertEqual(client.get('/api/paper/status').json['state'], 'simulated')
        self.assertTrue(client.get('/api/signals').json)
        self.assertTrue(client.get('/api/trades').json)
        self.assertEqual(foreign.get('/api/trades').json, [])
        manual = client.post('/api/execute-trade', json={'trading_pair': 'BTC/USDT', 'order_type': 'BUY', 'amount': .1})
        self.assertEqual(manual.json['data']['status'], 'filled')
        held = client.get('/api/positions').json['data'][0]
        self.assertEqual(foreign.post(f"/api/positions/{held['id']}/close").status_code, 404)
        self.assertTrue(client.post(f"/api/positions/{held['id']}/close").json['success'])
        backtest = client.post('/api/backtests', json={'strategy_id': strategy_id, 'trading_pair': 'BTC/USDT', 'start_date': '2026-01-01', 'end_date': '2026-01-01T04:00:00', 'initial_balance': 10000})
        self.assertEqual(backtest.status_code, 200, backtest.json)
        bid = backtest.json['backtest_id']
        self.assertEqual(foreign.get(f'/api/backtests/{bid}').status_code, 404)
        self.assertEqual(len(client.get('/api/backtests').json), 1)
        (root / 'ui-full-session.json').write_text(json.dumps({'replay': result.json, 'backtest': client.get(f'/api/backtests/{bid}').json}), encoding='utf-8')

    def test_old_request_patterns_have_no_rendered_controls(self):
        client = self.client()
        rendered = '\n'.join(client.get(path).get_data(as_text=True) for path in
                             ['/dashboard', '/backtesting', '/market-data', '/signals', '/static/js/paper.js'])
        # All 12 old requests are either replaced by real routes or visibly unavailable.
        retired = ['/api/trade/manual', '/api/backtesting/run', '/api/backtesting/history',
                   '/api/backtesting/details/', '/api/market-data/current/', '/api/market-data/historical/',
                   '/api/market-data/technical-analysis/', '/api/market-data/orderbook/',
                   '/api/market-data/trades/', '/api/signals/manual', '/cancel', 'fetch(`/api/signals/${signalId}`)']
        for pattern in retired:
            self.assertNotIn(pattern, rendered)
        for path in ['/api/prices', '/api/chart-data', '/api/backtests', '/api/signals']:
            self.assertEqual(client.get(path).status_code, 200, path)
        for path in ['/api/indicators', '/api/orderbook', '/api/market-trades']:
            self.assertEqual(client.get(path).status_code, 503, path)
        for path in ['/api/orderbook', '/api/market-trades', '/api/signals/manual', '/api/signals/999/cancel']:
            self.assertEqual(client.post(path).status_code, 503)

    def test_launcher_requires_existing_roots_and_loopback(self):
        from trading_stack.paper_server import build_app, parse_args
        root = Path(os.environ['TEAKA_TEST_ARTIFACT_ROOT'])
        args = parse_args(['--data-root', str(root), '--output-root', str(root), '--port', '0'])
        app = build_app(args)
        self.assertEqual(app.config['SQLALCHEMY_DATABASE_URI'], 'sqlite://')
        self.assertFalse(app.debug)
        with self.assertRaises(ValueError):
            build_app(parse_args(['--data-root', str(root / 'missing'), '--output-root', str(root)]))
