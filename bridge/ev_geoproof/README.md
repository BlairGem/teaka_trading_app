# EV GeoProof Chain

GeoProof (`GPROOF`) is a hash-linked geospatial evidence token for the EV GeoBlockchain.

## What it is

A proof-of-evidence grid that links geospatial data layers (UAV magnetics, LiDAR, assays, permits, groundwater bores) to 50m NZTM2000 grid cells. Each cell carries a hash chain proving data provenance.

## Relationship to TeAka

GeoProof is **not** a trading token. It's an evidence/provenance layer.

- TeAka owns trading (crypto, forex, stocks)
- EV GeoBlockchain owns geospatial proof
- They integrate only through adapters (see `ev_node.py`)

## Files

- `geoproof_token.json` — Token spec and bore cell data
