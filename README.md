# BTC/USDT PAPER practice

**Status: Running**

- Published UTC: 2026-09-06T23:44:18+00:00
- Worker snapshot observed UTC: 2026-09-06T23:44:06+00:00
- Last processed candle start UTC: 2026-09-06T23:43:00+00:00
- Run deadline UTC: 2026-09-07T00:01:54+00:00
- Next local check UTC: 2026-09-06T23:44:48+00:00

| Virtual metric | USDT |
|---|---:|
| Initial equity | 10000.0000 |
| Current equity | 9997.4840 |
| Total PnL | -2.5160 |
| Realized PnL | -2.5307 |
| Unrealized PnL | +0.0147 |
| Cash | 9947.4319 |
| Fees charged | 1.9491 |

Paper decisions: **464**. Simulated fills: **39**.

Latest simulated mark: **80448.8000 USDT**. This is not a live tick.

Real public Kraken one-minute candles; simulated paper execution only. Unvalidated 20-period SMA practice strategy, long-only, with a 50 USDT entry cap.

Signals use the prior completed candle. Fills simulate the following candle open after that candle completes; protective exits use its OHLC range. Fixed 10 bps fees and 5 bps slippage proxy; spread is not separately modeled. These are practice approximations, not brokerage-equivalent execution.

Held exposure remains marked at the last valid candle when the run stops; no artificial liquidation. If the published timestamp stops advancing, treat this page as stale.
New meaningful one-minute snapshots normally publish at most once per minute; unchanged checks are skipped. GitHub caching may delay visibility. Another chat or reader must poll the stable status URL for updates.

Snapshot generation: `57bf364e992b4387a470bcb8b4215bdd`
