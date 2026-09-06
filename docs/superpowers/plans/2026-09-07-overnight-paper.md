# Overnight paper practice implementation

Blair explicitly requested completing and running unattended paper practice before sleeping, with reasonable conservative defaults. The current authenticated finite-demo session must remain intact. No live orders, broker credentials, paid API, Windows service, restart of the current server, or GitHub push is authorized.

## Concrete design

A separate bounded Python process reads only Kraken public BTC/USDT one-minute OHLC data. This endpoint was verified reachable locally without credentials. Official semantics: https://docs.kraken.com/api-reference/market-data/get-ohlc-data . The final current candle is incomplete and excluded. Only fresh completed candles may produce simulated decisions; warmup history is not traded. Simulations use prior completed data for their signal and the following completed candle's opening price, explicitly labeled delayed candle simulation rather than real exchange fills.

Use the existing paper-only broker with virtual 10,000 USDT, a maximum 50 USDT order/position, one long BTC position, fees and slippage, 2% stop and 4% target, and existing broker protections. Practice rule: prior closing price above the 20-period SMA can buy when flat; below it can sell a held position. This is unvalidated practice, not an investment recommendation or a trained/profitable model.

Poll once per minute for eight hours. Deduplicate candle timestamps; reject malformed, stale, reversed or missing candles. Do not fabricate missing data, replay historical catch-up orders, or restart into the same run directory. Persist uniquely named snapshots containing process/feed/decision/economic state and stop reason. A STOP marker requests graceful termination; retain held exposure as marked/unrealized rather than inventing a final fill. A unique run marker prevents duplicate use of an output directory.

## Files and work

1. New trading_stack/overnight_paper.py: public fetch validation, finite loop, strategy decisions through existing PaperBroker, durable output, stop behavior.
2. New tests/test_overnight_paper.py: injected synthetic data/time, freshness/gaps/dedup, sizing/protection, startup and stop/persistence checks. Follow failing-test then implementation cycle under the existing offline test guard.
3. New D-drive operational status/stop script and concise user guide; no system service or scheduler changes.
4. Independent review, relevant tests, then hidden launch in a new D-drive run folder. Verify actual owned process and fresh continuing feed/decision snapshots before reporting it running. Report fill counts honestly, including zero if the rule has not entered.
5. Preserve current14284 session. Commit only intended reviewed source locally. No new push.

## Current demo display repair

Local commit bf41113a9e7520de0bbcb1c854fd13a6aa198e9d joins existing authenticated decision records to signals. Reason is visible in the table and Details. Controller regression and existing shared-risk replay regression pass; independent review approved. Static asset was verified served byte-for-byte without restarting the current server. The existing demo completed two fills and seven legitimate shared-pair-exposure rejections. No further demo replay is required.
