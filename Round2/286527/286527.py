"""
IMC Prosperity 4 — Round 2 — Game Theory MAF Strategy
=====================================================
Optimized for Maximum PnL and high-fidelity execution.
Integrates the Market Access Fee (MAF) mechanism with a Game Theory bid of 101.

Key Optimizations:
1. MAF Game Theory: Bids 101 to jump the 0/1/10/50/100 tiers.
2. Robust Mid-Pricing: Uses VWAP of multiple book levels if available.
3. Liquidity Capture: Aggressively consumes extra 25% quotes whenever profitable.
"""

import json
import math
from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple

# Constants
POSITION_LIMIT = 80
MAF_BID = 101 # Game Theory optimization (Jumps common 100-tier bids)

class Trader:
    
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str, int]:
        """
        Prosperity 4 Round 2 signature:
        Returns: (Orders, Conversions, TraderData, MarketAccessFee)
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
        
        # conversions return is currently unused but required by signature
        conversions = 0
        
        return result, conversions, json.dumps(ts_data), MAF_BID
    
    def _get_vwap_mid(self, od: OrderDepth, levels: int = 3) -> float:
        """Calculates a more robust mid-price using volume weighted average of top levels."""
        bids = sorted(od.buy_orders.items(), key=lambda x: x[0], reverse=True)[:levels]
        asks = sorted(od.sell_orders.items(), key=lambda x: x[0])[:levels]
        
        if not bids or not asks:
            if bids: return float(bids[0][0])
            if asks: return float(asks[0][0])
            return 10000.0 # Default fallback
            
        bid_vol = sum(v for p, v in bids)
        ask_vol = sum(abs(v) for p, v in asks)
        
        if bid_vol == 0 or ask_vol == 0:
            return (bids[0][0] + asks[0][0]) / 2.0
            
        vwap_bid = sum(p * v for p, v in bids) / bid_vol
        vwap_ask = sum(p * abs(v) for p, v in asks) / ask_vol
        
        return (vwap_bid + vwap_ask) / 2.0

    # ═══════════════════════════════════════════════════════════════════════
    # INTARIAN_PEPPER_ROOT — DRIFT CAPTURE
    # ═══════════════════════════════════════════════════════════════════════
    
    def _trade_intarian(
        self, od: OrderDepth, position: int, timestamp: int, ts_data: dict
    ) -> Tuple[List[Order], dict]:
        
        product = "INTARIAN_PEPPER_ROOT"
        orders: List[Order] = []
        
        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        
        if best_bid is None and best_ask is None:
            return orders, ts_data
            
        mid = self._get_vwap_mid(od, levels=3)
        
        # Drift Tracking (Anchor + Time-based drift)
        if "ipr_anchor" not in ts_data:
            ts_data["ipr_anchor"] = mid
            ts_data["ipr_anchor_ts"] = timestamp
        
        anchor = ts_data["ipr_anchor"]
        anchor_ts = ts_data["ipr_anchor_ts"]
        
        # Time drift: 0.001 tick per ms
        fair = anchor + (timestamp - anchor_ts) * 0.001
        fair = 0.6 * fair + 0.4 * mid # Weighted towards current mid to avoid massive lag
        
        buy_room = POSITION_LIMIT - position
        sell_room = POSITION_LIMIT + position
        
        # Aggressive Taking (Cross spread if price is better than our fair drift)
        if od.sell_orders and buy_room > 0:
            for ask_price in sorted(od.sell_orders.keys()):
                if ask_price < fair - 1: # Require at least 1 tick edge
                    take_qty = min(-od.sell_orders[ask_price], buy_room)
                    if take_qty > 0:
                        orders.append(Order(product, ask_price, take_qty))
                        buy_room -= take_qty
                        position += take_qty
                else: break

        if od.buy_orders and sell_room > 0:
            for bid_price in sorted(od.buy_orders.keys(), reverse=True):
                if bid_price > fair + 1:
                    take_qty = min(od.buy_orders[bid_price], sell_room)
                    if take_qty > 0:
                        orders.append(Order(product, bid_price, -take_qty))
                        sell_room -= take_qty
                        position -= take_qty
                else: break

        # Quoting (Pennying and Inventory Skew)
        inv_skew = -(position / POSITION_LIMIT) * 4.0
        quoted_fair = fair + inv_skew
        
        target_bid = int(round(quoted_fair - 2))
        target_ask = int(round(quoted_fair + 2))
        
        # Priority Queue Pennying
        if best_bid is not None:
            bid_price = min(target_bid, best_bid + 1)
        else:
            bid_price = target_bid
            
        if best_ask is not None:
            ask_price = max(target_ask, best_ask - 1)
        else:
            ask_price = target_ask
            
        # Safety Cross
        if bid_price >= ask_price:
            bid_price = int(mid) - 1
            ask_price = int(mid) + 1
            
        if buy_room > 0:
            orders.append(Order(product, bid_price, buy_room))
        if sell_room > 0:
            orders.append(Order(product, ask_price, -sell_room))
            
        return orders, ts_data
    
    # ═══════════════════════════════════════════════════════════════════════
    # ASH_COATED_OSMIUM — MEAN-REVERSION + DYNAMIC PENNYING
    # ═══════════════════════════════════════════════════════════════════════
    
    def _trade_ash(
        self, od: OrderDepth, position: int, timestamp: int, ts_data: dict
    ) -> Tuple[List[Order], dict]:
        
        product = "ASH_COATED_OSMIUM"
        orders: List[Order] = []
        
        best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
        
        if best_bid is None and best_ask is None:
            return orders, ts_data
            
        mid = self._get_vwap_mid(od, levels=3)
        
        # Order Imbalance Component
        if best_bid is not None and best_ask is not None:
            bv = od.buy_orders[best_bid]
            av = abs(od.sell_orders[best_ask])
            imb = (bv - av) / (bv + av) if (bv + av) > 0 else 0
        else:
            imb = 0
            
        # EMA Mid Calculation
        if "ash_ema" not in ts_data:
            ts_data["ash_ema"] = mid
            
        alpha = 0.15
        ema = ts_data["ash_ema"]
        ema = alpha * mid + (1 - alpha) * ema
        ts_data["ash_ema"] = ema
        
        # Mean Reversion Target (Fixed peg 10000 + structural shifting)
        true_peg = 10000
        fair = 0.5 * ema + 0.5 * true_peg + (0.5 * imb)
        
        buy_room = POSITION_LIMIT - position
        sell_room = POSITION_LIMIT + position
        
        # Aggressive Takes (Utilizing extra depth)
        # We take if price is significantly better than both EMA and Peg
        take_bound_bid = min(fair, ema, true_peg) - 0.5
        take_bound_ask = max(fair, ema, true_peg) + 0.5
        
        if od.sell_orders and buy_room > 0:
            for p in sorted(od.sell_orders.keys()):
                if p < take_bound_bid:
                    qty = min(-od.sell_orders[p], buy_room)
                    orders.append(Order(product, p, qty))
                    buy_room -= qty
                    position += qty
                else: break

        if od.buy_orders and sell_room > 0:
            for p in sorted(od.buy_orders.keys(), reverse=True):
                if p > take_bound_ask:
                    qty = min(od.buy_orders[p], sell_room)
                    orders.append(Order(product, p, -qty))
                    sell_room -= qty
                    position -= qty
                else: break

        # Skewed Quoting
        inv_ratio = position / POSITION_LIMIT
        skew = -inv_ratio * 4.0
        quoted_fair = fair + skew
        
        # Dynamic half-spread based on inventory pressure
        h_spread = 2 if abs(inv_ratio) < 0.6 else 3
        
        target_bid = int(round(quoted_fair - h_spread))
        target_ask = int(round(quoted_fair + h_spread))
        
        # Pennying Edge
        if best_bid is not None:
            bid_price = min(target_bid, best_bid + 1)
        else:
            bid_price = target_bid
            
        if best_ask is not None:
            ask_price = max(target_ask, best_ask - 1)
        else:
            ask_price = target_ask
            
        if bid_price >= ask_price:
            bid_price = int(mid) - 1
            ask_price = int(mid) + 1
            
        if buy_room > 0:
            orders.append(Order(product, bid_price, buy_room))
        if sell_room > 0:
            orders.append(Order(product, ask_price, -sell_room))
            
        return orders, ts_data