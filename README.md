# BTC/USDT PAPER practice

**Status: Running**

- Published UTC: 2026-09-06T19:19:18+00:00
- Worker snapshot observed UTC: 2026-09-06T19:19:14+00:00
- Last processed candle start UTC: 2026-09-06T19:18:00+00:00
- Run deadline UTC: 2026-09-07T00:01:54+00:00
- Next local check UTC: 2026-09-06T19:19:48+00:00

| Virtual metric | USDT |
|---|---:|
| Initial equity | 10000.0000 |
| Current equity | 9998.7722 |
| Total PnL | -1.2278 |
| Realized PnL | -1.2278 |
| Unrealized PnL | +0.0000 |
| Cash | 9998.7722 |
| Fees charged | 0.8996 |

Paper decisions: **199**. Simulated fills: **18**.

Latest simulated mark: **79878.6000 USDT**. This is not a live tick.

Real public Kraken one-minute candles; simulated paper execution only. Unvalidated 20-period SMA practice strategy, long-only, with a 50 USDT entry cap.

Signals use the prior completed candle. Fills simulate the following candle open after that candle completes; protective exits use its OHLC range. Fixed 10 bps fees and 5 bps slippage proxy; spread is not separately modeled. These are practice approximations, not brokerage-equivalent execution.

Held exposure remains marked at the last valid candle when the run stops; no artificial liquidation. If the published timestamp stops advancing, treat this page as stale.
New meaningful one-minute snapshots normally publish at most once per minute; unchanged checks are skipped. GitHub caching may delay visibility. Another chat or reader must poll the stable status URL for updates.

Snapshot generation: `212d7e845b984cf093fbf4084dbd1042`
