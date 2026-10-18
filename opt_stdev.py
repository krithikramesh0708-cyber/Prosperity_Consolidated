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
STRIKES = {
    'VEV_4000': 4000, 'VEV_4500': 4500, 'VEV_5000': 5000, 'VEV_5100': 5100,
    'VEV_5200': 5200, 'VEV_5300': 5300, 'VEV_5400': 5400, 'VEV_5500': 5500,
    'VEV_6000': 6000, 'VEV_6500': 6500
}
for v in STRIKES: LIMITS[v] = 300

class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        d = json.loads(state.traderData) if state.traderData else {}
        result = {}
        
        books = {}
        for p, od in state.order_depths.items():
            b, a = sorted(od.buy_orders.items(), reverse=True), sorted(od.sell_orders.items())
            if b and a: books[p] = {'bid': b[0][0], 'ask': a[0][0], 'mid': (b[0][0]+a[0][0])/2.0, 'bids': b, 'asks': a}

        # Underlying price S
        S = books['VELVETFRUIT_EXTRACT']['mid'] if 'VELVETFRUIT_EXTRACT' in books else 5230.0

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
                    skew = -2.0 * (norm_pos * abs(norm_pos))
                    f = ema + skew
                    b, s = int(math.floor(f - 1)), int(math.ceil(f + 1))
                    b, s = min(b, books[p]['bid'] + 1), max(s, books[p]['ask'] - 1)
                    orders.append(Order(p, b, limit - pos))
                    orders.append(Order(p, s, -(limit + pos)))

            elif p in STRIKES:
                if p in books:
                    hist_key = f'{p}_prm' # Store premium
                    K = STRIKES[p]
                    intrinsic = max(S - K, 0)
                    premium = books[p]['mid'] - intrinsic
                    
                    if hist_key not in d: d[hist_key] = []
                    d[hist_key].append(premium)
                    
                    win_len = {WINDOW_LEN}
                    if len(d[hist_key]) > win_len: d[hist_key].pop(0)
                    
                    if len(d[hist_key]) > 5:
                        mean_prm = sum(d[hist_key]) / len(d[hist_key])
                        variance = sum((x - mean_prm) ** 2 for x in d[hist_key]) / len(d[hist_key])
                        std_prm = math.sqrt(variance)
                        
                        # Threshold for arbitrage
                        lower_bound = mean_prm - {Z_SCORE} * std_prm
                        upper_bound = mean_prm + {Z_SCORE} * std_prm
                        
                        # Calculate Option Fair limits
                        fair_lower = intrinsic + lower_bound
                        fair_upper = intrinsic + upper_bound
                        
                        # Sniper Taker
                        for ap, av in books[p]['asks']:
                            if ap <= fair_lower and pos < limit:
                                q = min(-av, limit - pos); orders.append(Order(p, ap, q)); pos += q
                        for bp, bv in books[p]['bids']:
                            if bp >= fair_upper and pos > -limit:
                                q = min(bv, limit + pos); orders.append(Order(p, bp, -q)); pos -= q

            result[p] = orders
        return result, 0, json.dumps(d)
"""

def evaluate(params):
    window_len, z_score = params
    code = template.replace("{WINDOW_LEN}", str(window_len))\
                   .replace("{Z_SCORE}", str(z_score))
    
    filename = f"trader_stdev_{window_len}_{int(z_score*10)}.py"
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
    window_len_list = [20, 50, 100, 200]
    z_score_list = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    
    grid = list(itertools.product(window_len_list, z_score_list))
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
