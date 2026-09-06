# BTC/USDT PAPER practice

**Status: Running**

- Published UTC: 2026-09-06T20:02:18+00:00
- Worker snapshot observed UTC: 2026-09-06T20:02:01+00:00
- Last processed candle start UTC: 2026-09-06T20:01:00+00:00
- Run deadline UTC: 2026-09-07T00:01:54+00:00
- Next local check UTC: 2026-09-06T20:02:48+00:00

| Virtual metric | USDT |
|---|---:|
| Initial equity | 10000.0000 |
| Current equity | 9998.5442 |
| Total PnL | -1.4558 |
| Realized PnL | -1.3784 |
| Unrealized PnL | -0.0774 |
| Cash | 9948.5785 |
| Fees charged | 1.0495 |

Paper decisions: **242**. Simulated fills: **21**.

Latest simulated mark: **79826.4000 USDT**. This is not a live tick.

Real public Kraken one-minute candles; simulated paper execution only. Unvalidated 20-period SMA practice strategy, long-only, with a 50 USDT entry cap.

Signals use the prior completed candle. Fills simulate the following candle open after that candle completes; protective exits use its OHLC range. Fixed 10 bps fees and 5 bps slippage proxy; spread is not separately modeled. These are practice approximations, not brokerage-equivalent execution.

Held exposure remains marked at the last valid candle when the run stops; no artificial liquidation. If the published timestamp stops advancing, treat this page as stale.
New meaningful one-minute snapshots normally publish at most once per minute; unchanged checks are skipped. GitHub caching may delay visibility. Another chat or reader must poll the stable status URL for updates.

Snapshot generation: `2ad637d78a024e12b76345b6c8ae0812`
