# Data Availability Question - P-Trees Swedish Market Implementation

## Background
We're implementing the P-Trees methodology (Cong et al. 2024, JFE) for Swedish stocks as our bachelor thesis at SSE. The implementation is working with statistically significant results, but we want to make sure we haven't missed available data sources.

## Current Setup

**Data sources:** Finbas, LSEG/Refinitiv
**Sample:** 1997-2022, ~300 stocks/month, 102,823 stock-month observations
**Macro variables:** Swedish FF factors updated by Erik Jin

**19 characteristics we have:**
- Value (6): market_cap, book_to_market, ep_ratio, cfp_ratio, sp_ratio, price_to_assets
- Momentum (2): momentum_12m, return_1m
- Profitability (3): roa, gross_profitability, cfo_to_assets
- Growth (2): sales_growth, asset_growth
- Investment (2): capex_to_assets, asset_turnover
- Other (4): volatility_12m, debt_to_equity, asset_quality, turnover

## Results (Brief)

| Test | OOS Period | Sharpe | Alpha |
|------|------------|--------|-------|
| Forward (train 1997-2009) | 2010-2020 | 1.69 | 6.6% |
| Reverse (train 2010-2020) | 1997-2010 | 3.11 | 40.8% |
| Rolling windows | Various | 4.60 | 53.2% |

All statistically significant (t-stats > 9), but performance much better pre-2010 than post-2010.

## The Question

The Cong et al. paper uses **61 characteristics** (Table 1, p.7). We have **19**.

**We're asking:**
1. Are there Swedish market data sources beyond Finbas/LSEG that we should check?
2. Do you know which of the 61 characteristics from the paper are typically available for Swedish stocks?
3. Does Swedish House of Finance have datasets we could access for research?

We've already collected what we think is available from our current sources. We want to confirm we haven't missed anything before finalizing our analysis.

## What We've Checked
- Finbas: prices, volume, market cap
- LSEG/Refinitiv: accounting fundamentals, book values, cash flows, etc.
- Own calculations: Fama-French factors for Swedish market

## Potential Missing Categories
Based on Table 1 in the paper, we're likely missing (if available for Swedish stocks):
- More detailed accruals and quality metrics
- R&D and advertising data
- Analyst coverage/forecasts
- Actual bid-ask spreads and microstructure data
- More detailed investment measures

But we don't know if these are even available for Swedish stocks or worth pursuing.

## Attached
- This summary
- table2_alphas.csv - Our alpha results showing the model works

Any guidance appreciated - even just confirmation that 19 characteristics is reasonable for the Swedish market given data availability.

Thanks,
Michael Brusis & Erik Jin
