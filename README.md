# BTC/USDT PAPER practice

**Status: Running**

- Published UTC: 2026-09-06T16:34:48+00:00
- Worker snapshot observed UTC: 2026-09-06T16:34:34+00:00
- Last processed candle start UTC: 2026-09-06T16:33:00+00:00
- Run deadline UTC: 2026-09-07T00:01:54+00:00
- Next local check UTC: 2026-09-06T16:35:18+00:00

| Virtual metric | USDT |
|---|---:|
| Initial equity | 10000.0000 |
| Current equity | 9999.6183 |
| Total PnL | -0.3817 |
| Realized PnL | -0.3200 |
| Unrealized PnL | -0.0617 |
| Cash | 9949.6316 |
| Fees charged | 0.2499 |

Paper decisions: **34**. Simulated fills: **5**.

Latest simulated mark: **79745.8000 USDT**. This is not a live tick.

Real public Kraken one-minute candles; simulated paper execution only. Unvalidated 20-period SMA practice strategy, long-only, with a 50 USDT entry cap.

Signals use the prior completed candle. Fills simulate the following candle open after that candle completes; protective exits use its OHLC range. Fixed 10 bps fees and 5 bps slippage proxy; spread is not separately modeled. These are practice approximations, not brokerage-equivalent execution.

Held exposure remains marked at the last valid candle when the run stops; no artificial liquidation. If the published timestamp stops advancing, treat this page as stale.
New meaningful one-minute snapshots normally publish at most once per minute; unchanged checks are skipped. GitHub caching may delay visibility. Another chat or reader must poll the stable status URL for updates.

Snapshot generation: `b566dda52fb94bb799e73aeb29701e73`
