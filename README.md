# BTC/USDT PAPER practice

**Status: Running**

- Published UTC: 2026-09-06T21:48:48+00:00
- Worker snapshot observed UTC: 2026-09-06T21:48:44+00:00
- Last processed candle start UTC: 2026-09-06T21:47:00+00:00
- Run deadline UTC: 2026-09-07T00:01:54+00:00
- Next local check UTC: 2026-09-06T21:49:18+00:00

| Virtual metric | USDT |
|---|---:|
| Initial equity | 10000.0000 |
| Current equity | 9997.8187 |
| Total PnL | -2.1813 |
| Realized PnL | -2.1436 |
| Unrealized PnL | -0.0376 |
| Cash | 9947.8171 |
| Fees charged | 1.5492 |

Paper decisions: **348**. Simulated fills: **31**.

Latest simulated mark: **79980.3000 USDT**. This is not a live tick.

Real public Kraken one-minute candles; simulated paper execution only. Unvalidated 20-period SMA practice strategy, long-only, with a 50 USDT entry cap.

Signals use the prior completed candle. Fills simulate the following candle open after that candle completes; protective exits use its OHLC range. Fixed 10 bps fees and 5 bps slippage proxy; spread is not separately modeled. These are practice approximations, not brokerage-equivalent execution.

Held exposure remains marked at the last valid candle when the run stops; no artificial liquidation. If the published timestamp stops advancing, treat this page as stale.
New meaningful one-minute snapshots normally publish at most once per minute; unchanged checks are skipped. GitHub caching may delay visibility. Another chat or reader must poll the stable status URL for updates.

Snapshot generation: `50a6153aeb5042c8a1542f249216fd25`
