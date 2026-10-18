import pandas as pd
import numpy as np
import os

def analyze_pebbles_lead_lag():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path):
        return

    df = pd.read_csv(data_path, sep=';')
    pebbles = ["PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL"]
    
    pivot_df = df[df['product'].isin(pebbles)].pivot(index='timestamp', columns='product', values='mid_price')
    
    # Calculate returns
    returns = pivot_df.pct_change().dropna()
    
    for p1 in pebbles:
        for p2 in pebbles:
            if p1 == p2: continue
            corr = returns[p1].corr(returns[p2])
            # Check lag 1 correlation
            lag_corr = returns[p1].shift(1).corr(returns[p2])
            if lag_corr > 0.3 or lag_corr < -0.3:
                print(f"{p1} -> {p2} (lag 1): {lag_corr:.4f}")

if __name__ == "__main__":
    analyze_pebbles_lead_lag()
