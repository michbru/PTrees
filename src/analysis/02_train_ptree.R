#!/usr/bin/env Rscript

################################################################################
# Step 2: Train P-Tree Models
################################################################################
#
# Purpose: Train single P-Tree for each scenario following Cong et al. (2024)
#
# Model: ONE P-Tree per scenario (not boosted ensemble, just one tree)
# - The tree grows by iteratively splitting the cross-section
# - Optimizes Sharpe ratio at each split
# - Output: Factor time series (monthly returns of tangency portfolio)
#
# Scenarios:
#   A: Full sample (1998-2019) - In-sample performance
#   B: Train 1998-2009, Test 2010-2019 - Out-of-sample forward
#   C: Train 2010-2019, Test 1998-2009 - Out-of-sample reverse
#
################################################################################

suppressPackageStartupMessages({
  library(data.table)
})

if (!requireNamespace("PTree", quietly = TRUE)) {
  stop("PTree package required. Install from: devtools::install_github('bpf_ptree/PTree')")
}

# Set seed for reproducibility
set.seed(42)

# Paths
args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- if (length(file_arg) > 0) dirname(normalizePath(file_arg)) else getwd()
repo_root <- normalizePath(file.path(script_dir, "..", ".."))
setwd(repo_root)

INPUT_RDS <- "results/inputs/ptree_inputs.rds"
OUTPUT_DIR <- "results/models"

# Clear output directory - start fresh
if (dir.exists(OUTPUT_DIR)) {
  cat("Clearing previous model outputs...\n")
  unlink(OUTPUT_DIR, recursive = TRUE)
}
dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

cat("================================================================================\n")
cat("STEP 2: TRAIN P-TREE MODELS\n")
cat("================================================================================\n\n")

if (!file.exists(INPUT_RDS)) {
  stop("Input file not found. Run 01_prepare_inputs.R first.")
}

inp <- readRDS(INPUT_RDS)
dt <- copy(inp$dt)
char_cols <- inp$char_cols
instr_cols <- inp$instr_cols

cat(sprintf("Dataset loaded: %s obs, %s firms, %s months, %d characteristics\n\n",
            format(nrow(dt), big.mark=","),
            format(length(unique(dt$isin)), big.mark=","),
            format(length(unique(dt$date)), big.mark=","),
            length(char_cols)))

################################################################################
# Hyperparameters (Following Cong et al. 2024, adjusted for Swedish market)
################################################################################

PARAMS <- list(
  # Tree structure
  max_depth = 10,           # Maximum tree depth (paper: 10)
  min_leaf_size = 3,        # Min stocks per leaf (paper: 3, scaled for market size)
  num_cutpoints = 4,        # Split thresholds: {-0.6, -0.2, 0.2, 0.6} -> quintiles
  
  # Regularization
  gamma = 1e-4,             # Covariance shrinkage (paper: 1e-4)
  lambda = 1e-5,            # Factor covariance shrinkage (paper: 1e-5)
  
  # Weighting
  equal_weight = TRUE,      # Equal-weighted leaf portfolios (paper default)
  abs_normalize = TRUE      # Normalize by absolute values (paper default)
)

cat("Hyperparameters:\n")
for (name in names(PARAMS)) {
  cat(sprintf("  %s: %s\n", name, PARAMS[[name]]))
}
cat("\n")


################################################################################
# Helper: Prepare Training Data
################################################################################

prepare_data <- function(dt_subset, char_cols, instr_cols) {
  # Characteristics matrix (cross-sectionally ranked, already done in step 1)
  X <- as.matrix(dt_subset[, .SD, .SDcols = char_cols])
  
  # Returns (decimal, not percentage)
  R <- as.vector(dt_subset$ret_next)
  Y <- R  # Target returns (same as R for P-Tree)
  
  # Instruments (for portfolio optimization, paper uses intercept only)
  Z <- matrix(1, nrow = nrow(dt_subset), ncol = 1)
  colnames(Z) <- "Intercept"
  
  # Time and firm indices (0-indexed for C++ backend)
  months <- as.integer(as.factor(dt_subset$date)) - 1L
  stocks <- as.integer(as.factor(dt_subset$isin)) - 1L
  
  # Weights (market cap)
  pw <- as.vector(dt_subset$lag_me)  # Portfolio weights
  lw <- as.vector(dt_subset$lag_me)  # Leaf weights
  
  list(
    dt = dt_subset,
    X = X,
    R = R,
    Y = Y,
    Z = Z,
    months = months,
    stocks = stocks,
    num_months = length(unique(months)),
    num_stocks = length(unique(stocks)),
    pw = pw,
    lw = lw
  )
}

