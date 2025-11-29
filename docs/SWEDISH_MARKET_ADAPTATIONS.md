# P-Trees for Swedish Stock Market: Adaptations and Recommendations

## Problem

When applying P-Trees to Swedish stock market data, single unboosted trees produce only **1 split** regardless of parameter tuning, resulting in poor model performance. This is fundamentally different from US market applications where deep trees with many splits work well.

## Root Cause Analysis

The Swedish stock market has unique characteristics that make standard P-Tree configurations ineffective:

1. **Smaller Market Size**: ~270 stocks/month vs ~3000+ in US markets
2. **Lower Liquidity**: Fewer trades and higher bid-ask spreads
3. **Concentration**: Market cap concentrated in fewer large companies
4. **Weaker Cross-Sectional Signal**: Less variation to split on within each period
5. **Numerical Issues**: Covariance matrix becomes near-singular with value-weighted splits

### Diagnostic Results

Testing revealed:

| Configuration | Splits | Sharpe | Issue |
|---------------|--------|--------|-------|
| US defaults (min_leaf=10, no boosting) | 1 | 1.02 | Too conservative |
| Lower min_leaf (min_leaf=3) | 1 | 1.09 | Still insufficient |
| No regularization (lambda_cov=0) | 1 | 1.27 | Regularization not the issue |
| **Boosting (num_iter=5)** | **Multiple** | **1.25** | **Works!** |

## Solution: Boosted P-Trees

The key insight is that **boosted ensembles of shallow trees work better than single deep trees** for smaller markets.

### Recommended Parameters for Swedish Market

```r
PTree::PTree(
  # ... data inputs ...
  min_leaf_size = 3,        # Lower than US default (10)
  max_depth = 8,            # Same as US
  num_iter = 5,             # CRITICAL: Boosting (US default: 1)
  num_cutpoints = 50,       # More granular splits
  eta = 0.3,                # Learning rate for boosting
  equal_weight = TRUE,      # Reduce large-cap bias (US default: FALSE)
  lambda_cov = 0,           # No regularization (prevents numerical issues)
  lambda_cov_factor = 0,
  # ... other parameters ...
)
```

### Performance Comparison

| num_iter | Sharpe | Annual Return | Annual Vol | Tree Complexity |
|----------|--------|---------------|------------|-----------------|
| 1 (unboosted) | 1.05 | 14.95% | 14.17% | 1 split |
| **5** | **1.25** | **19.07%** | **15.23%** | **11 nodes, 4 splits** |
| 10 | 1.22 | 18.91% | 15.50% | 17 nodes, 7 splits |
| 20 | 1.22 | 18.91% | 15.50% | Same as 10 |
| 50 | 1.22 | 18.91% | 15.50% | Same as 10 |

**Conclusion**: `num_iter=5` provides optimal balance of performance and computation time.

## Why Boosting Works

1. **Ensemble of Weak Learners**: Combines multiple shallow trees instead of forcing a single deep tree
2. **Gradual Refinement**: Each iteration focuses on residuals, finding progressively finer patterns
3. **Robustness**: Less sensitive to numerical instabilities in covariance estimation
4. **Regularization through Early Stopping**: Natural stopping after 5 iterations prevents overfitting

## Implementation Guide

### Quick Start

Use the Swedish-optimized training script:

```bash
Rscript src/analysis/02_train_unboosted_swedish.R
```

### Custom Parameters

Override defaults via command line:

```bash
# Test more aggressive boosting
Rscript src/analysis/02_train_unboosted_swedish.R --num_iter=10 --eta=0.2

# Test even lower minimum leaf size
Rscript src/analysis/02_train_unboosted_swedish.R --min_leaf_size=2
```

### Diagnostic Scripts

Three diagnostic scripts are available in `src/analysis/`:

1. **`diagnose_ptree_splits.R`**: Tests 9 parameter combinations for single trees
2. **`test_regularization.R`**: Tests different lambda_cov values (0 to 1e-5)
3. **`test_boosted_trees.R`**: Tests num_iter from 1 to 50

Results saved to: `results/analysis/diagnostics/`

## Key Differences from US Market Applications

| Aspect | US Market | Swedish Market |
|--------|-----------|----------------|
| **Splits per tree** | Many (5-15+) | Few (1-2) |
| **Boosting** | Optional | **Required** |
| **min_leaf_size** | 10-20 | 3-5 |
| **equal_weight** | FALSE (value-weighted) | TRUE (equal-weighted) |
| **lambda_cov** | 1e-5 (regularization) | 0 (no regularization) |
| **Primary challenge** | Overfitting | Insufficient signal for splits |

## Theoretical Justification

From the P-Tree paper (Bryzgalova et al.):

> "P-Trees partition the cross-section of stocks based on characteristics to construct factors."

In smaller markets:
- **Cross-sectional variation** is limited by fewer stocks
- **Time-series variation** dominates cross-sectional patterns
- **Boosting** allows the model to extract signal from residuals across iterations
- **Shallow trees** avoid overfitting to noise in small cross-sections

## Warnings and Limitations

### Expected Warnings

When running on Swedish data, you'll see:
```
warning: solve(): system is singular; attempting approx solution
```

**This is normal** and expected due to the smaller market size. The algorithm handles it gracefully with approximate solutions.

### Model Limitations

1. **Lower Sharpe than US**: Swedish market Sharpe ~1.25 vs US ~2.0+ is expected
2. **Simpler Tree Structure**: Don't expect 20+ node trees like in US applications
3. **Higher Volatility**: Swedish factors have higher vol (15-16%) than US (8-10%)
4. **Convergence**: Boosting often converges after 5-10 iterations

## References

- Bryzgalova, S., Pelger, M., & Zhu, J. (2023). "Forest Through the Trees: Building Cross-Sections of Stock Returns"
- Swedish market characteristics: Lower liquidity and concentration documented in Swedish House of Finance research
- Diagnostic outputs: See `results/analysis/diagnostics/` for full test results

## Contact

For questions about Swedish market adaptations, refer to:
- Diagnostic outputs in `results/analysis/diagnostics/`
- Test scripts in `src/analysis/`
- This documentation

---

**Last updated**: Based on testing with 69,830 observations (258 months, 696 stocks, 37 characteristics) from Swedish market data.
