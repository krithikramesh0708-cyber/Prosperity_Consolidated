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
    with open('Round3/ROUND_3/prices_round_3_day_0.csv', 'r') as f:
        reader = list(csv.DictReader(f, delimiter=';'))
        
        for check_ts in [0, 500000, 990000]:
            S = 0
            C = 0
            strike = 5000.0
            
            for row in reader:
                ts = int(row['timestamp'])
                if ts == check_ts:
                    if row['product'] == 'VELVETFRUIT_EXTRACT':
                        S = float(row['mid_price'])
                    elif row['product'] == 'VEV_5000':
                        C = float(row['mid_price'])
                        
            # find IV assuming T = 8.0/252
            low, high = 0.001, 5.0
            for _ in range(40):
                mid_v = (low + high) / 2
                p = black_scholes_call(S, strike, 8.0/250, 0, mid_v)
                if p > C: high = mid_v
                else: low = mid_v
            iv_constant_T = mid_v
            
            # find IV assuming T fractional = (8.0 - ts/1000000) / 250
            T_frac = (8.0 - check_ts/1000000.0) / 250.0
            low, high = 0.001, 5.0
            for _ in range(40):
                mid_v = (low + high) / 2
                p = black_scholes_call(S, strike, T_frac, 0, mid_v)
                if p > C: high = mid_v
                else: low = mid_v
            iv_frac_T = mid_v
            
            print(f"TS {check_ts}: S={S}, C={C}")
            print(f"  IV (const T=8): {iv_constant_T:.4f}")
            print(f"  IV (frac T={T_frac*250}): {iv_frac_T:.4f}")
            
if __name__ == "__main__":
    main()
