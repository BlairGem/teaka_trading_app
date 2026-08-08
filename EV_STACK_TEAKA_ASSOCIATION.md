# EV Stack / Teaka Association

This branch records the working interpretation that EV Stack / EV Node should be associated with the Teaka app layer, not treated as an unrelated side system.

## Branch

- Repository: `BlairGem/teaka_trading_app`
- Branch: `evstack-teaka-association`
- Purpose: map Teaka to the EV Stack / EV Node framework layer

## Association model

```text
Teaka / teaka_trading_app
  = product / app / trading interface layer

EV Stack / evstack/ev-node
  = primary node / blockchain framework layer

BlairGem/Ev
  = private EV control, bridge, config, handoff, runtime evidence, GeoNode layer

BlairGem/GPT_AI_Workspace
  = GPT-side workspace and review layer
```

## External upstream

- Upstream repository: `evstack/ev-node`
- Clone URL: `https://github.com/evstack/ev-node.git`
- Framework: EV Node / Evolve Stack
- Role: modular blockchain / node / DA / P2P / sequencer / execution framework

## Teaka role

Teaka should be treated as the app or product layer that may sit above, call into, or be supported by EV Stack.

Do not assume Teaka already contains the EV Stack source. Prior indexed Git search did not find direct EV Node or evstack source inside `BlairGem/teaka_trading_app`.

## Clean integration options

1. Keep Teaka as app layer and point to a dedicated BlairGem EV Stack repo.
2. Add EV Stack as a submodule only if deliberate.
3. Add adapter code in Teaka that talks to an EV Stack node API.
4. Keep node runtime, chain state, signer files, databases, and generated artifacts out of Teaka.

## Do not mix

Do not blindly copy the full external `evstack/ev-node` source into Teaka.

Do not commit:

- node databases
- signer keys
- passphrase files
- generated chain state
- runtime logs containing secrets
- local machine auth/config files

## Recommended final structure

```text
BlairGem/teaka_trading_app
  app/product layer
  adapters/API clients only

BlairGem/EV_Stack or BlairGem/Teaka_EV_Stack
  controlled BlairGem EV Stack integration repo
  upstream pointer/submodule/fork strategy

BlairGem/Ev
  private control + runtime evidence + bridge layer

external upstream: evstack/ev-node
  public source framework
```
