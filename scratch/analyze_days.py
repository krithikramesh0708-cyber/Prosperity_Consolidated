import pandas as pd
import numpy as np
import os

def analyze_all_days_sums():
    groups = {
        'PEBBLES': 'PEBBLES',
        'SNACKPACK': 'SNACKPACK',
        'ROBOT': 'ROBOT',
        'GALAXY': 'GALAXY_SOUNDS'
    }
    
    for day in [2, 3, 4]:
        data_path = f"/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_{day}.csv"
        if not os.path.exists(data_path): continue
        df = pd.read_csv(data_path, sep=';')
        
        print(f"--- Day {day} ---")
        for name, prefix in groups.items():
            prods = [p for p in df['product'].unique() if p.startswith(prefix)]
            if len(prods) == 5:
                pivot_df = df[df['product'].isin(prods)].pivot(index='timestamp', columns='product', values='mid_price')
                s = pivot_df.sum(axis=1)
                print(f"{name:10}: Mean={s.mean():8.1f}, Std={s.std():8.4f}")

if __name__ == "__main__":
    analyze_all_days_sums()
