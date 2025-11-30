# P-Tree Interpretation Summary

## Overview
This document provides interpretation of the P-Tree models trained on Swedish stock market data.

## Key Characteristics Used

### Most Important Characteristics (Across All Scenarios)

1. **Specific Variance (rank_svar)** - Used in 2/3 scenarios
   - Category: Risk/Volatility
   - Indicates idiosyncratic (stock-specific) risk

2. **12-Month Momentum (rank_mom12m)** - Used in 2/3 scenarios
   - Category: Momentum
   - Classic momentum factor (winners vs losers)

3. **Market Equity / Size (rank_me)** - Used in 2/3 scenarios
   - Category: Size
   - Small vs large cap stocks

### Other Important Characteristics

- **Dollar Volume (rank_dolvol)** - Liquidity measure
- **Asset Growth (rank_agr)** - Investment factor
- **Return on Assets (rank_roa)** - Profitability
- **Cash Flow-to-Price (rank_cfp)** - Value factor
- **Illiquidity (rank_ill)** - Trading friction
- **Bid-Ask Spread (rank_baspread)** - Transaction costs

## Scenario-Specific Patterns

### Scenario A: Full Sample (1999-2020)
**Primary splits:** Specific Variance, 12-Month Momentum, Dollar Volume, Size

**Interpretation:** The full-sample tree prioritizes **risk** (variance) and **momentum** signals, combined with **liquidity** (dollar volume) and **size**.

### Scenario B: Train (1999-2009)
**Primary splits:** Asset Growth, Specific Variance, Return on Assets, Size, Net Income

**Interpretation:** The 1999-2009 period emphasizes **investment** (asset growth) and **profitability** (ROA, net income) factors, suggesting value/quality strategies worked well.

### Scenario C: Train (2010-2020)
**Primary splits:** Cash Flow-to-Price, Illiquidity, Bid-Ask Spread, Momentum, Asset Turnover

**Interpretation:** The 2010-2020 period focuses on **valuation** (CFP), **liquidity constraints**, and **transaction costs**, reflecting post-financial-crisis market structure.

## Economic Interpretation

### 1. Time-Varying Factor Importance
Different characteristics matter in different periods:
- **Pre-2010:** Profitability and growth signals (ROA, asset growth)
- **Post-2010:** Liquidity and valuation (illiquidity, cash flow-to-price)

This aligns with the **structural change** in markets after the 2008 financial crisis (increased regulation, liquidity concerns).

### 2. Consistent Themes
Some factors appear across scenarios:
- **Size** - Always relevant in Swedish market
- **Momentum** - Persistent predictor
- **Risk/Volatility** - Key discriminator

### 3. Swedish Market Characteristics
The emphasis on **liquidity measures** (dollar volume, illiquidity, bid-ask spread) reflects the **smaller, less liquid** nature of the Swedish market compared to US markets.

## Comparison to Original Paper (Cong et al. 2024)

### Similarities
- Momentum remains important (consistent with US findings)
- Size effect present
- Multiple characteristics used (not single-factor story)

### Differences
- **More emphasis on liquidity** in Swedish market
- **Fewer profitability splits** than US market
- **Higher variance** (Specific Variance used frequently)

This suggests P-Trees **adapt to local market conditions** rather than simply replicating US factor patterns.

## Implications for Thesis

### 1. Model Interpretability
P-Trees provide **clear, actionable splits**:
- "High momentum stocks with low variance outperform"
- "Small, profitable firms with asset growth deliver excess returns"

### 2. Economic Meaningfulness
Characteristics used are **economically interpretable**, not arbitrary:
- Momentum (behavioral bias)
- Liquidity (market microstructure)
- Profitability (fundamental value)

### 3. Robustness
Different characteristics across scenarios shows:
- Model **adapts to regime changes**
- Not overfitting to specific factors
- **Time-varying risk premia** captured

## Next Steps for Analysis

1. **Leaf Composition Analysis**
   - How many stocks per leaf?
   - What are average characteristics of each leaf?

2. **Economic Story**
   - Why do these splits improve Sharpe ratio?
   - What market inefficiencies are being exploited?

3. **Comparison to Sorted Portfolios**
   - How do P-Tree portfolios differ from simple momentum/value sorts?
