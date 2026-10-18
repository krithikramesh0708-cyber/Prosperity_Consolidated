import pandas as pd
import numpy as np
import os

def analyze_market_factor():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path): return
    df = pd.read_csv(data_path, sep=';')
    pivot_df = df.pivot(index='timestamp', columns='product', values='mid_price')
    
    # Normalize each product to start at 100
    norm_df = pivot_df / pivot_df.iloc[0] * 100
    market_mean = norm_df.mean(axis=1)
    
    # Correlation of each product returns with market factor returns
    market_returns = market_mean.pct_change().dropna()
    returns = pivot_df.pct_change().dropna()
    
    results = []
    for p in returns.columns:
        corr = returns[p].corr(market_returns)
        results.append({'product': p, 'market_corr': corr})
        
    res_df = pd.DataFrame(results).sort_values('market_corr', ascending=False)
    print(res_df.to_string())

if __name__ == "__main__":
    analyze_market_factor()
