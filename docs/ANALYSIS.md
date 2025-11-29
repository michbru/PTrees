# P-Tree Analysis — Swedish Market

This folder contains a small, modular analysis pipeline to train P-Tree factors on the Swedish dataset built in Steps 1–6.

## Prerequisites

- R with the `PTree` package available (install from the authors' repository).
- The dataset `data/processed/ptree_dataset_monthly.csv` created by Step 6.

## Steps

1) Prepare Inputs (A1)
   - Script: `src/analysis/01_prepare_inputs.R`
   - Loads the monthly dataset, filters the period (default from 1999-06),
     filters characteristics by 30% non-zero coverage, and builds matrices for PTree.
   - Output: `results/analysis/inputs/ptree_inputs.rds`

2) Train Unboosted Tree (A2)
   - Script: `src/analysis/02_train_unboosted.R`
   - Trains a single P-Tree (no boosting) and saves the factor time series and basic summary.
   - Outputs: `results/analysis/models/ptree_unboosted_tree.txt`,
     `results/analysis/models/ptree_factor_unboosted.csv`,
     `results/analysis/models/ptree_unboosted_summary.csv`

3) Train Boosted Trees (A3)
  - Script: `src/analysis/03_train_boosted.R`
  - Trains several trees with boosting (H contains prior factors), saves combined factor matrix and summary.

4) Robustness (A4)
  - Script: `src/analysis/04_robustness.R`
  - Runs: equal-weight vs value-weight, alternate start dates, and a small parameter sweep.

5) Factor Diagnostics (A5)
  - Script: `src/analysis/05_factor_diagnostics.R`
  - Computes stats, t-stats, correlations; saves cumulative plots.

6) In/Out-of-Sample Split (A6)
  - Script: `src/analysis/06_oos_validation.R`
  - Splits the sample (train to 2010-12-31, test after) and refits on each subset to assess stability (not strict OOS due to no predict()).

## Running

Run from the repo root with Rscript:

```
Rscript src/analysis/01_prepare_inputs.R
Rscript src/analysis/02_train_unboosted.R
Rscript src/analysis/03_train_boosted.R
Rscript src/analysis/04_robustness.R
Rscript src/analysis/05_factor_diagnostics.R
Rscript src/analysis/06_oos_validation.R
```

Proceed with boosted training and robustness once the basic factor is validated.
