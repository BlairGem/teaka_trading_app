# TeAka Trading System

EV recovery fork of [`TeAkaTrader/teaka_trading_app`](https://github.com/TeAkaTrader/teaka_trading_app).  
Homepage target: [teaka.trading](https://teaka.trading)

## What this repository is

This tree is the **TeAka app / recovery surface**:

- verified **paper trading** path (safe to run here)
- dashboard, risk, ML/backtest, SQL, EV bridge **fragments**
- pointers to the **full live trading engine** and local EV/GEMBot/Swarm layout

It is **not** a complete copy of every local Windows / Starforge / GEMBotSys artifact. Those stay on the local machine (`E:\EV_Files`, `D:\Starforge`, user `GEMBotSys`) and in sibling / private repos.

Live exchange order submission in this fork remains **disabled**.

---

## Ready to run now (verified)

### Paper trading

```text
CSV / public price ticks
        →
momentum demo strategy  (paper_trading/run_paper.py)
        →
PaperBroker risk checks  (paper_trading/paper_broker.py)
        →
virtual fills / positions / fees / slippage / drawdown kill switch
        →
JSONL audit log + account snapshot
```

```bash
python3 -m unittest discover -s paper_trading -v
python3 paper_trading/run_paper.py --ticks paper_trading/sample_ticks.csv
```

Defaults (see `paper_trading/config.example.json`):

| Control | Default |
|---------|---------|
| Virtual cash | 10,000 |
| Max order notional | 1,000 |
| Max position | 20% of equity |
| Max drawdown | 15% |
| Shorting | off |
| Symbols | BTC-USDT, ETH-USDT, SOL-USDT |

Tick CSV columns: `timestamp,symbol,price`

CI: `.github/workflows/paper-trading-tests.yml`

Safety: `paper_trading/` imports **no** exchange SDK and has **no** private order routes (`live_order_routes: false`).

---

## Full trading engine (sibling repo)

The complete strategy → signal → risk → broker engine lives in:

**[`TeAkaTrader/BoltBuddy`](https://github.com/TeAkaTrader/BoltBuddy)**  
(Replit: `replit.com/@gee8/BoltBuddy`)

| Module | Role |
|--------|------|
| `trading_engine.py` | Main loop: active strategies → signals → risk → optional auto-execute |
| `unified_trading.py` | Unified manager across crypto / forex / stocks |
| `signal_generator.py` | Technical + ML signal generation |
| `broker_apis.py` | KuCoin / OANDA / Interactive Brokers order APIs |
| `ccxt_integration.py` | CCXT exchanges (KuCoin, Binance, Coinbase, …) |
| `fxcm_integration.py` / `alpaca_integration.py` | Forex / stocks |
| `futures_trading.py` | KuCoin + IB futures |
| `risk_management.py` | Position size, exposure, portfolio risk |
| `ml_models.py` / `backtesting.py` | ML models and backtests |
| `messaging.py` | Telegram + Discord + email alert bots |
| `models.py` | Users, strategies, signals, executions, ML models |
| `api/routes.py` | Flask `/api/*` for prices, charts, strategies, trades |
| `templates/strategy_editor.html` | Strategy “bot” editor UI |
| `main.py` / `app.py` | Flask app on port 5000 |

Engine flow:

```text
TradingStrategy (active)
  → generate_signals_for_strategy()
  → check_risk_limits() + calculate_position_size()
  → notify (Telegram / Discord / email)
  → execute_trade_from_signal() if automated trading enabled
  → broker_apis / unified_trading / futures
```

Do **not** enable live keys in this recovery fork until credentials are rotated and a separate live-trading review is done. See `SECURITY.md`.

---

## Bots, Swarm, GEMBot (where they actually are)

| Name | Reality |
|------|---------|
| **Strategy bots** | BoltBuddy `TradingStrategy` + strategy editor + auto-trading flag |
| **Alert bots** | BoltBuddy `messaging.py`; this repo has Telegram alert stubs (`public/ev_alert_api.py`, `alert_routes.py.py`, `@teaka_trader_bot` notes) |
| **TeAka Swarm** | Branding / daily summary path in this repo (`email_report.py`, `schedule_teaka_summary.ps1`, sign-off “Teaka Swarm Core”). Not a multi-agent source tree in Git. |
| **GEMBot / EVBot** | Local EV control layer. Referenced here via `status_report.yaml`, `ev_ollama_*.py`, `ev_remote_server.py`, `Config/# Define the EV Shell Runtime Envir.txt`. Windows provenance: user `GEMBotSys`, vault `D:\Starforge\Vault`, bridge `E:\EV_Files\Bridge` / `D:\EV_Files\Bridge`. Private EV control repo is expected outside this fork (e.g. `BlairGem/Ev` when available). |
| **QTrader / RL bots** | Sketches in `model_output/` + planned tree in `integration_pipeline/QTrader.txt` — not wired to BoltBuddy or paper broker |
| **Dashboard bot panel** | `templates/dashboard.html` still has a bot placeholder block |

Local CS layout (from tracked paths / config — on your machine):

```text
E:\EV_Files\teaka_trading_app\     ← this app tree / reports / models
E:\EV_Files\Bridge\                ← EV inbox / bridge drops
E:\EV_Files\ev_virtual_brain.json  ← EV brain state
D:\Starforge\Vault\                ← GEM Bot vault + spells
D:\EV_Files\Tools\                 ← EV runtime environment JSON writers
C:\Users\GEMBotSys\...             ← GEMBotSys Python / venv provenance
```

---

## This fork — major areas

| Area | Location |
|------|----------|
| Verified paper broker | `paper_trading/` |
| React / Firemind dashboard stubs | `src/`, `dashboard/`, `package.json` |
| Risk UI / services | `RiskManagementPanel.tsx`, `riskManagementService.ts`, `riskAdjuster.ts` |
| API / KuCoin / Telegram notes | `api clients/` |
| Backtest TS + sklearn / RL sketches | `ml models/`, `model_output/`, `integration_pipeline/` |
| SQL dashboard schemas | `sql_teaka_dashboard/`, root `create_*.sql` |
| EV bridge / Ollama / brain | `ev_*.py`, `ev_virtual_brain.json`, `bridge/` |
| UI hooks / public dashboards | `ui hooks/`, `public/`, `templates/` |
| Full file cut | `teaka_file_index.txt` (exact inventory of this repo) |

---

## Environment

Copy `.env.example` → `.env` (never commit real values):

```text
TEAKA_MODE=paper
LIVE_TRADING_ENABLED=false
PRIVATE_EXCHANGE_API_ENABLED=false
```

---

## Security

- Rotate any exchange / Telegram / mail credentials that ever appeared in Git history.
- Paper mode by default; live orders stay off in this fork.
- Details: `SECURITY.md`.

---

## Related systems

```text
TeAkaTrader/teaka_trading_app   ← upstream of this recovery fork
TeAkaTrader/BoltBuddy           ← full trading engine + strategy bots
BlairGem/teaka_trading_app      ← this repo (audit / cleanup / paper rebuild)
Local EV / GEMBot / Starforge   ← private control + swarm ops on PC5000 / GEMBotSys
evstack/ev-node (external)      ← EV Stack / node framework (not vendored here)
```

Federation note (other branch docs): TeAka owns trading; EV GeoBlockchain / EV Stack stay in separate repos and integrate only through adapters.
