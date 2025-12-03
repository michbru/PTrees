# P-Trees on Swedish Stock Market: Empirical Analysis

## Overview

This project implements P-Trees (Prediction Trees) from Cong et al. (2023) on Swedish stock market data. P-Trees are an interpretable machine learning method for factor discovery in asset pricing that combines tree-based models with portfolio optimization.

## Data Sources & Sample

Data from stocks in the Swedish stock market were used.
- **Market Data**: Finbas (daily prices, volume, market cap)
- **Fundamentals**: Serrano (annual accounting data)
- **Mapping**: LSEG (used to map ISIN to Organization Number)
- **Risk Factors**: Swedish House of Finance (Fama-French factors)
- **Inflation**: Official Statistics of Sweden (inflation rate)

**Sample Characteristics (Post-Filtering):**
- **Time Period**: January 1998 - December 2019
- **Total Firms**: ~675
- **Average Firms per Month**: ~230
- **Total Observations**: ~59,314 firm-months

## Methodology

The main bulk of the work for obtaining the results was data preparation. The main steps were to clean the datasets, merge them, and create new variables from existing characteristics.

### 1. Data Cleaning & Filtering
Cleaning included filtering out data points outside the study time frame, handling missing values, and removing unnecessary variables.
- **Time Window**: Chosen to match the availability of Fama-French factors and Finbas data.
- **Share Class Filtering**: Multiple stock types from the same firm were filtered to ensure one set of predictors corresponds to one dependent variable value. If two stock classes from the same firm were included with different returns, explanatory variables would lose predictive power. We prioritized the most liquid share class.
- **Foreign Stocks**: Stocks of firms based in other countries (e.g., Finnish firms in Finbas) were filtered out.
- **Exchanges**: Only stocks of public firms listed on prominent Stockholm-based exchanges were included.
- **Variable Selection**: Only variables replicating `\textcite{PTree}` were kept. Variables with extremely low coverage (e.g., dividend yield) were excluded to maintain model robustness.

### 2. Merging Datasets
A mapping table was created to merge Finbas (ISIN identifier) and Serrano (Organization Number identifier).
- **Mapping**: LSEG data provided both ISIN and tax-ids. Swedish tax-ids were converted to organization numbers (stripping "SE" and "01") to create an ISIN-to-OrgNr dictionary.
- **Frequency Mismatch**: Finbas is monthly, Serrano is annual. We merged by aligning the most recent available annual report to each month. This "forward-filling" approach reflects investor knowledge, as decisions are based on the latest known financial statements.
- **New Characteristics**: Post-merge, we calculated ratios like Return on Assets (ROA), Book-to-Market (BM), Earnings-to-Price (EP), Sales-to-Price (SP), and Cashflow-to-Price (CFP).

### 3. Lag Implementation
To prevent look-ahead bias, lags were applied to all predictor variables.
- **Market Data**: Lagged by 1 month.
- **Accounting Data**: Lagged by 6 months to ensure financial reports were public information at the time of prediction.

## Model Configuration

The P-Tree model was trained with the following hyperparameters (Scenario A, B, and C):

```r
num_iter = 9           # Internal boosting iterations per tree
eta = 1.0              # Learning rate
min_leaf_size = 20     # Minimum observations per leaf
max_depth = 3          # Maximum tree depth
num_cutpoints = 50     # Number of candidate split points
lambda_cov = 1e-2      # Covariance regularization
lambda_ridge = 1e-4    # Ridge regularization
equal_weight = TRUE    # Equal weighting in leaf portfolios
weighted_loss = FALSE  # Standard loss function
abs_normalize = TRUE   # Absolute value normalization
```

## Key Results

### Scenario A: Full Sample (1998-2019)
- **Sharpe Ratio**: 0.68
- **Annualized Return**: 1.50%
- **Alpha (CAPM)**: 0.11% (t=2.31)
- **Tree Structure**: Simple 2-level tree with 5 leaf portfolios.

### Scenario B: Time-Split (Train 1998-2009 / Test 2010-2019)
- **Test Sharpe Ratio**: 0.92
- **Test Annualized Return**: 1.54%

### Scenario C: Reverse Split (Train 2010-2019 / Test 1998-2009)
- **Test Sharpe Ratio**: 0.56
- **Test Annualized Return**: 0.99%

## Discussion

The P-Trees exhibit limited splitting behavior (1-2 splits) compared to US studies. This is attributed to:
1. **Small Cross-Section**: ~230 firms/month vs ~8,000 in the US.
2. **Data Sparsity**: High proportion of missing/zero values in characteristics.
3. **Weak Signals**: Median univariate R² is extremely low (0.000053).

Despite these constraints, the model successfully extracts a factor with positive risk-adjusted returns and significant alpha, demonstrating the methodology's viability even in smaller markets.

## References

Cong, L. W., Tang, K., Wang, J., & Zhang, Y. (2023). Interpretable Machine Learning for Asset Pricing. *Management Science*, forthcoming.
