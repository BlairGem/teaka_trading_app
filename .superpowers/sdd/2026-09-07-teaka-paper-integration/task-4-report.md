# Task 4: paper UI, launcher and end-to-end evidence

Base: `99f0c10c8d744f085197d8126cc4bc1ab5ab877a`. Implementation commit is the
commit containing this report. Worktree/branch were verified before edits.

## Result

The actual recovered package factory now renders a consistent local-assets paper
workspace. All core controls work with external origins blocked: create/login a
memory user; create strategies with explicit BUY/SELL and stable references;
CSV/date/origin replay; actual cash/equity, signals and fills; owned manual order
and close; completed candle table; owned dated backtest/history; and paper risk
settings. No unsupported live/account/notification control reports success.

`trading_stack.paper_pages` replaces the legacy page handlers; new `paper*.html`,
`static/css/paper.css` and `static/js/paper.js` are the only delivered paper UI.
The old templates/scripts remain preserved but inactive. The existing recovered
auth logic is retained for disposable memory users, with local forms replacing
CDN templates and profile writes explicitly unavailable. Broker/notification
POST handlers return 503 without modifying ORM fields. Risk form validation
rejects invalid values before any update.

The API adds authenticated `/api/paper/status` and owned GET `/api/backtests`.
Optional order book, market tape, manual signal and cancel endpoints explicitly
return 503. Existing paper engine, broker, clock and ownership logic are unchanged.
The twelve previously missing request patterns are reconciled as documented in
`docs/PAPER_INTEGRATION.md`; their old handlers are absent from rendered pages and
the one active script. Manual order, replay, candle and backtest contracts are
verified through actual responses and actual browser controls.

The reusable launcher is `python -B -m trading_stack.paper_server` with required
existing `--data-root` and `--output-root`, optional `--port` (0 selects a free
port), literal 127.0.0.1 host, single process/no threads, debug/reloader off,
in-memory database and no external provider initialization. The root placeholder
`app.py` was not modified or started. Exact approved-venv commands, session steps,
result locations and limitations are in `docs/PAPER_INTEGRATION.md`.

## Test-first evidence

All commands ran in `D:\EV_AI\Worktrees\teaka-paper-integration-20260907` with
PowerShell profile loading disabled. No installation, move, deletion, private
data access, external account connection, push or PR was performed. The existing
offline guard remains intact; its only runner change adds the UI test module.

1. RED command: `& ./.venv-paper/Scripts/python.exe -I tests/run_offline.py tests.test_paper_ui`
   produced `Ran 33 tests in 10.739s`, `FAILED (failures=10, errors=5)`, exit 1.
   Six new UI tests failed: missing settings/profile template endpoints, absent
   launcher/status, successful credential/notification writes, invalid risk
   settings silently accepted and missing unavailable routes. The initial import
   accidentally exposed 27 existing test cases to discovery, all passing; the
   import was changed to a module alias so only the six intended cases load.
   Artifacts: `paper_trading/state/test-artifacts/run-61941e9420334317894136fecca0d08c`.
2. Intermediate focused run: six tests, five passed, one failed. The fixture used
   a bare editor ID where normalization requires `<type>_<id>`. The UI and fixture
   now emit the verified reference contract. The next run found Flask-Login's
   cached user in the test's retained app context. The test clears only that
   request-local cache before each request, matching real independent requests;
   all foreign-owner assertions were retained.
3. Focused GREEN, same command: `Ran 6 tests in 2.390s`, `OK`, exit 0.
   Artifacts: `paper_trading/state/test-artifacts/run-d27b523e9ec34036add2ec0eba5ae9ca`.
4. Full guarded suite: `& ./.venv-paper/Scripts/python.exe -I tests/run_offline.py`
   produced `Ran 102 tests in 10.143s`, `OK`, exit 0. Artifacts:
   `paper_trading/state/test-artifacts/run-fa505dc411954d4f97250153f23eaf53`.
   This includes all previous 96 tests plus six UI cases. `ui-full-session.json`
   preserves replay and owned backtest output from the two-user flow. Socket,
   subprocess, persistent SQLite and out-of-artifact writes remained forbidden.
5. After browser visual QA corrected a JavaScript UTF-8 display issue and
   self-review strengthened the exact retired-route assertions/compact-editor
   refusal of multiple pairs/custom MACD periods, the same focused UI command
   produced `Ran 6 tests in 2.134s`, `OK`, exit 0. Final focused artifacts:
   `paper_trading/state/test-artifacts/run-a6d338bb33f743218449b14783017076`.
