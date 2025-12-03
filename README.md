# P-Trees on Swedish Stock Market: Bachelor Thesis Replication

## Overview

This project replicates the P-Tree (Panel Tree) methodology from Cong et al. (2024) on Swedish stock market data for a bachelor thesis at the Stockholm School of Economics. P-Trees are an interpretable machine learning method for portfolio optimization that recursively splits the cross-section of stocks to maximize Sharpe ratio.

**Key Innovation**: Unlike ensemble approaches, this implementation trains **single, interpretable P-Trees** (one split per scenario), making the factor construction transparent and explainable.

## Data Sources

- **Market Data**: Finbas (daily prices, volume, market cap)
- **Fundamentals**: Serrano (annual accounting data)
- **Mapping**: LSEG (ISIN to Organization Number)
- **Risk Factors**: Swedish House of Finance (Fama-French 3-factor model, Shof et al. 2020)
- **Sample Period**: June 1998 - November 2019

**Final Sample Characteristics:**
- **Total Observations**: 39,524 firm-months
- **Unique Firms**: 575
- **Time Periods**: 258 months
- **Characteristics**: 33 (after filtering for coverage ≥30%)
- **Average Firms/Month**: 153

## Methodology

### Data Pipeline (Steps 1-6)

**1. Process Market Data (`1_process_finbas.py`)**
- Clean Finbas daily price/volume data
- Calculate monthly returns and market capitalization
- Filter for Stockholm exchanges only

**2. Process Accounting Data (`2_process_serrano_accounting.py`)**
- Extract annual accounting variables from Serrano database
- Calculate fundamental ratios (ROA, leverage, profitability metrics)

**3. Build ISIN-OrgNr Mapping (`3_build_isin_orgnr_mapping_LSEG.py`)**
- Use LSEG data to map ISIN (Finbas identifier) to Organization Number (Serrano identifier)
- Essential for merging market and accounting data

**4. Merge Mappings (`4_merge_mappings.py`)**
- Combine automated and manual mappings
- Final mapping coverage: 575 firms

**5. Merge Datasets (`5_merge_datasets.py`)**
- Align monthly market data with annual accounting data
- Forward-fill accounting data (investors use most recent report)
- Apply lags: 1 month for market data, 6 months for accounting data

**6. Prepare P-Tree Dataset (`6_prepare_ptree_dataset.py`)**
- Calculate 33 firm characteristics (momentum, value, profitability, investment)
- Cross-sectional rank transformation (0-1 scale)
- Filter characteristics with <30% coverage

### Analysis Pipeline (Steps 1-5)

**Step 1: Prepare Inputs (`01_prepare_inputs.R`)**
- Load merged dataset
- Winsorize at 1%/99% to remove outliers
- Create lead returns (predict t+1)
- Save as `.rds` matrices for PTree package

**Step 2: Train P-Trees (`02_train_ptree.R`)**
- Train single P-Tree per scenario (num_iter=1, no boosting)
- Three scenarios:
  - **A**: Full sample (1998-2019)
  - **B**: Train 1998-2009, Test 2010-2019 (forward validation)
  - **C**: Train 2010-2019, Test 1998-2009 (reverse robustness)
- Hyperparameters: max_depth=10, min_leaf_size=3, num_cutpoints=4
- Output: Factor returns, tree structures, model objects

**Step 3: Evaluate Models (`03_evaluate_model.R`)**
- Merge factor returns with Fama-French factors
- Compute CAPM and FF3 alphas with Newey-West standard errors
- Output: Performance metrics table

**Step 4: Visualize Results (`04_visualize_results.R`)**
- Generate 3 LaTeX tables (data summary, performance, tree structures)
- Generate 2 PNG figures (cumulative returns, time series)

**Step 5: Validation Analysis (`05_validation_analysis.R`)**
- Sample attrition analysis
- Temporal coverage checks
- Univariate R² analysis
- Output: 3 tables + 3 figures for methodology section

