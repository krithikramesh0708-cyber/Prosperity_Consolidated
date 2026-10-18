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
STRIKE_MAP = {
    'VEV_4000': 4000, 'VEV_4500': 4500, 'VEV_5000': 5000, 'VEV_5100': 5100,
    'VEV_5200': 5200, 'VEV_5300': 5300, 'VEV_5400': 5400, 'VEV_5500': 5500,
    'VEV_6000': 6000, 'VEV_6500': 6500
}
for v in STRIKE_MAP: LIMITS[v] = 300

SCALP_STRIKES = ['VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_5500']
SMILE_A, SMILE_B, SMILE_C = -0.01839205, -0.00707253, 0.27569916
DAYS_PER_YEAR = 365.0

def _phi(x):
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5*t + a4)*t) + a3)*t + a2)*t + a1)*t * math.exp(-x*x/2.0)
    return 0.5 * (1.0 + sign * y)

def _pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

def bs_call(S, K, TTE, sigma):
    if TTE <= 1e-8 or sigma <= 1e-8: return max(S - K, 0), 1.0 if S > K else 0.0
    d1 = (math.log(S/K) + 0.5 * sigma**2 * TTE) / (sigma * math.sqrt(TTE))
    d2 = d1 - sigma * math.sqrt(TTE)
    return S * _phi(d1) - K * _phi(d2), _phi(d1)

def bs_vega(S, K, TTE, sigma):
    if TTE <= 1e-8 or sigma <= 1e-8: return 0.0
    d1 = (math.log(S/K) + 0.5*sigma**2 * TTE) / (sigma * math.sqrt(TTE))
    return S * _pdf(d1) * math.sqrt(TTE)

def get_iv(S, K, TTE):
    if TTE <= 1e-8: return 0.2
    m = math.log(K/S) / math.sqrt(TTE)
    return max(0.05, SMILE_A * m**2 + SMILE_B * m + SMILE_C)