6. `git diff --check` returned exit 0. LF endings were preserved, so the guard
   runner diff is one added test-module line rather than whole-file churn.

## Actual finite browser evidence

Command, run only after offline GREEN:

```powershell
& 'C:/Users/Blair/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tests/browser_paper_smoke.cjs
```

The script starts the real reusable launcher with `--port 0`, the explicit
synthetic fixture data root and unique output root. It uses installed Playwright
1.62.1 and full Chromium1228 at the explicitly supplied executable path. Both
absolute persistent profile and browser artifacts directories are created before
`launchPersistentContext`; no disposable auto-cleaned directories, tracing,
downloads or personal profile are used. HTTP interception permits only the exact
own origin and blocks other origins; WebSockets are closed and service workers
blocked. Both owned processes stop at the finite end; evidence is retained.

Initial smoke PASS: `browser-c5bdfff0-d954-48c3-9f29-b613f82c9e12`. Its screenshot
was inspected with `view_image`; the JS status separator showed an encoding
artifact, which was corrected. No page errors or external requests occurred.

Final smoke PASS, exit 0, with actual launcher origin `http://127.0.0.1:41883`.
Final evidence root (absolute):

`D:\EV_AI\Worktrees\teaka-paper-integration-20260907\paper_trading\state\test-artifacts\browser-c9f135ec-3c7d-4400-b867-138db568027f`

- `browser-results.json`: nine observed action milestones, success=true,
  errors=[], blocked=[] (the application requested no outside resources).
- `launcher-output.txt`: real launcher startup and finite local HTTP requests.
- `01-ready-to-replay.png`: actual created strategies, explicit sides and visible
  expanded unavailable/shared-clock/memory constraints.
- `02-replay-and-manual-close.png`: actual replay result, cash, manual close,
  no remaining positions, real signals and execution rows.
- `03-dated-backtest.png`: actual local dated backtest and history; inspected
  with `view_image`, confirming readable layout and corrected UTF-8 status text.
- `04-settings.png`: successfully saved local risk values and explicit unsupported
  connection/notification notice.
- `paper-run-*.json`: actual source path/hash, inclusive range and economics.
- `profile/` and `browser-artifacts/`: preserved browser-owned evidence paths.

Observed workflow: create/login disposable memory-only user; create BUY strategy
with SELL exit and second SELL-only strategy; replay five synthetic candles;
assert actual fills/source hash; submit 0.1-unit manual BUY; close its owned lot;
read five completed candles; inspect signals/fills; execute owned dated backtest;
save risk settings; inspect profile; deliberately abort the own-origin status API
and verify a visible stale/unavailable warning rather than a live badge.

Actual synthetic replay economics: 5 candles, 8 decisions, 2 fills; 10001.34775075
USDT cash/equity, 1.3477507500000083 realized P&L, 0.10149925 fees, 10 bps fee and
5 bps slippage. After manual round-trip the displayed cash is 10001.3166 USDT.
The independent dated backtest has one completed trade, final balance
10001.347077211394 USDT and null profit factor (no loss denominator). These are
software-fixture outcomes, not recovered trading performance. The engine/backtest
quantity difference is disclosed; the UI makes no identical-economics claim.

After the final script reported both owned processes stopped, read-only
`Get-NetTCPConnection -LocalPort 41883 -State Listen` found zero listeners.
No unrelated listener was stopped. Final source diff is saved beside this
evidence as `task-4-source.diff` after narrow staging.

## Self-review and limits

Self-review checked one active controller, no external assets, safe textContent
rendering, explicit supported sides/references, actual API shapes, clear error
states, user-owned responses, root confinement, no credential/profile writes,
no live handler imports, and a no-reloader memory-only launcher. The existing
full suite and browser both exercise the real factory/ORM/runtime, not a mock
placeholder. The browser shutdown and final port state were verified.

Ready for a user to start the documented isolated finite offline paper session.
The runtime is intentionally memory-only and uses one forward-only dataset/clock.
Different datasets, rewind or independent historical sessions require a fresh
process; another user's exposure can block clock advancement. Only USDT, local
CSV and the compact supported editor schema are offered. JSON result panels are
functional evidence displays; there is no live chart/order book, fitted model,
FX conversion, ML/MATLAB/futures/provider activation, persistence or account
authentication. Live trading and unrestricted production readiness are not claimed.
