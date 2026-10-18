import subprocess
import itertools
import os
import re
from concurrent.futures import ProcessPoolExecutor

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
            if b and a: books[p] = {'bid': b[0][0], 'ask': a[0][0], 'mid': (b[0][0]+a[0][0])/2.0, 'bids': b, 'asks': a, 'bv': b[0][1], 'av': abs(a[0][1])}

        imb = 0.0
        p = 'VELVETFRUIT_EXTRACT'
        if p in books:
            bv = books[p]['bv']
            av = books[p]['av']
            imb = (bv - av) / (bv + av)

        for p in state.order_depths:
            pos = state.position.get(p, 0)
            limit = LIMITS.get(p, 300)
            orders = []

            if p in STRIKES:
                if p not in books: continue
                # FRONTRUN Logic
                if imb > {IMB_THRESH}:
                    # Going UP! Sweep Asks!
                    for ap, av in books[p]['asks']:
                        q = min(-av, limit - pos)
                        if q > 0: orders.append(Order(p, ap, q)); pos += q
                elif imb < -{IMB_THRESH}:
                    # Going DOWN! Sweep Bids!
                    for bp, bv in books[p]['bids']:
                        q = min(bv, limit + pos)
                        if q > 0: orders.append(Order(p, bp, -q)); pos -= q
                
                # Baseline MM to flush inventory if we aren't sweeping
                if not (imb > {IMB_THRESH} or imb < -{IMB_THRESH}):
                    hist_key = f'{p}_h'
                    if hist_key not in d: d[hist_key] = []
                    d[hist_key].append(books[p]['mid'])
                    if len(d[hist_key]) > 50: d[hist_key].pop(0)
                    ema = sum(d[hist_key])/len(d[hist_key])
                    skew = -2.0 * (pos / limit)**3
                    f = ema + skew
                    b, s = int(math.floor(f - 2)), int(math.ceil(f + 2))
                    if limit - pos > 0: orders.append(Order(p, b, limit - pos))
                    if limit + pos > 0: orders.append(Order(p, s, -(limit + pos)))
                    
            elif p in ['HYDROGEL_PACK', 'VELVETFRUIT_EXTRACT']:
                if p in books:
                    hist_key = f'{p}_h'
                    if hist_key not in d: d[hist_key] = []
                    d[hist_key].append(books[p]['mid'])
                    if len(d[hist_key]) > 50: d[hist_key].pop(0)
                    ema = sum(d[hist_key])/len(d[hist_key])
                    skew = -2.0 * (pos / limit)**3
                    f = ema + skew
                    b, s = int(math.floor(f - 1)), int(math.ceil(f + 1))
                    b, s = min(b, books[p]['bid'] + 1), max(s, books[p]['ask'] - 1)
                    orders.append(Order(p, b, limit - pos))
                    orders.append(Order(p, s, -(limit + pos)))

            result[p] = orders
        return result, 0, json.dumps(d)
"""

def evaluate(params):
    imb_thresh = params[0]
    code = template.replace("{IMB_THRESH}", str(imb_thresh))
    
    filename = f"trader_opt_frontrun_{int(imb_thresh*100)}.py"
    with open(filename, "w") as f:
        f.write(code)
    
    cmd = f"python3 -m prosperity4bt {filename} 3 --no-out --no-progress"
    try:
        res = subprocess.run(cmd, env=os.environ, shell=True, text=True, capture_output=True, timeout=90)
        match = re.search(r"final_pnl:\s*(-?\d+(?:,\d+)*)", res.stdout)
        if match:
            pnl = int(match.group(1).replace(",", ""))
            return params, pnl
    except Exception as e:
        return params, -999
    finally:
        if os.path.exists(filename):
            os.remove(filename)
    return params, -999

if __name__ == "__main__":
    imb_thresh_list = [0.2, 0.4, 0.6, 0.8, 0.9]
    grid = list(itertools.product(imb_thresh_list))
    print(f"Total combinations: {len(grid)}")
    
    best_pnl = -float('inf')
    best_params = None
    
    with ProcessPoolExecutor(max_workers=8) as executor:
        for params, pnl in executor.map(evaluate, grid):
            if pnl > best_pnl:
                best_pnl = pnl
                best_params = params
            print(f"Params {params} -> PnL: {pnl}")
            
    print(f"Best Params: {best_params} -> PnL: {best_pnl}")
