"""
Deep empirical analysis of VEV options data to understand:
1. Time to expiry structure  
2. Volatility smile shape
3. Theoretical vs market price deviations
"""
import csv
import math
from statistics import NormalDist

_N = NormalDist()

def bs_call(S, K, TTE, sigma, r=0):
    """Black-Scholes call price and delta"""
    if TTE <= 0 or sigma <= 0: return max(S - K, 0), 1.0 if S > K else 0.0
    d1 = (math.log(S/K) + (r + 0.5 * sigma**2) * TTE) / (sigma * TTE**0.5)
    d2 = d1 - sigma * TTE**0.5
    price = S * _N.cdf(d1) - K * math.exp(-r * TTE) * _N.cdf(d2)
    return price, _N.cdf(d1)

def implied_vol(market_price, S, K, TTE, r=0, tol=1e-6, max_iter=100):
    """Newton's method to find implied vol"""
    if TTE <= 0: return None
    intrinsic = max(S - K, 0)
    if market_price <= intrinsic + 0.01: return None
    
    sigma = 0.2  # initial guess
    for _ in range(max_iter):
        price, _ = bs_call(S, K, TTE, sigma, r)
        d1 = (math.log(S/K) + (r + 0.5*sigma**2) * TTE) / (sigma * TTE**0.5)
        vega = S * _N.pdf(d1) * TTE**0.5
        if vega < 1e-10: break
        sigma -= (price - market_price) / vega
        if sigma <= 0: sigma = 0.01
        if abs(price - market_price) < tol: break
    return sigma

# Read prices
prices_by_ts = {}
for day in range(3):
    with open(f'Round3/ROUND_3/prices_round_3_day_{day}.csv') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader)  # header
        for row in reader:
            ts = int(row[1]) + day * 1000000
            product = row[2]
            mid = float(row[15])
            if ts not in prices_by_ts: prices_by_ts[ts] = {}
            prices_by_ts[ts][product] = mid

# Analyze implied vols
strikes = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]

# Try different TTE assumptions
print("=" * 80)
print("TESTING TTE ASSUMPTIONS")
print("=" * 80)

for tte_days in [1, 2, 3, 5, 7]:
    TTE = tte_days / 365.0
    
    ivs_by_strike = {K: [] for K in strikes}
    
    for ts in sorted(prices_by_ts.keys())[:200]:  # first 200 ticks of day 0
        data = prices_by_ts[ts]
        S = data.get('VELVETFRUIT_EXTRACT')
        if S is None: continue
        
        for K in strikes:
            sym = f'VEV_{K}'
            if sym not in data: continue
            mkt_price = data[sym]
            iv = implied_vol(mkt_price, S, K, TTE)
            if iv is not None and 0.01 < iv < 5.0:
                ivs_by_strike[K].append(iv)
    
    print(f"\nTTE = {tte_days} days:")
    for K in strikes:
        if ivs_by_strike[K]:
            avg_iv = sum(ivs_by_strike[K])/len(ivs_by_strike[K])
            print(f"  Strike {K}: avg IV = {avg_iv:.4f} ({len(ivs_by_strike[K])} samples)")

# Now do a detailed analysis with the best TTE
print("\n" + "=" * 80)
print("MONEYNESS vs IV SMILE (searching for parabola)")
print("=" * 80)

for tte_days in [3, 5, 7]:
    TTE = tte_days / 365.0
    print(f"\n--- TTE = {tte_days} days ---")
    
    moneyness_iv = []
    
    for ts in sorted(prices_by_ts.keys()):
        data = prices_by_ts[ts]
        S = data.get('VELVETFRUIT_EXTRACT')
        if S is None: continue
        
        for K in strikes:
            sym = f'VEV_{K}'
            if sym not in data: continue
            mkt_price = data[sym]
            iv = implied_vol(mkt_price, S, K, TTE)
            if iv is not None and 0.01 < iv < 5.0:
                m = math.log(K/S) / TTE**0.5
                moneyness_iv.append((m, iv, K, ts))
    
    # Group by moneyness buckets
    if moneyness_iv:
        from collections import defaultdict
        buckets = defaultdict(list)
        for m, iv, K, ts in moneyness_iv:
            buckets[K].append((m, iv))
        
        print(f"  Total IV samples: {len(moneyness_iv)}")
        for K in sorted(buckets.keys()):
            ms = [x[0] for x in buckets[K]]
            ivs_vals = [x[1] for x in buckets[K]]
            if ivs_vals:
                avg_m = sum(ms)/len(ms)
                avg_iv = sum(ivs_vals)/len(ivs_vals)
                print(f"  K={K}: avg moneyness={avg_m:.4f}, avg IV={avg_iv:.4f}, n={len(ivs_vals)}")

