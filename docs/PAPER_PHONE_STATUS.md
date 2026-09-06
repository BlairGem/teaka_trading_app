# Phone monitoring for paper practice

Open the repository's **paper-status** branch to read its README status page. The code remains on the reviewed paper integration branch; status snapshots are separate from the code history.

The publisher polls local state every 30 seconds during the bounded practice run and publishes meaningful changes, normally once per completed one-minute candle. Unchanged snapshots do not create commits. Failures trigger backoff. This is snapshot hosting, not a socket or tick stream; GitHub caching can add latency. Always check publication time and source freshness. Another chat must fetch the page or JSON again to observe changes.

Published information is limited to paper mode, the instrument, public candle timestamps, virtual starting/current equity, paper profit and loss, cash, fees, and decision/fill counts. Local paths, process identifiers, credentials, account identifiers and raw logs are excluded. Gold is not enabled by this publisher.

The underlying strategy is an unvalidated SMA practice rule. Real public market candles drive simulated orders; fixed fees/slippage and delayed candle timing do not reproduce actual exchange matching, order-book depth or queue position.

The worker and publisher are separate processes. Publishing failure does not place orders or stop/restart the worker. A stale snapshot or dead worker must not be reported as currently healthy. Publishing ends after the worker's final state or the bounded deadline; it does not create a new trading session.

The publisher uses existing GitHub CLI authentication to publish only README.md and status.json together on the fixed paper-status branch. Both share a generation identifier. A fast-forward-only ref update rejects conflicting changes. It does not force-push, modify the main branch, change repository visibility, create issues or send alerts.

The stable machine-readable URL is https://raw.githubusercontent.com/BlairGem1234/teaka_trading_app/paper-status/status.json . The phone page is https://github.com/BlairGem1234/teaka_trading_app/tree/paper-status . A URL existing does not prove the publisher is healthy: compare the supplied timestamps with current time.
