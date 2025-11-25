###################################################################################
# MAIN - P-TREE ANALYSIS PIPELINE
# Single-tree approach for Swedish market
#
# Following Cong et al. (2024) Journal of Financial Economics
# Adapted for Swedish market with conservative parameters
###################################################################################

library(PTree)

# Load modules
source("config.R")
source("data_loader.R")
source("ptree_trainer.R")
source("run_boosting.R")
source("run_scenarios.R")
source("run_rolling_window.R")

# Load data
data_obj <- load_ptree_data(DATA_PATH)

# Prepare parameters
params <- list(
  min_leaf_size = MIN_LEAF_SIZE,
  max_depth = MAX_DEPTH,
  num_iter = NUM_ITER,
  num_cutpoints = NUM_CUTPOINTS,
  equal_weight = EQUAL_WEIGHT,
  lambda_cov = LAMBDA_COV,
  lambda_cov_factor = LAMBDA_COV_FACTOR
)

rolling_params <- list(
  train_months = ROLLING_TRAIN_MONTHS,
  test_months = ROLLING_TEST_MONTHS,
  step_months = ROLLING_STEP_MONTHS
)

# Run boosted trees
boosting_results <- run_boosting()

# Run three-scenario validation
scenario_results <- run_three_scenarios(
  data_obj$data,
  data_obj$all_chars,
  data_obj$instruments,
  params,
  SCENARIOS,
  OUTPUT_DIR
)

# Run rolling window validation
rolling_results <- run_rolling_window(
  data_obj$data,
  data_obj$all_chars,
  data_obj$instruments,
  params,
  rolling_params,
  OUTPUT_DIR
)

# Final summary
cat("\n")
cat("================================================================================\n")
cat("ANALYSIS COMPLETE\n")
cat("================================================================================\n\n")
cat("Results saved to:", OUTPUT_DIR, "\n")
cat("  - boosted_trees/             (5 boosted P-Trees with cumulative factors)\n")
cat("  - scenario_full_sample/      (Full sample IS performance)\n")
cat("  - scenario_time_split/       (Forward split: Train early, Test late)\n")
cat("  - scenario_reverse_split/    (Reverse split: Train late, Test early)\n")
cat("  - rolling_window/            (Multiple OOS tests)\n\n")
cat("INTERPRETATION GUIDE:\n")
cat("  - IS Sharpe > 1:         Good in-sample fit\n")
cat("  - OOS Sharpe > 0:        Model has predictive power\n")
cat("  - OOS Sharpe > 0.5:      Strong predictive power\n")
cat("  - Positive OOS %:        Fraction of winning test periods\n")
cat("  - Low degradation:       Model is not overfitting\n\n")
