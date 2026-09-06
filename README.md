# BTC/USDT PAPER practice

**Status: Running**

- Published UTC: 2026-09-06T17:03:48+00:00
- Worker snapshot observed UTC: 2026-09-06T17:03:38+00:00
- Last processed candle start UTC: 2026-09-06T17:02:00+00:00
- Run deadline UTC: 2026-09-07T00:01:54+00:00
- Next local check UTC: 2026-09-06T17:04:18+00:00

| Virtual metric | USDT |
|---|---:|
| Initial equity | 10000.0000 |
| Current equity | 9999.2233 |
| Total PnL | -0.7767 |
| Realized PnL | -0.7767 |
| Unrealized PnL | +0.0000 |
| Cash | 9999.2233 |
| Fees charged | 0.4997 |

Paper decisions: **63**. Simulated fills: **10**.

Latest simulated mark: **79676.1000 USDT**. This is not a live tick.

Real public Kraken one-minute candles; simulated paper execution only. Unvalidated 20-period SMA practice strategy, long-only, with a 50 USDT entry cap.

Signals use the prior completed candle. Fills simulate the following candle open after that candle completes; protective exits use its OHLC range. Fixed 10 bps fees and 5 bps slippage proxy; spread is not separately modeled. These are practice approximations, not brokerage-equivalent execution.

Held exposure remains marked at the last valid candle when the run stops; no artificial liquidation. If the published timestamp stops advancing, treat this page as stale.
New meaningful one-minute snapshots normally publish at most once per minute; unchanged checks are skipped. GitHub caching may delay visibility. Another chat or reader must poll the stable status URL for updates.

Snapshot generation: `d0a45f42ac14421bb25777090dc1a19e`
