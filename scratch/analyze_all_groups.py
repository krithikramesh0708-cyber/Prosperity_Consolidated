import pandas as pd
import numpy as np
import os

def analyze_all_groups():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path):
        return

    df = pd.read_csv(data_path, sep=';')
    
    groups = {
        'GALAXY': 'GALAXY_SOUNDS',
        'MICROCHIP': 'MICROCHIP',
        'OXYGEN': 'OXYGEN_SHAKE',
        'PANEL': 'PANEL',
        'PEBBLES': 'PEBBLES',
        'ROBOT': 'ROBOT',
        'SLEEP_POD': 'SLEEP_POD',
        'SNACKPACK': 'SNACKPACK',
        'TRANSLATOR': 'TRANSLATOR',
        'UV_VISOR': 'UV_VISOR'
    }
    
    for name, prefix in groups.items():
        prods = [p for p in df['product'].unique() if p.startswith(prefix)]
        if len(prods) == 5:
            pivot_df = df[df['product'].isin(prods)].pivot(index='timestamp', columns='product', values='mid_price')
            s = pivot_df.sum(axis=1)
            print(f"{name:10}: Mean={s.mean():8.1f}, Std={s.std():8.4f}")
        else:
            print(f"{name:10}: Found {len(prods)} products")

if __name__ == "__main__":
    analyze_all_groups()
