import subprocess
import itertools
import os
import re
from concurrent.futures import ProcessPoolExecutor

template = """import json
import math
from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple

class Trader:
    def __init__(self):
        self.pebbles_sum = 50000
        self.snack_sum = 20025
        self.products_limit = 10
        self.pebbles = ["PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL"]
        self.ema_window = 20

    def get_mid_price(self, order_depth):
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return (best_bid + best_ask) / 2

    def run(self, state: TradingState):
        result = {}
        trader_data = {}
        if state.traderData:
            trader_data = json.loads(state.traderData)

        mids = {}
        for product in state.order_depths:
            mid = self.get_mid_price(state.order_depths[product])
            if mid is not None:
                mids[product] = mid
                prev_ema = trader_data.get(f"ema_{product}", mid)
                new_ema = prev_ema + (mid - prev_ema) * (2 / (self.ema_window + 1))
                trader_data[f"ema_{product}"] = new_ema

        fairs = {}
        pebbles_present = [p for p in self.pebbles if p in mids]
        if len(pebbles_present) == 5:
            total_mid = sum(mids[p] for p in self.pebbles)
            dev = total_mid - self.pebbles_sum
            for p in self.pebbles:
                fairs[p] = mids[p] - (dev / 5.0)
        
        # Snackpack Arb
        if "SNACKPACK_CHOCOLATE" in mids and "SNACKPACK_VANILLA" in mids:
            s = mids["SNACKPACK_CHOCOLATE"] + mids["SNACKPACK_VANILLA"]
            dev = s - self.snack_sum
            fairs["SNACKPACK_CHOCOLATE"] = mids["SNACKPACK_CHOCOLATE"] - (dev / 2.0)
            fairs["SNACKPACK_VANILLA"] = mids["SNACKPACK_VANILLA"] - (dev / 2.0)

        for product in state.order_depths:
            if product not in fairs:
                fairs[product] = mids.get(product, trader_data.get(f"ema_{product}"))

        for product, fair_val in fairs.items():
            if fair_val is None: continue
            order_depth = state.order_depths[product]
            position = state.position.get(product, 0)
            orders: List[Order] = []
            
            # PARAMS
            take_edge = {TAKE_EDGE}
            mm_spread = {MM_SPREAD}
            skew_mult = {SKEW_MULT}
            
            # Market Taking
            buy_orders = sorted(order_depth.sell_orders.items())
            for ask_price, ask_qty in buy_orders:
                if ask_price < fair_val - take_edge and position < self.products_limit:
                    buy_qty = min(-ask_qty, self.products_limit - position)
                    orders.append(Order(product, ask_price, buy_qty))
                    position += buy_qty
            
            sell_orders = sorted(order_depth.buy_orders.items(), reverse=True)
            for bid_price, bid_qty in sell_orders:
                if bid_price > fair_val + take_edge and position > -self.products_limit:
                    sell_qty = max(-bid_qty, -self.products_limit - position)
                    orders.append(Order(product, bid_price, sell_qty))
                    position += sell_qty

            # Market Making
            skew = position * skew_mult
            bid_price = int(fair_val - mm_spread - skew)
            ask_price = int(fair_val + mm_spread - skew)
            
            if bid_price >= ask_price:
                bid_price = int(fair_val - 1)
                ask_price = int(fair_val + 1)

            if position < self.products_limit:
                orders.append(Order(product, bid_price, self.products_limit - position))
            if position > -self.position_limit if hasattr(self, 'position_limit') else 10: # wait, limit is 10
                pass
            if position > -10:
                orders.append(Order(product, ask_price, -10 - position))
            
            result[product] = orders

        return result, 0, json.dumps(trader_data)
"""

def evaluate(params):
    take_edge, mm_spread, skew_mult = params
    code = template.replace("{TAKE_EDGE}", str(take_edge))\
                   .replace("{MM_SPREAD}", str(mm_spread))\
                   .replace("{SKEW_MULT}", str(skew_mult))
    
    filename = f"trader_opt_{int(take_edge*10)}_{int(mm_spread*10)}_{int(skew_mult*10)}.py"
    with open(filename, "w") as f:
        f.write(code)
    
    # Run on Day 2 for speed
    cmd = f"python3 -m prosperity4bt {filename} 5-2 --data Final_Round --no-vis --no-progress"
    try:
        res = subprocess.run(cmd, env=os.environ, shell=True, text=True, capture_output=True, timeout=120)
        # Search for Total profit: XXX
        match = re.search(r"Total profit: (-?\d+(?:,\d+)*)", res.stdout)
        if match:
            pnl = int(match.group(1).replace(",", ""))
            return params, pnl
        else:
            # print(f"Failed {filename}. STDOUT: {res.stdout[:100]}")
            pass
    except Exception as e:
        pass
    finally:
        if os.path.exists(filename): os.remove(filename)
    return params, -999999

if __name__ == "__main__":
    take_edge_list = [5.0, 7.0, 9.0]
    mm_spread_list = [4.0, 6.0, 8.0]
    skew_mult_list = [1.0, 1.5, 2.0]
    
    grid = list(itertools.product(take_edge_list, mm_spread_list, skew_mult_list))
    print(f"Total combinations: {len(grid)}")
    
    with ProcessPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(evaluate, grid))
        
    for params, pnl in sorted(results, key=lambda x: x[1], reverse=True):
        print(f"Params {params} -> PnL: {pnl}")