################################################################################
# Helper: Train Single P-Tree
################################################################################

train_single_ptree <- function(train_data, scenario_name, params = PARAMS) {
  cat(sprintf("\n--- Training: %s ---\n", scenario_name))
  cat(sprintf("  Observations: %s\n", format(nrow(train_data$dt), big.mark=",")))
  cat(sprintf("  Time periods: %d months\n", train_data$num_months))
  cat(sprintf("  Firms: %d\n", train_data$num_stocks))
  cat(sprintf("  Characteristics: %d\n", ncol(train_data$X)))
  
  t_start <- Sys.time()
  
  # Train P-Tree (single tree, not boosted)
  suppressWarnings({
    fit <- PTree::PTree(
      # Data
      R = train_data$R,                    # Returns
      Y = train_data$Y,                    # Target (same as R)
      X = train_data$X,                    # Characteristics
      Z = train_data$Z,                    # Instruments (intercept)
      H = rep(0, train_data$num_months),  # No pre-existing factors
      portfolio_weight = train_data$pw,    # Portfolio weights
      loss_weight = train_data$lw,         # Loss weights
      stocks = train_data$stocks,          # Stock indices
      months = train_data$months,          # Month indices

      # Split variables (all characteristics)
      first_split_var = seq(0L, ncol(train_data$X) - 1L),
      second_split_var = seq(0L, ncol(train_data$X) - 1L),

      # Dimensions
      num_stocks = train_data$num_stocks,
      num_months = train_data$num_months,

      # Tree structure parameters
      min_leaf_size = params$min_leaf_size,
      max_depth = params$max_depth,
      num_cutpoints = params$num_cutpoints,
      
      # Training parameters
      num_iter = 1,                        # Single tree (no boosting)
      eta = 1.0,                           # Learning rate (not used for single tree)
      equal_weight = params$equal_weight,
      abs_normalize = params$abs_normalize,
      
      # Regularization
      lambda_mean = 0,
      lambda_cov = params$gamma,           # Covariance shrinkage
      lambda_mean_factor = 0,
      lambda_cov_factor = params$lambda,   # Factor covariance shrinkage
      lambda_ridge = 1e-6,                 # Ridge for numerical stability
      
      # Other settings
      no_H = TRUE,                         # Don't use H (no boosting)
      weighted_loss = FALSE,               # Unweighted loss
      early_stop = FALSE,                  # No early stopping
      stop_threshold = 1.0,
      random_split = FALSE,                # Deterministic splits
      a1 = 0,
      a2 = 0,
      list_K = matrix(0, nrow = 3, ncol = 1)
    )
  })
  
  duration <- as.numeric(difftime(Sys.time(), t_start, units = "secs"))
  
  # Extract factor (tangency portfolio time series)
  factor_returns <- as.numeric(fit$ft)
  
  # Calculate performance metrics
  mean_monthly <- mean(factor_returns, na.rm = TRUE)
  sd_monthly <- sd(factor_returns, na.rm = TRUE)
  sharpe <- if (sd_monthly > 0) mean_monthly / sd_monthly * sqrt(12) else NA_real_
  
  cat(sprintf("\n  Training completed in %.1f seconds\n", duration))
  cat(sprintf("  Factor performance:\n"))
  cat(sprintf("    Mean monthly return: %.4f (%.2f%%)\n", mean_monthly, mean_monthly * 100))
  cat(sprintf("    Monthly std dev: %.4f (%.2f%%)\n", sd_monthly, sd_monthly * 100))
  cat(sprintf("    Annualized Sharpe: %.3f\n", sharpe))
  
  # Extract tree structure information
  tree_str <- capture.output(print(fit$tree))
  # Count leaves from tree structure (tree is a matrix where col 2 and 3 are children)
  # Leaves have 0 in both child columns
  tree_matrix <- fit$tree
  if (is.matrix(tree_matrix)) {
    num_leaves <- sum(tree_matrix[, 2] == 0 & tree_matrix[, 3] == 0)
  } else {
    num_leaves <- NA
  }

  if (!is.na(num_leaves)) {
    cat(sprintf("    Number of leaves: %d\n", num_leaves))
  }
  
  list(
    fit = fit,
    factor_returns = factor_returns,
    mean = mean_monthly,
    sd = sd_monthly,
    sharpe = sharpe,
    num_leaves = num_leaves,
    tree_structure = tree_str,
    duration_sec = duration
  )
}

