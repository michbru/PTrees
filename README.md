# P-Tree Analysis - Swedish Stock Market

**Bachelor Thesis Project:** Implementation of Cong et al. (2024) "Growing the Efficient Frontier on Panel Trees" (*Journal of Financial Economics*) on Swedish stock market data (1997-2022).

**Status:** ✅ Complete Analysis with Robustness Checks

---

## 📊 Key Results Summary

### Rolling Window Analysis (Most Robust)
- **Sharpe Ratio:** 4.60 (120 out-of-sample months, 2002-2021)
- **Annual Return:** 36.77% gross, **27.8% net** (after transaction costs)
- **Stability:** Positive in all 10 test windows (100% success rate)
- **Verdict:** Strong and consistent out-of-sample performance

### Single Split Analysis
| Scenario | Type | Period | Sharpe | CAPM Alpha | After TC |
|----------|------|--------|--------|------------|----------|
| **A: Full Sample** | In-Sample | 1997-2020 | 2.74 | 21.84% | ~13% |
| **B: Forward Split** | OOS | 2010-2020 | 1.69 | 6.63% | **-1.2%** ❌ |
| **C: Reverse Split** | OOS | 1997-2010 | 3.11 | 40.84% | ~30% |

**Key Finding:** Strong regime dependence - performance varies significantly across time periods. Rolling window analysis provides most robust evidence of profitability.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ with pandas, numpy, statsmodels
- R 4.0+ with PTree package installed
- Datasets in `data/` folder

### Run Complete Analysis
```bash
# Data preparation
python src/1_prepare_data.py

# Train P-Tree models (3 scenarios)
Rscript src/2_ptree_analysis.R

# Benchmark analysis
python src/3_benchmark_analysis.py

# Robustness checks
python src/5_transaction_cost_analysis.py
python src/6_subperiod_analysis.py
Rscript src/7_rolling_window_ptree.R
python src/8_visualize_rolling_window.py
```

**Estimated Runtime:** 25-30 minutes total

---

## 📁 Project Structure

```
PTrees/
├── README.md                          # This file
├── data/
│   ├── ptrees_final_dataset.csv      # Swedish stock data (101,445 obs)
│   ├── macro_variables_with_dates.csv # Risk-free rate & Fama-French factors
│   └── FamaFrench2020/               # FF3/FF4 factor data
├── src/
│   ├── 1_prepare_data.py             # Data preparation & cross-sectional ranking
│   ├── 2_ptree_analysis.R            # P-Tree training (3 scenarios)
│   ├── 3_benchmark_analysis.py       # CAPM/FF3/FF4 benchmark regressions
│   ├── 4_rolling_window_analysis.py  # Rolling window setup
│   ├── 5_transaction_cost_analysis.py # Net returns after costs
│   ├── 6_subperiod_analysis.py       # Performance by regime
│   ├── 7_rolling_window_ptree.R      # Rolling window P-Trees (most robust)
│   └── 8_visualize_rolling_window.py # Visualizations
├── results/
│   ├── cross_scenario_comparison.csv # Main results table
│   ├── ptree_scenario_a_full/        # Full sample (1997-2022)
│   ├── ptree_scenario_b_split/       # Forward split (train 1997-2009, test 2010-2020)
│   ├── ptree_scenario_c_reverse/     # Reverse split (train 2010-2022, test 1997-2010)
│   └── robustness_checks/
│       ├── rolling_window_ptree_results.csv
│       ├── transaction_cost_analysis.csv
│       ├── subperiod_analysis.csv
│       └── plots/
├── notebooks/
│   ├── data_preprocessing.ipynb      # Data exploration & macro variable construction
│   └── README.md                     # Notebook documentation
└── docs/
    └── pdfs/
        ├── Bachelor_Thesis_SSE.pdf
        ├── Bachelor_Thesis_SSE_Midterm_Presentation.pdf
        └── trees.pdf                 # Cong et al. (2024) reference paper
```

---

## 🎯 Methodology

### Three P-Tree Scenarios (Following Cong et al. 2024)

