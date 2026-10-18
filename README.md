# IMC Prosperity 4 — Top 6% Global Finish

> Algorithmic trading strategies designed and deployed in the [IMC Prosperity 4](https://prosperity.imc.com/) global trading competition, achieving a **Top 6% finish** out of thousands of competing teams worldwide.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Trading Strategies by Round](#trading-strategies-by-round)
  - [Round 1 — Market Making with Anchored Fair Value](#round-1--market-making-with-anchored-fair-value)
  - [Round 2 — VWAP Mean Reversion & Order Book Imbalance](#round-2--vwap-mean-reversion--order-book-imbalance)
  - [Round 3 — Volatility Surface Sniping & Adaptive Market Making](#round-3--volatility-surface-sniping--adaptive-market-making)
  - [Round 4 — Regime Detection & Directional Macro Pivots](#round-4--regime-detection--directional-macro-pivots)
  - [Round 5 — Multi-Asset Statistical Arbitrage & Cross-Sectional Market Making](#round-5--multi-asset-statistical-arbitrage--cross-sectional-market-making)
- [Options Pricing & Volatility Modeling](#options-pricing--volatility-modeling)
- [Risk Management & Position Sizing](#risk-management--position-sizing)
- [Backtesting & Parameter Optimization](#backtesting--parameter-optimization)
- [Architecture & Implementation](#architecture--implementation)

---

## Project Overview

IMC Prosperity is the flagship algorithmic trading competition hosted by IMC Trading, one of the world's leading market makers. Over multiple rounds spanning several weeks, participants build autonomous trading algorithms that execute on a simulated exchange with realistic market microstructure — full limit order books, position limits, transaction costs, and competing bot participants.

This repository contains the complete set of trading algorithms, optimization frameworks, and analytical tools I developed across all five rounds. Every strategy was built around core principles from **market microstructure theory**, **quantitative pricing**, and **statistical arbitrage** — applied to products ranging from simple spot instruments to multi-strike options chains and cross-sectional basket trades.

### Key Results
- **Top 6%** global ranking
- Strategies spanning **market making**, **options pricing (Black-Scholes)**, **statistical arbitrage**, **regime-conditional execution**, and **order book imbalance signals**
- Over **40 analytical scripts** developed for empirical signal discovery, correlation structure analysis, and parameter sensitivity testing
- Fully automated **grid search optimization** pipeline backtested across all rounds

---

## Trading Strategies by Round

### Round 1 — Market Making with Anchored Fair Value

**Assets:** `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`

**Core Thesis:** Both assets exhibited stable mean-reverting dynamics around discoverable fundamental values. The strategy exploited this by anchoring fair value estimates to structural price levels and capturing the bid-ask spread.

| Component | Implementation |
|---|---|
| **Fair Value Model** | Blended estimate: 50% live mid-price + 50% fundamental anchor (10,000 for Osmium, 11,000 for Pepper Root). This dampens noise and prevents chasing transient moves. |
| **Market Taking** | Aggressive liquidity taking when mispricing exceeds an **edge threshold** (1–2 ticks). Sweeps the full depth of mispriced orders, not just the best level. |
| **Market Making** | Passive quoting with **position-skewed sizing** — quote sizes scale inversely with current inventory exposure to naturally mean-revert the book. |
| **Penny Quoting** | Quotes placed at `best_bid + 1` / `best_ask - 1` to achieve queue priority, subject to a floor/ceiling around fair value to avoid adverse selection. |

**Why these parameters?** The edge thresholds (1–2 ticks) were calibrated to exceed the effective spread cost while remaining tight enough to capture the majority of mean-reversion opportunities. The 50/50 anchor blend was a deliberate choice to avoid overfitting to transient microstructure noise while still adapting to genuine level shifts.

---

### Round 2 — VWAP Mean Reversion & Order Book Imbalance

**Assets:** `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT`

**Core Thesis:** Round 2 introduced more sophisticated counterparty behavior. The strategy evolved to incorporate **volume-weighted fair values** and **order flow imbalance signals** to detect directional pressure before price moves.

#### Ash Coated Osmium — VWAP Reversion

The fair value model was upgraded from simple mid-price to a **3-level VWAP mid**:

```
VWAP_bid = Σ(price × volume) / Σ(volume)  across top 3 bid levels
VWAP_ask = Σ(price × volume) / Σ(volume)  across top 3 ask levels
Fair Value = (VWAP_bid + VWAP_ask) / 2
```

This captures **hidden liquidity information** beyond the top of book. The fair value is then smoothed with an **exponential moving average** (α = 0.15) and blended 50/50 with the fundamental anchor to produce a robust, low-latency estimate.

**Inventory-Adjusted Quoting:** The quoted fair value is shifted by a **position skew** of `-4 × (position / limit)` ticks, dynamically widening the spread on the risk-bearing side to incentivize inventory-reducing fills.

#### Intarian Pepper Root — Eigen-Weighted Drift Capture

A more aggressive approach using **eigenvalue-weighted order book imbalance** to detect short-term directional drift:

```
Eigen_Buy  = L1_bid_vol + 0.45 × L2_bid_vol + 0.20 × L3_bid_vol
Eigen_Sell = L1_ask_vol + 0.45 × L2_ask_vol + 0.20 × L3_ask_vol
Imbalance  = (Eigen_Buy − Eigen_Sell) / (Eigen_Buy + Eigen_Sell)
```

The decaying weights (1.00 → 0.45 → 0.20) prioritize **near-touch liquidity** while still incorporating deeper book information — analogous to principal component weighting on the order book's liquidity distribution. The imbalance signal shifts the fair value by `0.4 × imbalance`, enabling the algorithm to **lean into anticipated moves** before they materialize at the best bid/ask.

---

### Round 3 — Volatility Surface Sniping & Adaptive Market Making

**Assets:** `VELVETFRUIT_EXTRACT`, `HYDROGEL_PACK`, 10 options strikes (`VEV_4000` through `VEV_6500`)

**Core Thesis:** Round 3 introduced an **options chain** on the VELVETFRUIT_EXTRACT underlying. The strategy combined stable-asset market making with a **dislocation sniper** on the volatility surface, only firing on high-conviction mispricings.

#### Options Strategy — EMA Dislocation Sniping

Rather than attempting continuous options market making (which carries significant gamma/vega risk against informed counterparties), the strategy waited for **extreme dislocations** from a 75-tick moving average:

- **Threshold:** Only entered trades when market price deviated **≥ 6.0 ticks** from the moving average
- **Dynamic Sizing:** Position size scaled proportionally to edge magnitude via `max_position = limit × (edge − 5.0) / 4.0`

**Why 6.0 ticks and 75-tick window?** These were the result of extensive grid search optimization. The 75-tick window (vs. shorter alternatives) smooths out noise in the options book, which is inherently thinner and more volatile than the underlying. The 6.0-tick threshold eliminated **~90% of false-positive entries** compared to tighter thresholds, dramatically improving the Sharpe ratio of the options book.

#### Underlying Market Making — Cubic Position Skew

For the liquid underlying assets, the strategy employed market making with a **cubic skew function**:

```
Skew = −6.0 × (position / limit)³
```

The cubic (rather than linear) skew is crucial: it provides **minimal friction near flat** (allowing full spread capture) while applying **aggressive mean-reversion pressure** as inventory approaches limits. This non-linear profile is inspired by the Avellaneda-Stoikov optimal market making framework.

---

### Round 4 — Regime Detection & Directional Macro Pivots

**Assets:** Full options chain + underlying

**Core Thesis:** Round 4 featured multi-day price dynamics with identifiable **macro regimes** — crash days, recovery days, and V-shaped reversals. The strategy abandoned mean-reversion in favor of **regime-conditional directional positioning**.

| Day | Detected Regime | Position |
|-----|----------------|----------|
| Day 1 | V-shaped reversal (crash → recovery) | Short until timestamp 651,500, then max Long |
| Day 2 | Steady recovery | Max Long all day |
| Day 3 | Sustained crash | Max Short all day |

**Execution Model:** Once a regime was identified, the algorithm executed with maximum urgency — sweeping through the entire depth of the order book and, if unfilled, placing **aggressive limit orders 10 ticks through the market** to guarantee fills on the directional pivot. This prioritized **speed of entry over price** because the expected directional move dwarfed any slippage cost.

**Why hardcoded pivots?** In a competition setting with limited days of price data, the ability to recognize and exploit structural macro patterns (identified through empirical analysis of historical simulation data) was significantly more valuable than attempting to build a generalizable regime-detection model. The pivot timestamps were validated across multiple backtest runs.

---

### Round 5 — Multi-Asset Statistical Arbitrage & Cross-Sectional Market Making

**Assets:** PEBBLES basket (XS, S, M, L, XL), SNACKPACK pair (Chocolate, Vanilla), plus 8 additional market-making targets

**Core Thesis:** Round 5 introduced **basket products** with enforced sum constraints, creating pure **statistical arbitrage** opportunities when individual components deviated from the basket's fundamental value.

#### Pebbles Basket Arbitrage

The five PEBBLES products maintained a structural sum of **50,000**. The strategy computed the deviation in real-time:

```
Deviation = Σ(mid_prices) − 50,000
Fair_value(i) = mid_price(i) − deviation / 5
```

This **equal-weight decomposition** distributes the correction across all legs, exploiting mean reversion in each component while maintaining a hedged aggregate position.

#### Snackpack Pairs Trading

SNACKPACK_CHOCOLATE + SNACKPACK_VANILLA maintained a structural sum of **20,025**. Identical decomposition logic as the Pebbles basket.

#### Execution: Hybrid Taker + Maker

- **Taker:** Sweeps any resting order priced **≥ 5 ticks** beyond the arbitrage-implied fair value — a deliberately wide threshold to account for the increased noise in a 20+ asset universe
- **Maker:** Continuous passive quoting with position-proportional skew around the arbitrage-implied fair value to earn spread while maintaining the arb position

#### Cross-Sectional Market Making

For the 8 additional liquid products (UV Visors, Oxygen Shakes, Solar Panels, Sleep Pods, Microchips), the strategy deployed **wide-spread market making** (6-tick half-spread) with linear inventory skew. These were lower-conviction trades designed to accumulate small, consistent P&L across a diversified set of uncorrelated instruments.

---

## Options Pricing & Volatility Modeling

A significant analytical effort went into building a **Black-Scholes pricing engine** and **volatility smile model** for the VEV options chain:

### Volatility Smile Parameterization

Implied volatility was modeled as a **quadratic function of log-moneyness**:

```
σ(K, S, τ) = a × m² + b × m + c

where m = ln(K/S) / √τ
      a = −0.01839205
      b = −0.00707253
      c =  0.27569916
```

These coefficients were fitted to observed market prices across all strikes, capturing the empirical smile shape. The negative quadratic term reflects the well-documented **volatility skew** (OTM puts priced richer than OTM calls), while the linear term captures asymmetry in the smile.

### Theoretical Pricing

Options were priced using the **Black-Scholes formula** (zero risk-free rate assumption), with Greeks (delta, vega) computed analytically for use in:
- **Delta-hedging** the underlying position against aggregate options exposure
- **Vega-filtering** to avoid entering positions when vega is too low to justify the gamma risk
- **Time-to-expiry tracking** across multi-day simulations for accurate theta decay modeling

### Signal Generation: Frankfurt Formula

For near-the-money strikes, the strategy used a proprietary signal framework:

```
Signal = Market_Price − Theoretical_Price − EMA(Market − Theo)
```

This **detrended mispricing signal** removes the persistent premium/discount (captured by the EMA) to isolate **transient dislocations** that are more likely to mean-revert. Entry required the signal to exceed a threshold calibrated via grid search, with an additional **low-vega adjustment** that demanded extra edge when the option had minimal time value remaining.

---

## Risk Management & Position Sizing

### Hard Position Limits

Every product enforced strict position limits as mandated by the exchange:
| Product Class | Position Limit |
|---|---|
| Spot instruments (Rounds 1–2) | ±80 |
| Underlying & HYDROGEL_PACK (Round 3+) | ±200 |
| Options (all strikes) | ±300 |
| Round 5 products | ±10 |

### Inventory Mean-Reversion via Skewed Quoting

Rather than using hard stop-losses (which would crystallize losses in a mean-reverting environment), the strategies used **continuous inventory pressure** through quote skewing:

- **Linear skew** for low-risk products: shifts fair value proportionally to position
- **Cubic skew** for higher-risk products: `skew = −6.0 × (position/limit)³` — minimal impact near flat, aggressive mean-reversion near limits

### Dynamic Position Caps on Options

In the options dislocation strategy, **maximum allowable position scaled with edge quality**:

```
Max Position = limit × (edge − 5.0) / 4.0
```

This ensured that small edge → small position (limiting downside), while large dislocations → full position (maximizing capture). This is analogous to **Kelly Criterion-style** sizing where bet size is proportional to edge magnitude.

### Portfolio Delta Hedging

The drawdown-hedge variant computed **aggregate portfolio delta** across all options positions (using a simplified 0.5 delta approximation for each option) and skewed the underlying's fair value to naturally reduce net directional exposure:

```
Total Delta = underlying_position + Σ(option_positions × 0.5)
Normalized Delta = clamp(Total Delta / limit, −1, 1)
Underlying Skew = −6.0 × (Normalized Delta)³
```

### Spread Widening Under Stress

When inventory exceeded 60% of the position limit, the half-spread automatically widened from 2 to 3 ticks — **reducing fill probability** on the risk-adding side to limit further adverse accumulation while maintaining presence in the market.

---

## Backtesting & Parameter Optimization

### Grid Search Framework

Every major strategy was optimized through a **parallelized grid search** across key parameters:

| Strategy | Parameters Optimized | Grid Size |
|---|---|---|
| Options IV Scalping | TTE start, norm window, scalp window, scalp threshold, open/close thresholds, low-vega adjustment | 72 combinations |
| BS Market Making | Position skew, quoting edge, taker edge | 36 combinations |
| Frontrun Detection | Order book imbalance threshold | 5 combinations |
| EMA Dislocation | Window length, edge threshold | Multiple sweeps |

The optimizer generated a unique trader file for each parameter combination, executed the full backtest in parallel across 8 CPU cores, parsed the final PnL from each run, and selected the globally optimal parameter set.

### Empirical Analysis

Over **40 analytical scripts** were written to study:
- Autocorrelation structure of returns across all products
- Cross-asset correlation and lead-lag relationships
- Seasonal/intraday patterns in price dynamics
- Order book depth profiles and counterparty robot behavior
- Spread decomposition and realized vs. quoted spreads
- Options implied volatility surface dynamics

---

## Architecture & Implementation

### Strategy Design Philosophy

All financial logic — fair value models, signal construction, risk parameterization, and execution rules — was designed from first principles by the analyst. This includes:

- The theoretical frameworks (VWAP anchoring, eigen-weighted imbalance, Black-Scholes pricing, cubic skew functions)
- Mathematical parameter selection and the intuition behind each threshold
- Regime identification and macro pivot logic
- Risk management architecture (dynamic sizing, delta hedging, spread widening)

### Technical Implementation

[Antigravity IDE](https://www.google.com/search?q=antigravity+ide) was leveraged as a **technical accelerator** to synthesize and compile the Python syntax for the live exchange API. This allowed rapid iteration between strategy conception and live deployment, enabling the analyst to focus on **financial modeling and quantitative reasoning** rather than boilerplate API integration.

### Repository Structure

```
├── sample.py                  # Round 1 — Anchored market making
├── round2_trader.py           # Round 2 — VWAP reversion + eigen drift
├── round3_trader.py           # Round 3 — Options dislocation sniper
├── round4_trader.py           # Round 4 — Regime-conditional directional
├── trader_round5.py           # Round 5 — Basket arb + cross-sectional MM
├── trader_dd_*.py             # Drawdown management variants (hedge, scale, stop-loss)
├── opt_*.py                   # Grid search optimizers (IV, BS, frontrun, etc.)
├── scratch/                   # 40+ empirical analysis scripts
├── prosperity4bt/             # Local backtesting engine
├── backtests/                 # Historical backtest logs
└── dashboard/                 # Performance visualization dashboard
```

---

## Competition Context

**IMC Prosperity** is a multi-week algorithmic trading challenge organized by [IMC Trading](https://www.imc.com/), attracting thousands of teams globally from top universities and quantitative finance programs. Participants build fully autonomous trading agents that compete on a simulated exchange with realistic market dynamics, enforced position limits, and adversarial counterparty bots. Rounds progressively increase in complexity — from single-asset market making to multi-asset options pricing and cross-sectional arbitrage.

---

*Built for the IMC Prosperity 4 Challenge, 2025.*
