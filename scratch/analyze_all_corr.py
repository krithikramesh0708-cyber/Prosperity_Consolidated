import pandas as pd
import numpy as np
import os

def analyze_correlations():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path): return
    df = pd.read_csv(data_path, sep=';')
    
    pivot_df = df.pivot(index='timestamp', columns='product', values='mid_price')
    corr_matrix = pivot_df.corr()
    
    high_corr = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            c = corr_matrix.iloc[i, j]
            if abs(c) > 0.8:
                high_corr.append((corr_matrix.columns[i], corr_matrix.columns[j], c))
                
    for p1, p2, c in sorted(high_corr, key=lambda x: -abs(x[2])):
        print(f"{p1:30} {p2:30} {c:.4f}")

if __name__ == "__main__":
    analyze_correlations()
