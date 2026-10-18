import pandas as pd
import numpy as np
import os

def analyze_robots():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path): return
    df = pd.read_csv(data_path, sep=';')
    pivot_df = df[df['product'].str.startswith('ROBOT')].pivot(index='timestamp', columns='product', values='mid_price')
    
    # Try all combinations of 3 summing to 1?
    # Or just correlations
    print(pivot_df.corr().to_string())

if __name__ == "__main__":
    analyze_robots()
