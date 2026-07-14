# TeAka Trading System

## Status

TeAka is currently being prepared for controlled paper trading validation.

Live trading is not enabled by this documentation.

## Architecture

```
Market Data
    |
    v
Strategy Engine
    |
    v
Risk Layer
    |
    v
Paper Order Simulator
    |
    v
Performance Tracking
```

## Current Components

- React dashboard frontend
- TypeScript build workflow
- EV integration references
- Database and runtime components under verification

## Paper Trading Requirements

Before enabling any automated strategy:

- Confirm paper/simulation mode
- Confirm market data feed
- Confirm virtual balance tracking
- Confirm simulated orders only
- Confirm logs and performance records
- Confirm live exchange orders remain disabled

## Safety Rules

- Never commit API keys or private credentials
- Do not enable live trading during testing
- Verify exchange permissions before any future production use
- Keep runtime state and logs auditable

## EV Integration

The EV runtime repository maintains system maps, manifests, launchers and TeAka references. TeAka integration should follow verified runtime documentation before activation.

## Next Validation Steps

1. Locate backend services
2. Locate trading strategy modules
3. Validate paper execution path
4. Run controlled simulation
5. Review performance before any live deployment
