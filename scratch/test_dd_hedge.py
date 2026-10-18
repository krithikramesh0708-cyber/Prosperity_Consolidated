import subprocess
import os
import re

template = """import json
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

        total_delta = state.position.get('VELVETFRUIT_EXTRACT', 0)
        for p in STRIKES:
            total_delta += state.position.get(p, 0) * 0.5  # simple approx static delta

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
                        if ap <= ema - 6.0 and pos < limit:
                            q = min(-av, limit - pos)
                            orders.append(Order(p, ap, q))
                            pos += q
                    for bp, bv in books[p]['bids']:
                        if bp >= ema + 6.0 and pos > -limit:
                            q = min(bv, limit + pos)
                            orders.append(Order(p, bp, -q))
                            pos -= q
                elif p == 'VELVETFRUIT_EXTRACT':
                    norm_delta = max(-1.0, min(1.0, total_delta / limit))
                    skew = -6.0 * (norm_delta)**3 
                    f = ema + skew
                    b, s = int(math.floor(f - 1)), int(math.ceil(f + 1))
                    b, s = min(b, books[p]['bid'] + 1), max(s, books[p]['ask'] - 1)
                    if limit - pos > 0: orders.append(Order(p, b, limit - pos))
                    if limit + pos > 0: orders.append(Order(p, s, -(limit + pos)))
                elif p == 'HYDROGEL_PACK':
                    norm_pos = pos / limit
                    skew = -6.0 * (norm_pos)**3 
                    f = ema + skew
                    b, s = int(math.floor(f - 1)), int(math.ceil(f + 1))
                    b, s = min(b, books[p]['bid'] + 1), max(s, books[p]['ask'] - 1)
                    if limit - pos > 0: orders.append(Order(p, b, limit - pos))
                    if limit + pos > 0: orders.append(Order(p, s, -(limit + pos)))

            result[p] = orders
        return result, 0, json.dumps(d)
"""

with open("trader_dd_hedge.py", "w") as f:
    f.write(template)

res = subprocess.run("python3 -m prosperity4bt trader_dd_hedge.py 3", env=os.environ, shell=True, text=True, capture_output=True)
match = re.search(r"final_pnl:\s*(-?\d+(?:,\d+)*)[\s\S]*?max_drawdown_abs:\s*(-?\d+(?:,\d+)*)", res.stdout)
if match:
    pnl = int(match.group(1).replace(",", ""))
    dd = int(match.group(2).replace(",", ""))
    print(f"PnL: {pnl}, Drawdown: {dd}")
else:
    print(res.stdout)
