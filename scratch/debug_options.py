"""Debug script: check what the options strategy is doing tick by tick"""
import csv
import math
from collections import defaultdict

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def bs_call_v(S, K, v):
    if v <= 0: return max(0.0, S - K)
    d1 = (math.log(S / K) + 0.5 * v**2) / v
    d2 = d1 - v
    return S * norm_cdf(d1) - K * norm_cdf(d2)

# Check what fair prices we'd compute vs market mids for options
with open('Round3/ROUND_3/prices_round_3_day_0.csv', 'r') as f:
    reader = list(csv.DictReader(f, delimiter=';'))

strikes = [5000, 5100, 5200, 5300, 5400, 5500]
sample_tss = [0, 100000, 200000, 500000, 800000]

for check_ts in sample_tss:
    S = None
    mids = {}
    bids = {}
    asks = {}
    for row in reader:
        ts = int(row['timestamp'])
        if ts == check_ts:
            if row['product'] == 'VELVETFRUIT_EXTRACT':
                S = float(row['mid_price'])
            elif row['product'].startswith('VEV_'):
                k = int(row['product'].split('_')[1])
                if k in strikes:
                    mids[k] = float(row['mid_price'])
                    b1 = float(row['bid_price_1']) if row['bid_price_1'] else None
                    a1 = float(row['ask_price_1']) if row['ask_price_1'] else None
                    bids[k] = b1
                    asks[k] = a1

    if S is None: continue
    
    # Calibrate from 5200
    if 5200 in mids:
        C = mids[5200]
        intrinsic = max(0, S - 5200)
        if C > intrinsic + 0.5:
            low, high = 1e-5, 0.5
            for _ in range(25):
                mid = (low + high) / 2
                p = bs_call_v(S, 5200, mid)
                if p > C: high = mid
                else: low = mid
            iv = mid
        else:
            iv = 0.001
    else:
        continue
        
    print(f"\nTS={check_ts}, S={S}, implied_v={iv:.6f}")
    for k in strikes:
        if k not in mids: continue
        fair = bs_call_v(S, k, iv)
        fair = max(fair, max(0, S - k) + 0.5)
        diff = fair - mids[k]
        print(f"  K={k}: fair={fair:.1f}, market_mid={mids[k]:.1f}, diff={diff:.1f}, bid={bids[k]}, ask={asks[k]}")
        if bids[k] and asks[k]:
            if fair < bids[k]:
                print(f"    -> SELL signal: fair < bid ({fair:.1f} < {bids[k]})")
            elif fair > asks[k]:
                print(f"    -> BUY signal: fair > ask ({fair:.1f} > {asks[k]})")
            else:
                print(f"    -> No take signal")
