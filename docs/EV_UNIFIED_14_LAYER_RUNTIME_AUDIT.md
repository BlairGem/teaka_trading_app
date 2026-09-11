# Unified EV Stack 14-Layer Runtime Audit & Topology

## Executive Summary
This document formalizes the runtime mapping, process hierarchy, user context boundaries, configuration state, and unified startup pipeline for the complete **EV Ecosystem on PC5000 (BLAIRSPC)**.

---

## 1. Complete 14-Layer Runtime Architecture

### Layer 1: EV Blair Runtime / Legacy EVBC
- **Canonical Path:** `C:\Users\Blair\EV_Git\Ev` & `C:\Users\Blair\EV_Git\Ev-fuzzy-on-main`
- **Executable / Entry Point:** `python -m ev_runtime_firemind_brainloop.py`, `fuzzy_control.py`, `ev_relay_fusionlink.py`
- **Process / Service / Task:** Interactive Python runtime (`python.exe` under user `Blair`)
- **Owning User:** `Blair` (Interactive console / desktop session)
- **Ports:** Internal PythonIPC / loopback sockets; interfaces to local SQLite / JSON logs
- **Config / State / Cache:** `C:\Users\Blair\EV_Git\Ev\brain\EV_CHAT_STATE_20260607.json`, `EV_FuzzyBrain_State.json`, `EV_LIVE_LINK_INDEX.json`, `pc5000_d_drive_collision_fault_map.json`
- **Brain / Memory Source:** `EV_PYTHONISTA_BRAIN_MAP_MASTER_2026-06-07.json`, `EV_LIVE_LINK_INDEX.json`
- **Startup Mechanism:** Invoked via `start_ev_stack.ps1` or interactive user terminal
- **Dependencies:** Python 3.10+, `scikit-fuzzy`, NumPy, SciPy
- **Invoked By:** User `Blair` or EV Startup Layer
- **Status:** **Active & Core** (Provides fuzzy integration, reflex loops, and trading math)

