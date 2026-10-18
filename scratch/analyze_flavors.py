import pandas as pd
import numpy as np
import os

def analyze_cross_correlations():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path):
        return

    df = pd.read_csv(data_path, sep=';')
    
    # Check correlations between SNACKPACK and OXYGEN_SHAKE of same flavor
    flavors = ['CHOCOLATE', 'VANILLA', 'STRAWBERRY', 'PISTACHIO', 'RASPBERRY']
    
    for f in flavors:
        s_name = f"SNACKPACK_{f}"
        o_name = f"OXYGEN_SHAKE_{f}"
        
        s_df = df[df['product'] == s_name]
        o_df = df[df['product'] == o_name]
        
        if s_df.empty or o_df.empty: continue
        
        merged = pd.merge(s_df[['timestamp', 'mid_price']], o_df[['timestamp', 'mid_price']], on='timestamp', suffixes=('_s', '_o'))
        corr = merged['mid_price_s'].corr(merged['mid_price_o'])
        print(f"{f:10}: Correlation = {corr:.4f}")

if __name__ == "__main__":
    analyze_cross_correlations()
