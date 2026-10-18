import pandas as pd
import numpy as np
import os

def analyze_seasonal():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path): return
    df = pd.read_csv(data_path, sep=';')
    
    # Check OXYGEN_SHAKE_MINT
    p = "OXYGEN_SHAKE_MINT"
    p_df = df[df['product'] == p]
    
    import matplotlib.pyplot as plt
    plt.plot(p_df['timestamp'], p_df['mid_price'])
    plt.savefig("/Users/krithikramesh/Antigravity/Backtester/scratch/seasonal.png")

if __name__ == "__main__":
    analyze_seasonal()