################################################################################
# Helper: Predict on Test Data
################################################################################

predict_ptree <- function(model, test_data, scenario_name) {
  cat(sprintf("\n--- Predicting: %s ---\n", scenario_name))
  cat(sprintf("  Test observations: %s\n", format(nrow(test_data$dt), big.mark=",")))
  cat(sprintf("  Test periods: %d months\n", test_data$num_months))
  
  # Predict using trained model
  # Note: predict.PTree only takes (object, X, R, months) - no pw argument
  pred <- predict(
    model$fit,
    X = test_data$X,
    R = test_data$R,
    months = test_data$months
  )
  
  factor_returns <- as.numeric(pred$ft)
  
  # Calculate metrics
  mean_monthly <- mean(factor_returns, na.rm = TRUE)
  sd_monthly <- sd(factor_returns, na.rm = TRUE)
  sharpe <- if (sd_monthly > 0) mean_monthly / sd_monthly * sqrt(12) else NA_real_
  
  cat(sprintf("  Test performance:\n"))
  cat(sprintf("    Mean monthly return: %.4f (%.2f%%)\n", mean_monthly, mean_monthly * 100))
  cat(sprintf("    Monthly std dev: %.4f (%.2f%%)\n", sd_monthly, sd_monthly * 100))
  cat(sprintf("    Annualized Sharpe: %.3f\n", sharpe))
  
  list(
    factor_returns = factor_returns,
    mean = mean_monthly,
    sd = sd_monthly,
    sharpe = sharpe
  )
}

################################################################################
# Helper: Save Results
################################################################################

save_results <- function(model, test_results = NULL, scenario_name, train_data, test_data = NULL) {
  # 1. Factor returns (train)
  factor_dt <- data.table(
    date = unique(train_data$dt$date),
    factor_return = model$factor_returns
  )
  fwrite(factor_dt, file.path(OUTPUT_DIR, sprintf("scenario_%s_1_factor.csv", tolower(scenario_name))))
  
  # 2. Factor returns (test, if applicable)
  if (!is.null(test_results) && !is.null(test_data)) {
    factor_test_dt <- data.table(
      date = unique(test_data$dt$date),
      factor_return = test_results$factor_returns
    )
    fwrite(factor_test_dt, file.path(OUTPUT_DIR, sprintf("scenario_%s_test_1_factor.csv", tolower(scenario_name))))
  }
  
  # 3. Tree structure
  writeLines(model$tree_structure, file.path(OUTPUT_DIR, sprintf("scenario_%s_trees.txt", tolower(scenario_name))))
  
  # 4. Summary statistics
  summary_dt <- data.table(
    scenario = scenario_name,
    dataset = c("train", if (!is.null(test_results)) "test" else NULL),
    n_obs = c(nrow(train_data$dt), if (!is.null(test_data)) nrow(test_data$dt) else NULL),
    n_months = c(train_data$num_months, if (!is.null(test_data)) test_data$num_months else NULL),
    n_stocks = c(train_data$num_stocks, if (!is.null(test_data)) test_data$num_stocks else NULL),
    mean_monthly = c(model$mean, if (!is.null(test_results)) test_results$mean else NULL),
    sd_monthly = c(model$sd, if (!is.null(test_results)) test_results$sd else NULL),
    sharpe_annual = c(model$sharpe, if (!is.null(test_results)) test_results$sharpe else NULL),
    num_leaves = c(model$num_leaves, if (!is.null(test_results)) model$num_leaves else NULL),
    train_duration_sec = c(model$duration_sec, NA)
  )
  fwrite(summary_dt, file.path(OUTPUT_DIR, sprintf("scenario_%s_summary.csv", tolower(scenario_name))))
  
  # 5. Model object (for later analysis)
  saveRDS(model$fit, file.path(OUTPUT_DIR, sprintf("scenario_%s_model.rds", tolower(scenario_name))))
  
  cat(sprintf("\n  ✓ Results saved for scenario %s\n", scenario_name))
}


################################################################################
# SCENARIO A: Full Sample (In-Sample)
################################################################################

