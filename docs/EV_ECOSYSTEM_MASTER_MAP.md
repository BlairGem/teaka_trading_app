# EV Ecosystem Master Map & Diagnostics
**Captured:** September 11, 2026  
**Host:** BLAIRSPC (PC5000)  
**Operator Shell:** `C:\EV_Operator`  
**User Profiles:** `Blair` (interactive console), `Administrator` (elevated daemon / OneDrive context), `GEMBotSys` (service engine / Python venv)

---

## 1. Storage & Drive Architecture

| Drive / Path | Type / Mechanism | Role & Status |
| :--- | :--- | :--- |
| **`C:\EV_Files`** | Directory Junction (`mklink /J -> D:\EV_Files`) | Fast SSD path redirection to protect C: drive capacity while satisfying scripts that hardcode `C:\EV_Files`. Top-level items: 66. |
| **`D:\EV_Files`** | Physical NTFS Directory | Physical storage home for `EV_Files`. Houses `Bridge\` (`bridge_config.json`, `ev_microserver.py`), `Archives\`, and working drops. |
| **`E:\EV_Files`** | **Missing / Virtual Drive Target** | Referenced historically across `teaka_trading_app` (`ev_virtual_brain.json`, `E:\EV_Files\Bridge`). Not currently mounted; must be mapped or redirected to `D:\EV_Files` or substituted via `subst E: D:\EV_Files`. |
| **`F:\`** | Secondary / Removable / Virtual Mount | Target location for extended storage or virtual disk snapshots. |
| **`C:\EV_Core`** | Physical Directory | Active live core containing `COMMAND_ROUTER.ps1`, `Config`, `Daemons`, `Launcher`, `Scripts`, `start_ev_stack.ps1`, and `firemind_rise_init_launcher.ps1`. |
| **`C:\EV_Core_Final`** | Backup / Finalized Tree | Verified static snapshot of EV_Core. |
| **`C:\EV_Core.bak_*`** | Rollback Archive | Previous core state archive (Sep 1, 2025). |
| **`D:\EV_Core`** | Deep Neural Vault & Data Lake | Heavy data lake, chat histories, LangGraph states, and 44MB file inventory. |
| **WSL / Docker VHDX** | Dynamic ext4 Virtual Disk (`ext4.vhdx`) | Holds Linux/WSL2 system files, Docker container layers, and local Ollama model blobs (`/home/blair/.nvm/`, Ollama sha256 stores). |

---

## 2. Active Git Repositories (`C:\Users\Blair\EV_Git\`)

The Notepad Git audit reveals your local private and upstream repository layout under `C:\Users\Blair\EV_Git\`:

### Personal & Core Bot Repositories:
* **`Ev`** (`C:\Users\Blair\EV_Git\Ev`): `https://github.com/BlairGem1234/Ev.git` — The private EV Core repository.
  * Contains deep brain states:
    * `EV_CHAT_STATE_20260607.json`
    * `EV_FuzzyBrain_State.json`
    * `EV_GPT_BRAIN_CONNECTOR.json`
    * `EV_LIVE_LINK_INDEX.json`
    * `EV_PYTHONISTA_BRAIN_MAP_MASTER_2026-06-07.json`
    * `EV_PYTHONISTA_GIT_HTTP_MAP_DRAFT_2026-06-07.json`
    * `EV_REPO_MAP.json`
    * `EV_RUNTIME_STATE_MAP_DRAFT.json`
    * `EV_VCS_BRIDGE_ANALYSIS.json`
  * Contains bridge checkpoints:
    * `pc5000_blairgem_git_visibility_20260616.json`
    * `pc5000_chat_handoff_20260616.json`
    * `pc5000_d_drive_collision_fault_map.json`
    * `pc5000_display_hardware_fault_map.json`
    * `pc5000_split_index.json`
    * `evos_dropbox_runtime_bind_manifest_v1.json`
* **`Ev-EVBot-Operator`** (`C:\Users\Blair\EV_Git\Ev-EVBot-Operator`): `https://github.com/BlairGem1234/Ev.git` — Dedicated branch/worktree for Operator shell & EVBot.
* **`Ev-fuzzy-on-main`** (`C:\Users\Blair\EV_Git\Ev-fuzzy-on-main`): `https://github.com/BlairGem1234/Ev.git` — Fuzzy logic & Firemind cluster modules (`scikit-fuzzy`, fractional integration).
* **`GEMBot29`** (`C:\Users\Blair\EV_Git\GEMBot29`): `https://github.com/blairgem/GEMBot29.git` — GEMBot LLM & Discord/Telegram integration core.
* **`GPT_AI_Workspace`** (`C:\Users\Blair\EV_Git\GPT_AI_Workspace`): `https://github.com/BlairGem1234/GPT_AI_Workspace.git` — GPT interaction logs, prompt workflows, and memory traces.
* **`Pc-5000-curser-`** (`C:\Users\Blair\EV_Git\Pc-5000-curser-.git`): `https://github.com/BlairGem1234/Pc-5000-curser-.git` — PC5000 workstation specific Cursor agent states and diagnostics.

