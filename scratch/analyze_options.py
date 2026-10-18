import csv
import math

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def black_scholes_call(S, K, T, r, sigma):
    if T <= 0:
        return max(0, S - K)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)

def main():
    # Day 0 TTE = 8 days? "TTE=8d at the start of historical day 0"
    T = 8.0 / 252.0  # Actually TTE means days, usually year fraction. 
    # Or maybe we need to guess the days properly. Let's output what IV works.
    
    with open('Round3/ROUND_3/prices_round_3_day_0.csv', 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        
        # We need a timestamp match.
        underlying = {} # timestamp -> mid
        options = {} # timestamp -> {strike -> mid}
        
        for row in reader:
            ts = int(row['timestamp'])
            prod = row['product']
            mid = float(row['mid_price'])
            if prod == 'VELVETFRUIT_EXTRACT':
                underlying[ts] = mid
            elif prod.startswith('VEV_'):
                strike = float(prod.split('_')[1])
                if ts not in options:
                    options[ts] = {}
                options[ts][strike] = mid
                
    # Calculate implied vol for first timestamp
    ts = 0
    S = underlying[ts]
    print(f"Timestamp {ts}, Underlying S = {S}")
    
    # Try different volatilities
    best_iv = {}
    for strike, C in sorted(options[ts].items()):
        if C < 1: continue # too low volume/price
        
        # simple binary search for IV
        low = 0.001
        high = 5.0
        for _ in range(30):
            mid_v = (low + high) / 2
            p = black_scholes_call(S, strike, T, 0, mid_v)
            if p > C:
                high = mid_v
            else:
                low = mid_v
        print(f"Strike {strike}, Call {C}, Implied Vol for T={T*252}d: {mid_v:.4f}")
        best_iv[strike] = mid_v
        
if __name__ == "__main__":
    main()