### Layer 2: StarForge Runtime
- **Canonical Path:** `C:\Users\Blair\EV_Git\_Upstream\StarForge\`
  - Blockchain/Router: `Nanle-code-StarForge`
  - Visual Reference: `Frykas-TheStarForge`
- **Executable / Entry Point:** `cargo run` (Rust binary: `ollama.rs`, `ai_model_router.rs`) / WebAssembly Canvas runtime
- **Process / Service / Task:** StarForge Model Router / Canvas Engine Daemon
- **Owning User:** `Blair`
- **Ports:** Port `11435` (StarForge upstream router) / proxy to Ollama `11434`
- **Config / State / Cache:** `src/config/`, Cargo manifests, sprite & canvas manifests
- **Brain / Memory Source:** Bound via `evbot/ev_viral_brain.json` (`CanvasEngineCore`, `VisualCortex`)
- **Startup Mechanism:** `cargo run --release` or PowerShell launcher script
- **Dependencies:** Rust toolchain, Ollama service, local GPU / Vulkan / DirectX
- **Invoked By:** EV Commander or manual workstation terminal
- **Status:** **Active Upstream & Visual Core** (Maintains local routing & UI canvas engine)

### Layer 3: EV_Core
- **Canonical Path:** `C:\EV_Core` (Active), `C:\EV_Core_Final` (Golden baseline), `D:\EV_Core` (Heavy data lake)
- **Executable / Entry Point:** `COMMAND_ROUTER.ps1`, `start_ev_stack.ps1`, `firemind_rise_init_launcher.ps1`, `ev_flask_fused_server.py`
- **Process / Service / Task:** PowerShell orchestrator & central routing engine
- **Owning User:** Dual-role: `Administrator` (elevated system daemons) / `Blair` (interactive CLI)
- **Ports:** Port `5000` (Legacy fused UI) / `5050` (TeAka Python bridge)
- **Config / State / Cache:** `C:\EV_Core\Config\`, `C:\EV_Core\Status\dior_brain_core.json`, `C:\EV_Core\Logs\`
- **Brain / Memory Source:** `C:\EV_Core\Status\`, `D:\EV_Files\ev_viral_brain.json`, `D:\EV_Core\`
- **Startup Mechanism:** Windows Task Scheduler / Admin startup batch
- **Dependencies:** PowerShell 5.1/7+, Python 3.10+, NSSM service wrappers
- **Invoked By:** Windows Login / Startup layer
- **Status:** **Active Central Orchestrator**

### Layer 4: EV_Files / EchoVault
- **Canonical Path:** Physical: `D:\EV_Files` | Fast Junction: `C:\EV_Files` (`mklink /J -> D:\EV_Files`) | Legacy: `E:\EV_Files` (`subst E: D:\EV_Files`)
- **Executable / Entry Point:** Storage store / Data vault. Files: `bridge_config.json`, `ev_microserver.py`, `ev_viral_brain.json`
- **Process / Service / Task:** NTFS Storage Layer; houses EchoVault: `D:\EV_Files\EVBot_runtime\EchoVault\`
- **Owning User:** SYSTEM / Administrators (Inherited ACLs)
- **Ports:** N/A (Storage layer)
- **Config / State / Cache:** 66 top-level items; `EchoVault\` (`echo_cava.vlt.json`, `echo_clouie.vlt.json`, `daemon_brain.json`, `commands.json`)
- **Brain / Memory Source:** Authoritative physical home for active reflex brain (`ev_viral_brain.json`), sensory feed (`EV_Sensory_Feed.json`), and runtime status (`ev_runtime_status.json`)
- **Startup Mechanism:** Mounted at boot via Windows volume manager; `subst E:` initialized by startup script
- **Dependencies:** Physical Drive D:
- **Invoked By:** All layers (EV_Core, EV_AI, TeAka, Codex, GEMBot, RoboShady)
- **Status:** **Active Authoritative State Store**

### Layer 5: EV_AI
- **Canonical Path:** `C:\EV_AI`
- **Executable / Entry Point:** Node-RED runtime (`node.exe`), Codex global state manager, Python OpenAI/Ollama brokers
- **Process / Service / Task:** Background AI gateway / Node-RED flows
- **Owning User:** `Blair` / `GEMBotSys`
- **Ports:** Port `1880` (Node-RED broker) / IPC
- **Config / State / Cache:** `C:\EV_AI\Codex\.codex-global-state.json`, `auth.json`, `openai-api-key.json`, `models_cache.json`, `ollama-launch-models.json`
- **Brain / Memory Source:** `C:\EV_AI\Cursor\Memory\EV_MEMORY.json`, LangGraph state
- **Startup Mechanism:** NSSM service `EV_AI_Service` or Node-RED launcher
- **Dependencies:** Node.js v24.18.0 (runtime: `C:\EV_Node`), npm, Python
- **Invoked By:** EV Startup Layer / Windows Service
- **Status:** **Active Engine Layer**

### Layer 6: EVOS
- **Canonical Path:** `C:\EV_Core\Daemons` & `D:\EV_Files\Runtime`
- **Executable / Entry Point:** `evos_runtime_daemon.py`, `evos_dropbox_runtime_bind_manifest_v1.json`, `enclave_memory_core.py`
- **Process / Service / Task:** Kernel daemon / system abstraction layer
- **Owning User:** `Administrator` / `GEMBotSys`
- **Ports:** Internal RPC / named pipes
- **Config / State / Cache:** `C:\EV_Core\Daemons\config.json`, `D:\EV_Files\Runtime\teaka_runtime_state.json`
- **Brain / Memory Source:** `enclave_memory_state.json`, `reflex_log.txt`
- **Startup Mechanism:** Elevated daemon script via NSSM
- **Dependencies:** Python 3.10+, Windows Management Instrumentation (WMI)
- **Invoked By:** `start_ev_stack.ps1`
- **Status:** **Active Core Daemon**

### Layer 7: EV Commander / EV_Command_8080
- **Canonical Path:** `C:\EV_Core\Daemons\EVCommander\` & `C:\EV_Operator`
- **Executable / Entry Point:** `EV_Command_8080.exe` / `python ev_commander_gateway.py`
- **Process / Service / Task:** Active socket gateway daemon
- **Owning User:** `Administrator` / `Blair`
- **Ports:** **Port 8080** (HTTP & WebSocket Command Interface)
- **Config / State / Cache:** `D:\EV_Files\EVBot_runtime\EchoVault\commands.json`, `EchoVault_command.json`
- **Brain / Memory Source:** Live binding to EchoVault & EV Sensory Feed
- **Startup Mechanism:** Auto-started via `C:\EV_Operator\launch_commander.ps1` or boot script
- **Dependencies:** Network loopback, Windows socket layer, EV_Core
- **Invoked By:** EV Operator / Remote Mobile Clients / FastMCP Adapter
- **Status:** **ALIVE & RUNNING (Verified Active)**

### Layer 8: EV Operator
- **Canonical Path:** `C:\EV_Operator`
- **Executable / Entry Point:** `powershell.exe` in `C:\EV_Operator` (Custom profiles, prompt bindings, ANSI color UI)
- **Process / Service / Task:** Interactive operator shell session (`Terminal] Operator=C:\EV_Operator`)
- **Owning User:** `Blair` (Running interactive operations)
- **Ports:** Console TTY; sends commands to `8080`, `5050`, `5056`, `5060`
- **Config / State / Cache:** `C:\EV_Operator\profile.ps1`, `C:\EV_AI\Cursor\Memory\EV_MEMORY.json`
- **Brain / Memory Source:** `C:\EV_AI\Cursor\Memory\EV_MEMORY.json`, `D:\EV_Files\ev_viral_brain.json`
- **Startup Mechanism:** User terminal launch / Desktop shortcut
- **Dependencies:** Windows Terminal, PowerShell 7 / Windows PowerShell
- **Invoked By:** Human Operator (`Blair`)
- **Status:** **Active Primary Operations Console**

### Layer 9: Windows Codex Stable
- **Canonical Path:** `C:\Users\Blair\AppData\Local\Programs\OpenAI-Codex` (or global npm: `C:\EV_AI\npm\codex`)
- **Executable / Entry Point:** `codex.exe` / `node codex-cli.js`
- **Process / Service / Task:** Stable Codex agent UI & background LSP
- **Owning User:** `Blair`
- **Ports:** Dynamic localhost ports / FastMCP stdio interface
- **Config / State / Cache:** `C:\Users\Blair\.codex\config.json`, `C:\EV_AI\Codex\.codex-global-state.json`
- **Brain / Memory Source:** `C:\Users\Blair\Documents\Codex\`, `EV_LOCAL_SYSTEM_AUDIT.json`
- **Startup Mechanism:** Desktop application launch
- **Dependencies:** Windows Node.js v24.18.0
- **Invoked By:** User `Blair`
- **Status:** **Active Primary Coding Agent**

### Layer 10: Windows Codex Beta
- **Canonical Path:** `C:\Users\Blair\AppData\Local\Programs\OpenAI-Codex-Beta` (or canary npm package)
- **Executable / Entry Point:** `codex-beta.exe`
- **Process / Service / Task:** Experimental feature testing / preview builds
- **Owning User:** `Blair`
- **Ports:** Dynamic localhost / isolated socket
- **Config / State / Cache:** Isolated configuration in `%APPDATA%\CodexBeta\`
- **Brain / Memory Source:** Same workspace projects, shared audit logs
- **Startup Mechanism:** Manual user testing
- **Dependencies:** Windows Node.js runtime
- **Invoked By:** User `Blair`
- **Status:** **Compatibility & Preview Layer** (Preserve without collision)

### Layer 11: WSL2 Native Codex
- **Canonical Path:** Linux filesystem: `/home/blair/.nvm/versions/node/.../bin/codex` (inside Ubuntu distro)
- **Executable / Entry Point:** Native Linux ELF binary `/usr/local/bin/codex` or NVM global binary
- **Process / Service / Task:** WSL2 background agent process
- **Owning User:** `blair` (Linux UID 1000)
- **Ports:** Shares localhost with Windows via WSL2 mirrored networking
- **Config / State / Cache:** `~/.codex/`, Linux native SQLite cache
- **Brain / Memory Source:** Accesses Windows files via `/mnt/c/` and `/mnt/d/`
- **Startup Mechanism:** Started inside WSL2 shell (`wsl.exe -d Ubuntu`)
- **Dependencies:** WSL2 Linux Kernel 6.x, Ubuntu 22.04/24.04, Linux NVM
- **Invoked By:** Terminal or Cursor Remote-WSL
- **Status:** **Needs Decoupling:** Must use native Linux binary instead of invoking `/mnt/c/EV_AI/npm/codex.cmd` across the 9P boundary

### Layer 12: Cursor Runtime
- **Canonical Path:** `C:\Users\Blair\AppData\Local\Programs\cursor\`
- **Executable / Entry Point:** `Cursor.exe`
- **Process / Service / Task:** IDE process, extension hosts, Language Server Protocol
- **Owning User:** `Blair`
- **Ports:** Dynamic extension host ports; connects to FastMCP adapters
- **Config / State / Cache:** `C:\Users\Blair\AppData\Roaming\Cursor\`, `.cursor/`, MCP server catalog
- **Brain / Memory Source:** `C:\EV_AI\Cursor\Memory\EV_MEMORY.json`, Git workspace repos
- **Startup Mechanism:** User IDE launch
- **Dependencies:** Electron, Chromium, VS Code OSS engine
- **Invoked By:** User `Blair`
- **Status:** **Active Primary Workspace Environment**

### Layer 13: Remote Desktop Commander
- **Canonical Path:** Windows Remote Desktop Services (`mstsc.exe` / RDP Gateway) & `EV_Remote_Desktop`
- **Executable / Entry Point:** `svchost.exe -k termsvcs`, `C:\EV_Core\Launcher\rdp_tunnel_launcher.ps1`
- **Process / Service / Task:** Windows RDP session manager & Tailscale/ZeroTier tunnel
- **Owning User:** `Administrator` / `Blair`
- **Ports:** Port `3389` (Standard RDP) / encrypted tunnel port
- **Config / State / Cache:** Windows Registry RDP policies, Tailscale state
- **Brain / Memory Source:** N/A (Transport layer)
- **Startup Mechanism:** Windows Service (TermService)
- **Dependencies:** Windows Network Stack, WAN/LAN security
- **Invoked By:** Remote client (iPad, laptop, mobile)
- **Status:** **Active Remote Ingress**

### Layer 14: Docker / Ollama / Local EV Service Mesh
- **Canonical Path:** Physical `.vhdx` on disk; Ollama Windows native at `C:\Users\Blair\AppData\Local\Programs\Ollama\ollama.exe`
- **Executable / Entry Point:**
  - Ollama: `ollama.exe serve` (:11434)
  - Minerals AI: `python minerals_service.py` (:5055)
  - GEMBot: `python gembot_service.py` (:5056)
  - Mt Greenland Docker: `docker run ... mt_greenland_roboshady` (:5057)
  - RoboShady Brain: `python roboshady_brain.py` (:5060)
  - EV Memory: `python memory_service.py` (:11436)
- **Process / Service / Task:** Local microservice mesh
- **Owning User:** `Blair` (Ollama/Python services) / Docker Desktop VM
- **Ports:** `5055`, `5056`, `5057`, `5060`, `11434`, `11436`
- **Config / State / Cache:** Docker container volumes, SQLite DBs, Ollama model cache
- **Brain / Memory Source:** PostgreSQL / SQLite persistent stores, Qwen model blobs
- **Startup Mechanism:** Docker Desktop boot + `scripts/cloud_agent_start.sh` / `start_mesh.ps1`
- **Dependencies:** WSL2 backend, GPU compute (CUDA/DirectML)
- **Invoked By:** EV Startup Layer / Codex FastMCP Adapter / TeAka Bridge
- **Status:** **Active Local AI Specialist Mesh**

---

## 2. Unified Target Startup Pipeline

```text
[ Windows Boot & User Login (Blair / Admin) ]
                      │
                      ▼
