import pandas as pd
import numpy as np
import os
from sklearn.decomposition import PCA

def analyze_round5_v14():
    data_path = "/Users/krithikramesh/Antigravity/Backtester/Final_Round/round5/prices_round_5_day_2.csv"
    if not os.path.exists(data_path):
        print(f"File not found: {data_path}")
        return

    df = pd.read_csv(data_path, sep=';')
    pivoted = df.pivot(index='timestamp', columns='product', values='mid_price')
    data = pivoted.dropna()
    
    # Scale data
    data_scaled = (data - data.mean()) / data.std()
    
    pca = PCA()
    pca.fit(data_scaled)
    
    print("--- PCA Analysis ---")
    explained_variance = pca.explained_variance_ratio_
    cumulative_variance = np.cumsum(explained_variance)
    
    for i in range(10):
        print(f"  PC{i+1}: {explained_variance[i]:.4f} (Cumulative: {cumulative_variance[i]:.4f})")
        
    print("\nTotal components to explain 90% variance:", np.argmax(cumulative_variance > 0.90) + 1)
    print("Total components to explain 95% variance:", np.argmax(cumulative_variance > 0.95) + 1)

if __name__ == "__main__":
    analyze_round5_v14()