class Trader:
    def run(self, state: TradingState):
        d = json.loads(state.traderData) if state.traderData else {}
        result = {}
        books = {}
        for p, od in state.order_depths.items():
            b = sorted(od.buy_orders.items(), reverse=True)
            a = sorted(od.sell_orders.items())
            if b and a:
                books[p] = {'bid': b[0][0], 'ask': a[0][0], 'mid': (b[0][0]+a[0][0])/2.0, 'bids': b, 'asks': a,
                            'bid_wall': b[-1][0], 'ask_wall': a[-1][0]}
                books[p]['wall_mid'] = (books[p]['bid_wall'] + books[p]['ask_wall']) / 2.0

        S = books['VELVETFRUIT_EXTRACT']['mid'] if 'VELVETFRUIT_EXTRACT' in books else None
        
        tc = d.get('tc', 0); d['tc'] = tc + 1
        day_in_sim = tc // 10000
        tick_in_day = tc % 10000
        TTE = max(0.001, ({TTE_START} - day_in_sim - tick_in_day / 10000.0) / DAYS_PER_YEAR)

        for p in state.order_depths:
            if p not in books: continue
            pos = state.position.get(p, 0)
            limit = LIMITS.get(p, 300)
            orders = []

            if p in ['VELVETFRUIT_EXTRACT', 'HYDROGEL_PACK']:
                hk = f'{p}_h'
                if hk not in d: d[hk] = []
                d[hk].append(books[p]['mid'])
                if len(d[hk]) > 50: d[hk].pop(0)
                ema = sum(d[hk])/len(d[hk])
                skew = -2.0 * (pos / limit)**3
                f = ema + skew
                bp = min(int(math.floor(f - 1)), books[p]['bid'] + 1)
                sp = max(int(math.ceil(f + 1)), books[p]['ask'] - 1)
                if limit - pos > 0: orders.append(Order(p, bp, limit - pos))
                if limit + pos > 0: orders.append(Order(p, sp, -(limit + pos)))

            elif p in STRIKE_MAP and S is not None:
                K = STRIKE_MAP[p]
                iv = get_iv(S, K, TTE)
                theo, delta = bs_call(S, K, TTE, iv)
                vega = bs_vega(S, K, TTE, iv)
                
                # theo_diff = market_mid - theoretical_price 
                theo_diff = books[p]['wall_mid'] - theo
                
                # EMA of theo_diff
                td_key = f'{p}_td'
                old_mean = d.get(td_key, 0)
                alpha = 2.0 / ({NORM_WIN} + 1)
                mean_td = alpha * theo_diff + (1 - alpha) * old_mean
                d[td_key] = mean_td
                
                # Switch mean (avg abs deviation)
                sm_key = f'{p}_sm'
                old_sm = d.get(sm_key, 0)
                alpha2 = 2.0 / ({SCALP_WIN} + 1)
                sw = alpha2 * abs(theo_diff - mean_td) + (1 - alpha2) * old_sm
                d[sm_key] = sw
                
                if p in SCALP_STRIKES and tc > {NORM_WIN}:
                    if sw >= {SCALP_THR}:
                        # Frankfurt formula: 
                        # sell_signal = theo_diff - wall_mid + best_bid - mean_td
                        #             = best_bid - theo - mean_td
                        # buy_signal  = theo_diff - wall_mid + best_ask - mean_td
                        #             = best_ask - theo - mean_td
                        sell_sig = books[p]['bid'] - theo - mean_td
                        buy_sig  = books[p]['ask'] - theo - mean_td
                        
                        lv_adj = {LV_ADJ} if vega <= 1.0 else 0.0
                        
                        # Open SELL
                        if sell_sig >= ({THR_OPEN} + lv_adj) and limit + pos > 0:
                            orders.append(Order(p, books[p]['bid'], -(limit + pos)))
                        # Close long
                        elif sell_sig >= {THR_CLOSE} and pos > 0:
                            orders.append(Order(p, books[p]['bid'], -pos))
                        # Open BUY
                        elif buy_sig <= -({THR_OPEN} + lv_adj) and limit - pos > 0:
                            orders.append(Order(p, books[p]['ask'], limit - pos))
                        # Close short
                        elif buy_sig <= -{THR_CLOSE} and pos < 0:
                            orders.append(Order(p, books[p]['ask'], -pos))
                    else:
                        if pos > 0: orders.append(Order(p, books[p]['bid'], -pos))
                        elif pos < 0: orders.append(Order(p, books[p]['ask'], -pos))
                else:
                    # Fallback sniper for deep ITM/OTM
                    hk = f'{p}_h'
                    if hk not in d: d[hk] = []
                    d[hk].append(books[p]['mid'])
                    if len(d[hk]) > 50: d[hk].pop(0)
                    ema = sum(d[hk])/len(d[hk])
                    for ap, av in books[p]['asks']:
                        if ap <= ema - 4.0 and pos < limit:
                            q = min(-av, limit - pos); orders.append(Order(p, ap, q)); pos += q
                    for bp2, bv in books[p]['bids']:
                        if bp2 >= ema + 4.0 and pos > -limit:
                            q = min(bv, limit + pos); orders.append(Order(p, bp2, -q)); pos -= q

            result[p] = orders
        return result, 0, json.dumps(d)
"""

def evaluate(params):
    tte_start, norm_win, scalp_win, scalp_thr, thr_open, thr_close, lv_adj = params
    code = template.replace("{TTE_START}", str(tte_start))\
                   .replace("{NORM_WIN}", str(norm_win))\
                   .replace("{SCALP_WIN}", str(scalp_win))\
                   .replace("{SCALP_THR}", str(scalp_thr))\
                   .replace("{THR_OPEN}", str(thr_open))\
                   .replace("{THR_CLOSE}", str(thr_close))\
                   .replace("{LV_ADJ}", str(lv_adj))
    
    fn = f"trader_iv_{tte_start}_{norm_win}_{scalp_win}_{int(scalp_thr*10)}_{int(thr_open*10)}_{int(thr_close*10)}_{int(lv_adj*10)}.py"
    with open(fn, "w") as f: f.write(code)
    
    try:
        res = subprocess.run(f"python3 -m prosperity4bt {fn} 3 --no-out --no-progress", env=os.environ, shell=True, text=True, capture_output=True, timeout=90)
        match = re.search(r"final_pnl:\s*(-?\d+(?:,\d+)*)", res.stdout)
        if match: return params, int(match.group(1).replace(",", ""))
    except: pass
    finally:
        if os.path.exists(fn): os.remove(fn)
    return params, -999

if __name__ == "__main__":
    tte_list = [3, 5, 7]
    norm_win_list = [10, 20]
    scalp_win_list = [50, 100]
    scalp_thr_list = [0.3, 0.7]
    thr_open_list = [0.3, 0.5, 1.0]
    thr_close_list = [0.0]
    lv_adj_list = [0.5]
    
    grid = list(itertools.product(tte_list, norm_win_list, scalp_win_list, scalp_thr_list, thr_open_list, thr_close_list, lv_adj_list))
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