| Scenario | Training Period | Test Period | Purpose |
|----------|----------------|-------------|---------|
| **A: Full Sample** | 1997-2022 (311 months) | N/A | Baseline (in-sample) |
| **B: Forward Split** | 1997-2009 (155 months) | 2010-2020 (127 months) | Realistic OOS test |
| **C: Reverse Split** | 2010-2022 (156 months) | 1997-2010 (148 months) | Academic robustness check |

**Notes:**
- Scenario B tests realistic forward prediction (most important for practice)
- Scenario C tests reverse prediction (academic interest only)
- Benchmark analysis limited to 2020-07 (Fama-French data availability)

### Rolling Window Analysis (Most Robust Test)

- **Method:** Expanding training windows with sequential 12-month test periods
- **Configuration:** Minimum 60 months training, step forward 12 months
- **Total windows:** 10 non-overlapping test periods
- **OOS months:** 120 (2002-2021)
- **Advantage:** More conservative than single split, reduces period-specific bias

### Parameter Scaling for Market Size

**Critical Implementation Detail:** Parameters must be scaled for market size.

```
US Market: ~2,500 stocks → min_leaf_size = 20
Swedish Market: ~300 stocks → min_leaf_size = 3

Formula: (Swedish stocks / US stocks) × US parameter
Calculation: (300 / 2,500) × 20 = 2.4 ≈ 3 (conservative)
```

**Other Parameters:**
- `max_depth = 10` (same as US paper)
- `num_iter = 9` (boosting iterations)
- `lambda_cov = 1e-4` (covariance regularization)
- `num_cutpoints = 4` (split point candidates)

---

## 📈 Detailed Results

### Scenario A: Full Sample (In-Sample)
- **Period:** 1997-09 to 2020-07 (275 months)
- **Sharpe Ratio:** 2.74
- **CAPM Alpha:** 21.84% (t = 9.92, p < 0.001)
- **FF3 Alpha:** 21.78% (t = 9.82, p < 0.001)
- **Interpretation:** Strong baseline, but optimistic (uses all data)

### Scenario B: Forward Split (True OOS)
- **Train:** 1997-2009 | **Test:** 2010-2020
- **Sharpe Ratio:** 1.69 (OOS)
- **CAPM Alpha:** 6.63% (t = 4.65, p < 0.001)
- **Gross Return:** 7.81% per year
- **Net Return (after costs):** -1.19% per year ❌
- **Interpretation:** Weak forward prediction, unprofitable after realistic transaction costs

### Scenario C: Reverse Split (Academic OOS)
- **Train:** 2010-2022 | **Test:** 1997-2010
- **Sharpe Ratio:** 3.11 (OOS)
- **CAPM Alpha:** 40.84% (t = 8.82, p < 0.001)
- **Gross Return:** 38.69% per year
- **Net Return (after costs):** 29.69% per year ✅
- **Interpretation:** Exceptional but not implementable (requires future data to train)

### Rolling Window (Most Robust)
- **Aggregate Sharpe:** 4.60
- **Mean Return:** 36.77% per year
- **Net Return (after TC):** 27.8% per year ✅
- **Stability:** 10/10 windows positive
- **Sharpe Range:** 3.08 to 10.25
- **Interpretation:** Strong evidence of robust out-of-sample performance

---

## 💰 Transaction Cost Analysis

### Assumptions
- **Bid-ask spread:** 30-50 bps
- **Commissions:** 10-20 bps
- **Market impact:** 10-30 bps
- **Total:** 50-100 bps per trade
- **Turnover:** 50-150% monthly (100% baseline)

### Results (Medium Scenario: 75 bps, 100% turnover)

| Scenario | Gross Return | Cost Drag | Net Return | Verdict |
|----------|--------------|-----------|------------|---------|
| Scenario A | 21.5% | -9.0% | 12.5% | Profitable |
| **Scenario B** | 7.8% | -9.0% | **-1.2%** | ❌ **Unprofitable** |
| Scenario C | 38.7% | -9.0% | 29.7% | ✅ Profitable |
| **Rolling Window** | 36.8% | -9.0% | **27.8%** | ✅ **Profitable** |

**Key Insight:** Transaction costs eliminate profits in forward single split but rolling window remains highly profitable.

---

