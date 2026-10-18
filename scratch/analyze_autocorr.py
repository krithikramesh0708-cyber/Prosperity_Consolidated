import pandas as pd
import numpy as np
import os

def analyze_autocorr():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path): return
    df = pd.read_csv(data_path, sep=';')
    
    pivot_df = df.pivot(index='timestamp', columns='product', values='mid_price')
    returns = pivot_df.pct_change().dropna()
    
    results = []
    for p in pivot_df.columns:
        ac = returns[p].autocorr(lag=1)
        results.append({'product': p, 'autocorr': ac})
        
    res_df = pd.DataFrame(results).sort_values('autocorr')
    print(res_df.to_string())

if __name__ == "__main__":
    analyze_autocorr()
