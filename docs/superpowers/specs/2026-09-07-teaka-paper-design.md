# Full TeAka paper integration design

Authorization: Blair explicitly approved repairing and connecting the full paper-trading system through the originating task on 7 September 2026. This document applies the reviewed remediation intent; it is not authorization for live trading. The earlier review findings remain a baseline.

Goal: a finite, repeatable end-to-end simulation through the recovered trading_stack strategy/indicator/risk/engine/ORM/API path, with multiple active strategies sharing a paper account and producing auditable signals, fills, positions, cash, equity and run results. Do not replace this with only the standalone momentum demo.

Approach: keep the existing modules and add explicit dependency boundaries. A paper runtime owns an in-memory account per user, a local candle store and replay state. The existing engine reads strategy rows, generates signals, applies risk and submits to PaperBroker. Multiple strategies are processed deterministically with a shared account/risk budget and correlation IDs. The API/UI can save valid strategies and invoke a finite offline replay; no background service/task is installed.

Alternatives considered: repairing only the standalone script would leave the full app disconnected; activating the current live-capable adapters would bypass paper isolation. Reusing the full engine with injected local market/paper execution is the selected approach.

Constraints:
- Work only in D:/EV_AI/Worktrees/teaka-paper-integration-20260907 on codex/teaka-paper-integration-20260907 based on2953a1107d3bdf1d70bd76f44d311aae8a9eec83.
- Preserve the original dirty C-drive checkout. No fetch/push/PR, source moves/deletions, credentials, account authentication, live orders, system service/task starts or unrelated runtime changes. Isolated local application startup for paper tests is explicitly approved.
- Do not display/store credential values or load Brain/private data, archives, binary models or databases. Exclude F_Drive.
- Local code and tests are authorized. Blair explicitly approved the isolated .venv-paper and requirements-paper.txt installation with required dependencies, reusing bundled numerical libraries; no global environment changes.
- Tests must deny sockets/subprocesses and write only within the isolated worktree/report area. Do not delete test directories or files; preserve uniquely named artifacts.
- Actual datasets/models remain distinct from synthetic fixtures. Every replay output states its data origin and time range. No fabricated training or profitability claim.
- Keep full-stack ML/MATLAB/futures optional and inactive in paper mode when their dependencies/artifacts are absent; no fake trained model output.
- Local commits may include only intended source/tests/docs. Disable repository hooks for commit/worktree operations; never stage secret/Brain/binary assets.

Domain contracts:
- Market candles: timezone-aware UTC timestamp, symbol canonicalized from slash/hyphen form, finite positive OHLC and nonnegative volume; unique increasing timestamps. Replay exposes only rows at or before the current clock.
- Strategy indicator config is a keyed object; accept the existing editor array only via explicit normalization. Conditions use stable calculated column names, supported operators and explicit BUY/SELL side. Empty/missing/invalid/ambiguous conditions do not create a signal.
- Quantity is base-asset units. Risk cash equals quote equity times risk percentage/100; quantity equals risk cash divided by absolute entry-stop distance, capped by account cash, position and order limits. SELL protection direction is validated.
- Balance normalization must happen before numeric sizing; provider routing is explicit. Paper mode does not create broker SDK managers or make market HTTP requests.
- Multiple strategy decisions share one user paper account. Process order is deterministic by strategy ID. Avoid repeated signal/fill for a strategy/pair/candle; record a run ID and decision outcome.
- Paper fill price includes slippage; fees count in cash and realized PnL. No shorting in this implementation. Kill switch blocks new exposure but permits a held long position to be reduced; do not allow an exit to exceed holdings.
- Execution uses an explicitly labeled bar-close simulation convention; no claim of tick-perfect matching. Stop/take processing and risk limits are deterministic and recorded.
- Backtests honor requested start/end and never use future bars/features; outputs are JSON serializable with finite metrics and ISO UTC times.
- Fresh runs start a labeled fresh paper session; no log file is mistaken for recovered persistent account state. Restart/resume beyond explicit replay remains unsupported.
- Flask app import and test-client usage are contained. Test databases are memory-only. No existing DATABASE_URL or provider secrets may be inherited.
- Rendered routes/forms must match implemented endpoints; missing optional capabilities return clear inactive/unavailable responses. Connection and Live labels must reflect simulated/observed state.

Acceptance:
1. Reproduced risk/signal/date faults have failing-before/passing-after regression evidence.
2. Existing four paper assertions still pass; fee reconciliation and risk-reducing exits pass new tests.
3. Full app creates an in-memory user and at least two valid strategies; a supplied synthetic candle sequence drives the real indicators, signal generation, risk checks, engine, PaperBroker and ORM execution records.
4. Repeat replay with the same input yields the same economic results; repeated same-candle processing does not duplicate fills; one strategy cannot bypass shared risk limits.
5. No socket/process/broker activity occurs during import, replay, manual paper API, close, backtest and template tests. No live-mode order path is activated.
6. Reports show strategy decisions, fills/rejections, account reconciliation, input provenance and unsupported optional components.


