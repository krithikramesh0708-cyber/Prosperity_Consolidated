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
DELTAS = {
    'VEV_4000': 1.0, 'VEV_4500': 1.0, 'VEV_5000': 0.9, 'VEV_5100': 0.8,
    'VEV_5200': 0.5, 'VEV_5300': 0.25, 'VEV_5400': 0.1, 'VEV_5500': 0.05,
    'VEV_6000': 0.01, 'VEV_6500': 0.01
}
STRIKES = list(DELTAS.keys())
for v in STRIKES: LIMITS[v] = 300

class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        d = json.loads(state.traderData) if state.traderData else {}
        result = {}
        
        books = {}
        for p, od in state.order_depths.items():
            b, a = sorted(od.buy_orders.items(), reverse=True), sorted(od.sell_orders.items())
            if b and a: books[p] = {'bid': b[0][0], 'ask': a[0][0], 'mid': (b[0][0]+a[0][0])/2.0, 'bids': b, 'asks': a}

        # Calculate Global Delta
        global_delta = 0.0
        vfe_pos = state.position.get('VELVETFRUIT_EXTRACT', 0)
        global_delta += vfe_pos
        for p in STRIKES:
            global_delta += state.position.get(p, 0) * DELTAS[p]
            
        # Target max delta might be around limit = 200, but with options it can get to 3000
        # Let's say max allowed delta conceptually is 1000
        net_risk = global_delta / {MAX_RISK}

        for p in state.order_depths:
            if p not in books: continue
            pos = state.position.get(p, 0)
            limit = LIMITS.get(p, 300)
            orders = []

            hist_key = f'{p}_h'
            if hist_key not in d: d[hist_key] = []
            d[hist_key].append(books[p]['mid'])
            if len(d[hist_key]) > {SMA_LEN}: d[hist_key].pop(0)
            ema = sum(d[hist_key])/len(d[hist_key])

            if p in ['VELVETFRUIT_EXTRACT', 'HYDROGEL_PACK']:
                # For HP, simple logic. For VFE, use global delta skew
                if p == 'HYDROGEL_PACK':
                    local_skew = -2.0 * (pos / limit)**3
                    f = ema + local_skew
                else:
                    # VFE uses global skew
                    skew = -{SKEW_FACTOR} * net_risk
                    f = ema + skew
                    
                b, s = int(math.floor(f - {SPREAD})), int(math.ceil(f + {SPREAD}))
                b, s = min(b, books[p]['bid'] + 1), max(s, books[p]['ask'] - 1)
                orders.append(Order(p, b, limit - pos))
                orders.append(Order(p, s, -(limit + pos)))

            elif p in STRIKES:
                delta = DELTAS[p]
                
                # Global delta skew applied relative to this option's delta
                skew = -{SKEW_FACTOR} * net_risk * delta
                f = ema + skew
                
                # We do pure MM for options since we are hedged across strikes!
                b, s = int(math.floor(f - {SPREAD_OPT})), int(math.ceil(f + {SPREAD_OPT}))
                # Do not blindly join top-of-book if spread is huge (avoid pennies)
                # Just rest orders at calculated safe bounds
                
                # Optionally Penny the spread if it's safe
                b = min(b, books[p]['ask'] - 1)
                s = max(s, books[p]['bid'] + 1)
                
                if limit - pos > 0: orders.append(Order(p, b, limit - pos))
                if limit + pos > 0: orders.append(Order(p, s, -(limit + pos)))

            result[p] = orders
        return result, 0, json.dumps(d)
"""

def evaluate(params):
    max_risk, ema, skew_factor, spread, spread_opt = params
    code = template.replace("{MAX_RISK}", str(max_risk))\
                   .replace("{SMA_LEN}", str(ema))\
                   .replace("{SKEW_FACTOR}", str(skew_factor))\
                   .replace("{SPREAD}", str(spread))\
                   .replace("{SPREAD_OPT}", str(spread_opt))
    
    filename = f"trader_mm_{max_risk}_{ema}_{int(skew_factor*10)}_{int(spread*10)}_{int(spread_opt*10)}.py"
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
    max_risk_list = [500, 1000, 2000]
    ema_list = [20, 50, 100]
    skew_factor_list = [5.0, 10.0, 20.0]
    spread_list = [1.0, 2.0]
    spread_opt_list = [1.0, 3.0, 5.0]
    
    grid = list(itertools.product(max_risk_list, ema_list, skew_factor_list, spread_list, spread_opt_list))
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
