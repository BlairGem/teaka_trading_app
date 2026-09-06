# Task 2 report

## Evidence

- Baseline: `D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe -I D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py` -> 21 tests, OK, before Task 2 edits.
- RED used the same guarded runner with focused unittest names. Regressions reproduced: sizing returned `0.5` instead of `50`; strategy contract module absent; eager TA-Lib/model/config imports failed; paper market wrappers lacked provider/as-of/date injection; risk helpers were absent; technical replay used the signal candle close; no-loss profit factor was infinite; ML replay included its execution candle, opened a short, and returned timestamp objects; symbolic backtest `>` evaluated false; explicit zero user limits were replaced by defaults.
- GREEN focused: `D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe -I D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py tests.test_strategy_contracts` -> 33 tests, OK. Artifacts: `paper_trading/state/test-artifacts/run-dbc899928e15400d9602e1713392222a`.
- GREEN complete: `D:\EV_AI\Worktrees\teaka-paper-integration-20260907\.venv-paper\Scripts\python.exe -I D:\EV_AI\Worktrees\teaka-paper-integration-20260907\tests\run_offline.py` -> 54 tests, OK. Artifacts: `paper_trading/state/test-artifacts/run-49a5f7f5de9c484695be6aeb6c4ce1b8`.
- The runner installs its audit guard before project imports and now accepts test names. Approved NumPy/Pandas are preloaded because the Windows Pandas import asks for the hostname; network, process, delete, move, link, metadata, and out-of-artifact writes remain denied.

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
