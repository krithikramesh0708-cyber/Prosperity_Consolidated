"""
IMC Prosperity 4 — Round 2 — HYBRID ALPHA STRATEGY
==================================================
Combines the best-of-breed algorithms for ASH and INTARIAN.

1. ASH_COATED_OSMIUM: Uses VWAP Mean-Reversion (beats Round 1 baseline).
2. INTARIAN_PEPPER_ROOT: Uses Eigen-weighted drift capture (from Round 1 251726).
3. MAF: Bids 101 via class attribute for extra quote advantage.
"""

import json
import math
from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple

# Constants
POSITION_LIMIT = 80

class Trader:
    # Set Market Access Fee as class variable for platform compatibility
    market_access_fee = 101 
    
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        """
        Prosperity 4 standard signature.
        Returns: (Orders, Conversions, TraderData)
        """
        result: Dict[str, List[Order]] = {}
        
        # Restore state
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
        if bid_vol == 0 or ask_vol == 0: return (bids[0][0] + asks[0][0]) / 2.0
        vwap_bid = sum(p * v for p, v in bids) / bid_vol
        vwap_ask = sum(p * abs(v) for p, v in asks) / ask_vol
        return (vwap_bid + vwap_ask) / 2.0

    # ═══════════════════════════════════════════════════════════════════════
    # INTARIAN_PEPPER_ROOT — EIGEN DRIFT (HYBRIDIZED)
    # ═══════════════════════════════════════════════════════════════════════
    
    def _trade_intarian(self, od: OrderDepth, position: int, timestamp: int, ts_data: dict):
        product = "INTARIAN_PEPPER_ROOT"
        orders: List[Order] = []
        
        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        if best_bid is None and best_ask is None: return orders, ts_data
        
        mid = (best_bid + best_ask) / 2.0 if (best_bid and best_ask) else (best_bid or best_ask)
        
        if "ipr_anchor" not in ts_data:
            ts_data["ipr_anchor"], ts_data["ipr_anchor_ts"] = mid, timestamp
        
        fair = ts_data["ipr_anchor"] + (timestamp - ts_data["ipr_anchor_ts"]) * 0.001
        fair = 0.7 * fair + 0.3 * mid
        
        # Eigen Imbalance Calculation
        bids = sorted(od.buy_orders.items(), key=lambda x: x[0], reverse=True)
        asks = sorted(od.sell_orders.items(), key=lambda x: x[0])
        
        b1 = bids[0][1] if len(bids) > 0 else 0
        a1 = abs(asks[0][1]) if len(asks) > 0 else 0
        b2 = bids[1][1] if len(bids) > 1 else 0
        a2 = abs(asks[1][1]) if len(asks) > 1 else 0
        b3 = bids[2][1] if len(bids) > 2 else 0
        a3 = abs(asks[2][1]) if len(asks) > 2 else 0
        
        eigen_buy = b1 + 0.45 * b2 + 0.2 * b3
        eigen_sell = a1 + 0.45 * a2 + 0.2 * a3
        imb = (eigen_buy - eigen_sell) / (eigen_buy + eigen_sell) if (eigen_buy + eigen_sell) > 0 else 0
        fair += 0.4 * imb
        
        buy_room, sell_room = POSITION_LIMIT - position, POSITION_LIMIT + position
        
        if buy_room > 0:
            if od.sell_orders:
                remaining = buy_room
                for ask_price in sorted(od.sell_orders.keys()):
                    if ask_price < fair - 0.5: # Aggressive Take
                        take_qty = min(-od.sell_orders[ask_price], remaining)
                        orders.append(Order(product, ask_price, take_qty))
                        remaining -= take_qty
                # Penny best ask for the rest
                if remaining > 0:
                    bid_p = best_ask - 1 if best_ask else int(round(fair))
                    orders.append(Order(product, bid_p, remaining))
        
        if sell_room > 0:
            if od.buy_orders:
                remaining = sell_room
                for bid_price in sorted(od.buy_orders.keys(), reverse=True):
                    if bid_price > fair + 0.5:
                        take_qty = min(od.buy_orders[bid_price], remaining)
                        orders.append(Order(product, bid_price, -take_qty))
                        remaining -= take_qty
                if remaining > 0:
                    ask_p = best_bid + 1 if best_bid else int(round(fair))
                    orders.append(Order(product, ask_p, -remaining))
                    
        return orders, ts_data

    # ═══════════════════════════════════════════════════════════════════════
    # ASH_COATED_OSMIUM — VWAP REVERSION (BEST PERFORMANCE)
    # ═══════════════════════════════════════════════════════════════════════
    
    def _trade_ash(self, od, position, timestamp, ts_data):
        product = "ASH_COATED_OSMIUM"
        orders: List[Order] = []
        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        if best_bid is None and best_ask is None: return orders, ts_data
        
        mid = self._get_vwap_mid(od, levels=3)
        
        if "ash_ema" not in ts_data: ts_data["ash_ema"] = mid
        ts_data["ash_ema"] = 0.15 * mid + 0.85 * ts_data["ash_ema"]
        
        fair = 0.5 * ts_data["ash_ema"] + 0.5 * 10000
        buy_room, sell_room = POSITION_LIMIT - position, POSITION_LIMIT + position
        
        # Take logic
        if od.sell_orders and buy_room > 0:
            for p in sorted(od.sell_orders.keys()):
                if p < fair - 0.5:
                    qty = min(-od.sell_orders[p], buy_room)
                    orders.append(Order(product, p, qty)); buy_room -= qty; position += qty
                else: break

        if od.buy_orders and sell_room > 0:
            for p in sorted(od.buy_orders.keys(), reverse=True):
                if p > fair + 0.5:
                    qty = min(od.buy_orders[p], sell_room)
                    orders.append(Order(product, p, -qty)); sell_room -= qty; position -= qty
                else: break

        # Pennying
        skew = -(position / POSITION_LIMIT) * 4.0
        quoted_fair = fair + skew
        h_spread = 2 if abs(position / POSITION_LIMIT) < 0.6 else 3
        
        bid_p = min(int(round(quoted_fair - h_spread)), best_bid + 1) if best_bid else int(round(quoted_fair - h_spread))
        ask_p = max(int(round(quoted_fair + h_spread)), best_ask - 1) if best_ask else int(round(quoted_fair + h_spread))
        
        if bid_p >= ask_p: bid_p, ask_p = int(mid) - 1, int(mid) + 1
        if buy_room > 0: orders.append(Order(product, bid_p, buy_room))
        if sell_room > 0: orders.append(Order(product, ask_p, -sell_room))
        return orders, ts_data
