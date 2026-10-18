import pandas as pd

def check_correlation():
    df = pd.read_csv("prosperity4bt/resources/round4/prices_round_4_day_1.csv", sep=';')
    hydro = df[df['product'] == 'HYDROGEL_PACK'][['timestamp', 'mid_price']].set_index('timestamp')
    velvet = df[df['product'] == 'VELVETFRUIT_EXTRACT'][['timestamp', 'mid_price']].set_index('timestamp')
    
    merged = hydro.join(velvet, lsuffix='_hydro', rsuffix='_velvet')
    print("Correlation:")
    print(merged.corr())
    
    # Check if there's a linear relationship: Hydro = A * Velvet + B
    # Or common ratio
    merged['ratio'] = merged['mid_price_hydro'] / merged['mid_price_velvet']
    print("\nRatio Stats:")
    print(merged['ratio'].describe())

if __name__ == "__main__":
    check_correlation()
