# Full TeAka Paper Integration Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development task-by-task, with task-scoped review and a final integration review.

Goal: repair and connect the full recovered TeAka stack for deterministic offline paper simulation.
Architecture: retain Flask/ORM strategy and engine components; inject local candles and one shared paper account per user. A finite replay drives multiple strategies with explicit safety, deduplication and provenance.
Tech stack: Python, existing Flask/SQLAlchemy application, pandas/numpy and stdlib PaperBroker. Broker SDKs are unnecessary for paper mode.
Spec: docs/superpowers/specs/2026-09-07-teaka-paper-design.md

## Global Constraints
- Work only in D:/EV_AI/Worktrees/teaka-paper-integration-20260907 on codex/teaka-paper-integration-20260907 based on2953a1107d3bdf1d70bd76f44d311aae8a9eec83.
- Preserve the original dirty C-drive checkout. No fetch/push/PR, source moves/deletions, credentials, account authentication, live orders, system service/task starts or unrelated runtime changes. Isolated local application startup for paper tests is explicitly approved.
- Do not display/store credential values or load Brain/private data, archives, binary models or databases. Exclude F_Drive.
- Local code and tests are authorized. Blair explicitly approved the isolated .venv-paper and requirements-paper.txt installation with required dependencies, reusing bundled numerical libraries; no global environment changes.
- Tests must deny sockets/subprocesses and write only within the isolated worktree/report area. Do not delete test directories or files; preserve uniquely named artifacts.
- Actual datasets/models remain distinct from synthetic fixtures. Every replay output states its data origin and time range. No fabricated training or profitability claim.
- Keep full-stack ML/MATLAB/futures optional and inactive in paper mode when their dependencies/artifacts are absent; no fake trained model output.
- Local commits may include only intended source/tests/docs. Disable repository hooks for commit/worktree operations; never stage secret/Brain/binary assets.

### Task 1: Correct the paper broker accounting and exit boundary

Files: modify paper_trading/paper_broker.py and paper_trading/test_paper_broker.py; create tests/test_paper_accounting.py and tests/run_offline.py plus tests/__init__.py if needed.
Use the existing PaperBroker; this is the execution boundary for later full-stack integration, not the final deliverable.

Interfaces: preserve PaperConfig, Position, Fill, PaperBroker, load_config and submit_market_order signatures. New optional helpers may remain internal. Existing run_paper callers must continue working.

- [ ] Write meaningful failing tests first. A no-slippage BUY1 at100 followed by SELL1 at100 with10bps fees must end with cash9999.8 and realized_pnl=-0.2. A marked drawdown must reject new BUY but permit SELL of held quantity; oversized SELL must not create a short. Invalid nonfinite config inputs must be rejected. Keep long-only; allow_shorting=True must explicitly reject unsupported configuration rather than produce false accounting.
- [ ] Run those tests against unchanged production code and record RED failures. Tests use the real broker; no network/provider mocks are needed. Derive expectations by hand.
- [ ] Repair entry-fee allocation into the cost basis so partial exits and multiple entries reconcile realized PnL; avoid double charging fees in cash. Permit strictly risk-reducing SELL after kill switch while preserving holdings validation. Validate config numeric bounds/symbols and unsupported shorting at construction/loading.
- [ ] Add a test harness which blocks socket/process events before importing project modules and forbids writes outside uniquely named worktree test-artifact folders. Do not run tempfile cleanup or delete files. Existing tests may replace their setup/cleanup with preserved isolated artifacts; do not remove their assertions.
- [ ] Run existing and new tests, save command/output in the task report, self-review diff, and make a local hook-disabled commit staging only these intended files.
Example economic assertion:
```python
broker = PaperBroker(PaperConfig(fee_bps=10, slippage_bps=0))
broker.submit_market_order("BTC-USDT", "BUY", 1, 100)
broker.submit_market_order("BTC-USDT", "SELL", 1, 100)
self.assertAlmostEqual(broker.cash, 9999.8)
self.assertAlmostEqual(broker.positions["BTC-USDT"].realized_pnl, -0.2)
```
Bundled Python: C:/Users/Blair/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe. No dependency installation for this task. Use -I -S for the stdlib-only harness; explicitly add the worktree to sys.path inside the reviewed harness. Never run or import the full application yet.

### Task 2: Repair strategy, signal, risk and historical data contracts

Files: trading_stack/signal_generator.py, risk_management.py, market_data.py, technical_indicators.py, backtesting.py; add trading_stack/strategy_contracts.py and focused tests under tests/.
Consumes existing ORM strategy/signal interfaces; produces the same public generate_signals_for_strategy, calculate_position_size, check_risk_limits and historical/backtest functions with optional injected paper collaborators where required.

