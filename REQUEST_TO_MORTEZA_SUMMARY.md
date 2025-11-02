# P-Trees Swedish Market Analysis - Data Expansion Request
**Contact:** Swedish House of Finance, Department of Finance
**Date:** February 2025
**Project:** Implementation of P-Trees Methodology for Swedish Equity Market

---

## 1. Project Overview

I am implementing the P-Trees methodology from **Cong, L. W., Feng, G., He, J., & He, X. (2024). "Growing the Efficient Frontier on Panel Trees." Journal of Financial Economics** for the Swedish equity market.

**Current Implementation:**
- **Dataset:** Swedish stocks from Finbas and LSEG/Refinitiv (1997-2022)
- **Sample Size:** 102,823 stock-month observations, ~300 stocks per month
- **Characteristics:** 19 firm-level characteristics (vs. 61 in original US paper)
- **Macro Variables:** Swedish Fama-French factors, market returns, inflation
- **Methodology:** Fully replicated including parameter scaling for smaller Swedish market

---

## 2. Current Data Setup

### 2.1 The 19 Characteristics Currently Used

| Category | Characteristics |
|----------|----------------|
| **Size** | market_cap |
| **Value** | book_to_market, ep_ratio, cfp_ratio, sp_ratio, price_to_assets |
| **Momentum** | momentum_12m, return_1m |
| **Volatility** | volatility_12m |
| **Profitability** | roa, gross_profitability, cfo_to_assets |
| **Growth** | sales_growth, asset_growth |
| **Investment** | capex_to_assets, asset_turnover |
| **Leverage** | debt_to_equity |
| **Quality** | asset_quality |
| **Trading** | turnover |

**Data Processing:**
- Cross-sectional percentile ranking (0-1) applied monthly
- Missing values filled with 0.5 (median rank)
- All characteristics winsorized at 1% and 99% to reduce outlier impact

### 2.2 Macro Variables Included

| Variable | Description |
|----------|-------------|
| rm_rf | Market risk premium (Swedish market) |
| smb_ew, smb_vw | Size factor (equal & value-weighted) |
| hml_ew, hml_vw | Value factor (equal & value-weighted) |
| mom_ew, mom_vw | Momentum factor (equal & value-weighted) |
| rolling_vol_* | Market volatility measures |
| inflation | Swedish inflation rate |

**Coverage:** 1997-09 to 2020-07 (275 months)

### 2.3 Current Data Sources

| Data Type | Source | Coverage |
|-----------|--------|----------|
| Stock prices & volume | Finbas | 1997-2022 |
| Fundamentals | LSEG/Refinitiv | 1997-2022 |
| Market returns | Finbas/Calculated | 1997-2022 |
| Risk-free rate | Swedish central bank | 1997-2022 |
| Fama-French factors | Own calculations | 1997-2020 |

---

## 3. Key Results Summary

### 3.1 Main Performance Metrics

| Scenario | Description | OOS Period | Sharpe Ratio | Annual Alpha | t-stat | Profitable After Costs? |
|----------|-------------|------------|--------------|--------------|--------|------------------------|
| **A (Full)** | No train/test split | 2010-2020 | 1.20 | 6.4% | 9.51 | Yes (marginal) |
| **B (Forward)** | Traditional forward test | 2010-2020 | 1.69 | 6.6% | 9.46 | **No** (-1.2% net) |
| **C (Reverse)** | Reverse test | 1997-2010 | **3.11** | **40.8%** | 14.95 | **Yes** (strong) |
| **Rolling Window** | 10 expanding windows | Various | **4.60** | 53.2% | 15.04 | **Yes** (27.8% net) |

### 3.2 Key Findings

**Strengths:**
- ✓ Statistically significant alphas (all p-values < 0.001)
- ✓ Model works well in pre-2010 period (Sharpe 3.11)
- ✓ Rolling window approach robust (Sharpe 4.60, profitable after costs)
- ✓ Parameter scaling successful (min_leaf_size = 3 for Swedish market)

**Challenges:**
- ✗ Asymmetric performance: Excellent pre-2010 (alpha 40.8%), modest post-2010 (alpha 6.6%)
- ✗ Forward test unprofitable after transaction costs (-1.2% net return)
- ✗ Performance concentrated in crisis periods (2001-2003, 2008-2009)
- ✗ Limited to 19 characteristics (vs. 61 in original paper)

**Interpretation:** Model demonstrates statistical validity but shows regime-dependent performance, working better in higher-volatility pre-2010 period.

---

## 4. The Data Gap Problem

### 4.1 Comparison to Original Paper

| Aspect | Original US Paper | My Swedish Implementation | Gap |
|--------|------------------|---------------------------|-----|
| **Characteristics** | 61 | 19 | **-42 characteristics** |
| **Stocks per Month** | ~2,500 | ~300 | Smaller market (expected) |
| **OOS Sharpe** | ~3-4 | 1.69 (forward) | May be due to fewer features |

### 4.2 Missing Characteristic Categories

Based on typical asset pricing literature, I am likely missing:

**Accounting-Based:**
- Accruals measures (operating accruals, total accruals)
- Working capital metrics
- Net operating assets
- Asset composition variables
- Inventory/receivables turnover

**Investment & Growth:**
- R&D to sales
- Advertising expenditure
- Employee growth
- Composite issuance measures
- Net stock issuance
- Net debt issuance

**Quality Metrics:**
- Piotroski F-Score components
- Altman Z-Score
- Earnings quality measures
- Discretionary accruals

**Market Microstructure:**
- Bid-ask spreads
- Amihud illiquidity
- Price impact measures
- Order flow imbalance

**Analyst & Institutional:**
- Analyst coverage
- Analyst forecast dispersion
- Earnings surprises
- Institutional ownership
- Short interest

**Risk Measures:**
- Beta (CAPM)
- Downside beta
- Idiosyncratic volatility
- Maximum drawdown
- Skewness, kurtosis

### 4.3 Additional Data Quality Concerns

1. **Survivor Bias:** Unknown if delisted firms are included in current dataset
2. **Look-Ahead Bias:** Need to verify announcement dates for fundamentals
3. **Corporate Actions:** Limited information on splits, dividends, restructurings
4. **Actual Trading Costs:** Currently using 75bps assumption, need bid-ask spread data

---

## 5. Specific Request for Guidance

I would greatly appreciate your help with the following:

### 5.1 Primary Request: More Characteristics

**Question:** Do you know of any data sources (commercial or academic) that provide extended firm characteristics for Swedish stocks?

Specifically looking for:
- Expanded accounting/fundamental variables beyond standard Finbas/Refinitiv
- Analyst-based variables (coverage, forecasts, recommendations)
- Microstructure data (bid-ask spreads, liquidity measures)
- Alternative data sources used in Swedish asset pricing research

### 5.2 Swedish House of Finance Resources

**Question:** Are there any datasets maintained by Swedish House of Finance that might be available for academic research?

Examples:
- Extended Swedish factor models
- Curated Swedish equity databases
- Quality-checked historical data with survivor bias correction
- Industry/sector classification schemes for Swedish market

### 5.3 International Benchmark Data

**Question:** Do you recommend any specific vendors for Swedish market data that provide broader coverage than standard providers?

### 5.4 Methodological Guidance

**Question:** Given the smaller Swedish market (300 vs. 2,500 stocks), do you have suggestions for:
- Dealing with limited cross-sectional variation?
- Alternative approaches when characteristic count is limited?
- Swedish market-specific considerations for tree-based models?

---

## 6. Sample Data Structure

### 6.1 Current Dataset Format

Here's an example of my current data structure (first 3 rows):

| date | permno | market_cap | book_to_market | momentum_12m | roa | ... | rank_market_cap | rank_book_to_market | ... |
|------|--------|------------|----------------|--------------|-----|-----|-----------------|---------------------|-----|
| 1997-09 | 1001 | 5234.2 | 0.65 | 0.15 | 0.08 | ... | 0.45 | 0.72 | ... |
| 1997-09 | 1002 | 12456.8 | 0.42 | -0.05 | 0.12 | ... | 0.78 | 0.38 | ... |
| 1997-09 | 1003 | 892.1 | 1.23 | 0.08 | -0.02 | ... | 0.12 | 0.95 | ... |

**Total:** 102,823 rows × 42 columns (19 raw + 19 ranked + metadata)

### 6.2 What I Can Provide

If helpful for understanding my setup, I can share:
- Sample of processed dataset (anonymized if needed)
- List of exact Finbas/Refinitiv data fields used
- Data processing code (Python/R scripts)
- Detailed results by subperiod

---

## 7. Next Steps

I would be grateful for:
1. **Any suggestions** on data sources for expanding my characteristic set
2. **A brief discussion** if you have time (15-30 min call/meeting)
3. **Connections** to researchers who have worked with extended Swedish equity data
4. **References** to papers that have successfully built comprehensive Swedish datasets

I am flexible and happy to work with whatever guidance you can provide. Even pointers to specific vendors, databases, or prior research papers would be extremely valuable.

Thank you very much for considering this request.

---

## Appendix: Technical Details

### Parameter Scaling for Swedish Market

Following the original paper's guidance, parameters were scaled proportionally:

```
US Market: ~2,500 stocks, min_leaf_size = 20
Swedish Market: ~300 stocks, min_leaf_size = (300/2,500) × 20 = 3
```

This scaling proved successful, with the model achieving similar statistical significance to US results.

### Model Specification

- **Training:** 1997-09 to 2009-12 (forward) or 2010-01 to 2020-07 (reverse)
- **Testing:** Out-of-sample on held-out period
- **Rebalancing:** Monthly
- **Transaction Costs:** 75 basis points per trade (one-way)
- **Monthly Turnover:** ~100% (high due to tree re-estimation)

### Statistical Robustness

All alphas tested using:
- Newey-West standard errors (12-month lag)
- Multiple testing adjustment consideration (~50-100 tests)
- Subperiod analysis (2010-2015 vs. 2015-2020)
- Rolling window validation (10 expanding windows)

---

**End of Summary**
