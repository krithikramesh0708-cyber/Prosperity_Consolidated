import pandas as pd
import numpy as np
import os

def analyze_microchips():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path):
        return

    df = pd.read_csv(data_path, sep=';')
    prods = [p for p in df['product'].unique() if 'MICROCHIP' in p]
    
    pivot_df = df[df['product'].isin(prods)].pivot(index='timestamp', columns='product', values='mid_price')
    
    # Check linear relationships
    # Maybe Rectangle = Square + Triangle?
    if 'MICROCHIP_RECTANGLE' in pivot_df.columns:
        others = [c for c in pivot_df.columns if c != 'MICROCHIP_RECTANGLE']
        for c in others:
            corr = pivot_df['MICROCHIP_RECTANGLE'].corr(pivot_df[c])
            print(f"Rectangle vs {c}: Corr = {corr:.4f}")
            
        # Check sum of others
        pivot_df['sum_others'] = pivot_df[['MICROCHIP_SQUARE', 'MICROCHIP_TRIANGLE']].sum(axis=1)
        corr_sum = pivot_df['MICROCHIP_RECTANGLE'].corr(pivot_df['sum_others'])
        print(f"Rectangle vs Square+Triangle: Corr = {corr_sum:.4f}")

if __name__ == "__main__":
    analyze_microchips()
