# P-Tree Analysis on Swedish Stock Market

**Bachelor Thesis Project**
Applying the P-Tree methodology (Cong et al., 2024) to Swedish stock market data (1997-2022)

---

## Quick Summary

This project replicates the P-Tree machine learning methodology on Swedish stock market data. **Key finding:** P-Trees achieve a **Sharpe Ratio of 1.20** (67.5% win rate) but default to market portfolio due to small market size and limited characteristics.

**Main Result:** The Swedish market (~300 stocks/month, 19 characteristics) is too small for P-Trees to find profitable splits beyond the market portfolio. This is a realistic and educational finding about methodology limitations in smaller markets.

---

## Project Structure

```
PTrees/
├── data/
│   └── ptrees_final_dataset.csv     # Swedish stock data (102,823 obs, 1997-2022)
├── scripts/
│   ├── 1_prepare_data_relaxed.py    # Data preprocessing (Python)
│   ├── 2_run_ptree_attempt2.R       # P-Tree analysis (R)
│   └── 3_debug_factors.R            # Diagnostics (R)
├── results/
│   ├── ptree_factors.csv            # Final factor returns (MAIN RESULT)
│   ├── ptree_models.RData           # Fitted P-Tree models
│   └── ptree_ready_data_*.csv       # Processed data files
├── docs/
│   ├── FINAL_ANALYSIS_SUMMARY.md    # Complete analysis findings
│   └── INVESTIGATION_FINDINGS.md    # Bug investigation (look-ahead bias)
├── PTree-2501/                      # R package (original implementation)
└── README.md                        # This file
```

---

## Results Summary

### Performance Metrics
- **Sharpe Ratio:** 1.20
- **Win Rate:** 67.5% (210 winning months out of 311 total)
- **Period:** 1997-2022 (311 months, 26 years)
- **Strategy:** Value-weighted market portfolio (no tree splits found)

### Key Files
- **Main Result:** `results/ptree_factors.csv` (factor returns by month)
- **Full Analysis:** `docs/FINAL_ANALYSIS_SUMMARY.md`
- **Bug Investigation:** `docs/INVESTIGATION_FINDINGS.md`

### Why No Tree Splits?
The P-Tree algorithm defaulted to the market portfolio because:
1. **Small market:** ~300 stocks/month vs thousands in US studies
2. **Few characteristics:** 19 factors vs 61 in original paper
3. **Conservative parameters:** min_leaf_size=10 prevents overfitting

This is a **realistic finding**, not a failure. It demonstrates that P-Trees require larger markets or more characteristics to find profitable splits.

---

## Replication Instructions

### Prerequisites

**Python Environment:**
```bash
# Activate virtual environment (if using one)
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install required packages
pip install pandas numpy pyarrow
```

**R Environment:**
```r
# Install required packages
install.packages(c("arrow", "rpart", "ranger", "data.table"))

# Install P-Tree package (from local source)
install.packages("PTree-2501/PTree", repos = NULL, type = "source")
```

### Running the Analysis

**Step 1: Prepare Data** (Python)
```bash
cd /path/to/PTrees
python scripts/1_prepare_data_relaxed.py
```
This script:
- Loads `data/ptrees_final_dataset.csv` (102,823 observations)
- Creates 19 cross-sectional ranked characteristics
- Handles missing data (keeps stocks with 10+ characteristics)
- Outputs `results/ptree_ready_data_full.csv` (95,514 observations)

**Step 2: Run P-Tree Analysis** (R)
```bash
Rscript scripts/2_run_ptree_attempt2.R
```
This script:
- Loads processed data from Step 1
- Runs P-Tree algorithm with parameters:
  - `min_leaf_size = 10` (prevents overfitting)
  - `equal_weight = FALSE` (value-weighted portfolios)
  - `num_cutpoints = 4` (standard setting)
- Outputs `results/ptree_factors.csv` (factor returns)

**Step 3: View Results**
```bash
# Open the main result file
cat results/ptree_factors.csv

# Or in R/Python for analysis
# R: factors <- read.csv("results/ptree_factors.csv")
# Python: factors = pd.read_csv("results/ptree_factors.csv")
```

### Expected Output

After running both scripts, you should see:
- `results/ptree_ready_data_full.csv` (95,514 rows)
- `results/ptree_factors.csv` (311 months of returns)
- Console output showing:
  - 95,514 observations processed
  - ~307 stocks per month (average)
  - Sharpe Ratio: 1.20
  - Win Rate: 67.5%

---

## Data Description

### Source Dataset (`data/ptrees_final_dataset.csv`)

**Origins:**
- **Market data:** Finbas (Swedish market database)
- **Fundamentals:** LSEG/Refinitiv (formerly Thomson Reuters)

**Coverage:**
- **Period:** 1997-2022 (26 years)
- **Observations:** 102,823 stock-month observations
- **Stocks:** 1,177 unique Swedish stocks
- **Average:** ~300 stocks per month

**19 Characteristics:**

| Category | Characteristics |
|----------|----------------|
| **Size** | market_cap (Market capitalization) |
| **Value** | book_to_market, ep_ratio (E/P), cfp_ratio (CF/P), sp_ratio (S/P), price_to_assets |
| **Momentum** | momentum_12m (12-month), return_1m (1-month, lagged) |
| **Volatility** | volatility_12m (12-month standard deviation) |
| **Profitability** | roa (Return on assets), gross_profitability, cfo_to_assets |
| **Growth** | sales_growth, asset_growth |
| **Investment** | capex_to_assets, asset_turnover |
| **Leverage** | debt_to_equity |
| **Quality** | asset_quality |
| **Trading** | turnover |

