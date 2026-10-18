import pandas as pd
import numpy as np
import os

def analyze_panels():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path):
        return

    df = pd.read_csv(data_path, sep=';')
    prods = [p for p in df['product'].unique() if 'PANEL' in p]
    
    pivot_df = df[df['product'].isin(prods)].pivot(index='timestamp', columns='product', values='mid_price')
    
    # Check if 1X2 + 1X2 = 2X2 ? No, that's area.
    # Maybe 1X2 * 2 = 1X4? Or 1X4 + 1X4 = 2X4?
    # Actually, let's check area based:
    # 1X2: Area 2
    # 1X4: Area 4
    # 2X2: Area 4
    # 2X4: Area 8
    # 4X4: Area 16
    
    # Check if 1X4 == 2X2
    if 'PANEL_1X4' in pivot_df.columns and 'PANEL_2X2' in pivot_df.columns:
        print(f"1X4 vs 2X2 Corr: {pivot_df['PANEL_1X4'].corr(pivot_df['PANEL_2X2']):.4f}")
        
    # Check if 2 * 1X4 == 2X4
    if 'PANEL_1X4' in pivot_df.columns and 'PANEL_2X4' in pivot_df.columns:
        print(f"2*1X4 vs 2X4 Corr: {(2*pivot_df['PANEL_1X4']).corr(pivot_df['PANEL_2X4']):.4f}")

if __name__ == "__main__":
    analyze_panels()