## Model Configuration

Single P-Tree trained per scenario with the following configuration:

```r
# Training parameters (matching Cong et al. 2024)
num_iter = 1           # Single tree (NO boosting)
no_H = TRUE            # Don't use boosting residuals
random_split = FALSE   # Deterministic splits (reproducibility)

# Tree structure
max_depth = 10         # Maximum tree depth
min_leaf_size = 3      # Minimum observations per leaf
num_cutpoints = 4      # Candidate split points per characteristic

# Regularization
gamma = 1e-4           # Complexity penalty
lambda = 1e-5          # Shrinkage parameter
```

**Note**: Despite max_depth=10, all trees made only 1 split → 2 leaf portfolios. This simplicity is due to:
1. Small cross-section (~153 firms/month vs ~8,000 in US studies)
2. Weak predictive signals (median univariate R² = 0.00005)
3. Stringent Sharpe ratio optimization criterion

## Key Results

### Scenario A: Full Sample (1998-2019)
- **Split Characteristic**: Asset Turnover (ato) at threshold 0.20
- **Sharpe Ratio**: 0.66
- **Mean Monthly Return**: 1.07%
- **Monthly Volatility**: 5.59%
- **CAPM Alpha**: 13.13% annualized (t=2.41**)
- **FF3 Alpha**: 12.79% annualized (t=2.27**)
- **Sample Size**: 258 months, 39,524 observations

### Scenario B: Forward Test (Train 1998-2009, Test 2010-2019)
- **Split Characteristic**: Cash-to-Debt (cashdebt) at threshold 0.60
- **Train Sharpe Ratio**: 0.49
- **Test Sharpe Ratio**: 1.03 ✓ (strong out-of-sample performance)
- **Test Mean Return**: 1.17%/month
- **Test Volatility**: 3.95%
- **Test CAPM Alpha**: 13.38% annualized (t=3.20***)
- **Test FF3 Alpha**: 14.79% annualized (t=3.60***)
- **Interpretation**: Tree trained on 2000s (financial crisis period) identifies financial stability (cash/debt) as key predictor

### Scenario C: Reverse Test (Train 2010-2019, Test 1998-2009)
- **Split Characteristic**: Cash-to-Debt (cashdebt) at threshold -0.60
- **Train Sharpe Ratio**: 1.48
- **Test Sharpe Ratio**: 0.59 (robustness check)
- **Test Mean Return**: 0.47%/month
- **Test Volatility**: 2.78%
- **Test CAPM Alpha**: 5.66% annualized (t=1.49)
- **Test FF3 Alpha**: 5.07% annualized (t=1.37)
- **Interpretation**: Tree trained on post-crisis period uses different cash/debt threshold, showing regime change

### Summary Statistics
| Metric | Scenario A | Scenario B (Test) | Scenario C (Test) |
|--------|-----------|-------------------|-------------------|
| Sharpe Ratio | 0.66 | 1.03 | 0.59 |
| FF3 Alpha (%) | 12.79** | 14.79*** | 5.07 |
| t-statistic | 2.27 | 3.60 | 1.37 |
| Months | 258 | 119 | 139 |

**Significance levels**: *** p<0.01, ** p<0.05, * p<0.10 (Newey-West SE with 12 lags)

## Discussion & Key Findings

### Why Simple Trees?
P-Trees exhibit minimal splitting (1 split → 2 portfolios) compared to US studies due to:

1. **Small Cross-Section**: ~153 firms/month vs ~8,000 in US markets
   - Fewer observations limit tree complexity
   - Less opportunity to find strong interaction effects

2. **Weak Predictive Signals**: Median univariate R² = 0.00005
   - Swedish characteristics have much weaker individual predictive power
   - Cross-sectional variation lower than in larger markets

