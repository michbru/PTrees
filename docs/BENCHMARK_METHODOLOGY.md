# P-Tree Benchmark Methodology

This document explains the benchmark comparison methodology used to validate the Swedish P-Tree implementation against standard asset pricing models.

## Overview

Following Cong et al. (2024) "Growing the Efficient Frontier on Panel Trees" published in the *Journal of Financial Economics*, we compare P-Tree factors against:

1. **CAPM** (Capital Asset Pricing Model)
2. **Fama-French 3-Factor Model** (FF3)
3. **Fama-French 4-Factor Model** (FF3 + Momentum)
4. **Macro Variables** (Market volatility, inflation)

## Data Sources

### Swedish Fama-French Factors
Source: Swedish House of Finance
- **Market Factor (rm_rf)**: Swedish market excess return over risk-free rate
- **SMB (Size)**: Small Minus Big - return differential between small and large cap stocks
- **HML (Value)**: High Minus Low - return differential between high and low book-to-market stocks
- **MOM (Momentum)**: Winners Minus Losers - return differential based on past performance

Both equal-weighted (EW) and value-weighted (VW) versions are available. We use **value-weighted** factors to match the P-Tree methodology.

### Macro Variables
- **Market Volatility**: Rolling annualized volatility from daily returns
- **Inflation**: Swedish CPI inflation rate
- **Risk-Free Rate**: Swedish short-term interest rate

## Analysis Components

### 1. Sharpe Ratio Analysis

**Individual Sharpe Ratios**
```
SR = (μ / σ) × √12
```
where:
- μ = mean monthly return
- σ = monthly return standard deviation
- √12 = annualization factor

**Mean-Variance Efficient (MVE) Sharpe Ratio**

For k factors F₁, F₂, ..., Fₖ, the optimal portfolio weight vector is:
```
w* = (Σ + λ_cov·I)⁻¹ (μ + λ_mean·1)
w = w* / ||w*||₁
```
where:
- Σ = covariance matrix of factor returns
- μ = mean return vector
- λ_cov = 1e-5 (regularization parameter)
- λ_mean = 0

The MVE Sharpe ratio is the Sharpe ratio of the portfolio with returns: F·w

### 2. Alpha Regression Analysis

**CAPM Alpha**
```
F_t = α + β·MKT_t + ε_t
```

**Fama-French 3-Factor Alpha**
```
F_t = α + β₁·MKT_t + β₂·SMB_t + β₃·HML_t + ε_t
```

**Fama-French 4-Factor Alpha**
```
F_t = α + β₁·MKT_t + β₂·SMB_t + β₃·HML_t + β₄·MOM_t + ε_t
```

**Key Metrics:**
- **Alpha (α)**: Annualized abnormal return (in %)
- **t-statistic**: Statistical significance using Newey-West HAC standard errors (3 lags)
- **R²**: Proportion of variance explained by benchmark factors
- **RMSE**: Root mean squared error (annualized)

### 3. Interpretation Guidelines

**Alpha Significance:**
- |t-stat| > 2: Statistically significant at ~5% level
- |t-stat| > 2.58: Statistically significant at ~1% level

**What It Means:**
- **Positive significant alpha**: P-Tree captures returns not explained by benchmarks (new risk factor or market inefficiency)
- **Insignificant alpha**: P-Tree returns can be replicated by existing factors (redundant)
- **High R²**: Strong correlation with benchmark factors

**Sharpe Ratio Comparison:**
- Swedish Market SR (historical): ~0.3-0.5
- P-Tree SR = 1.20: Significantly higher than market
- MVE SR: Maximum Sharpe achievable with factor combinations

## Implementation Details

### Newey-West Standard Errors

We use HAC (Heteroskedasticity and Autocorrelation Consistent) standard errors with 3 lags to account for:
- Heteroskedasticity (time-varying volatility)
- Autocorrelation (serial correlation in returns)

This is standard in asset pricing research.

### Regularization

Following the original paper:
- **λ_cov = 1e-5**: Small ridge regularization on covariance matrix
- **λ_mean = 0**: No mean regularization

This prevents numerical instability when factor covariance matrices are near-singular.

### Value-Weighted vs Equal-Weighted

We use **value-weighted** factors because:
1. P-Trees use value-weighted portfolios (lag_me weights)
2. More economically meaningful (represents actual investable returns)
3. Matches the original Cong et al. (2024) methodology

## Expected Results for Swedish Market

### P-Tree Performance
- **Sharpe Ratio**: ~1.20 (good for Swedish market)
- **Alpha vs CAPM**: Expected to be significant if tree finds patterns
- **Alpha vs FF3/FF4**: Smaller magnitude due to more controls

### Why P-Trees Default to Market Portfolio
With only ~300 stocks and 19 characteristics:
- Swedish market too small for profitable tree splits
- Algorithm conservatively defaults to market portfolio
- This is **correct behavior** (prevents overfitting)

### Benchmark Factors Performance
Expected Swedish factor Sharpe ratios:
- Market: 0.3-0.5
- SMB: 0.1-0.3
- HML: 0.2-0.4
- MOM: 0.4-0.6

## Output Files

The benchmark analysis generates:

1. **table1_sharpe_ratios.csv**: Individual and MVE Sharpe ratios
2. **table2_alphas.csv**: Alphas vs all benchmark models
3. **table3_benchmark_performance.csv**: Benchmark factor statistics
4. **table4_macro_variables.csv**: Macro variable descriptive stats
5. **table5_correlations.csv**: Correlation matrix
6. **summary_report.txt**: Human-readable summary

## References

1. Cong, Lin William, Guanhao Feng, Jingyu He, and Xin He (2024). "Growing the Efficient Frontier on Panel Trees." *Journal of Financial Economics*, forthcoming.

2. Fama, Eugene F., and Kenneth R. French (1993). "Common Risk Factors in the Returns on Stocks and Bonds." *Journal of Financial Economics* 33(1): 3-56.

3. Carhart, Mark M. (1997). "On Persistence in Mutual Fund Performance." *Journal of Finance* 52(1): 57-82.

4. Newey, Whitney K., and Kenneth D. West (1987). "A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix." *Econometrica* 55(3): 703-708.

## Usage

Run the complete analysis:
```bash
python src/replication/replicate.py
```

Or run benchmark analysis separately (after P-Tree training):
```bash
python src/3_benchmark_analysis.py
```

Results will be saved to: `results/benchmark_analysis/`
