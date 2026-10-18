import pandas as pd
import numpy as np
import os

def check_conversions():
    # Prosperity 4 backtester might have conversion data in the price CSVs or somewhere else
    # Let's check the columns of the price CSV
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path): return
    df = pd.read_csv(data_path, sep=';', nrows=5)
    print(df.columns.tolist())

if __name__ == "__main__":
    check_conversions()
