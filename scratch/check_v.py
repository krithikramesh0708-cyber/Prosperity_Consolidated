import csv
import math

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def bs_call_v(S, K, v):
    if v <= 0: return max(0, S - K)
    d1 = (math.log(S / K) + 0.5 * v**2) / v
    d2 = d1 - v
    return S * norm_cdf(d1) - K * norm_cdf(d2)

def main():
    with open('Round3/ROUND_3/prices_round_3_day_1.csv', 'r') as f:
        reader = list(csv.DictReader(f, delimiter=';'))
        
        for check_ts in [0, 500000]:
            S = 0
            calls = {}
            for row in reader:
                ts = int(row['timestamp'])
                if ts == check_ts:
                    if row['product'] == 'VELVETFRUIT_EXTRACT':
                        S = float(row['mid_price'])
                    elif row['product'].startswith('VEV_'):
                        strike = float(row['product'].split('_')[1])
                        calls[strike] = float(row['mid_price'])
                        
            # Find implied v using ATM
            # Find strike closest to S
            atm_k = min(calls.keys(), key=lambda k: abs(k - S))
            C_atm = calls[atm_k]
            
            low, high = 1e-5, 1.0
            for _ in range(40):
                mid = (low + high) / 2
                p = bs_call_v(S, atm_k, mid)
                if p > C_atm: high = mid
                else: low = mid
            implied_v = mid
            
            print(f"TS {check_ts}, S={S}")
            print(f"  ATM Strike {atm_k}, C={C_atm}, Implied v = {implied_v:.6f}")
            
            # Check errors for other strikes using this v
            for k, c in sorted(calls.items()):
                p = bs_call_v(S, k, implied_v)
                print(f"    Strike {k}: model={p:.2f}, mkt={c:.2f}, err={p-c:.2f}")

if __name__ == "__main__":
    main()
