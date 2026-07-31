# Upload intake notes

Safe artifacts imported from local CS / chat uploads.

## Imported
- `docs/GEMBotSys_path_map.txt` — local GEMBotSys / EV_Link file map
- `scripts/check_ev_for_chatgpt.ps1` — EV port 5000 health check
- `Config/backtest_config.json` — backtest strategy parameters
- `scripts/auth_api_example.py` — sanitized JWT auth example (env-based secrets)
- `scripts/create_validate_brain.ps1` — cleaned brain validator writer

## Not imported (secrets)
- KuCoin keys (`ev_keys*.json`) — rotate at exchange
- Dropbox tokens / app secret (`dropbox_credentials*.json`, `dropbox_auth*.py`) — revoke in Dropbox app console
- Hardcoded Flask/JWT/Postgres password app upload — replaced by sanitized example only

## Local GEMBot source (still on PC)
From the path map, primary bot code appears under:
`C:\Users\GEMBotSys\EV_Link\GemBot\` (`ev_bot.py`, `gem_bot.py`, `ev_remote_server.py`).
