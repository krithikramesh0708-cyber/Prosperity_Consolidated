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

SMILE_A, SMILE_B, SMILE_C = -0.01839205, -0.00707253, 0.27569916
DAYS_PER_YEAR = 365.0

def _phi(x):
    if x > 6.0: return 1.0
    if x < -6.0: return 0.0
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5*t + a4)*t) + a3)*t + a2)*t + a1)*t * math.exp(-x*x/2.0)
    return 0.5 * (1.0 + sign * y)

def bs_call(S, K, TTE, sigma):
    if TTE <= 1e-8 or sigma <= 1e-8: return max(S - K, 0)
    d1 = (math.log(S/K) + 0.5 * sigma**2 * TTE) / (sigma * math.sqrt(TTE))
    d2 = d1 - sigma * math.sqrt(TTE)
    return S * _phi(d1) - K * _phi(d2)

def get_iv(S, K, TTE):
    if TTE <= 1e-8: return 0.2
    m = math.log(K/S) / math.sqrt(TTE)
    return max(0.05, SMILE_A * m**2 + SMILE_B * m + SMILE_C)

class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        d = json.loads(state.traderData) if state.traderData else {}
        result = {}
        
        books = {}
        for p, od in state.order_depths.items():
            b, a = sorted(od.buy_orders.items(), reverse=True), sorted(od.sell_orders.items())
            if b and a: books[p] = {'bid': b[0][0], 'ask': a[0][0], 'mid': (b[0][0]+a[0][0])/2.0, 'bids': b, 'asks': a}

        S = books.get('VELVETFRUIT_EXTRACT', {}).get('mid')
        
        tc = d.get('tc', 0); d['tc'] = tc + 1
        day_in_sim = tc // 10000
        tick_in_day = tc % 10000
        TTE = max(0.001, (5.0 - day_in_sim - tick_in_day / 10000.0) / DAYS_PER_YEAR)

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
                    skew = -2.0 * (norm_pos)**3 
                    f = ema + skew
                    b, s = int(math.floor(f - 1)), int(math.ceil(f + 1))
                    b, s = min(b, books[p]['bid'] + 1), max(s, books[p]['ask'] - 1)
                    if limit - pos > 0: orders.append(Order(p, b, limit - pos))
                    if limit + pos > 0: orders.append(Order(p, s, -(limit + pos)))

            elif p in STRIKES and S is not None:
                K = int(p.split('_')[1])
                iv = get_iv(S, K, TTE)
                theo = bs_call(S, K, TTE, iv)
                
                if p in books:
                    best_bid = books[p]['bid']
                    best_ask = books[p]['ask']
                    
                    norm_pos = pos / limit
                    skew = -{SKEW} * norm_pos
                    f = theo + skew
                    
                    # Quoting params
                    edge = {EDGE}
                    b = int(math.floor(f - edge))
                    s = int(math.ceil(f + edge))
                    
                    # Dynamic offset to not get caught quoting too far into the book
                    b = min(b, best_bid + 1)
                    s = max(s, best_ask - 1)
                    
                    # Sniper Taker Logic overlaid on top of Market Making
                    taker_edge = {TAKER_EDGE}
                    if best_ask < f - taker_edge and pos < limit:
                        q = min(-books[p]['asks'][0][1], limit - pos)
                        orders.append(Order(p, best_ask, q))
                        pos += q
                    
                    if best_bid > f + taker_edge and pos > -limit:
                        q = min(books[p]['bids'][0][1], limit + pos)
                        orders.append(Order(p, best_bid, -q))
                        pos -= q
                    
                    if limit - pos > 0:
                        orders.append(Order(p, b, limit - pos))
                    if limit + pos > 0:
                        orders.append(Order(p, s, -(limit + pos)))

            result[p] = orders
        return result, 0, json.dumps(d)
"""

def evaluate(params):
    skew, edge, taker_edge = params
    code = template.replace("{SKEW}", str(skew))\
                   .replace("{EDGE}", str(edge))\
                   .replace("{TAKER_EDGE}", str(taker_edge))
    
    filename = f"trader_bs_mm_{int(skew*10)}_{int(edge*10)}_{int(taker_edge*10)}.py"
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
    skew_list = [5.0, 10.0, 20.0, 50.0]
    edge_list = [2.0, 3.0, 4.0]
    taker_edge_list = [1.5, 2.0, 3.0]
    
    grid = list(itertools.product(skew_list, edge_list, taker_edge_list))
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
