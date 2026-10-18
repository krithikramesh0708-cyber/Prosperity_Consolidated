import pandas as pd
import numpy as np
import os

def check_price_levels():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path): return
    df = pd.read_csv(data_path, sep=';')
    
    levels = df.groupby('product')['mid_price'].mean().sort_values()
    print(levels.to_string())

if __name__ == "__main__":
    check_price_levels()
