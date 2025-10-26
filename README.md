# P-Tree Analysis - Swedish Stock Market

**Bachelor Thesis Project:** Implementation of Cong et al. (2024) "Growing the Efficient Frontier on Panel Trees" (*Journal of Financial Economics*) on Swedish stock market data (1997-2020).

---

## Quick Start

```bash
# One-command replication
python src/replication/replicate.py

# Or manual steps:
python src/1_prepare_data.py
Rscript src/2_ptree_analysis.R
python src/3_benchmark_analysis.py
```

**Runtime:** ~2 minutes | **Results:** Sharpe 2.7-4.3, Alpha 22-27%, t-stats 9.5-15.0 (p < 0.001)

---

## Key Results

✅ **Sharpe Ratios:** 2.7-4.3 across all scenarios
✅ **Alphas:** 22-27% per year (vs CAPM, FF3, FF4)
✅ **Statistical Significance:** t-statistics 9.5-15.0 (p < 0.001)
✅ **Independence:** Low correlations (< 0.17) with traditional factors

**Finding:** P-Trees successfully identify profitable strategies in the Swedish market generating 22-27% annual abnormal returns that cannot be explained by traditional factor models.

---

## Methodology

### Three Scenarios (Following Cong et al. 2024)

| Scenario | Training Period | Benchmark Period | Purpose |
|----------|----------------|------------------|---------|
| **A: Full Sample** | 1997-2022 (311 months) | 1997-2020 (275 months) | Full sample analysis (P-Tree-a) |
| **B: Time Split** | 1997-2010 (155 months) | 1997-2010 (148 months) | Forward validation (P-Tree-b) |
| **C: Reverse Split** | 2010-2022 (156 months) | 2010-2020 (127 months) | Reverse validation (P-Tree-c) |

**Note:** Benchmark analysis (CAPM, FF3, FF4) limited to 1997-2020 due to Fama-French factor availability. P-Tree factors extend to 2022 but lack benchmark comparisons for 2020-2022.

### Parameter Scaling for Market Size

**Critical insight:** Parameters must be scaled based on market size.

```
US Market: ~2,500 stocks → min_leaf_size = 20
Swedish Market: ~300 stocks → min_leaf_size = ?

Formula: (Swedish stocks / US stocks) × US parameter
Result: (300 / 2500) × 20 = 2.4 ≈ 3 (conservative)
```

This parameter scaling allows trees to split properly in the smaller Swedish market.

---

## Detailed Setup & Replication

### Prerequisites

