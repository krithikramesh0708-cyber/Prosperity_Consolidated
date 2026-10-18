import json
import matplotlib.pyplot as plt
from collections import defaultdict

with open('Round3/ROUND_3/472988/472988.json') as f:
    data = json.load(f)

# Find max drawdown per asset!
pnl_by_asset = defaultdict(list)
time_series = []

for row in data:
    ts = row['timestamp']
    time_series.append(ts)
    for p, state in row['state'].items():
        if p in ['VELVETFRUIT_EXTRACT', 'HYDROGEL_PACK'] or p.startswith('VEV'):
            # The 'state' typically isn't directly formatted like this, wait.
            # I should inspect 472988.log or 472988.json structure first.
            pass
