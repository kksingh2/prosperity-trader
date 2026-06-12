# prosperity 4 v8 - market making with a combined signal on tomatoes

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

        prev = {}
        if state.traderData:
            try:
                prev = json.loads(state.traderData)
            except:
                prev = {}

        if "EMERALDS" in state.order_depths:
            result["EMERALDS"] = self.trade_emeralds(state)

        new_state = {}
        if "TOMATOES" in state.order_depths:
            result["TOMATOES"], new_state = self.trade_tomatoes(state, prev)

        conversions = 0
        trader_data = json.dumps(new_state)
        return result, conversions, trader_data

    def get_sorted_book(self, order_depth: OrderDepth):
        sells = sorted(order_depth.sell_orders.items())
        buys = sorted(order_depth.buy_orders.items(), reverse=True)
        return sells, buys

    def inventory_skew(self, position: int, pos_limit: int) -> float:
        return position / pos_limit if pos_limit > 0 else 0.0

    # EMERALDS - EXACT V2 (proven, untouched)
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

    # TOMATOES - V2 + combined volume asymmetry & mean reversion signal
    def trade_tomatoes(self, state: TradingState, prev: dict):
        orders: List[Order] = []
        product = "TOMATOES"
        position = state.position.get(product, 0)
        pos_limit = self.POSITION_LIMITS[product]

        order_depth = state.order_depths[product]
        sells, buys = self.get_sorted_book(order_depth)

        if not buys or not sells:
            return orders, prev

        max_buy = pos_limit - position
        max_sell = pos_limit + position

        # VWAP fair value (same as V2)
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

        # ---- COMBINED SIGNAL ----
        # Signal 1: Mean reversion (negative last return → expect up)
        prev_mid = prev.get("tom_mid", raw_fair)
        last_return = raw_fair - prev_mid

        # Signal 2: Volume asymmetry (more bid vol → expect up)
        vol_asymmetry = (total_bid_vol - total_ask_vol)

        # Combined: optimized weights from backtest
        # signal > 0 → expect price UP → fair should be higher
        signal = -0.2 * last_return + 0.18 * vol_asymmetry

        # Adjust fair value - conservative multiplier
        fair_value = raw_fair + 0.5 * signal

        best_bid = buys[0][0]
        best_ask = sells[0][0]

        # TAKE (V2 logic with adjusted fair)
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

        # MAKE (V2 logic with inventory skew)
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

        new_state = {"tom_mid": raw_fair}
        return orders, new_state
