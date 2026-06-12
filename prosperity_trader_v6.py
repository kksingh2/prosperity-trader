# prosperity 4 v6 - market making with a mean reversion shift on tomatoes

from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import json

class Trader:

    POSITION_LIMITS = {
        "EMERALDS": 50,
        "TOMATOES": 50,
    }

    EMERALD_FAIR_VALUE = 10000

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}

        # Load previous state
        prev_state = {}
        if state.traderData:
            try:
                prev_state = json.loads(state.traderData)
            except:
                prev_state = {}

        if "EMERALDS" in state.order_depths:
            result["EMERALDS"] = self.trade_emeralds(state)

        tom_mid = None
        if "TOMATOES" in state.order_depths:
            result["TOMATOES"], tom_mid = self.trade_tomatoes(state, prev_state)

        # Save state for next timestep
        new_state = {}
        if tom_mid is not None:
            new_state["tom_mid"] = tom_mid

        conversions = 0
        trader_data = json.dumps(new_state)
        return result, conversions, trader_data

    # HELPER: Get sorted order book
    def get_sorted_book(self, order_depth: OrderDepth):
        sells = sorted(order_depth.sell_orders.items())
        buys = sorted(order_depth.buy_orders.items(), reverse=True)
        return sells, buys

    # HELPER: Calculate inventory skew
    def inventory_skew(self, position: int, pos_limit: int) -> float:
        return position / pos_limit if pos_limit > 0 else 0.0

    # EMERALDS - EXACT V2 LOGIC (proven 1022 XIRECs, don't change)
    def trade_emeralds(self, state: TradingState) -> List[Order]:
        orders: List[Order] = []
        product = "EMERALDS"
        fair_value = self.EMERALD_FAIR_VALUE
        position = state.position.get(product, 0)
        pos_limit = self.POSITION_LIMITS[product]

        order_depth = state.order_depths[product]
        sells, buys = self.get_sorted_book(order_depth)

        max_buy = pos_limit - position
        max_sell = pos_limit + position

        # TAKE all profitable orders
        for ask_price, ask_vol in sells:
            ask_vol = abs(ask_vol)
            if ask_price < fair_value and max_buy > 0:
                qty = min(ask_vol, max_buy)
                orders.append(Order(product, ask_price, qty))
                max_buy -= qty
            elif ask_price == fair_value and position < 0 and max_buy > 0:
                qty = min(ask_vol, abs(position), max_buy)
                orders.append(Order(product, ask_price, qty))
                max_buy -= qty

        for bid_price, bid_vol in buys:
            bid_vol = abs(bid_vol)
            if bid_price > fair_value and max_sell > 0:
                qty = min(bid_vol, max_sell)
                orders.append(Order(product, bid_price, -qty))
                max_sell -= qty
            elif bid_price == fair_value and position > 0 and max_sell > 0:
                qty = min(bid_vol, position, max_sell)
                orders.append(Order(product, bid_price, -qty))
                max_sell -= qty

        # MAKE passive quotes with inventory skew
        skew = self.inventory_skew(position, pos_limit)
        skew_ticks = round(skew * 2)

        our_bid = fair_value - 7 - skew_ticks
        our_ask = fair_value + 7 - skew_ticks

        our_bid = min(our_bid, fair_value - 1)
        our_ask = max(our_ask, fair_value + 1)

        if max_buy > 0:
            orders.append(Order(product, our_bid, max_buy))
        if max_sell > 0:
            orders.append(Order(product, our_ask, -max_sell))

        return orders

    # TOMATOES - V2 logic + mean reversion adjusted fair value
    def trade_tomatoes(self, state: TradingState, prev_state: dict):
        orders: List[Order] = []
        product = "TOMATOES"
        position = state.position.get(product, 0)
        pos_limit = self.POSITION_LIMITS[product]

        order_depth = state.order_depths[product]
        sells, buys = self.get_sorted_book(order_depth)

        if not buys or not sells:
            return orders, None

        max_buy = pos_limit - position
        max_sell = pos_limit + position

        # Calculate raw fair value (VWAP mid, same as V2)
        total_bid_value = 0
        total_bid_vol = 0
        for price, vol in buys:
            v = abs(vol)
            total_bid_value += price * v
            total_bid_vol += v

        total_ask_value = 0
        total_ask_vol = 0
        for price, vol in sells:
            v = abs(vol)
            total_ask_value += price * v
            total_ask_vol += v

        if total_bid_vol > 0 and total_ask_vol > 0:
            vwap_bid = total_bid_value / total_bid_vol
            vwap_ask = total_ask_value / total_ask_vol
            raw_fair = (vwap_bid + vwap_ask) / 2
        else:
            bid_wall = min(price for price, _ in buys)
            ask_wall = max(price for price, _ in sells)
            raw_fair = (bid_wall + ask_wall) / 2

        # ---- MEAN REVERSION ADJUSTMENT ----
        # Autocorrelation is -0.44. If price just moved up, expect it to come back.
        # adjusted_fair = raw_fair - 0.4 * last_return
        # This makes us quote LOWER after up-moves (favoring sells)
        # and HIGHER after down-moves (favoring buys).
        prev_mid = prev_state.get("tom_mid", raw_fair)
        last_return = raw_fair - prev_mid
        
        fair_value = raw_fair - 0.4 * last_return

        best_bid = buys[0][0]
        best_ask = sells[0][0]

        # TAKE profitable orders (V2 logic, but using adjusted fair)
        for ask_price, ask_vol in sells:
            ask_vol = abs(ask_vol)
            if ask_price < fair_value - 1 and max_buy > 0:
                qty = min(ask_vol, max_buy)
                orders.append(Order(product, ask_price, qty))
                max_buy -= qty
            elif ask_price <= fair_value and position < 0 and max_buy > 0:
                qty = min(ask_vol, abs(position), max_buy)
                orders.append(Order(product, ask_price, qty))
                max_buy -= qty

        for bid_price, bid_vol in buys:
            bid_vol = abs(bid_vol)
            if bid_price > fair_value + 1 and max_sell > 0:
                qty = min(bid_vol, max_sell)
                orders.append(Order(product, bid_price, -qty))
                max_sell -= qty
            elif bid_price >= fair_value and position > 0 and max_sell > 0:
                qty = min(bid_vol, position, max_sell)
                orders.append(Order(product, bid_price, -qty))
                max_sell -= qty

        # MAKE passive quotes with inventory skew (V2 logic)
        skew = self.inventory_skew(position, pos_limit)
        skew_ticks = round(skew * 3)

        our_bid = int(min(best_bid + 1 - skew_ticks, fair_value - 1))
        our_ask = int(max(best_ask - 1 - skew_ticks, fair_value + 1))

        if our_bid >= our_ask:
            mid_int = int(fair_value)
            our_bid = mid_int - 1
            our_ask = mid_int + 1

        if max_buy > 0:
            orders.append(Order(product, our_bid, max_buy))
        if max_sell > 0:
            orders.append(Order(product, our_ask, -max_sell))

        # Return orders and current mid for state persistence
        return orders, raw_fair