### Upstream StarForge Ecosystem:
* **`Nanle-code-StarForge`** (`C:\Users\Blair\EV_Git\_Upstream\StarForge\Blockchain\Nanle-code-StarForge`):
  * Upstream: `https://github.com/Nanle-code/StarForge.git`
  * Contains local Ollama integration (`src/utils/ollama.rs`), AI model router (`ai_model_router.rs`), security training, and Starforge plugin SDKs.
* **`Frykas-TheStarForge`** (`C:\Users\Blair\EV_Git\_Upstream\StarForge\Visual_Reference\Frykas-TheStarForge`):
  * Upstream: `https://github.com/Frykas/TheStarForge.git`
  * Visual assets, celestial configs, sprite animations (unbound weapon frames, flame particles), and simulation references for CanvasEngineCore / VisualCortex.

---

## 3. The `C:\EV_AI` Heavy Engine & Codex Ingest

From the `CRYPTO_ACCOUNT_AUDIT_20260803-154833.txt` diagnostic:
* **Node-RED Automation:** Houses broker message routing (`worker-timers` / `load-or-return-broker`).
* **API Key Enclave:** `C:\EV_AI\openai-api-key.json` and `EV_cop_binding_interface.json`.
* **Codex Core Engine:**
  * Active state: `C:\EV_AI\Codex\.codex-global-state.json`, `auth.json`, `models_cache.json`, `ollama-launch-models.json`.
  * Sandbox ACLs: `.sandbox\deny_read_acl_state.json`.
  * Plugin marketplace: OpenAI bundled plugins for browser control, visualization, Airtable, Atlassian Rovo, Base44, Boltz API.
* **Local Codex Workspace Archives:**
  * `C:\Users\Blair\Documents\Codex\2026-07-22\` and `2026-07-30\`: Stores audit snapshots of the TeAka trading system (`EV_LOCAL_SYSTEM_AUDIT.json`, `cdrive-inventory-local`).

---

## 4. The Deep Vault Inside `D:\EV_Files`

The audit confirms the exact location of the **EchoVault / Vault inside the Brain**:
* **`D:\EV_Files\EVBot_runtime\EchoVault\`:**
  * `echo_cava.vlt.json`
  * `echo_clouie.vlt.json`
  * `daemon_brain.json`
  * `chat_clock_index.json`
  * `clouie_overlay_map.json`
  * `clouie_status_overlay.json`
  * `commands.json` & `EchoVault_command.json`
  * `EVBot_Notepade.json`
  * `evbot_reflex_plugin.json`
* **Root Files in `D:\EV_Files\` (Audit Verified):**
  * `ev_viral_brain.json` (525 bytes, active reflex brain)
  * `EV_Sensory_Feed.json` (5,586 bytes, telemetry stream)
  * `ev_runtime_status.json` (38 bytes, online status flag)
  * `EVBridge_Update_Service.ps1`, `EV_CERT_ALL.ps1`, `Move_EV_Logs_To_D.ps1`, `Check_Notepad_Runtime.ps1`
  * `Brain\`, `Brain_split_backup_20260804_111803\`, `Recovered_Brain\`
  * `RoboShady\`, `Mt_Greenland\`, `Voice\`, `VoiceJournal\`, `VoiceMemory\`, `VoiceRuntime\`
  * `Spells\`, `Reflex\`, `Hooks\`, `Launchers\`, `Paper_Practice\`
  * `Bridge\` (`bridge_config.json` [45 B, Archive], `ev_microserver.py` [45 B, Archive] - fully hydrated, not 0 KB)

---

## 5. Mobile & Cross-Device Brain Link

* **Phone First Execution:**
  * Pythonista: `phone/lore_script.py`, `phone/pythonista_boot.py`, mapped directly to `C:\Users\Blair\EV_Git\Ev\brain\EV_PYTHONISTA_BRAIN_MAP_MASTER_2026-06-07.json`.
  * Scriptable: `phone/Scriptable_EVBot_Lore.js`, mapped to `ev_scriptable_runtime_chat_checkpoint_2026-06-16.json`.
  * State files: `therruedevil7.json`, `Cross_device_brain.json`, `evbot_lore_state.json`.
* **Safe Fallback:** Operates OFFLINE on device; promotes to ONLINE when `http://<lan-ip>:5050` or `127.0.0.1:5050` is reachable.

---

## 6. Local EV Microservice Mesh & Codex FastMCP Adapter

TeAka is now connected directly to the local EV microservice mesh via `bridge/ev_mcp_adapter.py` and probed via `/api/ev/mesh/status`:

| Service | Port | Endpoint Role |
| :--- | :--- | :--- |
| **GEMBot** | `http://127.0.0.1:5056` | Local Qwen `qwen3:4b` bounded second-opinion agent (`gembot_ask`) |
| **RoboShady Brain** | `http://127.0.0.1:5060` | Bounded file diagnostics, cataloging, SQLite inventory, and builds (`roboshady_*`) |
| **Minerals AI** | `http://127.0.0.1:5055` | Geology & GIS specialist agent (`minerals_geology_ask`) |
| **Windows Ollama** | `http://127.0.0.1:11434` | Local model server & tags query (`/api/tags`) |
| **EV Memory** | `http://127.0.0.1:11436` | PostgreSQL-backed persistent conversation turns & stats (`ev_memory_chat`) |
| **Mt Greenland RoboShady** | `http://127.0.0.1:5057` | Docker specialist container for GIS/evidence and mapper status |

