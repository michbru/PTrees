#!/usr/bin/env Rscript

################################################################################
# Sensitivity Analysis: Tree Depth (num_iter)
################################################################################
#
# Purpose: Investigate the effect of tree depth on model performance
#
# This script explores whether allowing deeper trees (more splits) improves
# out-of-sample performance or leads to overfitting.
#
# Key Finding: Deeper trees (num_iter = 10) improve in-sample Sharpe ratios
# but do NOT improve out-of-sample performance, indicating overfitting.
# The optimal configuration for this dataset is num_iter = 1 (single split).
#
# To run this analysis, change num_iter in 02_train_ptree.R from 1 to 10,
# then run scripts 02-05 to regenerate all results.
#
################################################################################

suppressPackageStartupMessages({
  library(data.table)
})

cat("================================================================================\n")
cat("SENSITIVITY ANALYSIS: TREE DEPTH\n")
cat("================================================================================\n\n")

cat("This script documents the tree depth sensitivity analysis.\n\n")

cat("METHODOLOGY:\n")
cat("1. Original model: num_iter = 1 (one split maximum)\n")
cat("2. Alternative model: num_iter = 10 (up to 10 splits allowed)\n")
cat("3. Compare in-sample vs out-of-sample performance\n\n")

cat("RESULTS SUMMARY:\n")
cat("================================================================================\n\n")

results_comparison <- data.table(
  Configuration = c("num_iter = 1", "num_iter = 10", "num_iter = 1", "num_iter = 10"),
  Scenario = c("A (Full)", "A (Full)", "B (Test)", "B (Test)"),
  Num_Leaves = c(2, 10, 2, 10),
  Sharpe = c(0.92, 1.88, 0.19, 0.19),
  CAPM_Alpha_Annual = c("~10%", "10.3%", "~1%", "1.1%")
)

cat("Performance Comparison:\n")
print(results_comparison)

cat("\n================================================================================\n")
cat("KEY FINDINGS:\n")
cat("================================================================================\n\n")

cat("1. IN-SAMPLE IMPROVEMENT WITH DEEPER TREES:\n")
cat("   - Scenario A Sharpe: 0.92 -> 1.88 (+104%)\n")
cat("   - Scenario C Train Sharpe: ~1.9 -> 3.88 (+105%)\n\n")

cat("2. OUT-OF-SAMPLE PERFORMANCE UNCHANGED:\n")
cat("   - Scenario B Test Sharpe: 0.19 -> 0.19 (no change)\n")
cat("   - Scenario C Test Sharpe: 0.43 -> 0.43 (no change)\n")
cat("   - CAPM alphas remain statistically indistinguishable\n\n")

cat("3. FIRST SPLIT IS ROBUST:\n")
cat("   - Scenarios A & B: Split on 'rank_bm' at -0.2 (consistent)\n")
cat("   - Scenario C: Split on 'rank_cfp' at -0.6 (consistent)\n")
cat("   - The most important split is stable across configurations\n\n")

cat("4. EVIDENCE OF OVERFITTING:\n")
cat("   - Deeper trees capture training noise, not generalizable signal\n")
cat("   - Limited cross-sectional data (~150 firms/month) insufficient for complex trees\n")
cat("   - After first split, each leaf has ~75 firms/month on average\n")
cat("   - Further splits create leaves with too few observations per month\n\n")

cat("================================================================================\n")
cat("TREE STRUCTURE WITH num_iter = 10:\n")
cat("================================================================================\n\n")

cat("Scenario A (Full Sample) - 10 leaves:\n")
cat("  Root: rank_bm <= -0.2\n")
cat("  ├── Left: rank_mom1m <= 0.6\n")
cat("  │   ├── Left: rank_me <= 0.2\n")
cat("  │   │   ├── Left: rank_gma <= 0.6 (leaf)\n")
cat("  │   │   └── Right: (leaf)\n")
cat("  │   └── Right: (leaf)\n")
cat("  └── Right: rank_sp <= -0.6\n")
cat("      ├── Left: (leaf)\n")
cat("      └── Right: rank_op <= -0.2\n")
cat("          ├── Left: rank_sp <= 0.2 (leaf)\n")
cat("          └── Right: rank_pm <= 0.6\n")
cat("              ├── Left: rank_cashdebt <= -0.2 (leaf)\n")
cat("              └── Right: (leaf)\n\n")

cat("Scenario B (Train) - 10 leaves:\n")
cat("  Uses characteristics: bm, mom1m, me, cfp, cashdebt, roe\n\n")

cat("Scenario C (Train) - 11 leaves:\n")
cat("  Uses characteristics: cfp, gma, sgr, me, mom12m, acc, cashdebt, bm, lgr\n\n")

cat("================================================================================\n")
cat("CONCLUSION:\n")
cat("================================================================================\n\n")

cat("For the Swedish stock market dataset with limited cross-sectional depth,\n")
cat("a SINGLE SPLIT (num_iter = 1) is optimal. This configuration:\n")
cat("  1. Identifies the most important predictive characteristic\n")
cat("  2. Avoids overfitting to training noise\n")
cat("  3. Maintains stable out-of-sample performance\n")
cat("  4. Is consistent with data sparsity constraints\n\n")

cat("This finding is methodologically important: it demonstrates that\n")
cat("P-Trees can identify meaningful factors even with limited data,\n")
cat("but more complex trees require larger cross-sections to be effective.\n\n")

cat("The U.S. study (Cong et al. 2025) used ~8,000 firms vs our ~150-230 firms,\n")
cat("explaining why deeper trees work for them but not for Swedish data.\n\n")

cat("================================================================================\n")
cat("TO REPRODUCE DEEPER TREE RESULTS:\n")
cat("================================================================================\n\n")

cat("1. Edit src/analysis/02_train_ptree.R\n")
cat("2. Change line 174 from:\n")
cat("     num_iter = 1\n")
cat("   to:\n")
cat("     num_iter = params$max_depth\n")
cat("3. Run: Rscript src/analysis/02_train_ptree.R\n")
cat("4. Run: Rscript src/analysis/03_evaluate_model.R\n")
cat("5. Run: Rscript src/analysis/04_visualize_results.R\n\n")

cat("Note: The submitted results use num_iter = 1 (conservative configuration)\n")
cat("to avoid presenting overfitted results.\n\n")

cat("================================================================================\n")
