# BTC/USDT PAPER practice

**Status: Worker identity could not be verified**

- Published UTC: 2026-09-06T16:19:57+00:00
- Worker snapshot observed UTC: 2026-09-06T16:19:46+00:00
- Last processed candle start UTC: 2026-09-06T16:18:00+00:00
- Run deadline UTC: 2026-09-07T00:01:54+00:00
- Next local check UTC: 2026-09-06T16:20:27+00:00

| Virtual metric | USDT |
|---|---:|
| Initial equity | 10000.0000 |
| Current equity | 9999.7683 |
| Total PnL | -0.2317 |
| Realized PnL | -0.1620 |
| Unrealized PnL | -0.0697 |
| Cash | 9949.7888 |
| Fees charged | 0.1499 |

Paper decisions: **19**. Simulated fills: **3**.

Latest simulated mark: **79701.3000 USDT**. This is not a live tick.

Real public Kraken one-minute candles; simulated paper execution only. Unvalidated 20-period SMA practice strategy, long-only, with a 50 USDT entry cap.

Signals use the prior completed candle. Fills simulate the following candle open after that candle completes; protective exits use its OHLC range. Fixed 10 bps fees and 5 bps slippage proxy; spread is not separately modeled. These are practice approximations, not brokerage-equivalent execution.

Held exposure remains marked at the last valid candle when the run stops; no artificial liquidation. If the published timestamp stops advancing, treat this page as stale.
New meaningful one-minute snapshots normally publish at most once per minute; unchanged checks are skipped. GitHub caching may delay visibility. Another chat or reader must poll the stable status URL for updates.

Snapshot generation: `f236db1f01d34508995243771bd37560`
