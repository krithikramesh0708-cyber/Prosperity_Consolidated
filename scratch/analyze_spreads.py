import pandas as pd
import numpy as np
import os

def analyze_spreads():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path): return
    df = pd.read_csv(data_path, sep=';')
    pivot_df = df.pivot(index='timestamp', columns='product', values='mid_price')
    
    # Pairs to check (based on high corr)
    pairs = [
        ("SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA"),
        ("OXYGEN_SHAKE_EVENING_BREATH", "PEBBLES_XS"),
        ("OXYGEN_SHAKE_EVENING_BREATH", "UV_VISOR_YELLOW"),
        ("GALAXY_SOUNDS_BLACK_HOLES", "UV_VISOR_AMBER"),
    ]
    
    for p1, p2 in pairs:
        if p1 in pivot_df.columns and p2 in pivot_df.columns:
            # Linear regression to find hedge ratio
            y = pivot_df[p1]
            x = pivot_df[p2]
            
            # Simplified: just check sum or diff if corr is ~1 or -1
            corr = y.corr(x)
            if corr < 0:
                spread = y + x
                name = "Sum"
            else:
                spread = y - x
                name = "Diff"
                
            print(f"{p1} / {p2} ({name}): Mean={spread.mean():.1f}, Std={spread.std():.4f}, Std/Mean={spread.std()/abs(spread.mean()):.6f}")

if __name__ == "__main__":
    analyze_spreads()
