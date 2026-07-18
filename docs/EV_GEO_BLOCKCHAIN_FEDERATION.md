# Teaka and EV GeoBlockchain Federation

This branch organises Teaka alongside the EV GeoBlockchain without merging the two systems.

## Teaka scope

Teaka owns:

- trading application code;
- exchange and market-data integrations;
- strategy and backtesting logic;
- risk management;
- trading databases and dashboards;
- crypto-specific transaction or ledger components when verified in source;
- deployment and runtime configuration with secrets excluded.

## EV GeoBlockchain scope

The EV repository owns geological project provenance, GeoNode controls, GIS evidence, project manifests, hashes and verification records for Mt Greenland, Waimangaroa, Britannia, Owen River and Glenroy.

## Integration boundary

- Repositories remain independent.
- Integration occurs only through documented adapters or APIs.
- Geological evidence must not be copied into trading state without an explicit reviewed transformation.
- Exchange keys, wallet secrets, API tokens and private credentials must not be stored in Git.
- Existing Teaka crypto or blockchain components must be inventoried and verified before they are renamed or redesigned.

## Linked organisation branch

- EV repository: `BlairGem/Ev`, branch `ev-geo-blockchain-organisation`
- Teaka repository: `BlairGem/teaka_trading_app`, branch `ev-geo-blockchain-organisation`
