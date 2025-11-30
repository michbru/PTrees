# Step 2: P-Tree Training - Outputs Summary

## Overview
This directory contains all outputs from Step 2 (P-Tree Model Training) for the bachelor thesis.

## Training Methodology
- **Model Type**: Single P-Tree (unboosted)
- **Rationale**: Testing showed single tree outperforms boosted for Swedish market (Sharpe 2.46 vs 1.31)
- **Optimal Parameters** (from hyperparameter tuning):
  - num_iter = 5 (number of splits)
  - min_leaf_size = 5
  - lambda_cov = 1e-3
  - equal_weight = TRUE
  - eta = 1.0 (no boosting)

## Three Scenarios Implemented

### Scenario A: Full Sample (1999-06 to 2020-11)
- **Purpose**: Benchmark performance using all available data
- **Results**: Sharpe 2.46, Return 9.15% annualized, 6 leaf portfolios

### Scenario B: Time-Split (Past → Future)
- **Train**: 1999-06 to 2009-12 (127 months)
- **Test**: 2010-01 to 2020-11 (131 months)
- **Purpose**: Forward validation (past predicting future)
- **Test Results**: Sharpe 2.91, Return 11.53% annualized

### Scenario C: Reverse Split (Future → Past)  
- **Train**: 2010-01 to 2020-11 (131 months)
- **Test**: 1999-06 to 2009-12 (127 months)
- **Purpose**: Robustness check for look-ahead bias
- **Test Results**: Sharpe 1.54, Return 7.57% annualized

## Output Files

### Main Summary Files
- `all_scenarios_summary.csv` - Combined results for all three scenarios
- `single_vs_boosted_comparison.csv` - Comparison showing single tree superiority

### Per-Scenario Outputs

For each scenario (A, B, C):

**Factor Returns:**
- `scenario_X_factor.csv` - Time series of P-Tree factor returns
- `scenario_X_train_factor.csv` (B & C only) - Training period factor
- `scenario_X_test_factor.csv` (B & C only) - Test period factor

**Tree Structure:**
- `scenario_X_tree.txt` - Human-readable tree structure showing splits
- Shows which characteristics were used and at what thresholds

**Leaf Portfolios:**
- `scenario_X_leaf_portfolios.csv` - Returns of all 6 leaf portfolios
- Each leaf represents a characteristics-managed portfolio
- Used for constructing the final P-Tree factor

**Summary Statistics:**
- `scenario_X_summary.csv` - Sharpe ratio, mean, std dev, number of leaves

## Key Results for Thesis

| Scenario | Sharpe Ratio | Mean Monthly | Annualized Return | Num Leaves |
|----------|--------------|--------------|-------------------|------------|
| A: Full Sample | 2.46 | 0.76% | 9.15% | 6 |
| B: Time-Split (test) | 2.91 | 0.96% | 11.53% | 6 |
| C: Reverse Split (test) | 1.54 | 0.63% | 7.57% | 6 |

## Next Step
Step 3 will calculate CAPM and Fama-French 3-factor alphas with t-statistics for Table 1 in thesis.
