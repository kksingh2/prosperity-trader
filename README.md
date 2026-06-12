# prosperity 4 trader

a bot for imc prosperity 4 (april 2025), an algorithmic trading game with two products to trade.

**emeralds**: they barely move. i just quote a buy and a sell price around 10000 (their stable value).

**tomatoes**: they move more. looking at the data i noticed that when tomatoes go up by a bit they tend to come back down on the next step. so on tomatoes the bot shifts where it thinks the fair price is, based on the last move:

- if tomatoes just went up, the bot quotes a bit lower (it expects them to come back down)
- if they just went down, the bot quotes a bit higher

this is called mean reversion - the price tends to revert back to the average.

## files

- `prosperity_trader_v6.py` is the earlier version with just the mean reversion shift
- `prosperity_trader_v8.py` is the later version, adds a small extra signal that looks at whether more volume is on the buy side or the sell side
