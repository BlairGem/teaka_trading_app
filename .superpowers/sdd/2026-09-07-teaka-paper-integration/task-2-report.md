# Task 2 report

## Evidence

- Implementation commit: `894d00ff196459ffdd997008b0322233af0eaf4e` (`Repair strategy and backtest contracts`).
- Baseline: `D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe -I D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py` -> 21 tests, OK, before Task 2 edits.
- RED used the same guarded runner with focused unittest names. Regressions reproduced: sizing returned `0.5` instead of `50`; strategy contract module absent; eager TA-Lib/model/config imports failed; paper market wrappers lacked provider/as-of/date injection; risk helpers were absent; technical replay used the signal candle close; no-loss profit factor was infinite; ML replay included its execution candle, opened a short, and returned timestamp objects; symbolic backtest `>` evaluated false; explicit zero user limits were replaced by defaults.
- GREEN focused: `D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe -I D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py tests.test_strategy_contracts` -> 33 tests, OK. Artifacts: `paper_trading/state/test-artifacts/run-dbc899928e15400d9602e1713392222a`.
- GREEN complete: `D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe -I D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py` -> 54 tests, OK. Artifacts: `paper_trading/state/test-artifacts/run-49a5f7f5de9c484695be6aeb6c4ce1b8`.
- The runner installs its audit guard before project imports and now accepts test names. Approved NumPy/Pandas are preloaded because the Windows Pandas import asks for the hostname; network, process, delete, move, link, metadata, and out-of-artifact writes remain denied.

### Observed RED/GREEN output

- RED command: `$env:TEAKA_MODE='paper'; & 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe' -I 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py' tests.test_strategy_contracts.BacktestContractTests.test_ml_backtest_uses_completed_candles_and_does_not_open_shorts`
  Observed: `... FAIL`; the result contained one `SELL` trade; `Ran 1 test in 0.027s`; `FAILED (failures=1)`; `exit=1`.
- RED command: `$env:TEAKA_MODE='paper'; & 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe' -I 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py' tests.test_strategy_contracts.BacktestContractTests.test_ml_backtest_serializes_trade_timestamps tests.test_strategy_contracts.BacktestContractTests.test_backtest_condition_accepts_symbolic_operator_and_fails_closed`
  Observed: timestamp assertion received `Timestamp(...)` instead of the expected ISO string; `Unsupported operator >`; `Ran 2 tests in 0.023s`; `FAILED (failures=2)`; `exit=1`.
- RED command: `$env:TEAKA_MODE='paper'; & 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe' -I 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py' tests.test_strategy_contracts.RiskLimitContractTests.test_explicit_zero_user_limits_are_not_replaced_by_defaults tests.test_strategy_contracts.BacktestContractTests.test_ml_backtest_serializes_trade_timestamps tests.test_strategy_contracts.BacktestContractTests.test_performance_metrics_are_finite_when_there_are_no_losses`
  Observed: explicit zero limits returned `True`, result metadata raised `KeyError: 'data_origin'`, and empty profit factor was `0.0` instead of `None`; `Ran 3 tests in 0.025s`; `FAILED (failures=2, errors=1)`; `exit=1`.
- Focused GREEN command: `$env:TEAKA_MODE='paper'; & 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe' -I 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py' tests.test_strategy_contracts`
  Observed: `Ran 33 tests in 0.129s`; `OK`; `exit=0`.
- Complete GREEN command: `$env:TEAKA_MODE='paper'; & 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe' -I 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py'`
  Observed: `Ran 54 tests in 1.244s`; `OK`; `exit=0`.

## Task 3 interfaces

- `normalize_strategy_contract(raw_indicators, raw_conditions) -> (keyed_indicators, normalized_conditions)`. Editor IDs such as `sma_101` resolve to deterministic calculation columns such as `sma_3`; operators normalize to canonical names; every rule requires an unambiguous `BUY` or `SELL` side.
- `get_latest_prices(provider=None, as_of=None)`. Provider: `get_latest_prices(pairs, as_of=None) -> dict[pair, price]`. A replay provider must apply `as_of` or its own clock so a fixture containing later candles exposes only values at or before the replay clock.
- `get_historical_data(trading_pair, timeframe, limit=100, start_date=None, end_date=None, provider=None)`. Provider: `get_historical_data(trading_pair, timeframe, *, start_date, end_date, limit) -> DataFrame`. Both bounds are required together and are inclusive; the wrapper sorts, re-filters to the requested range, validates OHLCV columns, and then applies `limit`. For rolling replay, Task 3 should pass the clock as `end_date`; a provider with an internal clock must also cap returned rows at that clock.
- `generate_signals_for_strategy(strategy, market_provider=None, pending_signal_lookup=None, signal_factory=None, model_predictor=None, now=None)`. Pending lookup: `(strategy_id, pair) -> pending signal or None`; signal factory: keyword values -> signal with `set_signal_data`; `now` is a datetime or zero-argument clock.
- `calculate_position_size(account_balance, entry_price, stop_loss, risk_per_trade_pct=1.0) -> asset units` and `check_risk_limits(user, trading_pair, entry_price, account_balance_provider=None, active_positions_provider=None, latest_prices_provider=None, strategy_provider=None) -> bool`. Injected collaborators return a balance snapshot/equity, shared position list, pair-price mapping, and active strategy respectively.
- `get_historical_data_for_backtest(trading_pair, timeframe, start_date, end_date, market_provider=None)` forwards both dates and limit 5000. `backtest_technical_strategy(..., fee_bps=0.0, slippage_bps=0.0)` uses a completed candle for its decision and the next candle open for execution. `run_backtest(...)` additionally accepts provider, ORM, fee/slippage, and model-predictor injections while preserving its original positional parameters.

