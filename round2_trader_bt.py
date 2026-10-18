"""
IMC Prosperity 4 — Round 2 — BACKTEST MODIFIED
==============================================
This is a version of round2_trader.py modified specifically for the local backtester.
The only difference is that the 'run' method returns 3 values instead of 4,
as the current local backtester does not support the Market Access Fee (MAF) signature.
"""

import json
import math
from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple

# Constants
POSITION_LIMIT = 80
# MAF_BID is not used in this backtest version but defined for completeness
MAF_BID = 101 

class Trader:
    
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        """
        Modified signature for LOCAL BACKTESTER consistency (3 elements).
        Returns: (Orders, Conversions, TraderData)
        """
        result: Dict[str, List[Order]] = {}
        
        ts_data = {}
        if state.traderData:
            try:
                ts_data = json.loads(state.traderData)
            except:
                ts_data = {}
        
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            position = state.position.get(product, 0)
            timestamp = state.timestamp
            
            if product == "INTARIAN_PEPPER_ROOT":
                orders, ts_data = self._trade_intarian(
                    order_depth, position, timestamp, ts_data
                )
            elif product == "ASH_COATED_OSMIUM":
                orders, ts_data = self._trade_ash(
                    order_depth, position, timestamp, ts_data
                )
            else:
                orders = []
            
            result[product] = orders
        
        conversions = 0
        
        # NOTE: Returning 3 values for backtester compatibility
        return result, conversions, json.dumps(ts_data)
    
    def _get_vwap_mid(self, od: OrderDepth, levels: int = 3) -> float:
        bids = sorted(od.buy_orders.items(), key=lambda x: x[0], reverse=True)[:levels]
        asks = sorted(od.sell_orders.items(), key=lambda x: x[0])[:levels]
        
        if not bids or not asks:
            if bids: return float(bids[0][0])
            if asks: return float(asks[0][0])
            return 10000.0
            
        bid_vol = sum(v for p, v in bids)
        ask_vol = sum(abs(v) for p, v in asks)
        
        if bid_vol == 0 or ask_vol == 0:
            return (bids[0][0] + asks[0][0]) / 2.0
            
        vwap_bid = sum(p * v for p, v in bids) / bid_vol
        vwap_ask = sum(p * abs(v) for p, v in asks) / ask_vol
        
        return (vwap_bid + vwap_ask) / 2.0

    def _trade_intarian(self, od, position, timestamp, ts_data):
        product = "INTARIAN_PEPPER_ROOT"
        orders = []
        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        if best_bid is None and best_ask is None: return orders, ts_data
        mid = self._get_vwap_mid(od, levels=3)
        if "ipr_anchor" not in ts_data:
            ts_data["ipr_anchor"], ts_data["ipr_anchor_ts"] = mid, timestamp
        fair = 0.6 * (ts_data["ipr_anchor"] + (timestamp - ts_data["ipr_anchor_ts"]) * 0.001) + 0.4 * mid
        buy_room, sell_room = POSITION_LIMIT - position, POSITION_LIMIT + position
        if od.sell_orders and buy_room > 0:
            for p in sorted(od.sell_orders.keys()):
                if p < fair - 1:
                    qty = min(-od.sell_orders[p], buy_room)
                    orders.append(Order(product, p, qty)); buy_room -= qty; position += qty
                else: break
        if od.buy_orders and sell_room > 0:
            for p in sorted(od.buy_orders.keys(), reverse=True):
                if p > fair + 1:
                    qty = min(od.buy_orders[p], sell_room)
                    orders.append(Order(product, p, -qty)); sell_room -= qty; position -= qty
                else: break
        inv_skew = -(position / POSITION_LIMIT) * 4.0
        quoted_fair = fair + inv_skew
        target_bid, target_ask = int(round(quoted_fair - 2)), int(round(quoted_fair + 2))
        bid_p = min(target_bid, best_bid + 1) if best_bid else target_bid
        ask_p = max(target_ask, best_ask - 1) if best_ask else target_ask
        if bid_p >= ask_p: bid_p, ask_p = int(mid) - 1, int(mid) + 1
        if buy_room > 0: orders.append(Order(product, bid_p, buy_room))
        if sell_room > 0: orders.append(Order(product, ask_p, -sell_room))
        return orders, ts_data

    def _trade_ash(self, od, position, timestamp, ts_data):
        product = "ASH_COATED_OSMIUM"
        orders = []
        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        if best_bid is None and best_ask is None: return orders, ts_data
        mid = self._get_vwap_mid(od, levels=3)
        imb = (od.buy_orders[best_bid] - abs(od.sell_orders[best_ask])) / (od.buy_orders[best_bid] + abs(od.sell_orders[best_ask])) if best_bid and best_ask else 0
        if "ash_ema" not in ts_data: ts_data["ash_ema"] = mid
        ts_data["ash_ema"] = 0.15 * mid + 0.85 * ts_data["ash_ema"]
        true_peg = 10000
        fair = 0.5 * ts_data["ash_ema"] + 0.5 * true_peg + (0.5 * imb)
        buy_room, sell_room = POSITION_LIMIT - position, POSITION_LIMIT + position
        tbb, tba = min(fair, ts_data["ash_ema"], true_peg) - 0.5, max(fair, ts_data["ash_ema"], true_peg) + 0.5
        if od.sell_orders and buy_room > 0:
            for p in sorted(od.sell_orders.keys()):
                if p < tbb:
                    qty = min(-od.sell_orders[p], buy_room)
                    orders.append(Order(product, p, qty)); buy_room -= qty; position += qty
                else: break
        if od.buy_orders and sell_room > 0:
            for p in sorted(od.buy_orders.keys(), reverse=True):
                if p > tba:
                    qty = min(od.buy_orders[p], sell_room)
                    orders.append(Order(product, p, -qty)); sell_room -= qty; position -= qty
                else: break
        skew = -(position / POSITION_LIMIT) * 4.0
        quoted_fair = fair + skew
        h_spread = 2 if abs(position / POSITION_LIMIT) < 0.6 else 3
        tb, ta = int(round(quoted_fair - h_spread)), int(round(quoted_fair + h_spread))
        bid_p = min(tb, best_bid + 1) if best_bid else tb
        ask_p = max(ta, best_ask - 1) if best_ask else ta
        if bid_p >= ask_p: bid_p, ask_p = int(mid) - 1, int(mid) + 1
        if buy_room > 0: orders.append(Order(product, bid_p, buy_room))
        if sell_room > 0: orders.append(Order(product, ask_p, -sell_room))
        return orders, ts_data
