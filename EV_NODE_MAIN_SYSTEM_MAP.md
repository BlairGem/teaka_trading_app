# EV Node Main System Map & Swarm Connectivity

This file records the hierarchical mapping of EV Node, EV Stack, the EV Swarm, and the TeAka trading application layer.

## System Hierarchy

```text
EV Node / EV Stack (evstack/ev-node)
  │── Primary blockchain, node, and consensus framework layer
  │── Data Availability (DA), P2P networking, sequencer, execution APIs
  │
  ├── BlairGem/Ev (Private EV OS & Control)
  │     └── Brain recovery, Fuzzy Brain, Qwen traces, GeoNode / GeoBlockchain
  │
  ├── blairgem/GEMBot29 (AI Swarm Gateway)
  │     └── Qwen Flask gateway, Ollama split mode, agent interfaces
  │
  ├── BlairGem/GPT_AI_Workspace (Sync & Workspace)
  │     └── Ollama workspace sync; 30B is disabled on this PC; use qwen2.5:3b
  │
  ├── BlairGem/Pc-5000-curser- (Memory & MCP)
  │     └── Postgres GEMBot memory API, 14-tool EV<->Cursor MCP server
  │
  └── BlairGem/teaka_trading_app (App & Execution Layer)
        ├── EV Node Adapter (`ev_node.py`)
        ├── EV Swarm Signal Adapter (`paper_trading/ev_swarm_adapter.py`)
        └── PaperBroker virtual execution with strict risk guardrails
```

## TeAka Integration Guidelines

1. **Keep EV Stack decoupled**: TeAka acts as an authorized client application and does not bundle internal blockchain state or private key databases.
2. **Deterministic Risk Controls**: AI signals emitted from the EV Swarm (Qwen, Ollama, GEMBot) must always pass through TeAka's `PaperBroker` and `RiskManagementService` before execution.
3. **Auditability**: Trade receipts and paper execution logs link back to the EV Virtual Brain (`ev_virtual_brain.json`) and EV Swarm generation metadata.