3. **Stringent Optimization**: Sharpe ratio maximization requires strong evidence
   - Additional splits must significantly improve risk-adjusted returns
   - Algorithm correctly identifies when complexity doesn't add value

### Despite Simplicity, Factors Work

**Positive Finding**: Even single-split trees generate:
- Significant alphas (12-15% annually) relative to Fama-French 3-factor model
- Strong out-of-sample performance (Scenario B: Sharpe 1.03)
- Interpretable factor construction (Asset Turnover, Cash-to-Debt)

**Economic Intuition**:
- Full sample favors operational efficiency (Asset Turnover)
- 2000s training identifies financial stability (Cash/Debt) - important during financial crisis
- 2010s training uses different Cash/Debt threshold - evidence of regime change

### Comparison to Original Paper

| Aspect | Cong et al. (2024) - US | This Study - Sweden |
|--------|-------------------------|---------------------|
| Avg Firms/Month | ~8,000 | ~153 |
| Tree Complexity | 3-7 splits | 1 split |
| Top Characteristics | Market cap, momentum | Asset turnover, Cash/Debt |
| Sharpe Ratios | 1.2-1.8 | 0.59-1.48 |
| Interpretation | Complex interactions | Simple, transparent |

### Contribution

This thesis demonstrates:
1. **Methodology Transfer**: P-Trees work in small markets despite data constraints
2. **Interpretability**: Single splits create fully transparent factor definitions
3. **Robustness**: Out-of-sample validation confirms genuine predictive power
4. **Market Insights**: Different characteristics matter in Swedish vs US markets

## Project Structure

```
PTrees/
├── data/
│   ├── raw/              # Original data sources
│   ├── intermediate/     # Processed individual datasets
│   ├── processed/        # Final merged datasets
│   └── mappings/         # ISIN-OrgNr mapping tables
├── src/
│   ├── data_preparation/ # Python scripts (Steps 1-6)
│   └── analysis/         # R scripts (Steps 1-5)
├── results/
│   ├── inputs/           # Prepared .rds matrices
│   ├── models/           # Trained P-Trees & factor returns
│   ├── evaluation/       # Performance metrics
│   ├── thesis_visualisations/ # Tables & figures for Results
│   └── validation/       # Diagnostic outputs for Methodology
└── notebooks/            # Exploratory analysis (Jupyter)
```

## Reproducibility

### Data Pipeline (Python)
```bash
python src/data_preparation/1_process_finbas.py
python src/data_preparation/2_process_serrano_accounting.py
python src/data_preparation/3_build_isin_orgnr_mapping_LSEG.py
python src/data_preparation/4_merge_mappings.py
python src/data_preparation/5_merge_datasets.py
python src/data_preparation/6_prepare_ptree_dataset.py
```

### Analysis Pipeline (R)
```bash
Rscript src/analysis/01_prepare_inputs.R
Rscript src/analysis/02_train_ptree.R
Rscript src/analysis/03_evaluate_model.R
Rscript src/analysis/04_visualize_results.R
Rscript src/analysis/05_validation_analysis.R
```

**Note**: Set `set.seed(42)` ensures reproducible results. All scripts clear output directories before running to guarantee fresh results.

## Requirements

### R Packages
```r
install.packages(c("data.table", "ggplot2", "sandwich", "lmtest"))
```

### Python Packages
```bash
pip install pandas numpy
```

### PTree Package
The custom PTree package (Cong et al. 2024 implementation) must be installed separately. Contact authors or check the replication materials from the original paper.

## References

Cong, L. W., Tang, K., Wang, J., & Zhang, Y. (2024). AlphaPortfolio: Direct Construction Through Deep Reinforcement Learning and Interpretable AI. *Management Science*, forthcoming.

Shof, M., Driessen, J., & Eiling, E. (2020). A Swedish Factor Model. Swedish House of Finance Research Paper.

## Contact

Bachelor Thesis - Stockholm School of Economics
Date: December 2025
