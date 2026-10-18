import json
import math
from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple

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

            if p in books:
                hist_key = f'{p}_h'
                if hist_key not in d: d[hist_key] = []
                d[hist_key].append(books[p]['mid'])
                
                win = 75 if p in STRIKES else 50
                if len(d[hist_key]) > win: d[hist_key].pop(0)
                
                ema = sum(d[hist_key])/len(d[hist_key])
                
                if p in STRIKES:
                    for ap, av in books[p]['asks']:
                        diff = ema - ap
                        if diff >= 6.0 and pos < limit:
                            # If edge is 6.0, we want to buy a small chunk
                            # If edge is 10.0, we want to buy a huge chunk
                            # Max position scaling based on diff:
                            max_pos = min(limit, limit * (diff - 5.0) / 4.0)
                            if pos < max_pos:
                                q = min(-av, int(max_pos) - pos)
                                orders.append(Order(p, ap, q))
                                pos += q
                    for bp, bv in books[p]['bids']:
                        diff = bp - ema
                        if diff >= 6.0 and pos > -limit:
                            max_pos = min(limit, limit * (diff - 5.0) / 4.0)
                            if pos > -max_pos:
                                q = min(bv, int(max_pos) + pos)
                                orders.append(Order(p, bp, -q))
                                pos -= q
                else:
                    norm_pos = pos / limit
                    skew = -6.0 * (norm_pos)**3 
                    f = ema + skew
                    b, s = int(math.floor(f - 1)), int(math.ceil(f + 1))
                    b, s = min(b, books[p]['bid'] + 1), max(s, books[p]['ask'] - 1)
                    if limit - pos > 0: orders.append(Order(p, b, limit - pos))
                    if limit + pos > 0: orders.append(Order(p, s, -(limit + pos)))

            result[p] = orders
        return result, 0, json.dumps(d)
