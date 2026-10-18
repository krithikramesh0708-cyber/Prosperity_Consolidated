import pandas as pd
import numpy as np
import os

def analyze_galaxy():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path):
        return

    df = pd.read_csv(data_path, sep=';')
    prods = [p for p in df['product'].unique() if 'GALAXY_SOUNDS' in p]
    
    pivot_df = df[df['product'].isin(prods)].pivot(index='timestamp', columns='product', values='mid_price')
    pivot_df['sum'] = pivot_df.sum(axis=1)
    
    print(f"GALAXY Sum Mean: {pivot_df['sum'].mean()}")
    print(f"GALAXY Sum Std:  {pivot_df['sum'].std()}")

if __name__ == "__main__":
    analyze_galaxy()
