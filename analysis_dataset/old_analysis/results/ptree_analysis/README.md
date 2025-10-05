# PTree Analysis Results - Swedish Stock Market (1998-2022)

## Overview
This folder contains the complete analysis of PTree factors generated from the Swedish stock market.

**Date Generated:** 2025-10-02 17:18
**Analysis Period:** 1998-01-30 to 2022-12-30
**Number of Months:** 300

## Folder Structure

```
ptree_analysis/
├── plots/                          # Visualizations
│   ├── 01_cumulative_returns.png   # Cumulative return plot
│   ├── 02_rolling_sharpe.png       # Rolling Sharpe ratios
│   ├── 03_return_distributions.png # Histogram of returns
│   ├── 04_correlation_heatmap.png  # Factor correlations
│   └── 05_drawdowns.png            # Drawdown analysis
├── tables/                         # Summary statistics
│   ├── summary_statistics.csv      # Raw statistics
│   └── summary_statistics_formatted.csv  # Formatted for display
└── README.md                       # This file
```

## Key Findings

### Factor Performance Summary

| Factor   | Mean Monthly Return   | Annualized Return   | Monthly Std Dev   | Annualized Std Dev   |   Sharpe Ratio (Annual) | Cumulative Return   | Max Drawdown   |   Skewness |   Kurtosis | Min Monthly Return   | Max Monthly Return   | Positive Months %   |
|:---------|:----------------------|:--------------------|:------------------|:---------------------|------------------------:|:--------------------|:---------------|-----------:|-----------:|:---------------------|:---------------------|:--------------------|
| Factor 1 | 8.31%                 | 160.60%             | 2.50%             | 8.66%                |                   11.52 | 2320186281545.12%   | 0.00%          |      1.789 |      3.946 | 5.22%                | 19.47%               | 100.0%              |
| Factor 2 | 0.79%                 | 9.85%               | 1.67%             | 5.78%                |                    1.63 | 904.93%             | -11.56%        |      1.467 |      6.122 | -4.41%               | 8.79%                | 72.7%               |
| Factor 3 | 8.31%                 | 160.60%             | 2.50%             | 8.66%                |                   11.52 | 2320186281545.12%   | 0.00%          |      1.789 |      3.946 | 5.22%                | 19.47%               | 100.0%              |
| Factor 4 | 8.31%                 | 160.60%             | 2.50%             | 8.66%                |                   11.52 | 2320186281545.12%   | 0.00%          |      1.789 |      3.946 | 5.22%                | 19.47%               | 100.0%              |
| Factor 5 | 8.31%                 | 160.60%             | 2.50%             | 8.66%                |                   11.52 | 2320186281545.12%   | 0.00%          |      1.789 |      3.946 | 5.22%                | 19.47%               | 100.0%              |

## Plots Description

1. **Cumulative Returns**: Shows how $1 invested in each factor grows over time
2. **Rolling Sharpe Ratios**: 36-month rolling Sharpe ratios to show time-varying performance
3. **Return Distributions**: Histograms showing the distribution of monthly returns
4. **Correlation Heatmap**: Shows how correlated the factors are with each other
5. **Drawdowns**: Maximum decline from peak for each factor

## Factor Interpretation

- **Factor 1**: Primary PTree factor (base tree, no benchmark)
- **Factor 2**: First boosted factor (orthogonal to Factor 1)
- **Factors 3-5**: Additional boosted factors

### Split Information
The algorithm found splits primarily on:
- **rank_sp** (Sales-to-Price ratio) at threshold 0.636

## Notes

- All Sharpe ratios are annualized
- Annualized returns assume monthly compounding
- Equal-weighted portfolios were used
- Data cleaned to remove observations with missing characteristics

## Next Steps

1. Compare these factors with traditional Swedish market factors (size, value, momentum)
2. Test out-of-sample performance
3. Construct efficient frontier using these factors
4. Analyze factor exposures of individual stocks

## Data Source

Swedish stock market data (1997-2022) from FinBas and LSEG
