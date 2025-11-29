# Quick Start Guide - P-Tree Analysis

## TL;DR - Run Analysis

```bash
# Complete pipeline (prepare data + train model)
Rscript src/analysis/00_run_all.R
```

**Output**:
- Factor returns: `results/analysis/models/ptree_factor.csv`
- Performance: `results/analysis/models/ptree_summary.csv`
- Tree structure: `results/analysis/models/ptree_tree.txt`

## Results at a Glance

✅ **Working Model**: Sharpe 1.25, Annual Return 19.07%

The model selects 3 characteristics from 40 available:
- **Variance** (rank_svar) - Low volatility outperforms
- **12-month momentum** (rank_mom12m) - Winners continue
- **6-month momentum** (rank_mom6m) - Shorter-term trends

## What Changed from Standard P-Trees?

| What | Standard (US) | Swedish Optimized |
|------|---------------|-------------------|
| Boosting | Single tree | **5 iterations** |
| Min leaf size | 10 | **3** |
| Weighting | Value-weighted | **Equal-weighted** |
| Regularization | 1e-5 | **0** |

**Why?** Swedish market is smaller (~270 stocks vs ~3000 in US). Single deep trees don't work. Boosted ensembles do.

## Project Structure

```
PTrees/
├── src/
│   ├── data_preparation/       # Steps 1-6: Build dataset
│   └── analysis/
│       ├── 00_run_all.R        # Run everything
│       ├── 01_prepare_inputs.R # Prepare training data
│       └── 02_train_ptree.R    # Train model
├── data/
│   ├── raw/                    # Source data
│   ├── intermediate/           # Cleaned data
│   └── processed/              # Final monthly dataset
├── results/
│   └── analysis/
│       ├── models/             # Factor outputs
│       └── RESULTS_SUMMARY.md  # Full results
└── docs/
    ├── ANALYSIS.md             # General documentation
    └── SWEDISH_MARKET_ADAPTATIONS.md  # Why/how we adapted P-Trees
```

## Individual Steps

```bash
# 1. Prepare training data
Rscript src/analysis/01_prepare_inputs.R

# 2. Train P-Tree model
Rscript src/analysis/02_train_ptree.R

# Override parameters
Rscript src/analysis/02_train_ptree.R --num_iter=10 --eta=0.2
```

## Key Files

| File | What It Does |
|------|-------------|
| `00_run_all.R` | Runs complete pipeline |
| `01_prepare_inputs.R` | Loads data, filters characteristics, creates matrices |
| `02_train_ptree.R` | Trains boosted P-Tree, generates factor |
| `ptree_factor.csv` | **Main output**: Monthly factor returns |
| `ptree_summary.csv` | Performance metrics (Sharpe, return, vol) |

## Understanding the Output

### Factor Returns (ptree_factor.csv)

```csv
date,factor
1999-06-30,-1.38
1999-07-31,4.96
1999-08-31,0.76
...
```

These are **monthly returns in percent** from a portfolio strategy based on the P-Tree model.

### Summary (ptree_summary.csv)

```csv
metric,value
mean_monthly,1.59
std_monthly,4.40
sharpe_annual,1.25
annualized_return,19.07
annualized_vol,15.23
```

### Tree Structure (ptree_tree.txt)

```
11                          # Total nodes
1 35 -0.922 1 0            # Node 1: split on char 35 (rank_svar) at -0.922
2 0 0 0 0                  # Node 2: leaf
3 18 0.882 47 1            # Node 3: split on char 18 (rank_mom12m) at 0.882
...
```

## Customization

### Test Different Parameters

```bash
# More aggressive boosting
Rscript src/analysis/02_train_ptree.R --num_iter=10 --min_leaf_size=2

# Slower learning
Rscript src/analysis/02_train_ptree.R --eta=0.1

# More cutpoint candidates
Rscript src/analysis/02_train_ptree.R --num_cutpoints=100
```

### Parameter Reference

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `--num_iter` | 5 | 1-50 | More iterations = more complex model |
| `--eta` | 0.3 | 0.1-1.0 | Lower = slower learning, more stable |
| `--min_leaf_size` | 3 | 2-10 | Lower = more splits possible |
| `--num_cutpoints` | 50 | 20-100 | More = finer split granularity |

## Common Issues

### "Only 1 split in tree"

**Solution**: Use boosting (`num_iter >= 5`). This is expected for smaller markets.

### "Singular matrix warnings"

**Solution**: Normal for Swedish data. Already suppressed in code.

### "Low Sharpe ratio"

**Solution**: 1.25 is good for Swedish market. Don't expect US-level performance (>2.0).

## Documentation

- **Full Results**: `results/analysis/RESULTS_SUMMARY.md`
- **Methodology**: `docs/SWEDISH_MARKET_ADAPTATIONS.md`
- **General Docs**: `docs/ANALYSIS.md`

## Next Steps

1. ✅ Basic model working (Sharpe 1.25)
2. ⏭️ Run robustness checks: `Rscript src/analysis/04_robustness.R`
3. ⏭️ Compare to benchmarks: `Rscript src/analysis/07_benchmarks.R`
4. ⏭️ Analyze portfolio composition and turnover
5. ⏭️ Test out-of-sample performance

## Questions?

- Read `docs/SWEDISH_MARKET_ADAPTATIONS.md` for detailed methodology
- Check `results/analysis/RESULTS_SUMMARY.md` for performance breakdown
- Review diagnostic tests (removed) documented in Swedish adaptations doc

---

**Status**: ✅ P-Trees successfully adapted and working for Swedish market
