# EV Node Main System Map

This file records the corrected hierarchy for Teaka and EV Stack.

## Correct conclusion

EV Node / EV Stack should be treated as the main system layer.

Teaka should be treated as an app, product, or trading layer that integrates with EV Node. Teaka is not the parent system.

## Evidence basis

The upstream EV Node repository identifies `ev-node` as the basis of the Evolve Stack.

The Evolve documentation describes `ev-node` as the modular node at the core of the stack, exposing an execution interface for custom VMs, Cosmos SDK logic, EVM paths, and custom runtimes.

The same documentation describes the system in terms of data availability, P2P sync, sequencing, execution, DA-backed security, and chain launch capability.

## Correct hierarchy

```text
EV Node / EV Stack / evstack/ev-node
  = primary blockchain, node, and framework layer
  = DA, P2P, sequencer, execution, RPC, signer, EVM, Cosmos, and custom runtime support

Teaka / teaka_trading_app
  = app, product, and trading layer
  = should call into or sit above EV Node through adapters or API clients

BlairGem/Ev
  = private EV control, bridge, config, handoff, runtime evidence, and GeoNode layer

BlairGem/GPT_AI_Workspace
  = GPT-side workspace and review layer
```

## Teaka placement

Teaka is associated with EV Node, but EV Node is not subordinate to Teaka.

Teaka should contain:

- UI or product code
- trading workflows
- adapters or API clients that communicate with an EV Node runtime
- configuration pointers to the EV Stack integration repo

Teaka should not contain a blind full copy of upstream `evstack/ev-node` or local runtime state.

## Pulling EV Stack into BlairGem

Recommended approach:

1. Create or use a dedicated BlairGem EV Stack repo, preferably `BlairGem/EV_Stack` or `BlairGem/Teaka_EV_Stack`.
2. Pull upstream `evstack/ev-node` into that repo by fork, mirror, or submodule strategy.
3. Keep Teaka connected by adapter or API client references.
4. Keep `BlairGem/Ev` as the private control and runtime evidence repo.

Do not pull the full upstream source directly into `BlairGem/teaka_trading_app` unless a deliberate vendor decision is made.

## Preferred structure

```text
BlairGem/EV_Stack or BlairGem/Teaka_EV_Stack
  upstream link: evstack/ev-node
  role: controlled main EV Stack integration repo

BlairGem/teaka_trading_app
  role: app, product, and trading layer
  integration: adapters or API clients into EV Stack

BlairGem/Ev
  role: private EV control, runtime evidence, and bridge layer

external upstream: evstack/ev-node
  role: public primary source framework
```
