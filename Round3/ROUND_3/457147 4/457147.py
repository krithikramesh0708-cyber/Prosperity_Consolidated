import json
import math
from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple

# =============================================================================
# PROSPERITY ROUND 3 — THE ZENITH (v27)
# =============================================================================
# STRATEGY: STABLE FRUIT MM + HISTORICAL VOUCHER SNIPER
# 1. Fruit MM: v26 logic for VFE/Hydrogel (The "Green Base").
# 2. Voucher Sniper: Taker-only trades when price deviates 5.0 ticks from its 50-tick EMA.
# 3. No Smile Fitting: Eliminates BS-model noise in favor of pure mean reversion.
# =============================================================================

LIMITS = {'VELVETFRUIT_EXTRACT': 200, 'HYDROGEL_PACK': 200}
STRIKES = ['VEV_4000', 'VEV_4500', 'VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_5500', 'VEV_6000', 'VEV_6500']
for v in STRIKES: LIMITS[v] = 300

class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        d = json.loads(state.traderData) if state.traderData else {}
        result = {}
        
        books = {}
        for p, od in state.order_depths.items():
            b, a = sorted(od.buy_orders.items(), reverse=True), sorted(od.sell_orders.items())
            if b and a: books[p] = {'bid': b[0][0], 'ask': a[0][0], 'mid': (b[0][0]+a[0][0])/2.0, 'bids': b, 'asks': a}

        for p in state.order_depths:
            pos = state.position.get(p, 0)
            limit = LIMITS.get(p, 300)
            orders = []

            if p in ['VELVETFRUIT_EXTRACT', 'HYDROGEL_PACK']:
                if p in books:
                    hist_key = f'{p}_h'
                    if hist_key not in d: d[hist_key] = []
                    d[hist_key].append(books[p]['mid'])
                    if len(d[hist_key]) > 50: d[hist_key].pop(0)
                    ema = sum(d[hist_key])/len(d[hist_key])
                    skew = -6.0 * (pos / limit)**3
                    f = ema + skew
                    b, s = int(math.floor(f - 1)), int(math.ceil(f + 1))
                    b, s = min(b, books[p]['bid'] + 1), max(s, books[p]['ask'] - 1)
                    orders.append(Order(p, b, limit - pos))
                    orders.append(Order(p, s, -(limit + pos)))

            elif p in STRIKES:
                if p in books:
                    hist_key = f'{p}_h'
                    if hist_key not in d: d[hist_key] = []
                    d[hist_key].append(books[p]['mid'])
                    if len(d[hist_key]) > 50: d[hist_key].pop(0)
                    ema = sum(d[hist_key])/len(d[hist_key])
                    
                    # Sniper Taker
                    for ap, av in books[p]['asks']:
                        if ap < ema - 5.0 and pos < limit:
                            q = min(-av, limit - pos); orders.append(Order(p, ap, q)); pos += q
                    for bp, bv in books[p]['bids']:
                        if bp > ema + 5.0 and pos > -limit:
                            q = min(bv, limit + pos); orders.append(Order(p, bp, -q)); pos -= q

            result[p] = orders
        return result, 0, json.dumps(d)