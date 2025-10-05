# Final P-Tree Analysis - Swedish Stock Market

**Results:** Sharpe Ratio 1.20, Win Rate 67.5% (1997-2022)

This folder is **completely self-contained** - everything needed to run and understand the analysis is here.

---

## Structure

```
final_ptree_analysis/
├── README.md                    # This file
├── data/
│   └── ptrees_final_dataset.csv         # Input data (102,823 obs)
├── scripts/
│   ├── 1_prepare_data_relaxed.py        # Step 1: Prepare for P-Tree
│   └── 2_run_ptree_attempt2.R           # Step 2: Run P-Tree
├── results/
│   ├── ptree_ready_data.feather         # Prepared data (95,514 obs)
│   ├── ptree_ready_data_full.csv        # Same as above (CSV)
│   ├── ptree_factors.csv                # ⭐ FINAL RESULTS
│   └── ptree_models.RData               # Fitted models
└── diagnostics/
    └── (debugging scripts)
```

---

## Quick Start

### Run the Analysis

```bash
# Navigate to scripts folder
cd scripts

# Step 1: Prepare data for P-Tree
python 1_prepare_data_relaxed.py

# Step 2: Run P-Tree
Rscript 2_run_ptree_attempt2.R
```

**Output:** `results/ptree_factors.csv`

---

## Data Flow

```
data/ptrees_final_dataset.csv (102,823 obs)
        ↓
[1_prepare_data_relaxed.py]
    - Filters stocks with 10+ characteristics
    - Cross-sectional ranking
    - Imputes missing values
        ↓
results/ptree_ready_data_full.csv (95,514 obs)
        ↓
[2_run_ptree_attempt2.R]
    - Trains 3 P-Trees with boosting
    - Parameters: min_leaf_size=10, value-weighted
        ↓
results/ptree_factors.csv (311 months)
```

---

## Results

### Final Performance
- **Sharpe Ratio:** 1.20
- **Win Rate:** 67.5% (210/311 positive months)
- **Monthly Return:** 1.89% (mean), 5.46% (std)
- **Max Drawdown:** -48.14%
- **Period:** Feb 1997 - Dec 2022

### Tree Structure
- **Leaf Nodes:** 1 (NO SPLITS)
- **Interpretation:** Returns value-weighted market portfolio
- **Why?** Insufficient data for tree to find profitable splits

---

## Key Parameters

### P-Tree Settings (in 2_run_ptree_attempt2.R)
```R
min_leaf_size = 10          # Minimum stocks per leaf
num_cutpoints = 4           # Number of split candidates
equal_weight = FALSE        # Value-weighted portfolio
max_depth = 10              # Tree depth limit
num_iter = 9                # Training iterations
```

### Data Preparation (in 1_prepare_data_relaxed.py)
- **Min characteristics:** 10/19 required per stock
- **Missing values:** Imputed with cross-sectional median
- **Ranking:** Cross-sectional [0,1] normalization

---

## Input Data

### ptrees_final_dataset.csv
- **Observations:** 102,823
- **Period:** 1997-2022
- **Sources:** Finbas (prices) + LSEG (fundamentals)
- **Characteristics:** 19 total

**Characteristics:**
1. return_1m, return_3m, return_6m, return_12m (momentum)
2. volatility_1m
3. market_cap, pb_ratio, pe_ratio, peg_ratio
4. roe, roa, profit_margin
5. debt_to_equity, current_ratio, quick_ratio
6. asset_turnover, dividend_yield
7. revenue_growth, earnings_growth

**Critical:** `current_return` = target variable (properly lagged, no look-ahead bias)

---

## Why Sharpe 1.20?

### Tree Made No Splits Because:
1. **Small market:** ~300 stocks/month (vs 2000+ in US)
2. **Few characteristics:** 19 (vs 61 in original paper)
3. **Conservative parameters:** min_leaf_size=10 prevents overfitting

**This is realistic!** P-Trees need large cross-sections and many features to find profitable strategies. With Swedish data, the optimal strategy is the market portfolio.

---

## Comparison to Old Analysis

| Aspect | Old (Overfitted) | Final (This) |
|--------|------------------|--------------|
| min_leaf_size | 3 | 10 |
| equal_weight | TRUE | FALSE |
| num_cutpoints | 10 | 4 |
| Sharpe Ratio | 2.53 | 1.20 |
| Tree splits | 5-6 leaves | 1 leaf (no splits) |
| Assessment | Too good to be true | Realistic |

---

## Files Explained

### Scripts
- **1_prepare_data_relaxed.py** - Converts raw data to P-Tree format
- **2_run_ptree_attempt2.R** - Trains P-Trees using PTree R package

### Data
- **data/ptrees_final_dataset.csv** - Input (merged Finbas + LSEG)
- **results/ptree_ready_data_full.csv** - After filtering/ranking
- **results/ptree_factors.csv** - Final monthly factor returns ⭐

### Results
- **ptree_factors.csv** - 311 monthly returns (factor1, factor2, factor3)
- **ptree_models.RData** - Fitted models for R inspection

---

## Requirements

### Python
- pandas, numpy, pyarrow (for feather)
- Python 3.8+

### R
- PTree package
- R 4.0+

### Installation
```bash
# Python packages
pip install pandas numpy pyarrow

# R package (requires compilation)
R CMD INSTALL /path/to/PTree
```

---

## Important Notes

### Look-Ahead Bias Fix
✅ The `current_return` variable is properly constructed:
- Uses `t-1` to `t` return as target
- All characteristics use `t-2` data (lagged)
- Correlation between rank_mom1m and xret: 0.075 (correct!)

### Self-Contained
✅ This folder contains EVERYTHING needed:
- Input data (`data/`)
- Processing scripts (`scripts/`)
- Final results (`results/`)
- No external dependencies on parent folders

### Validation
✅ Results validated:
- 2008 crisis shows realistic losses (5 negative months in crisis period)
- Win rate 67.5% (reasonable for equity portfolio)
- Sharpe 1.20 (consistent with market portfolio)

---

## Citation

If using these results, cite:
- Original P-Tree paper: Cong et al. (2024)
- Swedish data: Finbas + LSEG Refinitiv
- Analysis period: February 1997 - December 2022

---

## Contact

For questions about replication or methodology, see:
- This README for technical details
- Parent folder `../docs/` for complete analysis summary