## Assumptions and limitations

- Paper mode without an injected provider returns unavailable data (`{}` or an empty OHLCV frame); it never falls back to HTTP. Live providers remain lazy.
- Technical and injected-ML replays are long-only. `SELL` closes held exposure and never opens a short. A final held long closes at the final candle close. Technical entry and signal exit use next-open fills; stop/take triggers use their threshold prices.
- Technical fees are charged on entry and exit notionals. BUY slippage raises the entry fill and SELL slippage lowers the exit fill. Output records the fee/slippage inputs, inclusive time range, origin, and ISO timestamps.
- Profit factor is `null` when there is no loss denominator, including zero-trade and all-win samples. Other numeric metrics remain finite.
- SMA, EMA, RSI, and MACD are deterministic Pandas implementations. Other TA-Lib indicators and custom MATLAB indicators remain lazy and raise `IndicatorUnavailableError` when unavailable.
- Paper ML signal/backtest functions require an injected predictor and raise `ModelUnavailableError` without one. The regression uses only a deterministic synthetic predictor; no recovered trained artifact was loaded or trained in Task 2.

## Review fix round 1

### Observed RED/GREEN evidence

- RED command: `$env:TEAKA_MODE='paper'; & 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe' -I 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py' tests.test_offline_guard.OfflineGuardTests.test_numeric_bootstrap_installs_guard_before_imports tests.test_offline_guard.OfflineGuardTests.test_only_hostname_socket_metadata_event_is_allowed tests.test_strategy_contracts.SignalGenerationTests.test_signal_rejects_zero_derived_protective_prices tests.test_strategy_contracts.MarketDataContractTests.test_invalid_provider_ohlcv_is_rejected tests.test_strategy_contracts.RiskLimitContractTests.test_selected_strategy_is_used_and_zero_derived_size_is_rejected tests.test_strategy_contracts.BacktestContractTests.test_backtest_uses_completed_signal_candle_and_preserves_empty_exit tests.test_strategy_contracts.BacktestContractTests.test_open_signal_precedes_intrabar_stop_and_cannot_reopen tests.test_strategy_contracts.BacktestContractTests.test_new_technical_entry_gets_same_candle_protection_and_risk_sizing tests.test_strategy_contracts.BacktestContractTests.test_technical_risk_size_is_capped_by_cash_and_entry_fee tests.test_strategy_contracts.BacktestContractTests.test_ml_entry_protection_prevents_same_candle_reopen tests.test_strategy_contracts.BacktestContractTests.test_ml_honors_fee_slippage_and_stop_distance_sizing tests.test_strategy_contracts.BacktestContractTests.test_replays_reject_invalid_ohlcv_and_ml_economics`
  Observed: `Ran 12 tests in 0.057s`; `FAILED (failures=7, errors=5)`; `exit=1`. Failures reproduced all seven review findings. Artifacts: `paper_trading/state/test-artifacts/run-35f9760f565d4839a2d680f315b97772`.
- Narrow-hostname RED command: `$env:TEAKA_MODE='paper'; & 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe' -I 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py' tests.test_offline_guard.OfflineGuardTests.test_socket_events_are_denied_outside_numeric_bootstrap`
  Observed: `socket.gethostname` did not raise; `Ran 1 test in 0.001s`; `FAILED (failures=1)`; `exit=1`.
- Focused GREEN command: `$env:TEAKA_MODE='paper'; & 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe' -I 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py' tests.test_strategy_contracts tests.test_offline_guard`
  Observed: `Ran 51 tests in 0.357s`; `OK`; `exit=0`. Artifacts: `paper_trading/state/test-artifacts/run-9814696228e5452eb82ea1b6f25bcd83`.
- Complete GREEN command: `$env:TEAKA_MODE='paper'; & 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe' -I 'D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py'`
  Observed: `Ran 67 tests in 0.531s`; `OK`; `exit=0`. Artifacts: `paper_trading/state/test-artifacts/run-e3d08ccdb8fe4b5db3e53babe59fd614`.

### Revised interfaces and execution contract

- `check_risk_limits(..., strategy_provider=None, strategy=None)` accepts the selected strategy explicitly. With neither explicit strategy nor injected provider it fails closed; it does not select the first active strategy. `trading_engine.run_trading_engine()` passes its current strategy.
- `backtest_ml_strategy(strategy, data, start_date, end_date, initial_balance, model_predictor=None, fee_bps=0.0, slippage_bps=0.0)` preserves the original positional parameters and adds costs at the end. `run_backtest(...)` forwards both cost inputs to technical and ML replay.
- Both replay functions use `calculate_position_size(equity, entry, stop, risk_pct)`, then cap quantity so entry notional plus entry fee cannot exceed cash. Derived entry, stop, take, quantity, notional, equity, proceeds, fees and P&L must be finite; prices and quantities must be positive.
- Candle processing order is prior-completed-candle decision at current open, then current-candle stop/take, then close marking. Open-time exits precede later intrabar ranges; newly opened positions receive same-candle protection; a position closed during a candle cannot reopen at that candle's already-passed open.
- Historical provider normalization and direct replay reject nonfinite/nonpositive prices, negative volume, invalid high/low ranges and duplicate replay timestamps. Invalid replay economics raise `ValueError` rather than returning nonfinite results.
- `_install_guard_then_import_numerics(add_guard=..., import_module=...)` installs the audit guard before NumPy/Pandas. `socket.gethostname` is allowed only during that bootstrap window; all socket events are denied again afterward, and process/file restrictions remain active throughout.
