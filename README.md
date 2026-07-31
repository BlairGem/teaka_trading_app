# TeAka Trading System

## Current status

**Production-ready for controlled paper trading with supplied price ticks.**

The verified paper path is isolated from exchange order APIs. It creates virtual fills, virtual positions, P/L, fees, slippage, drawdown and JSONL audit logs. Live order submission remains disabled.

## Verified paper path

```text
CSV/public price ticks
        |
        v
Momentum demo strategy
        |
        v
PaperBroker risk checks
        |
        v
Virtual fills and positions
        |
        v
JSONL audit log + account snapshot
```

## Safety guarantees

The `paper_trading` package:

- imports no exchange SDK
- contains no private exchange API route
- reports `live_order_routes: false`
- rejects symbols outside the allowlist
- limits order notional
- limits position concentration
- blocks shorting by default
- applies configurable fees and slippage
- activates a kill switch at the configured drawdown
- writes every fill or rejection to an auditable JSONL log

## Run the verified sample

From the repository root:

```powershell
python -m unittest discover -s paper_trading -v
python paper_trading/run_paper.py --ticks paper_trading/sample_ticks.csv
```

The default fill log is written to:

```text
paper_trading/state/paper_fills.jsonl
```

## Configuration

Copy and edit:

```text
paper_trading/config.example.json
```

Default controls:

- virtual cash: 10,000
- maximum order notional: 1,000
- maximum position: 20% of equity
- maximum drawdown: 15%
- shorting: disabled
- allowed symbols: BTC-USDT, ETH-USDT, SOL-USDT

## Feed format

The runner accepts CSV data with these columns:

```csv
timestamp,symbol,price
2026-07-14T00:00:00Z,BTC-USDT,60000
```

This allows historical data, recorded public market data, or a separate public-feed collector to drive the paper broker without exposing private trading credentials.

## Existing project components located

High-level areas:

- React/TypeScript dashboard
- historical TypeScript backtest engine
- FastAPI market/prediction prototype
- KuCoin public-feed prototypes
- EV runtime and GEMBot integration references
- PostgreSQL/authentication prototypes
- verified `paper_trading` broker and CI gate

### TeAka full file list

Canonical inventory also lives in `teaka_file_index.txt`. Current repository map:

```text
paper_trading/
  paper_broker.py
  run_paper.py
  test_paper_broker.py
  config.example.json
  sample_ticks.csv

dashboard/ + src/
  dashboard/src/App.tsx
  src/App.tsx
  package.json
  RiskManagementPanel.tsx
  riskManagementService.ts
  riskAdjuster.ts

api clients/
  auth.py
  fastapi.server.py
  kucoin.asyncio
  kucoin.client
  telegram_api.txt

ml models/ + model_output/ + integration_pipeline/
  backtestEngine.ts / Backtester.ts / Backtest*.ts
  sklearn model train/evaluate
  Algoithms/classifier.py, dqn_agent.py, train.rl.py
  q_learning_trader.py
  tensorflow.py, train_model.js, model_config.json

sql_teaka_dashboard/ + SQL schemas/
  create_users.sql
  create_trades.sql
  create_settings.sql
  create_dashboard_metrics.sql

EV / runtime /
  ev_remote_server.py
  ev_ollama_bridge.py
  ev_ollama_auto_bind.py
  ev_virtual_brain.json
  bridge/inbox/
  Config/

ui hooks/ + public/ + templates/
  main.js, TradingView widgets, dashboard HTML
  public/dashboard.html, ev_alert_api.py

docs / safety /
  README.md
  SECURITY.md
  .env.example
  .github/workflows/paper-trading-tests.yml
```

The verified paper execution path is `paper_trading/` only. Other components are part of the broader TeAka product surface and integrations.

## Credential security

Tracked exchange credentials were removed from the current branch. Any credential that previously appeared in Git history must be revoked or rotated before private API access is considered. See `SECURITY.md`.

Use `.env.example` only as a template. Never commit real values.

## CI gate

GitHub Actions runs:

```text
.github/workflows/paper-trading-tests.yml
```

The workflow executes the unit tests and a deterministic paper session on paper-trading changes.

## Live trading status

Live trading is **not enabled**. Before live deployment, complete a separate review of exchange permissions, credential storage, order-routing code, reconciliation, monitoring and emergency shutdown behavior.
