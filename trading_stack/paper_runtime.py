"""Local candles and per-user virtual accounts for the recovered ORM engine.

All accounting is in USDT. State lives only for this application process.
Signals observe completed candles; execution uses the next candle open.
"""
from dataclasses import asdict
import json
import math
import threading
from types import SimpleNamespace
import pandas as pd
from paper_trading.paper_broker import PaperBroker, PaperConfig
from .market_data import _normalize_history
from .models import db, User, TradingStrategy, TradingSignal, TradeExecution, PaperRun, PaperDecision
from .risk_management import calculate_position_size, normalize_account_equity, check_risk_limits


def timestamp(value):
    result = pd.Timestamp(value)
    if pd.isna(result):
        raise ValueError('Invalid timestamp')
    if result.tzinfo is not None:
        result = result.tz_convert('UTC').tz_localize(None)
    return result


def positive(value):
    if isinstance(value, bool):
        raise ValueError('Expected a positive finite number')
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError('Expected a positive finite number')
    return result


def supported_pair(pair):
    return isinstance(pair, str) and len(pair.split('/')) == 2 and pair.endswith('/USDT') and bool(pair.split('/')[0])


class LocalCandleProvider:
    def __init__(self, frames, data_origin, timeframe='1h'):
        if not isinstance(data_origin, str) or not data_origin.strip():
            raise ValueError('An explicit data_origin label is required')
        self.data_origin, self.timeframe, self.clock = data_origin.strip(), timeframe, None
        self.frames = {}
        for pair, raw in frames.items():
            if not supported_pair(pair):
                raise ValueError('Paper account supports USDT quoted pairs only')
            frame = raw.copy()
            frame.index = pd.DatetimeIndex([timestamp(item) for item in frame.index])
            if frame.empty or frame.index.has_duplicates:
                raise ValueError('Candles must be nonempty with unique timestamps')
            normalized = _normalize_history(frame, None, None, len(frame))
            normalized.index = normalized.index.tz_convert('UTC').tz_localize(None)
            normalized.attrs['data_origin'] = self.data_origin
            self.frames[pair] = normalized

    def advance(self, when):
        when = timestamp(when)
        if self.clock is not None and when < self.clock:
            raise ValueError('Replay clock cannot move backward')
        guard = getattr(self, '_advance_guard', None)
        if guard is not None:
            guard(when)
        self.clock = when

    def get_historical_data(self, trading_pair, timeframe, *, start_date=None, end_date=None, limit=100):
        data = self.frames.get(trading_pair, pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume']))
        if self.clock is None or timeframe != self.timeframe:
            return data.iloc[:0].copy()
        data = data.loc[data.index <= self.clock]
        if start_date is not None:
            data = data.loc[data.index >= timestamp(start_date)]
        if end_date is not None:
            data = data.loc[data.index <= timestamp(end_date)]
        return data.tail(int(limit)).copy()

    def get_latest_prices(self, pairs, as_of=None):
        result = {}
        for pair in pairs:
            data = self.get_historical_data(pair, self.timeframe, end_date=as_of, limit=1)
            if not data.empty:
                result[pair] = float(data.iloc[-1]['close'])
        return result


class PaperRuntime:
    mode = 'paper'

    def __init__(self, provider, config=None):
        self.provider = provider
        self.config = config or PaperConfig()
        PaperBroker(self.config)  # Validate economics before accepting any work.
        self.accounts, self.lots, self.seen, self.results = {}, {}, set(), {}
        self.processed_candles = set()
        self.current_run = None
        self.lock = threading.RLock()

    @property
    def provider(self):
        return self._provider

    @provider.setter
    def provider(self, provider):
        if (hasattr(self, '_provider') and provider is not self._provider
            and (getattr(self, 'processed_candles', None) or getattr(self, 'results', None)
                 or getattr(self, 'seen', None) or any(b.fills for b in getattr(self, 'accounts', {}).values()))):
            raise ValueError('Replacing processed market data requires a fresh runtime')
        self._provider = provider
        provider._advance_guard = lambda when: self.validate_clock_advance(
            getattr(self, '_advancing_user', None), when)

    def validate_clock_advance(self, user_id, when, scheduled_candles=()):
        """Fail before mutation if advancement would strand any held account.

        A replay may schedule all intermediate candles for its own user. A
        direct engine call must process the next known candle while exposure
        is held. Advancing another user's clock cannot bypass that exposure.
        """
        when = timestamp(when)
        clock = self.provider.clock
        if clock is None or when <= clock:
            return
        held_users = {lot['user_id'] for lot in self.lots.values() if lot['amount'] > 0}
        if held_users - {user_id}:
            raise ValueError('Shared clock advancement would skip a held account; process its candles or close it first')
        if user_id in held_users:
            scheduled = set(scheduled_candles)
            for frame in self.provider.frames.values():
                for candle in frame.index:
                    if clock < candle < when and candle not in scheduled and (user_id, candle.isoformat()) not in self.processed_candles:
                        raise ValueError('Shared clock advancement would skip an unprocessed candle for a held account')

    def _advance_clock(self, user_id, when):
        self.validate_clock_advance(user_id, when)
        self._advancing_user = user_id
        try:
            self.provider.advance(when)
        finally:
            self._advancing_user = None

    def user(self, user_id):
        user = db.session.get(User, int(user_id))
        if user is None:
            raise ValueError('Unknown paper user')
        return user

    def account(self, user_id):
        self.user(user_id)
        if user_id not in self.accounts:
            self.accounts[user_id] = PaperBroker(self.config, clock=lambda: self.provider.clock.isoformat() if self.provider.clock is not None else 'unstarted')
        return self.accounts[user_id]

    def balance(self, user_id):
        broker = self.account(user_id)
        return {'paper': {'equity': broker.equity(), 'cash': broker.cash, 'currency': 'USDT'}}

    def positions(self, user_id):
        return [dict(lot, current_price=self.account(user_id).last_prices.get(lot['trading_pair'].replace('/', '-'), lot['entry_price']))
                for lot in self.lots.values() if lot['user_id'] == user_id and lot['amount'] > 0]

    def decision(self, user_id, strategy_id, pair, status, reason=''):
        row = PaperDecision(run_id=self.current_run, user_id=user_id, strategy_id=strategy_id,
                            candle_time=self.provider.clock.isoformat(), trading_pair=pair,
                            status=status, reason=reason)
        db.session.add(row)
        return row

    def submit(self, user_id, pair, side, quantity, price, *, strategy=None, signal=None,
               stop=None, take=None, lot_id=None, reason='manual'):
        """Validate the actual requested size; SELL can only reduce an owned lot."""
        if self.provider.clock is None:
            raise ValueError('A completed local candle clock is required before orders')
        user = self.user(user_id)
        if not supported_pair(pair):
            raise ValueError('Paper account supports USDT quoted pairs only')
        side = str(side).upper()
        if side not in ('BUY', 'SELL'):
            raise ValueError('side must be BUY or SELL')
        quantity, price = positive(quantity), positive(price)
        strategy_id = strategy.id if strategy is not None else None
        if strategy is not None and strategy.user_id != user_id:
            raise ValueError('Strategy not owned by user')
        if signal is not None and (signal.user_id != user_id or signal.strategy_id != strategy_id):
            raise ValueError('Signal ownership mismatch')
        broker = self.account(user_id)
        equity = normalize_account_equity(self.balance(user_id), pair)
        risk_reason = ''
        owned = self.lots.get(str(lot_id)) if lot_id is not None else None
        if side == 'SELL':
            if not owned or owned['user_id'] != user_id or owned['trading_pair'] != pair or owned['strategy_id'] != strategy_id or quantity > owned['amount'] + 1e-9:
                risk_reason = 'owned_held_quantity_required'
        else:
            if (isinstance(user.max_open_positions, bool) or not isinstance(user.max_open_positions, int)
                or user.max_open_positions < 0 or isinstance(user.max_position_size_pct, bool)
                or not isinstance(user.max_position_size_pct, (int, float))
                or not math.isfinite(user.max_position_size_pct) or not 0 <= user.max_position_size_pct <= 100):
                raise ValueError('Invalid user risk limits')
            stop = positive(stop if stop is not None else price * (1 - user.default_stop_loss_pct / 100))
            take = positive(take if take is not None else price * (1 + user.default_take_profit_pct / 100))
            if not stop < price < take:
                raise ValueError('Invalid long protective prices')
            risk_pct = strategy.risk_per_trade_pct if strategy is not None else 1.0
            max_risk = calculate_position_size(equity, price, stop, risk_pct)
            fill_price = price * (1 + broker.config.slippage_bps / 10000)
            notional = quantity * fill_price
            held = self.positions(user_id)
            if not all(math.isfinite(v) for v in (notional, equity, stop, take)):
                raise ValueError('Nonfinite order economics')
            if quantity > max_risk + 1e-9 or max_risk <= 0:
                risk_reason = 'risk_per_trade_limit'
            elif any(lot['trading_pair'] == pair for lot in held):
                risk_reason = 'shared_pair_exposure'
            elif len(held) >= user.max_open_positions:
                risk_reason = 'max_open_positions'
            elif notional > equity * user.max_position_size_pct / 100 + 1e-9:
                risk_reason = 'user_position_limit'
            else:
                # Keep the strategy's maximum risk budget separate from the
                # requested quantity used for exposure and position limits.
                context = strategy or SimpleNamespace(stop_loss_pct=(price - stop) / price * 100,
                    risk_per_trade_pct=1.0)
                if not check_risk_limits(user, pair, price,
                    account_balance_provider=lambda _: self.balance(user_id),
                    active_positions_provider=self.positions,
                    latest_prices_provider=lambda: {pair: price}, strategy=context,
                    requested_quantity=quantity, stop_loss=stop):
                    risk_reason = 'shared_risk_limits'
        if risk_reason:
            if signal is not None:
                signal.status = 'rejected'
            self.decision(user_id, strategy_id, pair, 'rejected', risk_reason)
            db.session.commit()
            return {'success': False, 'mode': 'paper', 'error': risk_reason}
        symbol = pair.replace('/', '-')
        before_pnl = broker.positions[symbol].realized_pnl if symbol in broker.positions else 0.
        fill = broker.submit_market_order(symbol, side, quantity, price, str(strategy_id) if strategy_id else 'manual')
        filled = fill.status == 'FILLED'
        if signal is not None:
            signal.status = 'executed' if filled else 'rejected'
        execution = TradeExecution(user_id=user_id, strategy_id=strategy_id, signal_id=signal.id if signal is not None else None,
            trading_pair=pair, order_type=side, order_id=fill.order_id, amount=fill.quantity,
            price=fill.fill_price, timestamp=self.provider.clock.to_pydatetime(),
            status=fill.status.lower(), platform='paper', fee=fill.fee,
            pnl=(broker.positions[symbol].realized_pnl - before_pnl) if filled and side == 'SELL' else None,
            is_automated=strategy is not None, executed_by=strategy.name if strategy else 'Manual',
            notes=json.dumps({'reason': reason, 'data_origin': self.provider.data_origin, 'strategy_id': strategy_id, 'run_id': self.current_run}))
        db.session.add(execution)
        db.session.flush()
        if filled and side == 'BUY':
            self.lots[str(execution.id)] = {'id': str(execution.id), 'user_id': user_id,
                'strategy_id': strategy_id, 'trading_pair': pair, 'amount': quantity,
                'entry_price': fill.fill_price, 'stop_loss': stop, 'take_profit': take,
                'order_type': 'BUY', 'platform': 'paper'}
        elif filled:
            owned['amount'] -= quantity
        self.decision(user_id, strategy_id, pair, 'filled' if filled else 'rejected', reason if filled else fill.reason)
        db.session.commit()
        result = asdict(fill)
        result.update(status=fill.status.lower(), execution_id=execution.id, price=fill.fill_price, amount=fill.quantity)
        return {'success': filled, 'mode': 'paper', 'data': result, 'error': fill.reason or None}

    def manual_order(self, user_id, pair, side, quantity):
        with self.lock:
            prices = self.provider.get_latest_prices([pair])
            if pair not in prices:
                raise ValueError('No completed local candle for this pair')
            if str(side).upper() == 'SELL':
                lot = next((p for p in self.positions(user_id) if p['trading_pair'] == pair and p['strategy_id'] is None), None)
                return self.submit(user_id, pair, side, quantity, prices[pair], lot_id=lot['id'] if lot else None)
            return self.submit(user_id, pair, side, quantity, prices[pair])

    def close(self, user_id, position_id, price=None, reason='manual_close'):
        with self.lock:
            lot = self.lots.get(str(position_id))
            if not lot or lot['user_id'] != user_id or lot['amount'] <= 0:
                return {'success': False, 'mode': 'paper', 'error': 'Position not found'}
            strategy = db.session.get(TradingStrategy, lot['strategy_id']) if lot['strategy_id'] else None
            if price is None:
                price = self.provider.get_latest_prices([lot['trading_pair']]).get(lot['trading_pair'])
            return self.submit(user_id, lot['trading_pair'], 'SELL', lot['amount'], price,
                               strategy=strategy, lot_id=lot['id'], reason=reason)

    def replay(self, user_id, start, end):
        from .trading_engine import run_trading_engine
        with self.lock:
            start, end = timestamp(start), timestamp(end)
            if end < start:
                raise ValueError('end must be at or after start')
            key = (user_id, start.isoformat(), end.isoformat())
            if key in self.results:
                return self.results[key]
            times = sorted({t for frame in self.provider.frames.values() for t in frame.index if start <= t <= end})
            if not times or (self.provider.clock is not None and times[0] < self.provider.clock):
                raise ValueError('No replay candles or range moves backward')
            self.validate_clock_advance(user_id, times[-1], scheduled_candles=times)
            self.user(user_id)
            run = PaperRun(user_id=user_id, data_origin=self.provider.data_origin, start_time=start.isoformat(), end_time=end.isoformat())
            db.session.add(run)
            db.session.flush()
            self.current_run = run.id
            initial_fill_count = len(self.account(user_id).fills)
            try:
                for current in times:
                    run_trading_engine(runtime=self, user_id=user_id, candle_time=current)
                for lot in self.positions(user_id):
                    self.close(user_id, lot['id'], reason='final_liquidation')
                broker = self.account(user_id)
                fills = broker.fills[initial_fill_count:]
                economic = {'cash': broker.cash, 'equity': broker.equity(),
                    'realized_pnl': sum(p.realized_pnl for p in broker.positions.values()),
                    'fees': sum(f.fee for f in fills), 'currency': 'USDT'}
                result = {'run_id': run.id, 'mode': 'paper', 'data_origin': self.provider.data_origin,
                    'start': start.isoformat(), 'end': end.isoformat(), 'candle_count': len(times),
                    'decision_count': PaperDecision.query.filter_by(run_id=run.id).count(),
                    'fill_count': sum(f.status == 'FILLED' for f in fills),
                    'economic_summary': economic, 'fee_bps': self.config.fee_bps,
                    'slippage_bps': self.config.slippage_bps,
                    'fills': [asdict(f) for f in fills]}
                run.summary = json.dumps(result, allow_nan=False)
                db.session.commit()
                self.results[key] = result
                return result
            finally:
                self.current_run = None