[ EV Startup Layer ] ──> Creates Junctions (C:\EV_Files -> D:\EV_Files)
                      ──> Maps Virtual Drive (subst E: D:\EV_Files)
                      ──> Checks Permissions (Administrator <-> Blair)
                      │
                      ▼
[ EV Blair Runtime / EVOS ] ──> Boots Daemons (enclave_memory, reflex)
                             ──> Firemind fuzzy cluster & frac-state
                      │
                      ▼
[ EV_Core ] ──> COMMAND_ROUTER.ps1
             ──> Launches TeAka Python Bridge (:5050)
                      │
                      ▼
[ EV_AI ] ──> Node-RED broker (:1880)
           ──> Global Codex state & auth initialization
                      │
                      ▼
[ EV_Files / EchoVault / Brain ] ──> Loads ev_viral_brain.json
                                  ──> Mounts EchoVault (echo_cava / echo_clouie)
                      │
                      ▼
[ EV Commander (:8080) + EV Operator ] ──> Socket Gateway Live (:8080)
                                        ──> Interactive Operator Shell (C:\EV_Operator)
                      │
                      ▼
[ Coding & Agent Layer ] ──> Cursor Runtime
                          ──> Windows Codex Stable
                          ──> Windows Codex Beta (isolated)
                          ──> WSL2 Native Codex (Linux binary)
                          ──> Connects to FastMCP Adapter (bridge/ev_mcp_adapter.py)
                      │
                      ▼
