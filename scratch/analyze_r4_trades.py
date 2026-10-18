import pandas as pd
import glob
import os

def analyze_round4_trades():
    trade_files = glob.glob("prosperity4bt/resources/round4/trades_round_4_day_*.csv")
    all_trades = []
    for f in trade_files:
        df = pd.read_csv(f, sep=';')
        all_trades.append(df)
    
    if not all_trades:
        print("No trade files found.")
        return
        
    df = pd.concat(all_trades)
    
    print("Top Buyers:")
    buyer_counts = df['buyer'].value_counts().head(10)
    print(buyer_counts)
    
    print("\nTop Sellers:")
    seller_counts = df['seller'].value_counts().head(10)
    print(seller_counts)
    
    # Analyze specific symbols
    for symbol in df['symbol'].unique():
        print(f"\n--- {symbol} ---")
        sym_df = df[df['symbol'] == symbol]
        print("Traders involved:")
        traders = set(sym_df['buyer'].unique()) | set(sym_df['seller'].unique())
        print(traders)
        
        # Check volume per trader
        buyer_vol = sym_df.groupby('buyer')['quantity'].sum().sort_values(ascending=False).head(5)
        seller_vol = sym_df.groupby('seller')['quantity'].sum().sort_values(ascending=False).head(5)
        print("Top Buyers Volume:")
        print(buyer_vol)
        print("Top Sellers Volume:")
        print(seller_vol)

if __name__ == "__main__":
    analyze_round4_trades()
