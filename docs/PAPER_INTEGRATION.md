# Local paper session

The actual recovered application is available as a loopback-only, single-process
paper session with an in-memory database. Its local HTML, JavaScript and CSS
support account creation, strategy editing, local CSV replay, balances, signals,
paper fills, owned positions, manual orders/close and dated backtests without
external assets. This is finite offline simulation; live-provider readiness is
not claimed.

## Start the actual application

From PowerShell, use the approved isolated environment. No installation or
environment activation is needed. Create a new output folder so every session's
exports are easy to distinguish; the server requires both roots to already exist.

```powershell
Set-Location 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907'
$paperOutput = Join-Path 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\paper_trading\state\test-artifacts' ('session-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $paperOutput
& '.\.venv-paper\Scripts\python.exe' -B -m trading_stack.paper_server --data-root 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\fixtures\paper-session' --output-root $paperOutput --port 0
```

Open the exact `PAPER_URL=http://127.0.0.1:<port>` printed by the launcher in a
browser. Port 0 selects an unused port; a fixed free port may also be supplied.
Only 127.0.0.1 is bound. The launcher uses one process without threading,
debugging or a reloader. It creates no scheduler and starts no live adapters.
Stop with Ctrl+C. Accounts, strategies, signals, fills and backtests disappear
when the process stops; exported replay JSON remains in the output folder.
Create a new local session user after restarting. Use disposable credentials and
an `example.invalid` email label, not an existing external account. No mail is sent.

The root `app.py` is an unrelated placeholder and is not this entrypoint.
The actual factory is `trading_stack.app.create_app`. Persistent database URLs
are rejected/ignored as documented by that factory; inherited live flags are
forced off. Runtime dependencies are in `requirements-paper.txt`, already
installed in `.venv-paper` (Python 3.12.14; Flask 3.1.0, Flask-Login 0.6.3,
Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.40, requests 2.32.3, NumPy 2.3.5,
Pandas 3.0.1). No request manager or requests-based market provider runs here.

## Complete a session

1. Create a disposable local user and log in. The initial simulated account has
   10000 USDT cash. Until a replay completes, quotes are explicitly unavailable.
2. On Session or Strategies, save the labeled synthetic SMA example. The compact
   editor supports one SMA/EMA/RSI/MACD, a numeric rule with explicit BUY or SELL,
   optional SELL exit, and risk/stop/take settings. MACD uses 12/26/9. Indicator
   IDs and references are stable (`sma_entry_indicator`, for example). Additional
   strategies can be created. Activate/deactivate and Edit affect owned strategies.
3. On Session, use the displayed CSV path, `synthetic_ui_fixture` origin, BTC/USDT,
   1h, and January 1, 2026 00:00–04:00 UTC. Run finite replay. Its results contain
   actual decisions, fills, fees, source SHA256 and economic totals. Every replay
   reserves a unique `paper-run-<uuid>.json` under the output root. Existing
   outputs are not overwritten. Failed reserved outputs are retained.
4. Inspect current paper cash/equity, actual signals and executions. On Candles,
   Show candles presents completed OHLCV. On Signals & fills, Details displays
   actual signal data; pending signals may be executed with an explicit quantity.
5. After replay, submit a small manual BUY such as 0.1 BTC. It uses the last
   completed historical price with costs. Close paper position sells that owned
   lot. Manual SELL reduces only manually owned exposure; it does not open shorts.
6. On Backtesting, select an owned strategy, pair, inclusive completed date range
   and initial USDT balance. Run dated backtest, then inspect actual result data
   and history. A backtest does not mutate account cash or advance the clock.
7. Settings changes finite paper risk limits only. Profile shows the local user.
   Broker/credential, profile changes and notification operations are unavailable.

## Simulation boundaries

Each user has one shared USDT account with strategy-owned lots. BTC/USDT,
ETH/USDT and SOL/USDT controls are present, but a pair is usable only when local
data exists for it. The web session loads one pair/timeframe CSV; the current
editor is 1h. Custom strategy JSON may be submitted to owned `/api/strategies`
POST/PUT using the canonical contract. Ambiguous duplicate indicator types reject.
The compact editor refuses multi-indicator/multi-pair or other unrepresentable
strategies rather than replacing them with its smaller schema.
It validates the entire definition before populating any form field. Unsupported
timeframes/operators, price/close references and incompatible exit references or
sides leave the current draft, including its hidden strategy ID, untouched.
Stored SMA/EMA/RSI configurations with omitted periods use the canonical defaults
20/20/14 when edited; a name-only save preserves those calculation semantics.

One process owns one dataset and a monotonic shared clock. A different dataset
after any replay activity, or historical rewind, requires a fresh process. An
identical replay returns cached economics without duplicate fills. New requests
still produce distinct export names. Another user's held exposure blocks forward
advancement; its owner cannot skip available intervening candles. Close that
exposure at the current clock or use a fresh independent session. Finite replay
liquidates remaining positions at its last close. Live time does not advance the
simulation. API failures visibly mark displayed values stale.

The engine and backtest both use prior completed candle decisions, next-open
fills and intrabar protection; fees default to 10 bps and slippage to 5 bps.
Their position-sizing/cost bases can produce slightly different quantities;
they are separate simulations, not identical performance series. No currency
conversion or non-USDT accounting is offered. Recovered data/models have not
been loaded. ML learning/prediction, MATLAB, futures, WebSockets, extra technical
analysis, live feeds, order books, market trade tapes, manual signal creation,
signal cancellation, messaging and broker connections are explicitly unavailable.
No displayed synthetic metric is an investment or profitability claim.

The 12 old request patterns are retired from rendered pages: manual trade uses
`/api/execute-trade`; backtest run/history/detail use `/api/backtests` and its owned
ID route; market quote/history use `/api/prices` and `/api/chart-data`; technical
analysis, order book and market tape controls are unavailable; manual signals and
cancellation are unavailable; signal details use the owned signal list response.
Legacy templates/scripts remain preserved as historical source but are not loaded
by this factory. No duplicate legacy controller runs.

## Verification

Run the guarded offline suite from the worktree:

```powershell
& '.\.venv-paper\Scripts\python.exe' -I tests/run_offline.py
```

This installs socket/process/write/deletion and memory-only SQLite guards before
application imports, includes the actual Flask test-client session, and preserves
unique outputs under `paper_trading/state/test-artifacts/run-*`. Do not replace it
with unguarded test discovery. Synthetic provenance is beside the fixture CSV.

After offline tests pass, the separately authorized finite browser smoke uses the
real launcher, exact own-origin interception, explicit retained profile and
artifact directories, and installed Chromium. It starts/stops only its own server
and browser; it never cleans evidence. The machine-specific installed tooling is:

```powershell
& 'C:\Users\Blair\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/browser_paper_smoke.cjs
```

Each `browser-*` folder preserves `browser-results.json`, `launcher-output.txt`,
screenshots, `paper-run-*.json`, `profile` and `browser-artifacts`. This test uses
disposable memory-only users and never a personal browser profile. It proves the
local controls work with outside origins blocked, not that external providers work.