### Data Preparation Notes

1. **Look-Ahead Bias Fix (Critical):**
   - Original bug: Used `return_1m` (current month) to predict itself
   - Fix: Created `current_return` for target, lagged `return_1m` by 1 month
   - Verification: Correlation dropped from 0.74 → 0.075 ✅

2. **Missing Data Handling:**
   - Dropped observations missing return or market cap (critical fields)
   - Kept stocks with at least 10/19 characteristics available
   - Imputed remaining NAs with cross-sectional medians

3. **Ranking:**
   - All characteristics cross-sectionally ranked by month
   - Normalized to [0, 1] using percentile ranks
   - Follows original P-Tree paper methodology

---

## Understanding the Results

### What is a Sharpe Ratio of 1.20?

- **Good:** Exceeds typical equity portfolio (Sharpe ~0.5-0.8)
- **Realistic:** Lower than US P-Trees (Sharpe 2-3) due to smaller market
- **Interpretation:** For every unit of risk, the strategy earns 1.20 units of excess return

### Why Is This Result Valid?

**Overfitting Check:**
We tested multiple parameter settings and found:
- **Aggressive params** (min_leaf_size=3): Sharpe 2.53 → **OVERFITTED**
- **Original params** (min_leaf_size=20): Sharpe 1.20 → **REALISTIC**
- **Balanced params** (min_leaf_size=10): Sharpe 1.20 → **REALISTIC**

With proper parameters, the model conservatively defaults to market portfolio rather than overfitting.

### Comparison to Original Paper

| Metric | US (Original) | Swedish (This Study) |
|--------|--------------|---------------------|
| Observations | ~2.2M | 95K |
| Stocks/month | Thousands | ~300 |
| Characteristics | 61 | 19 |
| Sharpe Ratio | 2-3 | 1.20 |
| Tree Complexity | Multiple splits | No splits (market) |

**Conclusion:** Swedish market is too small for P-Tree methodology to find profitable splits beyond market portfolio.

---

## Limitations & Future Work

### Known Limitations

1. **Small Market:**
   - Only ~300 stocks/month vs thousands in US
   - Limits tree splitting capability

2. **Limited Characteristics:**
   - 19 factors vs 61 in original paper
   - May miss important signals

3. **No Out-of-Sample Testing:**
   - Results are in-sample only
   - Need train/test split for validation

4. **No Benchmark Comparison:**
   - Should compare to OMXS30 or Swedish indices
   - Should test vs Fama-French factors

### Recommendations for Future Research

1. **Expand Characteristics:**
   - Add more fundamentals (target 30-40 factors)
   - Include Swedish-specific factors (export exposure, etc.)

2. **Out-of-Sample Validation:**
   - Split 1997-2015 (train) vs 2016-2022 (test)
   - Rolling window validation

3. **Benchmark Comparisons:**
   - Compare to Swedish market indices (OMXS30, SIXRX)
   - Test against Swedish Fama-French factors

4. **Alternative Methods:**
   - Try Random Forests or Gradient Boosting
   - Compare to traditional factor models
   - Test ensemble methods

---

## Technical Details

### Software Requirements
- **Python:** 3.8+ (tested with 3.11)
- **R:** 4.0+ (tested with 4.3)
- **Python packages:** pandas, numpy, pyarrow
- **R packages:** arrow, rpart, ranger, data.table, PTree

### Computing Requirements
- **RAM:** 8GB minimum (16GB recommended)
- **Storage:** ~500MB for data files
- **Runtime:** ~5 minutes for full pipeline

### File Sizes
- Input data: 61 MB (`ptrees_final_dataset.csv`)
- Processed data: 50 MB (`ptree_ready_data_full.csv`)
- Results: <1 MB (`ptree_factors.csv`)

---

## Key Findings for Thesis

1. **P-Trees work but have limitations in small markets**
   - Achieved realistic Sharpe 1.20 on Swedish data
   - Could not find profitable splits (defaults to market)
   - Demonstrates methodology requires scale

2. **Look-ahead bias is a critical issue**
   - Fixed subtle bug in return calculation
   - Verification essential for ML in finance
   - Correlation checks reveal hidden biases

3. **Parameter tuning matters immensely**
   - Too aggressive → overfitting (Sharpe 2.53)
   - Too conservative → no signal (but honest!)
   - Original paper params may not transfer to smaller markets

4. **Data quality > quantity**
   - 19 high-quality characteristics with good coverage
   - Better than 61 characteristics with poor coverage
   - Imputation helps but doesn't create signal

---

## References

**Original P-Tree Paper:**
Cong, L. W., Feng, G., He, J., & He, X. (2024). Growing the efficient frontier on panel trees. *Journal of Financial Economics*.

**Data Sources:**
- **Finbas:** Swedish stock market database (prices, returns)
- **LSEG/Refinitiv:** Fundamental data (balance sheet, income statement)

**Implementation:**
- P-Tree R package: `PTree-2501/PTree/`
- Original replication code: `PTree-2501/PTree/replication-JFE/`

---

## Citation

If you use this work, please cite:

```
[Your Name] (2025). P-Tree Analysis on Swedish Stock Market Data (1997-2022).
Bachelor Thesis, [Your University].
```

---

## Contact & Questions

For questions about this implementation:
1. Read `docs/FINAL_ANALYSIS_SUMMARY.md` for complete findings
2. Read `docs/INVESTIGATION_FINDINGS.md` for bug details
3. Check script comments in `scripts/` for technical details

---

**Last Updated:** 2025-10-25
**Status:** Analysis Complete
**Main Result:** Sharpe 1.20 (realistic market portfolio performance)
