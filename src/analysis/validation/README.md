# Validation Scripts

This folder contains validation analyses supporting the thesis defense.

## Active Scripts

### `data_coverage_analysis.py`
- **Purpose**: Comprehensive data coverage analysis comparing Swedish market data to US academic studies (Cong et al., 2023)
- **Key analyses**:
  - Temporal coverage evolution
  - Firm representation distribution
  - Variable coverage rates
  - Comparison to US market benchmarks
- **Outputs**: Multiple PNG figures and LaTeX tables in `results/validation/coverage_analysis/`
- **Run**: `python src/analysis/validation/data_coverage_analysis.py`

### `decode_tree_structures.R`
- **Purpose**: Decodes and interprets the tree structures from P-Tree models
- **Use case**: Understanding which characteristics were used for splits
- **Outputs**: Human-readable tree structure descriptions

## Main Validation Pipeline

The primary validation script is now integrated into the main analysis pipeline:

### Step 5: `../05_validation_analysis.R`
- **Purpose**: Generate essential statistical evidence for thesis defense explaining limited P-Tree splits
- **Key analyses**:
  1. **Characteristic Sparsity** - Proportion of zeros/missing in each characteristic
  2. **Univariate Predictive Power** - R² from simple regressions
  3. **Cross-Sectional Coverage** - Coverage quality over time
  4. **Market Comparison** - Swedish vs US market data quality
- **Outputs**:
  - `results/validation/table_sparsity.tex` - Data sparsity by characteristic
  - `results/validation/table_r2.tex` - Predictive power rankings
  - `results/validation/table_comparison.tex` - Swedish vs US comparison
  - `results/validation/figure_sparsity.png` - Sparsity visualization
  - `results/validation/figure_r2.png` - R² visualization
  - `results/validation/figure_coverage_time.png` - Coverage over time
  - `results/validation/validation_results.rds` - All results for further analysis
- **Run**: `Rscript src/analysis/05_validation_analysis.R`

## Key Findings for Thesis Defense

The validation analysis provides statistical evidence that limited P-Tree splits are attributable to:

1. **Weak Predictive Signals**: Median univariate R² of 0.0001 (vs ~0.05-0.15 in US studies)
2. **Small Sample Size**: ~104 firms/month (vs ~8,000 in US studies)
3. **Limited Coverage**: 26.7/32 usable characteristics per observation (vs ~45/50 in US)
4. **Data Quality**: 84.2% average coverage (vs >90% typical in US)

These limitations demonstrate that the Swedish market data does not provide sufficient signal for P-Trees to find profitable splitting strategies, unlike the rich US market data used in the original methodology.
