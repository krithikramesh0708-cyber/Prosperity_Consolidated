import csv
from collections import defaultdict
import glob

violations = 0
total = 0

for day in range(3):
    prices_by_ts = defaultdict(dict)
    with open(f'Round3/ROUND_3/prices_round_3_day_{day}.csv') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader)
        for row in reader:
            ts = int(row[1])
            product = row[2]
            ask = float(row[9]) if row[9] else 0
            bid = float(row[3]) if row[3] else 0
            prices_by_ts[ts][product] = {'ask': ask, 'bid': bid}

    strikes = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]
    
    for ts, data in prices_by_ts.items():
        total += 1
        for i in range(len(strikes)-1):
            for j in range(i+1, len(strikes)):
                K1, K2 = strikes[i], strikes[j]
                sym1 = f'VEV_{K1}'
                sym2 = f'VEV_{K2}'
                if sym1 in data and sym2 in data:
                    ask1, bid1 = data[sym1]['ask'], data[sym1]['bid']
                    ask2, bid2 = data[sym2]['ask'], data[sym2]['bid']
                    if ask1 and bid2:
                        # If I can buy K1 cheaper than I can sell K2
                        if ask1 < bid2:
                            violations += 1

print(f"Total ticks: {total}, Vertical Arbitrage Violations: {violations}")