## 🔍 Regime Dependence Analysis

### Subperiod Performance (Scenario A)

| Period | Regime | Sharpe | Alpha | Observation |
|--------|--------|--------|-------|-------------|
| 1997-2000 | Dot-com Boom | 3.33 | 27.5% | Strong |
| 2001-2003 | **Dot-com Bust** | **3.87** | **43.7%** | **Best** |
| 2004-2007 | Pre-Crisis | 3.34 | 20.5% | Strong |
| 2008-2009 | Financial Crisis | 1.88 | 23.2% | Weakest (still positive) |
| 2010-2014 | Post-Crisis | 2.89 | 13.6% | Moderate |
| 2015-2020 | Late Expansion | 2.60 | 12.9% | Moderate (declining) |

**Finding:** Performance declines over time from 43.7% (2001-2003) → 12.9% (2015-2020). Model excels during crisis periods.

---

## ✅ Implementation Validation

### Correctness Checks
- ✅ **No look-ahead bias:** All characteristics properly lagged
- ✅ **Clean temporal split:** Zero overlap between train/test periods
- ✅ **Proper value-weighting:** Uses lagged market cap (`lag_me`)
- ✅ **Cross-sectional ranking:** Percentile ranks computed within each month
- ✅ **Parameter scaling:** Correctly adjusted for market size
- ✅ **OOS prediction:** True out-of-sample using `predict()` function
- ✅ **Statistical calculations:** Sharpe ratios and alphas manually verified

### Data Quality
- **Total observations:** 101,445
- **Stocks:** 883 unique (avg 326 per month)
- **Missing values:** 0% in critical columns
- **Extreme returns:** 1.22% with |return| > 50% (normal for small stocks)
- **Date range:** 1997-02 to 2022-12 (311 months)

---

## 📚 Data Description

### Swedish Stock Market Data
- **Source:** Finbas, LSEG/Refinitiv
- **Period:** 1997-2022
- **Stocks:** ~300 per month on average
- **Observations:** 101,445 stock-month observations

### 19 Stock Characteristics

| Category | Features |
|----------|----------|
| **Size** | Market capitalization |
| **Value** | Book-to-market, E/P, CF/P, S/P, Price-to-assets |
| **Momentum** | 12-month momentum, 1-month return |
| **Volatility** | 12-month volatility |
| **Profitability** | ROA, Gross profitability, CFO-to-assets |
| **Growth** | Sales growth, Asset growth |
| **Investment** | Capex-to-assets, Asset turnover |
| **Leverage** | Debt-to-equity |
| **Quality** | Asset quality |
| **Trading** | Share turnover |

---

## 🎓 Key Contributions

1. **First application of P-Trees to non-US market**
   - Successfully adapts methodology to smaller market
   - Demonstrates parameter scaling approach

2. **More rigorous testing than original paper**
   - Rolling window analysis (not in original paper)
   - Transaction cost analysis with realistic assumptions
   - Subperiod regime analysis

3. **Important empirical finding**
   - **Regime dependence matters more than market size**
   - Strong performance in crisis periods, weaker in calm periods
   - ML strategies can work in small markets during appropriate regimes

4. **Honest reporting of mixed results**
   - Forward OOS weak (but still significant)
   - Rolling window strong (most robust test)
   - Clear discussion of limitations and regime dependence

---

## 📖 References

**Original Paper:**
Cong, L. W., Feng, G., He, J., & He, X. (2024). Growing the efficient frontier on panel trees. *Journal of Financial Economics*, forthcoming.

**Implementation:**
- PTree R package (Cong et al., 2024)
- Replication materials adapted for Swedish market

---

## 📝 Citation

If you use this code or findings, please cite:

```
[Your Name] (2025). P-Tree Analysis on Swedish Stock Market.
Bachelor Thesis, Stockholm School of Economics.
Implementation of Cong et al. (2024) "Growing the Efficient Frontier on Panel Trees."
```

---

**Last Updated:** 2025-11-09
**Status:** ✅ Analysis Complete with Full Robustness Checks
**Main Finding:** P-Trees show strong rolling window performance (Sharpe 4.60, net 27.8% after costs) but with significant regime dependence
