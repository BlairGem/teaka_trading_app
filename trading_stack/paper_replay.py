"""Finite CSV replay and provenance export; never starts a scheduler."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
from .paper_runtime import LocalCandleProvider


def confined_path(value, root, suffix):
    root = Path(root).resolve(strict=True)
    path = Path(value).resolve(strict=False)
    if root not in path.parents or path.suffix.lower() != suffix:
        raise ValueError('Replay path must resolve inside the configured local root')
    return path


def replay_csv(runtime, user_id, csv_path, pair, timeframe, start, end, data_origin, output_path):
    with runtime.lock:
        return _replay_csv(runtime, user_id, csv_path, pair, timeframe, start, end, data_origin, output_path)


def _replay_csv(runtime, user_id, csv_path, pair, timeframe, start, end, data_origin, output_path):
    source = Path(csv_path).resolve(strict=True)
    output = Path(output_path).resolve(strict=False)
    if source.suffix.lower() != '.csv' or output.suffix.lower() != '.json' or output.exists():
        raise ValueError('Use a CSV source and a new JSON output path')
    if source.stat().st_size > 20_000_000:
        raise ValueError('CSV exceeds the finite replay size limit')
    content = source.read_bytes()
    signature = (str(source), hashlib.sha256(content).hexdigest(), pair, timeframe, data_origin)
    existing = getattr(runtime, 'csv_signature', None)
    if existing != signature and (runtime.processed_candles or runtime.results or runtime.seen or any(b.fills for b in runtime.accounts.values())):
        raise ValueError('A different CSV requires a fresh runtime to preserve account history')
    from io import BytesIO
    data = pd.read_csv(BytesIO(content))
    if set(data.columns) != {'timestamp', 'open', 'high', 'low', 'close', 'volume'} or len(data) > 100000:
        raise ValueError('CSV must contain timestamp, open, high, low, close, volume only; maximum 100000 rows')
    data = data.set_index('timestamp')
    provider = LocalCandleProvider({pair: data}, data_origin, timeframe)
    # Reserve the output before changing account state; preserve failed artifacts.
    with output.open('x', encoding='utf-8') as handle:
        if existing != signature:
            runtime.provider = provider
            runtime.csv_signature = signature
        result = runtime.replay(user_id, start, end)
        result = dict(result, source_path=str(source), source_sha256=signature[1])
        json.dump(result, handle, indent=2, allow_nan=False)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Replay local USDT candles through recovered ORM strategies in paper mode')
    for name in ('csv', 'strategies', 'pair', 'timeframe', 'start', 'end', 'data-origin', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    from .app import create_app
    from .models import db, User, TradingStrategy
    app = create_app()
    with app.app_context():
        user = User(username='local_replay', email='local-replay@example.invalid', password_hash='no-login', max_position_size_pct=80, max_open_positions=10)
        db.session.add(user)
        db.session.flush()
        definitions = json.loads(Path(args.strategies).read_text(encoding='utf-8'))
        if not isinstance(definitions, list) or not definitions:
            raise ValueError('Provide a nonempty strategy definition list')
        for entry in definitions:
            strategy = TradingStrategy(user_id=user.id, name=entry['name'], timeframe=args.timeframe, is_active=True,
                risk_per_trade_pct=entry['risk_per_trade_pct'], stop_loss_pct=entry['stop_loss_pct'], take_profit_pct=entry['take_profit_pct'])
            strategy.set_trading_pairs([args.pair])
            strategy.set_indicators_config(entry['indicators_config'])
            strategy.set_entry_conditions(entry['entry_conditions'])
            strategy.set_exit_conditions(entry.get('exit_conditions', []))
            db.session.add(strategy)
        db.session.commit()
        result = replay_csv(app.extensions['paper_runtime'], user.id, args.csv, args.pair, args.timeframe,
                            args.start, args.end, args.data_origin, args.output)
        print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
