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

THRESHOLDS = {
    'VEV_4000': {T4000}, 'VEV_4500': {T4500}, 'VEV_5000': {T5000}, 'VEV_5100': {T5100},
    'VEV_5200': {T5200}, 'VEV_5300': {T5300}, 'VEV_5400': {T5400}, 'VEV_5500': {T5500},
    'VEV_6000': {T6000}, 'VEV_6500': {T6500}
}
WINDOWS = {
    'VEV_4000': {W4000}, 'VEV_4500': {W4500}, 'VEV_5000': {W5000}, 'VEV_5100': {W5100},
    'VEV_5200': {W5200}, 'VEV_5300': {W5300}, 'VEV_5400': {W5400}, 'VEV_5500': {W5500},
    'VEV_6000': {W6000}, 'VEV_6500': {W6500}
}

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
                
                win = WINDOWS.get(p, 50)
                if len(d[hist_key]) > win: d[hist_key].pop(0)
                ema = sum(d[hist_key])/len(d[hist_key])
                
                if p in STRIKES:
                    edge = THRESHOLDS[p]
                    for ap, av in books[p]['asks']:
                        if ap <= ema - edge and pos < limit:
                            q = min(-av, limit - pos); orders.append(Order(p, ap, q)); pos += q
                    for bp, bv in books[p]['bids']:
                        if bp >= ema + edge and pos > -limit:
                            q = min(bv, limit + pos); orders.append(Order(p, bp, -q)); pos -= q
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

STRIKES = ['VEV_4000', 'VEV_4500', 'VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_5500', 'VEV_6000', 'VEV_6500']

def test_strike(args):
    strike, win, edge = args
    code = template
    for s in STRIKES:
        w = win if s == strike else 50
        e = edge if s == strike else 5.0
        code = code.replace(f"{{W{s.split('_')[1]}}}", str(w))
        code = code.replace(f"{{T{s.split('_')[1]}}}", str(e))
    
    filename = f"trader_{strike}_{win}_{int(edge*10)}.py"
    with open(filename, "w") as f:
        f.write(code)
    
    try:
        res = subprocess.run(f"python3 -m prosperity4bt {filename} 3 --no-out --no-progress", env=os.environ, shell=True, text=True, capture_output=True, timeout=90)
        strike_pnl = 0
        for line in res.stdout.splitlines():
            if line.startswith(f"{strike}: "):
                strike_pnl += int(line.split(': ')[1].replace(',', ''))
        return args, strike_pnl
    except Exception as e:
        pass
    finally:
        if os.path.exists(filename): os.remove(filename)
    return args, -999

import sys
if __name__ == "__main__":
    import multiprocessing
    wins = [5, 10, 20, 30, 40, 50, 75, 100]
    edges = [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
    STRIKES = ['VEV_4000', 'VEV_4500', 'VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_5500', 'VEV_6000', 'VEV_6500']
    
    results = {}
    with ProcessPoolExecutor(max_workers=8) as executor:
        for strike in STRIKES:
            print(f"Optimizing {strike}...")
            grid = [(strike, w, e) for w in wins for e in edges]
            best_pnl = -float('inf')
            best_params = None
            for args, pnl in executor.map(test_strike, grid):
                if pnl > best_pnl:
                    best_pnl = pnl
                    best_params = args
            print(f"Best for {strike}: Window {best_params[1]}, Edge {best_params[2]} -> PnL: {best_pnl}")
            results[strike] = best_params