- [ ] Create failing regression cases for empty/SELL-only/missing-indicator rules, scalar sizing10000/100/98/1 ->50, nested-balance normalization, correct BTC/USDT routing, SELL stop direction and malformed/ambiguous rules.
- [ ] Normalize editor indicator arrays into keyed config and stable column references; support its symbolic operators by mapping to canonical above/below/equals/crossing rules. Require a side rather than silently inventing BUY.
- [ ] Make provider/model imports lazy so pure signal/risk tests do not initialize external managers. Optional unavailable indicator/model implementations fail explicitly; pandas SMA/EMA/RSI/MACD are supported for deterministic offline replay without talib.
- [ ] Introduce a local market-provider injection used by get_latest_prices/get_historical_data; in paper mode no provider means unavailable data, never an HTTP fallback. get_historical_data accepts start_date/end_date and enforces range. Backtest helper forwards both dates.
- [ ] Correct risk units and normalize paper account equity before sizing. Preserve strategy-specific risk and shared-position limits. Validate finite positive amounts/prices and percent bounds.
- [ ] Repair date filtering, empty exits, timestamp serialization, finite metrics, and obvious future-data use in the Python backtest path. Keep fees/slippage conventions explicit and hand-checked.
- [ ] Run RED/GREEN focused tests then the existing paper suite; commit only intended source/tests. Report interface signatures and fixtures for Task3.
Example required signal assertions:
```python
self.assertIsNone(generate_technical_signal(empty_strategy, "BTC/USDT", candles))
self.assertEqual(generate_technical_signal(sell_strategy, "BTC/USDT", candles).signal_type, "SELL")
self.assertEqual(calculate_position_size(10000, 100, 98, 1), 50)
```

### Task 3: Wire the full engine and ORM to a contained paper runtime

Files: trading_stack/trading_engine.py, database.py, config.py, app.py, api/routes.py, models.py as necessary; create trading_stack/paper_runtime.py, trading_stack/paper_replay.py and tests/test_full_paper_integration.py.
Consumes Task1 broker and Task2 strategy/risk/data functions. Preserve the recovered Flask/ORM application and use the real engine; do not create a replacement standalone demo.

- [ ] Write failing integration tests creating memory-only ORM users and two strategies, injecting a labeled synthetic OHLCV sequence, processing it through the real engine and asserting economic/ORM results.
- [ ] Add explicit paper runtime injection with one account per user, local candles, replay clock, stable strategy ordering, shared risk budget and per-strategy/pair/candle deduplication. Persist signal/execution rows and a run/decision/fill summary.
- [ ] Route engine, manual and close APIs through this boundary in paper mode. Do not construct/import external SDK managers. Any live execution attempted from this new paper path must be rejected regardless of environment flags.
- [ ] Make full app creation configurable before DB initialization, with tests using sqlite:// memory and no inherited DATABASE_URL. Avoid production DB creation on import.
- [ ] Add finite replay API/CLI using a caller-specified local CSV and range, provenance label and output path. Do not install services or schedulers. A contained loopback application listener is authorized for final paper UI tests after offline containment passes. Multiple active strategies share state and risk, with no fabricated autonomous agents.
- [ ] Verify deterministic two-strategy replay, repeated-candle idempotency, shared exposure rejection, closing/stop behavior, per-user separation, JSON serializability, and zero external calls using the deny-network harness.
- [ ] Repair manual order result mapping and ownership checks for related paper data/API operations. Optional ML/MATLAB/futures routes must clearly report inactive/unavailable instead of fake success.
- [ ] Run focused RED/GREEN integration tests and all earlier tests, record complete finite run output, self-review and commit intended files.
Example acceptance:
```python
self.assertGreater(result["decision_count"], 0)
self.assertGreater(result["fill_count"], 0)
self.assertEqual(result["mode"], "paper")
self.assertEqual(result["data_origin"], "synthetic_test_fixture")
self.assertEqual(second_run["economic_summary"], first_run["economic_summary"])
```

### Task 4: Reconcile UI, full-path regressions and run documentation

Files: trading_stack/templates/*.html, trading_stack/static/js/*.js, trading_stack/api/routes.py as necessary; docs/PAPER_INTEGRATION.md; tests/test_paper_ui.py; fixture CSV/JSON and provenance beside tests.
Consumes the actual Task3 API contracts; produces a coherent paper UI and complete reviewable run instructions.

- [ ] Add failing template/API contract tests for settings/profile endpoint names, strategy normalization and the12 previously missing request patterns. Test actual responses/templates rather than grep-only source assertions.
- [ ] Point rendered backtesting/manual/market/signal controls at implemented routes; remove duplicate handler conflicts. Implement paper-only missing operations where meaningful; remove/disable unsupported controls with clear explanations.
- [ ] Show simulated/data-unavailable/stale states truthfully. Remove unlabeled canned monthly/performance success numbers. Ensure API errors do not turn badges Live.
- [ ] Exercise the full flow with test client: create user/strategies, load local candles, replay, retrieve signals/fills/positions/balances, perform paper close, and run dated backtest. Include two-user ownership and no-network checks.
- [ ] Document exact entrypoints, dependencies, synthetic provenance, result paths, unsupported optional learning components and local-only scope. No actual dataset or model claim without artifact evidence.
- [ ] Run all relevant tests once and a finite end-to-end simulation, save outputs and source diff, and commit only intended files. Report unresolved defects honestly; do not activate live adapters to make tests pass.
```python
self.assertEqual(client.get("/settings").status_code, 200)
self.assertEqual(client.get("/profile").status_code, 200)
self.assertEqual(client.get("/api/positions").json["success"], True)
```



