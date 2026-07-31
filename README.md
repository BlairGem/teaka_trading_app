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

Complete cut verified against the repository tree. Canonical inventory: `teaka_file_index.txt` (107 project files; excludes local venv binaries only).

```text
.env.example
.github/workflows/paper-trading-tests.yml
.github/workflows/webpack.yml
.gitignore
Config/# Define the EV Shell Runtime Envir.txt
Config/Repeatable Launch Commands (PowerShell).txt
Config/backtest_config.json
Config/ev_keys.json
README.md
RiskManagementPanel.tsx
SECURITY.md
alert_routes.py.py
api clients/auth.py
api clients/ev_keys.json
api clients/fastapi.server.py
api clients/kucoin.asyncio
api clients/kucoin.client
api clients/telegram_api.txt
app.py
app.py.py
bridge/inbox/PC5000_GIT_ACCESS_DIAGNOSTIC_001.json
create_dashboard_metrics.sql
create_settings.sql
create_trades.sql
create_users.sql
dashboad.zip
dashboard/package.json
dashboard/src/App.tsx
directory.txt
email_report.py
ev.remote.server.py.py
ev_node.py
ev_ollama_auto_bind.py
ev_ollama_bridge.py
ev_remote_server.py
ev_virtual_brain.json
flask_api_routes.py
flask_dashboard_stub.py
generate_summary.py
import_sql.ps1
init_db.py
initcluster.ps1
integration_pipeline/QTrader.txt
integration_pipeline/model_config.json
integration_pipeline/sample_training_data.json
integration_pipeline/tensorflow.py
integration_pipeline/train_model.js
launcher_shortcut.ps1
market_prices.csv
market_screener_table.html
ml models/BacktestFunction.ts
ml models/BacktestHistorical.ts
ml models/BacktestInterval.ts
ml models/BacktestSummary.ts
ml models/Backtester.ts
ml models/BacktesterTest.spec.ts
ml models/backtestEngine.ts
ml models/backtestEngine_1.ts
ml models/gym.env
ml models/sklearn model/.py
ml models/sklearn model/evaluate.py
ml models/sklearn model/sklearn.model.py
ml models/sklearn model/train.model.py
model_output/Algoithms/classifier.py
model_output/Algoithms/dqn_agent.py
model_output/Algoithms/train.rl.py
model_output/BacktestDate.ts
model_output/q_learning_trader.py
package.json
paper_trading/config.example.json
paper_trading/paper_broker.py
paper_trading/run_paper.py
paper_trading/sample_ticks.csv
paper_trading/test_paper_broker.py
public/dashboard.html
public/dashboard_backup_20250603_101019.html
public/ev_alert_api.py
public/ev_alert_api.py.json
public/index.ts
riskAdjuster.ts
riskManagementService.ts
schedule_teaka_summary.ps1
sql_scripts.py
sql_teaka_dashboard/create_dashboard_metrics.sql
sql_teaka_dashboard/create_settings.sql
sql_teaka_dashboard/create_trades.sql
sql_teaka_dashboard/create_users.sql
sql_teaka_dashboard/import_sql.ps1
sql_teaka_dashboard/import_teaka_sql.ps1
sql_teaka_dashboard/market_prices.csv
sql_teaka_dashboard/package.json
sql_teaka_dashboard/scan_postgresql_paths.ps1
src/.ps1
src/App.tsx
status_report.yaml
teaka_file_index.txt
teaka_trading_app_validate_brain.py
templates/dashboard.html
templates/ws_feed.py
train_model.py
ui hooks/main.js
ui hooks/ssl/cloudfare-origin-key.pem
ui hooks/ssl/cloudfare.origin.pem
ui hooks/ssl/index.html
ui hooks/tradingview-widget-ui.txt
ui hooks/web ui_index.html
websocket.send_sql
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
