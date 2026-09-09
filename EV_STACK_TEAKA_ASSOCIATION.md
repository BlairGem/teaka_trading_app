# EV Stack / Teaka Association & Swarm Mapping

This document records the architectural and Git association between EV Stack, EV Node, the EV Swarm (Qwen, Ollama, GEMBot, EV Virtual Brain), and the TeAka trading application layer.

## Architecture and Git Ecosystem Map

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        EV Ecosystem Architecture                       │
├────────────────────────┬───────────────────────────────────────────────┤
│ Repository             │ Role and Tracked Assets                       │
├────────────────────────┼───────────────────────────────────────────────┤
│ evstack/ev-node        │ Upstream modular blockchain framework         │
│ (upstream)             │ DA, P2P, execution, sequencer, CometBFT/Evolve│
├────────────────────────┼───────────────────────────────────────────────┤
│ BlairGem1234/Ev        │ Private EV OS, brain recovery, fuzzy brain,   │
│ (worktrees: Ev,        │ Qwen bundle traces, GeoNode, EVBot operator   │
│ Ev-EVBot-Operator,     │                                               │
│ Ev-fuzzy-on-main)      │                                               │
├────────────────────────┼───────────────────────────────────────────────┤
│ blairgem/GEMBot29      │ First-party AI bridges (Qwen Flask gateway,   │
│                        │ Ollama connectors, local agent tooling)       │
├────────────────────────┼───────────────────────────────────────────────┤
│ BlairGem1234/          │ Phone/Scriptable sync, Google Drive admin     │
│ GPT_AI_Workspace       │ wiring, Qwen 30B Ollama verification          │
├────────────────────────┼───────────────────────────────────────────────┤
│ BlairGem1234/          │ PC5000 Cursor MCP server (Postgres brain,     │
│ Pc-5000-curser-        │ 14 MCP tools, Ghost circles, Cloak branch)    │
├────────────────────────┼───────────────────────────────────────────────┤
│ BlairGem1234/          │ TeAka product/trading layer, PaperBroker,     │
│ teaka_trading_app      │ EV Node client adapter (`ev_node.py`),        │
│                        │ EV Swarm paper trading execution adapter      │
└────────────────────────┴───────────────────────────────────────────────┘
```

## Machine-Readable Specification

A structured schema of all repos, endpoints, and paper parameters is tracked at:
- `EV_SWARM_INTEGRATION_MAP.json`

## Integration Boundaries

1. **Teaka Layer**:
   - Resides in `BlairGem/teaka_trading_app`.
   - Contains trading strategies, paper broker, order management, and UI.
   - Communicates with EV Node and EV Swarm via clean adapters (`ev_node.py` and `paper_trading/ev_swarm_adapter.py`).
2. **EV Node / EV Stack Framework**:
   - Primary blockchain layer (`evstack/ev-node`).
   - Handles data availability, consensus/sequencing, and cryptographic state verification.
3. **EV Swarm (Qwen / Ollama / GEMBot / Virtual Brain / Core Memory)**:
   - Provides AI-driven market analysis, sentiment evaluation, and multi-agent coordination.
   - Core memory anchor: `C:\EV_AI\Cursor\Memory\EV_MEMORY.json`.
   - Local LLM inference: Ollama (:11434) using lightweight, fast local models (such as `qwen2.5:3b`, `qwen3:4b`, or `phi4-mini:3.8b`) suitable for PC hardware, without requiring heavy 30B/32B models.
   - Fed into TeAka's paper broker where all trades are bounded by conservative risk parameters (50 USDT maximum order, stop loss, take profit, drawdown circuit breaker).
