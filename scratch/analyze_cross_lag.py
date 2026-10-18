import pandas as pd
import numpy as np
import os

def analyze_cross_lead_lag():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path): return
    df = pd.read_csv(data_path, sep=';')
    
    # Selected pair from previous analysis
    p1 = "OXYGEN_SHAKE_EVENING_BREATH"
    p2 = "PEBBLES_XS"
    
    pivot_df = df[df['product'].isin([p1, p2])].pivot(index='timestamp', columns='product', values='mid_price')
    returns = pivot_df.pct_change().dropna()
    
    corr0 = returns[p1].corr(returns[p2])
    corr1 = returns[p1].shift(1).corr(returns[p2]) # p1 leads p2
    corr2 = returns[p2].shift(1).corr(returns[p1]) # p2 leads p1
    
    print(f"Corr(0):     {corr0:.4f}")
    print(f"p1 leads p2: {corr1:.4f}")
    print(f"p2 leads p1: {corr2:.4f}")

if __name__ == "__main__":
    analyze_cross_lead_lag()
