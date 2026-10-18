import pandas as pd
import numpy as np

def analyze_mark_alpha():
    df_trades = pd.read_csv("prosperity4bt/resources/round4/trades_round_4_day_1.csv", sep=';')
    df_prices = pd.read_csv("prosperity4bt/resources/round4/prices_round_4_day_1.csv", sep=';')
    
    symbol = 'VEV_4000'
    trades = df_trades[df_trades['symbol'] == symbol]
    prices = df_prices[df_prices['product'] == symbol].set_index('timestamp')['mid_price']
    
    results = []
    for trader in ['Mark 01', 'Mark 14', 'Mark 22']:
        trader_trades = trades[(trades['buyer'] == trader) | (trades['seller'] == trader)]
        
        for horizon in [100, 500, 1000]:
            pnl = []
            for _, trade in trader_trades.iterrows():
                t = trade['timestamp']
                side = 1 if trade['buyer'] == trader else -1
                price_now = trade['price']
                if t + horizon in prices.index:
                    price_future = prices.loc[t + horizon]
                    pnl.append(side * (price_future - price_now))
            
            if pnl:
                results.append({
                    'trader': trader,
                    'horizon': horizon,
                    'avg_pnl': np.mean(pnl),
                    'win_rate': np.mean([1 if x > 0 else 0 for x in pnl])
                })
    
    print(pd.DataFrame(results))

if __name__ == "__main__":
    analyze_mark_alpha()
