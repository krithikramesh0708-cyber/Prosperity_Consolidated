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
            if b and a: books[p] = {'bid': b[0][0], 'ask': a[0][0], 'mid': (b[0][0]+a[0][0])/2.0, 'bids': b, 'asks': a}

        for p in state.order_depths:
            pos = state.position.get(p, 0)
            limit = LIMITS.get(p, 300)
            orders = []

            if p in books:
                hist_key = f'{p}_h'
                if hist_key not in d: d[hist_key] = []
                d[hist_key].append(books[p]['mid'])
                
                win = {WINDOW} if p in STRIKES else 50
                if len(d[hist_key]) > win: d[hist_key].pop(0)
                ema = sum(d[hist_key])/len(d[hist_key])
                
                if p in STRIKES:
                    skew = -{SKEW} * (pos / limit)**3
                    f = ema + skew
                    
                    b = int(math.floor(f - {EDGE}))
                    s = int(math.ceil(f + {EDGE}))
                    
                    b = min(b, books[p]['bid'] + 1)
                    s = max(s, books[p]['ask'] - 1)
                    
                    # Taker fallback like 457147
                    for ap, av in books[p]['asks']:
                        if ap < ema - {TAKER_EDGE} and pos < limit:
                            q = min(-av, limit - pos); orders.append(Order(p, ap, q)); pos += q
                    for bp, bv in books[p]['bids']:
                        if bp > ema + {TAKER_EDGE} and pos > -limit:
                            q = min(bv, limit + pos); orders.append(Order(p, bp, -q)); pos -= q

                    if limit - pos > 0: orders.append(Order(p, b, limit - pos))
                    if limit + pos > 0: orders.append(Order(p, s, -(limit + pos)))
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
"""

def evaluate(params):
    window, skew, edge, taker_edge = params
    code = template.replace("{WINDOW}", str(window))\
                   .replace("{SKEW}", str(skew))\
                   .replace("{EDGE}", str(edge))\
                   .replace("{TAKER_EDGE}", str(taker_edge))
    
    filename = f"trader_mm_noise_{window}_{int(skew*10)}_{int(edge*10)}_{int(taker_edge*10)}.py"
    with open(filename, "w") as f:
        f.write(code)
    
    cmd = f"python3 -m prosperity4bt {filename} 3 --no-out --no-progress"
    try:
        res = subprocess.run(cmd, env=os.environ, shell=True, text=True, capture_output=True, timeout=90)
        match = re.search(r"final_pnl:\s*(-?\d+(?:,\d+)*)", res.stdout)
        if match:
            pnl = int(match.group(1).replace(",", ""))
            return params, pnl
        else:
            print(f"Failed {filename}. STDOUT: {res.stdout[:100]}")
    except Exception as e:
        pass
    finally:
        if os.path.exists(filename): os.remove(filename)
    return params, -999

if __name__ == "__main__":
    window_list = [20, 50, 100]
    skew_list = [6.0, 10.0, 20.0]
    edge_list = [2.0, 3.0, 4.0]
    taker_edge_list = [4.0, 5.0]
    
    grid = list(itertools.product(window_list, skew_list, edge_list, taker_edge_list))
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
