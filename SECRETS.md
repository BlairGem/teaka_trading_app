# TeAka Trading App — Secrets & Credentials

All credentials are loaded from **environment variables only**.
Copy `.env.example` → `.env` and fill in your values. Never commit `.env`.

---

## Required for Telegram Alerts

| Variable | Where to get it | Used by |
|----------|----------------|---------|
| `TELEGRAM_BOT_TOKEN` | @BotFather → `/newbot` | `alert_routes.py.py`, `public/ev_alert_api.py`, `trading_stack/messaging.py` |
| `TELEGRAM_CHAT_ID` | `curl https://api.telegram.org/bot<TOKEN>/getUpdates` | Same as above |

**Bot name:** `@teaka_trader_bot`
**Token from repo history (ROTATE THIS):** `7711152546:AAFAf-5JT1yKg7c6gsk6p3UWYqiy249BPUc`

> This token was previously hardcoded in source files and must be rotated via @BotFather → `/revoke`.

---

## Required for Live Trading (paper mode needs none of these)

| Variable | Service | Used by |
|----------|---------|---------|
| `KUCOIN_API_KEY` | KuCoin exchange | `trading_stack/broker_apis.py` |
| `KUCOIN_API_SECRET` | KuCoin exchange | Same |
| `KUCOIN_API_PASSPHRASE` | KuCoin exchange | Same |
| `OANDA_API_KEY` | OANDA forex | `trading_stack/broker_apis.py` |
| `OANDA_ACCOUNT_ID` | OANDA forex | Same |
| `IB_API_KEY` | Interactive Brokers | `trading_stack/broker_apis.py` |
| `IB_ACCOUNT_ID` | Interactive Brokers | Same |
| `ALPACA_API_KEY` | Alpaca (stocks: TSLA, AAPL, etc.) | `trading_stack/alpaca_integration.py`, `trading_stack/config.py` |
| `ALPACA_SECRET_KEY` | Alpaca | Same |
| `ALPACA_BASE_URL` | Alpaca (default: paper API) | Same |

---

## Optional

| Variable | Purpose | Used by |
|----------|---------|---------|
| `DISCORD_WEBHOOK_URL` | Discord alert channel | `trading_stack/messaging.py` |
| `TEAKA_BIND_HOST` | Bridge bind address (default `0.0.0.0`) | `connect_python.py` |
| `TEAKA_BIND_PORT` | Bridge port (default `5050`) | `connect_python.py` |
| `TEAKA_BRAIN_FILE` | Custom brain JSON path | `connect_python.py` |

---

## Safety Gates

Live trading requires **all three** to be set:

```text
TEAKA_MODE=live
LIVE_TRADING_ENABLED=true
PRIVATE_EXCHANGE_API_ENABLED=true
```

Paper mode (default) needs no exchange credentials.

---

## Cursor Cloud Agent Secrets

If running as a Cursor Cloud Agent, add secrets at:
**Cursor Dashboard → Cloud Agents → Secrets**

Required for this repo:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
