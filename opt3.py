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

        vfe_diff = 0.0
        p = 'VELVETFRUIT_EXTRACT'
        if p in books:
            hist_key = f'{p}_h'
            l = d.get(hist_key, [])
            if l:
                vfe_ema = sum(l)/len(l)
                vfe_diff = books[p]['mid'] - vfe_ema

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
                    norm_pos = pos / limit
                    skew = -2.0 * norm_pos * abs(norm_pos) 
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
                    
                    # Sniper Taker with VFE filter
                    for ap, av in books[p]['asks']:
                        # The ask is very low. It's a fake move only if VFE hasn't plunged.
                        if ap <= ema - {TAKER_THRESH} and pos < limit:
                            if {USE_VFE_FILTER}:
                                if vfe_diff > -{VFE_THRESH}:
                                    q = min(-av, limit - pos); orders.append(Order(p, ap, q)); pos += q
                            else:
                                q = min(-av, limit - pos); orders.append(Order(p, ap, q)); pos += q

                    for bp, bv in books[p]['bids']:
                        # The bid is very high. It's a fake move only if VFE hasn't mooned.
                        if bp >= ema + {TAKER_THRESH} and pos > -limit:
                            if {USE_VFE_FILTER}:
                                if vfe_diff < {VFE_THRESH}:
                                    q = min(bv, limit + pos); orders.append(Order(p, bp, -q)); pos -= q
                            else:
                                q = min(bv, limit + pos); orders.append(Order(p, bp, -q)); pos -= q

            result[p] = orders
        return result, 0, json.dumps(d)
"""

def evaluate(params):
    taker_thresh, use_vfe_filter, vfe_thresh = params
    code = template.replace("{TAKER_THRESH}", str(taker_thresh))\
                   .replace("{USE_VFE_FILTER}", str(use_vfe_filter))\
                   .replace("{VFE_THRESH}", str(vfe_thresh))
    
    filename = f"trader_opt3_{int(taker_thresh*10)}_{use_vfe_filter}_{int(vfe_thresh*10)}.py"
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
    taker_thresh_list = [3.0, 3.5, 4.0, 4.5]
    use_vfe_filter_list = [True, False]
    vfe_thresh_list = [0.5, 1.0, 2.0, 3.0, 999.0]
    
    grid = list(itertools.product(taker_thresh_list, use_vfe_filter_list, vfe_thresh_list))
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