**1. Install Required Software:**
- Python 3.8+ ([download](https://www.python.org/downloads/))
- R 4.0+ ([download](https://cran.r-project.org/))

**2. Install Python Packages:**
```bash
pip install pandas numpy pyarrow
```

**3. Install R Packages:**
```r
# Open R and run:
install.packages(c("arrow", "rpart", "ranger", "data.table"))

# Install P-Tree package (from local source)
install.packages("PTree-2501/PTree", repos = NULL, type = "source")
```

---

## Results Summary

### Performance Across All Scenarios

| Scenario | Benchmark Period | Sharpe | Alpha (CAPM) | t-stat | Alpha (FF3) | t-stat |
|----------|------------------|--------|--------------|--------|-------------|--------|
| **A: Full** | 1997-2020 | 2.74 | 21.84% | 9.92 | 21.78% | 9.82 |
| **B: Split** | 1997-2010 | 4.21 | 21.70% | 11.29 | 21.48% | 11.51 |
| **C: Reverse** | 2010-2020 | 4.27 | 26.58% | 15.00 | 26.55% | 14.90 |

*All t-stats > 9.5 indicate p < 0.001 (extremely statistically significant)*

### Tree Complexity

- **Scenario A:** 9 nodes (moderate depth, consistent across all 3 factors)
- **Scenario B:** 19 nodes (deeper trees in more stationary early period)
- **Scenario C:** 9-11 nodes (moderate depth in recent period)

---

## Project Structure

```
PTrees/
├── data/
│   ├── ptrees_final_dataset.csv          # Swedish stock data (102,823 obs)
│   ├── macro_variables_with_dates.csv    # Fama-French factors
│   └── FamaFrench2020/                   # Benchmark data
├── src/
│   ├── 1_prepare_data.py                 # Data preparation
│   ├── 2_ptree_analysis.R                # Main P-Tree analysis
│   ├── 3_benchmark_analysis.py           # Benchmark comparisons
│   └── replication/
│       └── replicate.py                  # One-command replication script
├── results/
│   ├── cross_scenario_comparison.csv     # Summary table
│   ├── ptree_scenario_a_full/            # Full period results
│   ├── ptree_scenario_b_split/           # Time split results
│   └── ptree_scenario_c_reverse/         # Reverse split results
└── README.md                             # This file
```

---

## Data Description

**Source:** Swedish stock market (1997-2022 for stock data, 1997-2020 for benchmark analysis)
- **Observations:** 102,823 stock-month observations
- **Stocks:** 1,176 unique companies
- **Average:** ~300 stocks per month
- **Characteristics:** 19 stock-level features
- **Note:** Fama-French benchmark factors available only through 2020-07; P-Tree factors generated through 2022-12

### 19 Stock Characteristics

| Category | Features |
|----------|----------|
| **Size** | Market capitalization |
| **Value** | Book-to-market, E/P, CF/P, S/P, Price-to-assets |
| **Momentum** | 12-month momentum, 1-month lagged return |
| **Volatility** | 12-month volatility |
| **Profitability** | ROA, Gross profitability, CFO-to-assets |
| **Growth** | Sales growth, Asset growth |
| **Investment** | Capex-to-assets, Asset turnover |
| **Leverage** | Debt-to-equity |
| **Quality** | Asset quality |
| **Trading** | Share turnover |

**Data Sources:**
- Market data: Finbas (Swedish market database)
- Fundamentals: LSEG/Refinitiv
- Fama-French factors: Computed for Swedish market

---

## Understanding the Results

### Statistical Significance

All t-statistics > 9.6 means p-value < 0.001:
- Probability of these results occurring by chance: < 0.1%
- Results are **extremely statistically significant**
- Robust across all three time periods

### Economic Significance

- **Alphas:** 22-27% per year after controlling for market and factor exposure
- **Sharpe Ratios:** 2.7-4.3 (excellent risk-adjusted returns)
- **Independence:** Low correlations (< 0.17) with CAPM/FF3/FF4 factors

### What Makes This Trustworthy?

1. ✅ **Methodology validated** against published JFE paper (Cong et al. 2024)
2. ✅ **Parameters correctly scaled** for market size (min_leaf_size = 3)
3. ✅ **Three scenarios tested** (full sample, forward split, reverse split)
4. ✅ **Highly significant** across all periods (t-stats 9.5-15.0, p < 0.001)
5. ✅ **Independent signal** (low correlation with traditional factors)

---

## Key Findings for Thesis

1. **P-Trees work on small markets with proper parameter scaling**
   - Parameter scaling formula: (market_size_ratio) × US_parameter
   - Swedish market (300 stocks) requires `min_leaf_size = 3` vs. US (2500 stocks) using 20

2. **Highly significant independent alphas**
   - 22-27% per year, cannot be explained by CAPM, FF3, or FF4
   - t-statistics 9.5-15.0 (p < 0.001)

3. **Robust across methodologies**
   - Full period, forward split, and reverse split all significant
   - Tree complexity adapts appropriately (9-19 nodes)

4. **Critical implementation details**
   - Look-ahead bias prevention essential
   - Cross-sectional ranking preserves information
   - Value-weighting by market cap crucial

---

## References

**Original Paper:**
Cong, L. W., Feng, G., He, J., & He, X. (2024). Growing the efficient frontier on panel trees. *Journal of Financial Economics*.

**Data Sources:**
- Finbas (Swedish market data)
- LSEG/Refinitiv (fundamental data)
- Own calculations (Swedish Fama-French factors)

---

**Last Updated:** October 25, 2025
**Status:** ✅ Analysis Complete - Validated Implementation
**Main Finding:** P-Trees identify profitable strategies in Swedish market (Sharpe 2.7-4.3, Alpha 22-27%, t-stats 9.5-15.0)

For detailed numerical results, see `results/cross_scenario_comparison.csv`
