import pandas as pd
import numpy as np
import os

def analyze_uv_visors():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path):
        return

    df = pd.read_csv(data_path, sep=';')
    uv_prods = [p for p in df['product'].unique() if 'UV_VISOR' in p]
    
    # Pivot to get mids at each timestamp
    pivot_df = df[df['product'].isin(uv_prods)].pivot(index='timestamp', columns='product', values='mid_price')
    pivot_df['sum'] = pivot_df.sum(axis=1)
    
    print(f"UV_VISOR Sum Mean: {pivot_df['sum'].mean()}")
    print(f"UV_VISOR Sum Std:  {pivot_df['sum'].std()}")
    print(f"UV_VISOR Sum Min:  {pivot_df['sum'].min()}")
    print(f"UV_VISOR Sum Max:  {pivot_df['sum'].max()}")

if __name__ == "__main__":
    analyze_uv_visors()
