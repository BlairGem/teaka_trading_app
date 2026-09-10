from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from paper_broker import PaperBroker, load_config


def momentum_signal(previous: float, current: float, threshold: float) -> str | None:
    change = (current - previous) / previous
    if change >= threshold:
        return "BUY"
    if change <= -threshold:
        return "SELL"
    return None


def run_ticks(config_path: Path, ticks_path: Path, log_path: Path, threshold: float) -> dict:
    broker = PaperBroker(load_config(config_path), log_path)
    previous: dict[str, float] = {}

    with ticks_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"timestamp", "symbol", "price"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"ticks CSV must contain {sorted(required)}")

        for row in reader:
            symbol = row["symbol"]
            price = float(row["price"])
            broker.mark(symbol, price)
            prior = previous.get(symbol)
            if prior is not None:
                signal = momentum_signal(prior, price, threshold)
                if signal == "BUY":
                    max_notional = min(
                        broker.config.max_order_notional,
                        broker.equity() * broker.config.max_position_pct,
                    )
                    quantity = max_notional / price * 0.25
                    broker.submit_market_order(
                        symbol, "BUY", quantity, price, "momentum_demo"
                    )
                elif signal == "SELL":
                    position = broker.positions.get(symbol)
                    if position and position.quantity > 0:
                        broker.submit_market_order(
                            symbol,
                            "SELL",
                            position.quantity,
                            price,
                            "momentum_demo",
                        )
            previous[symbol] = price

    return broker.snapshot()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run TeAka in paper-only mode using CSV ticks."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("paper_trading/config.example.json"),
    )
    parser.add_argument("--ticks", type=Path, required=True)
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("paper_trading/state/paper_fills.jsonl"),
    )
    parser.add_argument("--threshold", type=float, default=0.01)
    args = parser.parse_args()
    result = run_ticks(args.config, args.ticks, args.log, args.threshold)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
