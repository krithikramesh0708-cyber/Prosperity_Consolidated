import pandas as pd
import numpy as np
import os

def analyze_snackpacks():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path):
        return

    df = pd.read_csv(data_path, sep=';')
    snack_prods = [p for p in df['product'].unique() if 'SNACKPACK' in p]
    print(f"Snackpack products: {snack_prods}")
    
    pivot_df = df[df['product'].isin(snack_prods)].pivot(index='timestamp', columns='product', values='mid_price')
    
    pairs = [
        (['SNACKPACK_CHOCOLATE', 'SNACKPACK_VANILLA'], "C+V"),
        (['SNACKPACK_PISTACHIO', 'SNACKPACK_RASPBERRY', 'SNACKPACK_STRAWBERRY'], "P+R+S")
    ]
    
    for prods, name in pairs:
        available = [p for p in prods if p in pivot_df.columns]
        if len(available) == len(prods):
            s = pivot_df[prods].sum(axis=1)
            print(f"{name:10} Mean: {s.mean():.4f}, Std: {s.std():.4f}")

if __name__ == "__main__":
    analyze_snackpacks()
