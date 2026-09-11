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
  * Visual assets, celestial configs, and game/simulation engine references.

---

## 3. The Administrator vs. Blair Profile Conflict

### Symptom:
Scripts fail to run cleanly or claim "cannot run properly" when launched from `Blair`'s interactive terminal.

### Root Cause:
1. **OneDrive Mount Mismatch:**
   * OneDrive and the active Cloud Brain sync are registered under `C:\Users\Administrator\OneDrive` instead of `C:\Users\Blair\OneDrive`.
   * When `Blair` attempts to start the stack, access is denied to Administrator's OneDrive folders due to Windows ACL security boundaries.
2. **Elevation Scope:**
   * PowerShell was launched as standard user `Blair` while the daemons (`EV_Waitress_Launcher.ps1`, `start_ev_stack.ps1`, Docker daemon) require administrative elevation (`Run as Administrator`).

### Solution:
* Run PowerShell via **Run as Administrator** on PC5000.
* Ensure shared brain paths route through directory junctions in `C:\EV_Files` or `D:\EV_Files` instead of user-specific `OneDrive` subpaths.
