# prosperity 4 trader

my bot for imc prosperity 4 (april 2025), an algorithmic trading game.

two products to trade: emeralds (stable) and tomatoes (noisier).

- emeralds: just market making around a fixed fair value of 10000.
- tomatoes: same market making but the fair value gets shifted based on the recent price move (after an up move, lower fair, and vice versa). i found tomatoes had a slight mean reversion in the data so this was the simplest way to use it.

## files

- `prosperity_trader_v6.py` - earlier version, mean reversion only
- `prosperity_trader_v8.py` - final version, adds a small volume signal on top
