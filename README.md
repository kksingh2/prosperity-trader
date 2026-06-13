# Prosperity 4 Trader

My bot for IMC Prosperity 4 (April 2025), an algorithmic trading game with two products to trade: Emeralds, which barely move, and Tomatoes, which are noisier.

## How the bot works

For both products the bot is a market maker: it offers to buy a little below the fair price and sell a little above, and earns the small gap each time someone trades with it.

**Emeralds** are stable, so the bot just quotes around their fixed fair value of 10,000.

**Tomatoes** get one extra idea. Looking at the data, I noticed that when Tomatoes jump up they tend to drift back down on the next step, and vice versa. This is called mean reversion. So on Tomatoes the bot shifts where it thinks the fair price is, based on the last move:

- If Tomatoes just went up, it quotes a bit lower, expecting a pull-back.
- If they just went down, it quotes a bit higher.

## Files

- `prosperity_trader_v6.py` is the earlier version, with just the mean-reversion shift.
- `prosperity_trader_v8.py` is the final version. It adds a small extra signal that looks at whether more buying or more selling volume is sitting in the order book.

## Run it

The bot plugs into IMC's Prosperity engine, which provides the `datamodel` module and feeds it market updates.
