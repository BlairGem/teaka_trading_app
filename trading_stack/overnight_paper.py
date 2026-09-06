"""Bounded, unauthenticated public-candle PAPER practice in its own directory.

This unvalidated SMA practice strategy uses delayed candle simulation: a signal
from a completed minute can fill at the following minute's open only after that
minute has completed. Startup warms up without filling historical orders.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import http.client
import json
import math
import os
from pathlib import Path
import signal
import time

from paper_trading.paper_broker import PaperBroker, PaperConfig


SOURCE = 'https://api.kraken.com/0/public/OHLC?pair=XBTUSDT&interval=1'
SYMBOL = 'BTC-USDT'


def utc(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


class DataError(ValueError):
    """Fatal data integrity error; message is a fixed, safe reason code."""


class StaleData(DataError):
    pass


class FetchError(Exception):
    pass


def fetch_public():
    """Only this fixed public GET; no redirects, proxies, auth, or order route."""
    connection = http.client.HTTPSConnection('api.kraken.com', timeout=20)
    try:
        connection.request('GET', '/0/public/OHLC?pair=XBTUSDT&interval=1',
                           headers={'Accept': 'application/json', 'User-Agent': 'Teaka-Paper-Practice/1'})
        response = connection.getresponse()
        if response.status != 200:
            raise FetchError('public_http_failure')
        body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise DataError('response_too_large')
        try:
            return json.loads(body)
        except (ValueError, UnicodeError):
            raise DataError('malformed_json') from None
    except (OSError, http.client.HTTPException):
        raise FetchError('public_transport_failure') from None
    finally:
        connection.close()


@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def completed_candles(payload, now):
    """Validate the feed before any state change; always exclude last OHLC row."""
    try:
        if not isinstance(payload, dict) or payload.get('error') != []:
            raise DataError('public_api_error')
        result = payload['result']
        keys = [key for key in result if key != 'last']
        if len(keys) != 1 or keys[0] not in ('XBTUSDT', 'XXBTUSDT'):
            raise DataError('unexpected_pair')
        rows = result[keys[0]]
        if not isinstance(rows, list) or not 22 <= len(rows) <= 1000:
            raise DataError('insufficient_or_excess_candles')
        bars = []
        for row in rows:
            if not isinstance(row, list) or len(row) != 8 or any(isinstance(x, bool) for x in row):
                raise DataError('malformed_candle')
            stamp = float(row[0])
            values = [float(row[i]) for i in (1, 2, 3, 4, 5, 6, 7)]
            if not math.isfinite(stamp) or stamp <= 0 or stamp % 60 or any(not math.isfinite(v) for v in values):
                raise DataError('nonfinite_or_unaligned_candle')
            op, hi, lo, close, vwap, volume, count = values
            if min(op, hi, lo, close, vwap) <= 0 or volume < 0 or count < 0 or count != int(count) or not lo <= min(op, close) <= max(op, close) <= hi:
                raise DataError('invalid_ohlc')
            bar = Candle(int(stamp), op, hi, lo, close, volume)
            if bars and bar.timestamp != bars[-1].timestamp + 60:
                raise DataError('feed_gap_or_backward')
            bars.append(bar)
        completed = bars[:-1]  # Kraken's final row is always uncommitted.
        if completed[-1].timestamp + 60 > now or bars[-1].timestamp > now:
            raise DataError('future_candle')
        if now - (completed[-1].timestamp + 60) > 180:
            raise StaleData('stale_data')
        return completed
    except DataError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError):
        raise DataError('malformed_response') from None


class OvernightPaper:
    def __init__(self, output, *, hours=8, poll_seconds=60, fetch=fetch_public,
                 wall=time.time, monotonic=time.monotonic, sleep=time.sleep):
        if not math.isfinite(hours) or not 0 < hours <= 8:
            raise ValueError('hours must be positive and at most eight')
        if not math.isfinite(poll_seconds) or not 1 <= poll_seconds <= 60:
            raise ValueError('poll_seconds must be between one and sixty')
        self.output = Path(output).resolve()
        # mkdir is the exclusive single-instance reservation. Existing folders,
        # including prior STOP markers, are never reused or modified.
        self.output.mkdir(parents=True, exist_ok=False)
        self.wall, self.monotonic, self.sleep, self.fetch = wall, monotonic, sleep, fetch
        self.started = wall()
        self.duration, self.poll_seconds = hours * 3600, poll_seconds
        self.deadline = monotonic() + self.duration
        self.sequence = 0
        self.last = None
        self.last_bar = None
        self.stop_price = self.take_price = None
        self.decision_count = 0
        self.stop_requested = False
        self.broker = PaperBroker(PaperConfig(max_order_notional=50, max_position_pct=0.005,
                                             allowed_symbols=(SYMBOL,)),
                                  clock=lambda: utc(self.last) if self.last is not None else utc(self.wall()))
        self.write('run-marker.json', {'pid': os.getpid(), 'started_at': utc(self.started)})
        self.write('manifest.json', {
            'mode': 'paper', 'live_order_routes': False, 'pid': os.getpid(),
            'started_at': utc(self.started), 'deadline_at': utc(self.started + self.duration),
            'duration_seconds': self.duration, 'poll_seconds': poll_seconds,
            'source': SOURCE, 'symbol': SYMBOL, 'timeframe_seconds': 60,
            'execution_model': 'delayed candle simulation; prior completed SMA signal, next completed candle open',
            'fill_limitations': 'Fixed fees and 5bps slippage proxy; spread is not separately modeled; not brokerage-equivalent',
            'strategy': 'unvalidated 20-period SMA; long only; startup warmup without orders',
            'stop_loss_pct': 2, 'take_profit_pct': 4, 'stale_after_seconds': 180,
            'config': asdict(self.broker.config), 'output': str(self.output),
            'stop_control': 'create STOP in this directory; no liquidation on stop',
        })
        self.snapshot('starting')

    def write(self, name, data):
        with (self.output / name).open('x', encoding='utf-8') as handle:
            json.dump(data, handle, indent=2, allow_nan=False)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())

    def snapshot(self, state, *, error=None, event=None, final=False):
        self.sequence += 1
        position = self.broker.positions.get(SYMBOL)
        mark = self.broker.last_prices.get(SYMBOL)
        held = position.quantity if position else 0
        economics = {'currency': 'USDT', 'cash': self.broker.cash,
                     'equity': self.broker.equity(),
                     'realized_pnl': sum(p.realized_pnl for p in self.broker.positions.values()),
                     'unrealized_pnl': held * (mark - position.average_cost) if held and mark is not None else 0,
                     'fees': sum(f.fee for f in self.broker.fills),
                     'drawdown_pct': self.broker.drawdown_pct(),
                     'kill_switch': self.broker.kill_switch}
        result = {'mode': 'paper', 'state': state, 'pid': os.getpid(),
                  'started_at': utc(self.started), 'deadline_at': utc(self.started + self.duration),
                  'updated_at': utc(self.wall()), 'source': SOURCE,
                  'last_candle': utc(self.last) if self.last is not None else None,
                  'last_candle_close_at': utc(self.last + 60) if self.last is not None else None,
                  'mark_price': mark, 'mark_is_last_valid_candle': True,
                  'decision_count': self.decision_count,
                  'fill_count': sum(f.status == 'FILLED' for f in self.broker.fills),
                  'order_count': len(self.broker.fills), 'economics': economics,
                  'position': dict(asdict(position), stop_price=self.stop_price, take_price=self.take_price) if position else None,
                  'error': error, 'event': event,
                  'held_exposure_not_liquidated': bool(held) if final else None}
        self.write(f'status-{self.sequence:06d}.json', result)
        if final:
            self.write('final-status.json', result)
        return result

    def stopped(self):
        return self.stop_requested or (self.output / 'STOP').exists()

    def submit(self, side, quantity, price, reason, event):
        # Durable intent precedes the in-memory broker change.
        event = dict(event, observed_at=utc(self.wall()),
                     fill_timestamp_semantics='candle_start_bucket; exact only for opening fills',
                     simulated_execution_at=utc(self.last) if reason in ('sma_entry', 'sma_exit', 'stop_gap', 'take_gap') else None,
                     execution_candle_start=utc(self.last),
                     execution_candle_end=utc(self.last + 60))
        self.snapshot('order_intent', event=dict(event, side=side, quantity=quantity,
                                               requested_price=price, reason=reason))
        fill = self.broker.submit_market_order(SYMBOL, side, quantity, price, 'overnight_sma20')
        self.snapshot('running', event=dict(event, reason=reason, fill=asdict(fill)))
        return fill

    def process(self, payload, now):
        bars = completed_candles(payload, now)
        bar = bars[-1]
        if self.last is not None:
            if bar.timestamp < self.last:
                raise DataError('backward_data')
            prior = next((b for b in bars if b.timestamp == self.last), None)
            if prior != self.last_bar:
                raise DataError('revised_or_missing_processed_candle')
            if bar.timestamp == self.last:
                return self.snapshot('waiting_for_candle')
            if bar.timestamp != self.last + 60:
                raise DataError('missed_candle_no_catchup')
        first = self.last is None
        self.last, self.last_bar = bar.timestamp, bar
        self.decision_count += 1
        prior = bars[-21:-1]
        sma = sum(b.close for b in prior) / 20
        signal_close = prior[-1].close
        event = {'candle': asdict(bar), 'fetched_at': utc(now),
                 'signal_candle': utc(prior[-1].timestamp), 'signal_close': signal_close,
                 'sma20': sma, 'signal_closes': [b.close for b in prior],
                 'execution_model': 'delayed candle simulation'}
        if first:
            self.broker.mark(SYMBOL, bar.close)
            return self.snapshot('running', event=dict(event, decision='startup_warmup_no_order'))
        position = self.broker.positions.get(SYMBOL)
        held = position.quantity if position else 0
        decision = 'hold_long' if held else 'hold_flat'
        if held:
            # Protective orders predate this candle. An opening gap executes at
            # the worse opening price for stops; simultaneous OHLC hits stop first.
            if bar.open <= self.stop_price:
                reason, price = 'stop_gap', bar.open
            elif bar.open >= self.take_price:
                reason, price = 'take_gap', self.take_price
            elif signal_close < sma:
                reason, price = 'sma_exit', bar.open
            elif bar.low <= self.stop_price:
                reason, price = 'stop_loss', self.stop_price
            elif bar.high >= self.take_price:
                reason, price = 'take_profit', self.take_price
            else:
                reason = None
            if reason:
                fill = self.submit('SELL', held, price, reason, event)
                decision = reason + '_' + fill.status.lower()
                if fill.status == 'FILLED':
                    self.stop_price = self.take_price = None
        elif signal_close > sma:
            fill_price = bar.open * (1 + self.broker.config.slippage_bps / 10000)
            cap = min(50, self.broker.config.max_order_notional,
                      self.broker.equity() * self.broker.config.max_position_pct,
                      self.broker.cash / (1 + self.broker.config.fee_bps / 10000))
            if cap > 0:
                fill = self.submit('BUY', cap / fill_price, bar.open, 'sma_entry', event)
                decision = 'sma_entry_' + fill.status.lower()
                if fill.status == 'FILLED':
                    self.stop_price, self.take_price = fill.fill_price * .98, fill.fill_price * 1.04
                    # Entry is at the open, so the same candle can hit its stop.
                    if bar.low <= self.stop_price or bar.high >= self.take_price:
                        stop = bar.low <= self.stop_price
                        exit_fill = self.submit('SELL', fill.quantity,
                                               self.stop_price if stop else self.take_price,
                                               'entry_bar_stop' if stop else 'entry_bar_take', event)
                        if exit_fill.status == 'FILLED':
                            self.stop_price = self.take_price = None
                        decision += '_then_' + ('stop_' if stop else 'take_') + exit_fill.status.lower()
        self.broker.mark(SYMBOL, bar.close)
        return self.snapshot('running', event=dict(event, decision=decision))

    def wait(self, seconds):
        until = min(self.monotonic() + seconds, self.deadline)
        while self.monotonic() < until and not self.stopped():
            self.sleep(min(1, until - self.monotonic()))

    def run(self):
        failures = 0
        state, error = 'completed', None
        try:
            while self.monotonic() < self.deadline:
                if self.stopped():
                    state = 'stopped'
                    break
                try:
                    payload = self.fetch()
                    if self.stopped():
                        state = 'stopped'
                        break
                    if self.monotonic() >= self.deadline:
                        break
                    self.process(payload, self.wall())
                    failures = 0
                except StaleData:
                    self.snapshot('paused_stale', error='stale_data_no_trades')
                    failures += 1
                except FetchError:
                    self.snapshot('retrying', error='public_data_unavailable_no_trades')
                    failures += 1
                self.wait(min(60, 5 * 2 ** min(failures - 1, 4)) if failures else self.poll_seconds)
        except DataError as exc:
            state, error = 'failed', str(exc)
        except KeyboardInterrupt:
            state = 'stopped'
        except Exception:
            # Never persist arbitrary exception text, environment, or credentials.
            state, error = 'failed', 'unexpected_failure'
        if self.stopped() and state == 'completed':
            state = 'stopped'
        return self.snapshot(state, error=error, final=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New unique directory; never reuse a run directory')
    parser.add_argument('--hours', type=float, default=8)
    parser.add_argument('--poll-seconds', type=float, default=60)
    args = parser.parse_args(argv)
    runner = OvernightPaper(args.output, hours=args.hours, poll_seconds=args.poll_seconds)
    def stop_signal(_signum, _frame):
        runner.stop_requested = True
    signal.signal(signal.SIGINT, stop_signal)
    signal.signal(signal.SIGTERM, stop_signal)
    result = runner.run()
    print(json.dumps({'state': result['state'], 'output': str(runner.output), 'mode': 'paper'}))
    return 1 if result['state'] == 'failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