[ StarForge Runtime ] ──> Model Router & Visual Canvas Engine
                      │
                      ▼
[ Local EV Service Mesh ] ──> Ollama (:11434)
                          ──> Minerals Geology AI (:5055)
                          ──> GEMBot Qwen (:5056)
                          ──> Mt Greenland Docker (:5057)
                          ──> RoboShady Brain (:5060)
                          ──> EV Memory Store (:11436)
```

---

## 3. Discovered Collisions, Conflicts & Remediation

1. **WSL2 vs. Windows Codex Execution Collision:**
   - *Issue:* Running `codex` inside WSL2 was resolving to the Windows batch wrapper `/mnt/c/EV_AI/npm/codex.cmd` across the interop boundary, causing path mangling and latency.
   - *Fix:* In WSL2, run `nvm use 22 && npm install -g @openai/codex@latest` and ensure `/home/blair/.nvm/.../bin` precedes `/mnt/c/...` in Linux `$PATH`.
2. **Missing `E:\` Drive Dependency:**
   - *Issue:* Legacy scripts crash on `E:\EV_Files` because physical E: is unmounted.
   - *Fix:* Preserved seamless compatibility by running `subst E: D:\EV_Files` at login.
3. **User Profile Permission Split (`Blair` vs `Administrator`):**
   - *Issue:* OneDrive tokens and elevated daemons run as `Administrator`, blocking interactive `Blair` console access.
   - *Fix:* Created directory junction `mklink /J "C:\Users\Blair\OneDrive\EV_Core" "C:\Users\Administrator\OneDrive\EV_Core"`.
4. **Duplicate Brain State Sources:**
   - *Resolution:* Authoritative live state is pinned to `D:\EV_Files\ev_viral_brain.json` and `D:\EV_Files\EVBot_runtime\EchoVault\daemon_brain.json`. `connect_python.py` and `teaka_trading_app_validate_brain.py` dynamically resolve across these paths with zero code modifications needed when switching workstations.
