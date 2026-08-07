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

### Connect Python (host + phone)

On the host (PC / cloud):

```bash
pip3 install -r requirements.txt
python3 connect_python.py
```

Bridge listens on `0.0.0.0:5050` (paper-safe).

**Start EVBot from HTML**

```text
http://127.0.0.1:5050/evbot
```

Uses your uploaded EVBot GPT instructions + `ev_viral_brain.json`.  
Button **Start EVBot** hits `/api/evbot/start` (paper-safe bridge online).  
Full Windows Waitress dual-launch remains in `evbot/EV_Waitress_Launcher.ps1` for local CS.

On a phone that has Python / Scriptable:

**Scriptable (recommended if you can’t run PC-only)**

1. Install **Scriptable** on iPhone.
2. New script → paste `phone/Scriptable_EVBot_Lore.js`.
3. Set `TEAKA_HOST` inside the script to your PC LAN IP when you want ONLINE.
4. Run from Scriptable (or add to Shortcuts / home-screen).

Works **OFFLINE on the phone** (writes `therruedevil7.json`, `Cross_device_brain.json`, `evbot_lore_state.json`).  
If the PC bridge is up, it auto-routes **ONLINE** and calls `/api/evbot/start`.

**Pythonista3 lore script**

Add to your lore boot (or run alone):

```python
import os
os.environ["TEAKA_HOST"] = "http://<pc-lan-ip>:5050"  # optional
os.environ["ROUTE_MODE"] = "AUTO"
import lore_script
lore_script.main()
```

Copy `phone/lore_script.py` + `phone/pythonista_boot.py` into Pythonista Documents.

Expect:

```text
ST_BOOT: SENTINEL_AL7_DAEMON_STARTED
BRAIN_SYNCED: therruedevil7.json -> Cross_device_brain.json route=ONLINE|OFFLINE
LORE_READY: evbot_lore_state.json local_ready=true
```

**Termux / generic**

```bash
export TEAKA_HOST=http://192.168.x.x:5050
python phone/client.py status
python phone/client.py paper
python phone/client.py command ping
```

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

## Full trading engine (connected here + sibling)

Connected into this repo as **`trading_stack/`** (from [`TeAkaTrader/BoltBuddy`](https://github.com/TeAkaTrader/BoltBuddy)).

Live order gates stay **off** unless all of these are set:

```text
TEAKA_MODE=live
LIVE_TRADING_ENABLED=true
PRIVATE_EXCHANGE_API_ENABLED=true
```

| Module | Role |
|--------|------|
| `trading_stack/trading_engine.py` | Main loop: strategies → signals → risk → gated execute |
| `trading_stack/unified_trading.py` | Crypto / forex / stocks manager |
| `trading_stack/signal_generator.py` | Technical + ML signals |
| `trading_stack/broker_apis.py` | KuCoin / OANDA / IB APIs |
| `trading_stack/messaging.py` | Telegram + Discord alert bots |
| `trading_stack/models.py` | Users, strategies, signals (`enable_automated_trading` defaults false) |
| `phone/client.py` | Phone Python client for the bridge |
| `connect_python.py` | Paper-safe host bridge for phone / LAN |

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

## Local CS intake (safe only)

Imported without secrets:

- `docs/GEMBotSys_path_map.txt` — GEMBotSys / EV_Link path map (shows real `GemBot\` location)
- `scripts/check_ev_for_chatgpt.ps1` — EV `:5000` health check
- `Config/backtest_config.json` — backtest parameters
- `scripts/auth_api_example.py` — env-based JWT auth example
- `docs/UPLOAD_INTAKE_NOTES.md` — what was kept vs excluded

KuCoin / Dropbox / hardcoded DB secrets from uploads were **not** committed. Rotate those on the providers.
