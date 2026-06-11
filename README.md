# Prosperity 4 trader

IMC Prosperity 4 (April 2025) algorithmic trading competition. Two product strategies:

**EMERALDS**: stable market-making around the wall mid. Hit 1022 XIRECs in v2 and left it alone after that.

**TOMATOES**: combined-signal market-making. Found `-0.44` lag-1 autocorrelation (after a +2 move, next step reverses ~1.4 on average, 64% directional accuracy). Layered a volume-asymmetry signal (bid_vol vs ask_vol, 0.22 correlation). Combined signal: 0.61 correlation, ~73.7% directional accuracy. Used to shift fair value before quoting.

## Files

- `prosperity_trader_v6.py` - v6, mean-reversion signal only
- `prosperity_trader_v8.py` - v8, combined signal (final submission)
