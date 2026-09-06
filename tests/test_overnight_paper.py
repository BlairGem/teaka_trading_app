"""Offline contracts for the separate, bounded public-data practice process."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

from trading_stack.overnight_paper import (
    DataError, FetchError, OvernightPaper, StaleData, completed_candles, fetch_public,
    utc,
)


BASE = 1_800_000_000


def payload(end=BASE, *, close=102, opening=102, high=103, low=101):
    rows = []
    for timestamp in range(end - 21 * 60, end + 61, 60):
        value = 100 if timestamp < BASE - 60 else close
        op = value if timestamp < BASE else opening
        hi = max(value, op) + .1 if timestamp < BASE else high
        lo = min(value, op) - .1 if timestamp < BASE else low
        rows.append([timestamp, str(op), str(hi), str(lo), str(value), str(value), '1', 1])
    return {'error': [], 'result': {'XBTUSDT': rows, 'last': end}}


class FakeClock:
    def __init__(self, value=BASE + 65):
        self.value = value

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class OvernightTests(unittest.TestCase):
    def test_kraken_empty_minutes_are_valid_but_never_fill(self):
        runner = self.runner()
        runner.process(payload(), BASE + 65)
        data = payload(BASE + 60)
        data['result']['XBTUSDT'][-2][1:] = ['102', '102', '102', '102', '0', '0', 0]
        result = runner.process(data, BASE + 125)
        self.assertEqual(result['fill_count'], 0)
        self.assertEqual(result['event']['decision'], 'no_market_trades')
        self.assertEqual(runner.last, BASE + 60)
        invalid = payload(BASE + 120)
        invalid['result']['XBTUSDT'][-2][5] = '0'
        with self.assertRaises(DataError):
            completed_candles(invalid, BASE + 185)

    def runner(self, **kwargs):
        root = Path(os.environ.get('TEAKA_TEST_ARTIFACT_ROOT',
                                  str(Path(__file__).resolve().parents[1] / 'paper_trading/state/test-artifacts')))
        output = root / ('overnight-' + uuid.uuid4().hex)
        clock = kwargs.pop('clock', FakeClock())
        return OvernightPaper(output, wall=clock.now, monotonic=clock.now,
                              sleep=clock.sleep, **kwargs)

    def test_startup_warmup_dedup_then_next_open_only(self):
        runner = self.runner()
        first = runner.process(payload(), BASE + 65)
        self.assertEqual(first['decision_count'], 1)
        self.assertEqual(first['fill_count'], 0)
        runner.process(payload(), BASE + 66)
        self.assertEqual(runner.decision_count, 1)
        runner.process(payload(BASE + 60), BASE + 125)
        self.assertEqual(len(runner.broker.fills), 1)
        fill = runner.broker.fills[0]
        self.assertEqual(fill.side, 'BUY')
        self.assertEqual(fill.requested_price, 102)
        self.assertLessEqual(fill.notional, 50 + 1e-9)
        self.assertGreater(fill.fee, 0)
        self.assertGreater(fill.fill_price, fill.requested_price)
        self.assertEqual(fill.timestamp, utc(BASE + 60))
        events = [json.loads(p.read_text()).get('event') for p in runner.output.glob('status-*.json')]
        filled = next(e for e in events if e and e.get('fill'))
        self.assertEqual(filled['simulated_execution_at'], fill.timestamp)
        runner.process(payload(BASE + 60), BASE + 126)
        self.assertEqual(len(runner.broker.fills), 1)

    def test_ignores_incomplete_signal_and_no_lookahead(self):
        runner = self.runner()
        first = payload()
        first['result']['XBTUSDT'][-1][1:6] = ['10000'] * 5
        runner.process(first, BASE + 65)
        second = payload(BASE + 60)
        # Current completed close falls below SMA, but its prior signal is BUY.
        second['result']['XBTUSDT'][-2][1:6] = ['102', '103', '101', '101', '101']
        runner.process(second, BASE + 125)
        self.assertEqual(runner.broker.fills[0].side, 'BUY')
        self.assertEqual(runner.broker.fills[0].requested_price, 102)

    def test_stale_malformed_gaps_and_backward_reject_without_orders(self):
        runner = self.runner()
        runner.process(payload(), BASE + 65)
        for value, now, reason in (
            (payload(), BASE + 241, StaleData),
            (payload(BASE + 120), BASE + 185, DataError),
            (payload(BASE - 60), BASE + 65, DataError),
        ):
            with self.assertRaises(reason):
                runner.process(value, now)
        bad = payload(BASE + 60)
        bad['result']['XBTUSDT'][3][0] += 60
        with self.assertRaises(DataError):
            runner.process(bad, BASE + 125)
        bad = payload(BASE + 60)
        bad['result']['XBTUSDT'][-2][4] = 'NaN'
        with self.assertRaises(DataError):
            runner.process(bad, BASE + 125)
        self.assertEqual(len(runner.broker.fills), 0)
        self.assertEqual(runner.last, BASE)

    def test_revised_processed_bar_fails_closed(self):
        runner = self.runner()
        runner.process(payload(), BASE + 65)
        revised = payload(BASE + 60)
        revised['result']['XBTUSDT'][-3][4] = '102.5'
        with self.assertRaisesRegex(DataError, 'revised'):
            runner.process(revised, BASE + 125)
        self.assertEqual(runner.broker.fills, [])

    def test_stop_first_on_entry_bar_when_both_protective_prices_hit(self):
        runner = self.runner()
        runner.process(payload(), BASE + 65)
        bars = payload(BASE + 60)
        bars['result']['XBTUSDT'][-2][2:4] = ['110', '90']
        runner.process(bars, BASE + 125)
        buy, sell = runner.broker.fills
        self.assertEqual(sell.side, 'SELL')
        self.assertAlmostEqual(sell.requested_price, buy.fill_price * .98)
        self.assertEqual(runner.broker.positions['BTC-USDT'].quantity, 0)
        self.assertLess(runner.broker.cash, 10000)
        events = [json.loads(p.read_text()).get('event') for p in runner.output.glob('status-*.json')]
        protective = next(e for e in events if e and e.get('reason') == 'entry_bar_stop' and e.get('fill'))
        self.assertIsNone(protective['simulated_execution_at'])
        self.assertIn('bucket', protective['fill_timestamp_semantics'])
        self.assertEqual(protective['execution_candle_start'], sell.timestamp)

    def test_held_stop_uses_worse_gap_open(self):
        runner = self.runner()
        runner.process(payload(), BASE + 65)
        runner.process(payload(BASE + 60), BASE + 125)
        bars = payload(BASE + 120)
        bars['result']['XBTUSDT'][-2][1:6] = ['90', '103', '89', '102', '102']
        runner.process(bars, BASE + 185)
        self.assertEqual(runner.broker.fills[-1].requested_price, 90)
        self.assertEqual(runner.broker.fills[-1].side, 'SELL')

    def test_broker_kill_switch_still_blocks_entry(self):
        runner = self.runner()
        runner.process(payload(), BASE + 65)
        runner.broker.kill_switch = True
        runner.process(payload(BASE + 60), BASE + 125)
        self.assertEqual(runner.broker.fills[-1].status, 'REJECTED')
        self.assertEqual(runner.broker.fills[-1].reason, 'kill_switch_active')
        self.assertFalse(runner.broker.positions)

    def test_below_sma_flat_never_shorts(self):
        runner = self.runner()
        runner.process(payload(close=98, opening=98, high=99, low=97), BASE + 65)
        runner.process(payload(BASE + 60, close=98, opening=98, high=99, low=97), BASE + 125)
        self.assertEqual(runner.broker.fills, [])

    def test_stop_preserves_held_exposure_and_immutable_files(self):
        runner = self.runner(fetch=lambda: self.fail('STOP must prevent fetch'))
        runner.process(payload(), BASE + 65)
        runner.process(payload(BASE + 60), BASE + 125)
        original = (runner.output / 'status-000001.json').read_bytes()
        (runner.output / 'STOP').open('x').close()
        result = runner.run()
        self.assertEqual(result['state'], 'stopped')
        self.assertTrue(result['held_exposure_not_liquidated'])
        self.assertEqual(result['fill_count'], 1)
        self.assertGreater(result['position']['quantity'], 0)
        self.assertAlmostEqual(result['economics']['equity'] - 10000,
                               result['economics']['realized_pnl'] + result['economics']['unrealized_pnl'])
        self.assertEqual(original, (runner.output / 'status-000001.json').read_bytes())
        self.assertEqual(json.loads((runner.output / 'final-status.json').read_text())['state'], 'stopped')
        with self.assertRaises(FileExistsError):
            OvernightPaper(runner.output)

    def test_loop_retries_then_stops_at_deadline_without_postdeadline_trade(self):
        clock = FakeClock()
        calls = []
        def fetch():
            calls.append(clock.now())
            if len(calls) == 1:
                raise FetchError('public_transport_failure')
            return payload()
        runner = self.runner(clock=clock, fetch=fetch, hours=10 / 3600, poll_seconds=1)
        result = runner.run()
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(result['fill_count'], 0)
        self.assertEqual(calls[1] - calls[0], 5)
        self.assertEqual(clock.now(), BASE + 75)

    def test_stale_loop_has_no_trades_and_gap_is_fatal(self):
        clock = FakeClock(BASE + 300)
        runner = self.runner(clock=clock, fetch=payload, hours=6 / 3600)
        result = runner.run()
        self.assertEqual(result['fill_count'], 0)
        states = [json.loads(p.read_text())['state'] for p in runner.output.glob('status-*.json')]
        self.assertIn('paused_stale', states)
        clock = FakeClock()
        values = iter([payload(), payload(BASE + 120)])
        def gap_fetch():
            value = next(values)
            clock.value = value['result']['last'] + 65
            return value
        runner = self.runner(clock=clock, fetch=gap_fetch)
        result = runner.run()
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['error'], 'missed_candle_no_catchup')
        self.assertEqual(result['fill_count'], 0)

    def test_fixed_public_transport_refuses_redirect_and_private_routes(self):
        with patch('trading_stack.overnight_paper.http.client.HTTPSConnection') as connection:
            response = connection.return_value.getresponse.return_value
            response.status = 302
            with self.assertRaises(FetchError):
                fetch_public()
            connection.assert_called_once_with('api.kraken.com', timeout=20)
            args, kwargs = connection.return_value.request.call_args
            self.assertEqual(args, ('GET', '/0/public/OHLC?pair=XBTUSDT&interval=1'))
            self.assertNotIn('Authorization', kwargs['headers'])
            connection.return_value.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