# Now find the smile coefficients by fitting a parabola
print("\n" + "=" * 80)
print("FITTING PARABOLIC VOL SMILE")
print("=" * 80)

for tte_days in [3, 5, 7]:
    TTE = tte_days / 365.0
    
    all_m = []
    all_iv = []
    
    for ts in sorted(prices_by_ts.keys()):
        data = prices_by_ts[ts]
        S = data.get('VELVETFRUIT_EXTRACT')
        if S is None: continue
        
        for K in strikes:
            sym = f'VEV_{K}'
            if sym not in data: continue
            mkt_price = data[sym]
            iv = implied_vol(mkt_price, S, K, TTE)
            if iv is not None and 0.01 < iv < 5.0:
                m = math.log(K/S) / TTE**0.5
                all_m.append(m)
                all_iv.append(iv)
    
    if len(all_m) > 10:
        # Fit quadratic: iv = a*m^2 + b*m + c
        n = len(all_m)
        sum_m = sum(all_m)
        sum_m2 = sum(x**2 for x in all_m)
        sum_m3 = sum(x**3 for x in all_m)
        sum_m4 = sum(x**4 for x in all_m)
        sum_iv = sum(all_iv)
        sum_m_iv = sum(all_m[i]*all_iv[i] for i in range(n))
        sum_m2_iv = sum(all_m[i]**2 * all_iv[i] for i in range(n))
        
        # Solve 3x3 system via manual Cramer's rule
        # [sum_m4, sum_m3, sum_m2] [a]   [sum_m2_iv]
        # [sum_m3, sum_m2, sum_m ] [b] = [sum_m_iv ]
        # [sum_m2, sum_m,  n     ] [c]   [sum_iv   ]
        
        A = [[sum_m4, sum_m3, sum_m2],
             [sum_m3, sum_m2, sum_m],
             [sum_m2, sum_m, n]]
        B = [sum_m2_iv, sum_m_iv, sum_iv]
        
        def det3(M):
            return (M[0][0]*(M[1][1]*M[2][2]-M[1][2]*M[2][1])
                   -M[0][1]*(M[1][0]*M[2][2]-M[1][2]*M[2][0])
                   +M[0][2]*(M[1][0]*M[2][1]-M[1][1]*M[2][0]))
        
        D = det3(A)
        if abs(D) > 1e-10:
            Da = det3([[B[0], A[0][1], A[0][2]],
                       [B[1], A[1][1], A[1][2]],
                       [B[2], A[2][1], A[2][2]]])
            Db = det3([[A[0][0], B[0], A[0][2]],
                       [A[1][0], B[1], A[1][2]],
                       [A[2][0], B[2], A[2][2]]])
            Dc = det3([[A[0][0], A[0][1], B[0]],
                       [A[1][0], A[1][1], B[1]],
                       [A[2][0], A[2][1], B[2]]])
            a, b, c = Da/D, Db/D, Dc/D
            print(f"\nTTE={tte_days} days: Smile coeffs = [{a:.8f}, {b:.8f}, {c:.8f}]")
            
            # Now compute theoretical prices and deviations
            deviations = []
            for ts in sorted(prices_by_ts.keys()):
                data = prices_by_ts[ts]
                S = data.get('VELVETFRUIT_EXTRACT')
                if S is None: continue
                
                for K in strikes:
                    sym = f'VEV_{K}'
                    if sym not in data: continue
                    mkt_price = data[sym]
                    m = math.log(K/S) / TTE**0.5
                    fitted_iv = a * m**2 + b * m + c
                    if fitted_iv > 0.01:
                        theo_price, delta = bs_call(S, K, TTE, fitted_iv)
                        dev = mkt_price - theo_price
                        deviations.append((K, dev))
            
            from collections import defaultdict
            dev_by_strike = defaultdict(list)
            for K, dev in deviations:
                dev_by_strike[K].append(dev)
            
            print(f"  Price Deviations from Fitted Smile:")
            for K in sorted(dev_by_strike.keys()):
                devs = dev_by_strike[K]
                avg_dev = sum(devs)/len(devs)
                std_dev = (sum((x-avg_dev)**2 for x in devs)/len(devs))**0.5
                print(f"    K={K}: avg_dev={avg_dev:.2f}, std_dev={std_dev:.2f}, n={len(devs)}")

print("\nDone!")