cat("\n")
cat("================================================================================\n")
cat("SCENARIO A: FULL SAMPLE (1998-2019)\n")
cat("================================================================================\n")

train_a <- prepare_data(dt, char_cols, instr_cols)
model_a <- train_single_ptree(train_a, "Scenario A", PARAMS)
save_results(model_a, NULL, "a", train_a, NULL)

################################################################################
# SCENARIO B: Time Split (Train: 1998-2009, Test: 2010-2019)
################################################################################

cat("\n")
cat("================================================================================\n")
cat("SCENARIO B: TIME SPLIT (Past → Future)\n")
cat("================================================================================\n")

split_date <- as.IDate("2010-01-01")
dt_train_b <- dt[date < split_date]
dt_test_b <- dt[date >= split_date]

cat(sprintf("\nTrain: %s to %s (%d obs)\n", 
            min(dt_train_b$date), max(dt_train_b$date), nrow(dt_train_b)))
cat(sprintf("Test:  %s to %s (%d obs)\n", 
            min(dt_test_b$date), max(dt_test_b$date), nrow(dt_test_b)))

train_b <- prepare_data(dt_train_b, char_cols, instr_cols)
test_b <- prepare_data(dt_test_b, char_cols, instr_cols)

model_b <- train_single_ptree(train_b, "Scenario B (Train)", PARAMS)
test_results_b <- predict_ptree(model_b, test_b, "Scenario B (Test)")
save_results(model_b, test_results_b, "b", train_b, test_b)

################################################################################
# SCENARIO C: Reverse Split (Train: 2010-2019, Test: 1998-2009)
################################################################################

cat("\n")
cat("================================================================================\n")
cat("SCENARIO C: REVERSE SPLIT (Future → Past)\n")
cat("================================================================================\n")

dt_train_c <- dt[date >= split_date]
dt_test_c <- dt[date < split_date]

cat(sprintf("\nTrain: %s to %s (%d obs)\n", 
            min(dt_train_c$date), max(dt_train_c$date), nrow(dt_train_c)))
cat(sprintf("Test:  %s to %s (%d obs)\n", 
            min(dt_test_c$date), max(dt_test_c$date), nrow(dt_test_c)))

train_c <- prepare_data(dt_train_c, char_cols, instr_cols)
test_c <- prepare_data(dt_test_c, char_cols, instr_cols)

model_c <- train_single_ptree(train_c, "Scenario C (Train)", PARAMS)
test_results_c <- predict_ptree(model_c, test_c, "Scenario C (Test)")
save_results(model_c, test_results_c, "c", train_c, test_c)

################################################################################
# Final Summary
################################################################################

cat("\n")
cat("================================================================================\n")
cat("TRAINING COMPLETE\n")
cat("================================================================================\n\n")

cat("Results saved to:", normalizePath(OUTPUT_DIR), "\n\n")

cat("Files per scenario:\n")
cat("  - scenario_X_1_factor.csv       : Factor returns (train)\n")
cat("  - scenario_X_ensemble.csv       : Same as above (compatibility)\n")
cat("  - scenario_X_test_1_factor.csv  : Factor returns (test, B & C only)\n")
cat("  - scenario_X_test_ensemble.csv  : Same as above (compatibility)\n")
cat("  - scenario_X_trees.txt          : Tree structure\n")
cat("  - scenario_X_summary.csv        : Performance metrics\n")
cat("  - scenario_X_model.rds          : Trained model object\n\n")

# Quick comparison table
summary_comparison <- data.table(
  Scenario = c("A (Full)", "B (Train)", "B (Test)", "C (Train)", "C (Test)"),
  Sharpe = c(
    model_a$sharpe,
    model_b$sharpe,
    test_results_b$sharpe,
    model_c$sharpe,
    test_results_c$sharpe
  ),
  Mean_Monthly = c(
    model_a$mean,
    model_b$mean,
    test_results_b$mean,
    model_c$mean,
    test_results_c$mean
  ),
  SD_Monthly = c(
    model_a$sd,
    model_b$sd,
    test_results_b$sd,
    model_c$sd,
    test_results_c$sd
  ),
  Num_Leaves = c(
    model_a$num_leaves,
    model_b$num_leaves,
    NA,
    model_c$num_leaves,
    NA
  )
)

cat("Performance Summary:\n")
print(summary_comparison, digits = 4)

cat("\n")
cat("================================================================================\n")

