# Synthetic paper-session example

`candles.csv` contains five hand-authored hourly OHLCV rows for BTC/USDT, from
2026-01-01 00:00 through 04:00 UTC. The values are artificial round numbers
selected to exercise prior-candle decisions, next-open execution, fees,
slippage and finite liquidation. They are not exchange history, a market
forecast, recovered performance or a fitted model artifact.

`strategies.json` is a one-indicator example using the editor-array contract:
indicator ID `entry`, reference `sma_entry`, explicit BUY side, period 1,
threshold 1, 0.01% equity risk, 2% stop, 50% take profit. It is a software
test example, not a trading recommendation. The browser test adds an explicit
SELL exit and a second SELL-only strategy through the actual editor.

Replay exports record the supplied origin label, exact source path, SHA256,
inclusive dates, fees/slippage and actual execution results. The label is
user-supplied; a hash identifies source bytes, not their authenticity.
