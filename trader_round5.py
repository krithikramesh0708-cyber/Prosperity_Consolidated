import json
import math
from typing import Dict, List
from datamodel import Order, TradingState, Symbol

class Trader:
    def __init__(self):
        self.pebbles_sum = 50000
        self.snack_sum = 20025
        self.products_limit = 10
        self.pebbles = ["PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL"]
        self.mm_winners = [
            "UV_VISOR_AMBER", "UV_VISOR_YELLOW", "UV_VISOR_ORANGE",
            "OXYGEN_SHAKE_GARLIC", "OXYGEN_SHAKE_EVENING_BREATH",
            "PANEL_1X2", "SLEEP_POD_LAMB_WOOL", "MICROCHIP_SQUARE"
        ]

    def get_mid_price(self, order_depth):
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return (best_bid + best_ask) / 2

    def run(self, state: TradingState):
        result = {}
        mids = {}
        for product in state.order_depths:
            mid = self.get_mid_price(state.order_depths[product])
            if mid is not None:
                mids[product] = mid

        fairs = {}
        # 1. Pebbles Arb
        pebbles_present = [p for p in self.pebbles if p in mids]
        if len(pebbles_present) == 5:
            total_mid = sum(mids[p] for p in self.pebbles)
            dev = total_mid - self.pebbles_sum
            for p in self.pebbles:
                fairs[p] = mids[p] - (dev / 5.0)
        
        # 2. Snackpack Arb
        if "SNACKPACK_CHOCOLATE" in mids and "SNACKPACK_VANILLA" in mids:
            s = mids["SNACKPACK_CHOCOLATE"] + mids["SNACKPACK_VANILLA"]
            dev = s - self.snack_sum
            fairs["SNACKPACK_CHOCOLATE"] = mids["SNACKPACK_CHOCOLATE"] - (dev / 2.0)
            fairs["SNACKPACK_VANILLA"] = mids["SNACKPACK_VANILLA"] - (dev / 2.0)

        # 3. Execution
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            position = state.position.get(product, 0)
            orders: List[Order] = []
            
            fair_val = fairs.get(product)
            
            # Arb Execution (Dominant MM + Taker)
            if fair_val is not None and (product in self.pebbles or "SNACKPACK" in product):
                best_bid = max(order_depth.buy_orders.keys())
                best_ask = min(order_depth.sell_orders.keys())
                
                # Taker part
                take_edge = 5.0
                for ask_price, ask_qty in sorted(order_depth.sell_orders.items()):
                    if ask_price < fair_val - take_edge and position < self.products_limit:
                        q = min(-ask_qty, self.products_limit - position)
                        orders.append(Order(product, ask_price, q))
                        position += q
                for bid_price, bid_qty in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid_price > fair_val + take_edge and position > -self.products_limit:
                        q = max(-bid_qty, -self.products_limit - position)
                        orders.append(Order(product, bid_price, q))
                        position -= q # wait, Order quantity is negative for sell

                # Dominant Maker part
                skew = position * 1.0
                bid_price = min(int(fair_val - 1 - skew), best_bid + 1)
                ask_price = max(int(fair_val + 1 - skew), best_ask - 1)
                
                if position < self.products_limit:
                    orders.append(Order(product, bid_price, self.products_limit - position))
                if position > -self.products_limit:
                    orders.append(Order(product, ask_price, -self.products_limit - position))
            
            # Winner MM
            elif product in self.mm_winners:
                fair_val = mids.get(product)
                if fair_val is not None:
                    mm_spread = 6.0
                    skew = position * 1.0
                    bid_price = int(fair_val - mm_spread - skew)
                    ask_price = int(fair_val + mm_spread - skew)
                    
                    if position < self.products_limit:
                        orders.append(Order(product, bid_price, self.products_limit - position))
                    if position > -self.products_limit:
                        orders.append(Order(product, ask_price, -self.products_limit - position))
            
            if orders:
                result[product] = orders

        return result, 0, ""
