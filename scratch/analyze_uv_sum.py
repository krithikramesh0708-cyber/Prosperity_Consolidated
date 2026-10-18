import pandas as pd
import numpy as np
import os

def analyze_uv_visor_sum():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path): return
    df = pd.read_csv(data_path, sep=';')
    prods = [p for p in df['product'].unique() if p.startswith('UV_VISOR')]
    pivot_df = df[df['product'].isin(prods)].pivot(index='timestamp', columns='product', values='mid_price')
    s = pivot_df.sum(axis=1)
    print(f"UV_VISOR Sum: Mean={s.mean():.1f}, Std={s.std():.4f}")

if __name__ == "__main__":
    analyze_uv_visor_sum()
