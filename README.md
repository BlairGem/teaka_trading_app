# BTC/USDT PAPER practice

**Status: Running**

- Published UTC: 2026-09-06T21:52:48+00:00
- Worker snapshot observed UTC: 2026-09-06T21:52:19+00:00
- Last processed candle start UTC: 2026-09-06T21:51:00+00:00
- Run deadline UTC: 2026-09-07T00:01:54+00:00
- Next local check UTC: 2026-09-06T21:53:18+00:00

| Virtual metric | USDT |
|---|---:|
| Initial equity | 10000.0000 |
| Current equity | 9997.8007 |
| Total PnL | -2.1993 |
| Realized PnL | -2.1436 |
| Unrealized PnL | -0.0557 |
| Cash | 9947.8171 |
| Fees charged | 1.5492 |

Paper decisions: **352**. Simulated fills: **31**.

Latest simulated mark: **79951.4000 USDT**. This is not a live tick.

Real public Kraken one-minute candles; simulated paper execution only. Unvalidated 20-period SMA practice strategy, long-only, with a 50 USDT entry cap.

Signals use the prior completed candle. Fills simulate the following candle open after that candle completes; protective exits use its OHLC range. Fixed 10 bps fees and 5 bps slippage proxy; spread is not separately modeled. These are practice approximations, not brokerage-equivalent execution.

Held exposure remains marked at the last valid candle when the run stops; no artificial liquidation. If the published timestamp stops advancing, treat this page as stale.
New meaningful one-minute snapshots normally publish at most once per minute; unchanged checks are skipped. GitHub caching may delay visibility. Another chat or reader must poll the stable status URL for updates.

Snapshot generation: `922754a51f5a4f96a246bb43e351825a`
