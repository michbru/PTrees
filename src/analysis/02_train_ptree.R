#!/usr/bin/env Rscript

# A2: Train P-Tree Models for Three Scenarios
# --------------------------------------------
# Scenario A: Full Sample (1999-06 to 2019-12) - train and evaluate on ALL data
# Scenario B: Time-Split (train 1999-06 to 2009-12, test 2010-01 to 2019-12)
# Scenario C: Reverse Split (train 2010-01 to 2019-12, test 1999-06 to 2009-12)
# NOTE: Sample constrained to 2019-12 to match factor coverage
#
# IMPORTANT: Scenarios B & C use TRUE OUT-OF-SAMPLE evaluation
# - Train model on training period
# - Use predict() to apply SAME tree structure to test period
#
# Swedish market configuration (current baseline):
# - Single tree (num_iter=1, eta=1.0)
# - Extreme capacity settings to allow complex trees if supported by data:
#   min_leaf_size=10, max_depth=6, num_cutpoints=100
# - No regularization: lambda_cov=0, lambda_ridge=0
# - Equal-weighted leaves (equal_weight=TRUE) chosen empirically for Sweden
#   (value-weighted can be tested as robustness)

suppressPackageStartupMessages({
  library(data.table)
})

if (!requireNamespace("PTree", quietly = TRUE)) {
  stop("The 'PTree' package is required. Install it before running.")
}

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")
out_dir <- file.path(repo_root, "results", "models")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

cat("\n=== A2: TRAIN P-TREE MODELS (THREE SCENARIOS) ===\n")
cat("Repo root:", repo_root, "\n\n")

if (!file.exists(in_rds)) stop(sprintf("Inputs RDS not found: %s\nRun A1 first.", in_rds))
inp <- readRDS(in_rds)

# Helper function to build training data from filtered dataset
build_train_data <- function(dt_sub, keep_chars, instr) {
  X <- as.matrix(dt_sub[, ..keep_chars])
  R <- as.vector(dt_sub$ret_next) * 100  # Scale to percent
  Y <- R
  Z <- cbind(Intercept = 1, if (length(instr)>0) as.matrix(dt_sub[, ..instr]) else NULL)
  months <- as.integer(as.factor(dt_sub$date)) - 1L
  stocks <- as.integer(as.factor(dt_sub$isin)) - 1L
  pw <- as.vector(dt_sub$lag_me)
  lw <- as.vector(dt_sub$lag_me)

  list(dt=dt_sub, X=X, R=R, Y=Y, Z=Z, months=months, stocks=stocks,
       num_months=length(unique(months)), num_stocks=length(unique(stocks)),
       pw=pw, lw=lw)
}

# Helper function to train P-Tree (flexible parameters)
train_ptree <- function(train_data, scenario_name, num_iter=1, eta=1.0) {
  cat(sprintf("\n--- Training %s ---\n", scenario_name))
  cat(sprintf("  Obs: %d | Months: %d | Stocks: %d\n",
              nrow(train_data$dt), train_data$num_months, train_data$num_stocks))
  cat(sprintf("  Date range: %s to %s\n",
              as.character(min(train_data$dt$date)), as.character(max(train_data$dt$date))))
  cat(sprintf("  Parameters: num_iter=%d, eta=%.2f\n", num_iter, eta))

  # Swedish market parameters (EXTREME capacity to allow deeper trees)
  min_leaf_size <- 10
  max_depth <- 6
  num_cutpoints <- 100
  # num_iter and eta passed as arguments

  suppressWarnings({
    fit <- PTree::PTree(
      train_data$R, train_data$Y, train_data$X, train_data$Z,
      H = rep(0, train_data$num_months),
      train_data$pw, train_data$lw,
      train_data$stocks, train_data$months,
      seq(0L, ncol(train_data$X)-1L), seq(0L, ncol(train_data$X)-1L),
      train_data$num_stocks, train_data$num_months,
      min_leaf_size = min_leaf_size,
      max_depth = max_depth,
      num_iter = num_iter,
      num_cutpoints = num_cutpoints,
      eta = eta,
      equal_weight = TRUE,
      no_H = TRUE,
      abs_normalize = TRUE,
      weighted_loss = FALSE,
      lambda_mean = 0,
      lambda_cov = 0,
      lambda_mean_factor = 0,
      lambda_cov_factor = 0,
      early_stop = FALSE,
      stop_threshold = 0.95,
      lambda_ridge = 0,
      a1 = 0, a2 = 0,
      list_K = matrix(rep(0, 3), nrow = 3, ncol = 1),
      random_split = FALSE
    )
  })

  ft <- as.numeric(fit$ft)
  mean_m <- mean(ft, na.rm=TRUE)
  std_m <- sd(ft, na.rm=TRUE)
  sharpe <- if (std_m > 0) mean_m / std_m * sqrt(12) else NA_real_

  # Extract leaf portfolios
  leaf_portfolios <- as.data.table(fit$portfolio)
  num_leaves <- ncol(leaf_portfolios)

  cat(sprintf("  ✓ Sharpe: %.2f | Mean: %.2f%% | SD: %.2f%% | Leaves: %d\n",
              sharpe, mean_m, std_m, num_leaves))

  list(fit=fit, ft=ft, mean=mean_m, sd=std_m, sharpe=sharpe,
       tree=as.character(fit$tree), leaf_portfolios=leaf_portfolios, num_leaves=num_leaves)
}

# Helper to evaluate factor on test data using predict (TRUE OUT-OF-SAMPLE)
evaluate_on_test <- function(train_model, test_data, scenario_name) {
  cat(sprintf("\n--- Evaluating %s on Test Set (OUT-OF-SAMPLE) ---\n", scenario_name))
  cat(sprintf("  Test obs: %d | Months: %d | Stocks: %d\n",
              nrow(test_data$dt), test_data$num_months, test_data$num_stocks))
  cat(sprintf("  Test range: %s to %s\n",
              as.character(min(test_data$dt$date)), as.character(max(test_data$dt$date))))

  # Use trained model to predict on test data
  # This applies the SAME tree structure learned from training data
  pred <- predict(train_model$fit, test_data$X, test_data$R, test_data$months, test_data$pw)

  ft <- as.numeric(pred$ft)
  mean_m <- mean(ft, na.rm=TRUE)
  std_m <- sd(ft, na.rm=TRUE)
  sharpe <- if (std_m > 0) mean_m / std_m * sqrt(12) else NA_real_

  # Extract leaf portfolios
  leaf_portfolios <- as.data.table(pred$portfolio)
  num_leaves <- ncol(leaf_portfolios)

  cat(sprintf("  ✓ OUT-OF-SAMPLE Sharpe: %.2f | Mean: %.2f%% | SD: %.2f%% | Leaves: %d\n",
              sharpe, mean_m, std_m, num_leaves))
  cat(sprintf("  (Using tree structure from training period)\n"))

  # Note: tree structure is from training model
  list(fit=train_model$fit, ft=ft, mean=mean_m, sd=std_m, sharpe=sharpe,
       tree=as.character(train_model$fit$tree), leaf_portfolios=leaf_portfolios,
       num_leaves=num_leaves, leaf_ids=pred$leaf_index)
}

# Load full dataset
dt_full <- copy(inp$dt)
keep_chars <- inp$char_cols
instr <- inp$instr_cols

# Define split date
split_date <- as.IDate("2010-01-01")

cat("Data availability:\n")
cat(sprintf("  Full range: %s to %s (%d months)\n",
            as.character(min(dt_full$date)), as.character(max(dt_full$date)),
            length(unique(dt_full$date))))
cat(sprintf("  Split date: %s\n", as.character(split_date)))
cat(sprintf("  Period 1 (train B): %s to %s (%d months)\n",
            as.character(min(dt_full[date < split_date]$date)),
            as.character(max(dt_full[date < split_date]$date)),
            length(unique(dt_full[date < split_date]$date))))
cat(sprintf("  Period 2 (train C): %s to %s (%d months)\n",
            as.character(min(dt_full[date >= split_date]$date)),
            as.character(max(dt_full[date >= split_date]$date)),
            length(unique(dt_full[date >= split_date]$date))))

# ==============================================================================
# MODEL COMPARISON: SINGLE TREE vs BOOSTED
# ==============================================================================
cat("\n\n╔════════════════════════════════════════════════╗\n")
cat("║     COMPARISON: SINGLE TREE vs BOOSTED        ║\n")
cat("╚════════════════════════════════════════════════╝\n")

# Use full sample for comparison
train_comp <- build_train_data(dt_full, keep_chars, instr)

# 1. Single Tree
model_single <- train_ptree(train_comp, "Single Tree", num_iter=1, eta=1.0)

# 2. Boosted Tree (e.g., 50 iterations, learning rate 0.1)
model_boosted <- train_ptree(train_comp, "Boosted Tree", num_iter=50, eta=0.1)

cat("\nComparison Results (In-Sample):\n")
cat(sprintf("  Single Tree (iter=1, eta=1.0): Sharpe = %.2f\n", model_single$sharpe))
cat(sprintf("  Boosted Tree (iter=50, eta=0.1): Sharpe = %.2f\n", model_boosted$sharpe))
cat("\nDecision: Using SINGLE TREE (num_iter=1) for main analysis as per thesis hypothesis.\n")

# Save comparison results
comp_table <- data.table(
  model = c("Single Tree", "Boosted Tree"),
  num_iter = c(1, 50),
  eta = c(1.0, 0.1),
  sharpe = c(model_single$sharpe, model_boosted$sharpe),
  mean_monthly = c(model_single$mean, model_boosted$mean),
  std_monthly = c(model_single$sd, model_boosted$sd)
)
fwrite(comp_table, file.path(out_dir, "model_comparison.csv"))


# ==============================================================================
# SCENARIO A: FULL SAMPLE
# ==============================================================================
cat("\n\n╔════════════════════════════════════════════════╗\n")
cat("║     SCENARIO A: FULL SAMPLE (1999-2019)       ║\n")
cat("╚════════════════════════════════════════════════╝\n")

train_a <- build_train_data(dt_full, keep_chars, instr)
model_a <- train_ptree(train_a, "Scenario A", num_iter=1, eta=1.0)

# Save outputs
fwrite(data.table(date=sort(unique(dt_full$date)), factor=model_a$ft),
       file.path(out_dir, "scenario_a_factor.csv"))
writeLines(model_a$tree, file.path(out_dir, "scenario_a_tree.txt"))
fwrite(data.table(
  metric=c("mean_monthly","std_monthly","sharpe_annual","annualized_return","annualized_vol","num_leaves"),
  value=c(model_a$mean, model_a$sd, model_a$sharpe, model_a$mean*12, model_a$sd*sqrt(12), model_a$num_leaves)
), file.path(out_dir, "scenario_a_summary.csv"))

# Save leaf portfolios
leaf_a <- copy(model_a$leaf_portfolios)
leaf_a[, date := sort(unique(dt_full$date))]
setcolorder(leaf_a, c("date", setdiff(names(leaf_a), "date")))
setnames(leaf_a, old=paste0("V", 1:model_a$num_leaves), new=paste0("leaf_", 1:model_a$num_leaves))
fwrite(leaf_a, file.path(out_dir, "scenario_a_leaf_portfolios.csv"))

# ==============================================================================
# SCENARIO B: TIME-SPLIT (Past predicting Future)
# ==============================================================================
cat("\n\n╔════════════════════════════════════════════════╗\n")
cat("║   SCENARIO B: PAST → FUTURE (1999-2009 train) ║\n")
cat("╚════════════════════════════════════════════════╝\n")

train_b <- build_train_data(dt_full[date < split_date], keep_chars, instr)
test_b <- build_train_data(dt_full[date >= split_date], keep_chars, instr)

model_b_train <- train_ptree(train_b, "Scenario B - Train (1999-2009)", num_iter=1, eta=1.0)
model_b_test <- evaluate_on_test(model_b_train, test_b, "Scenario B")

# Save outputs
fwrite(data.table(date=sort(unique(train_b$dt$date)), factor=model_b_train$ft),
       file.path(out_dir, "scenario_b_train_factor.csv"))
fwrite(data.table(date=sort(unique(test_b$dt$date)), factor=model_b_test$ft),
       file.path(out_dir, "scenario_b_test_factor.csv"))
writeLines(model_b_train$tree, file.path(out_dir, "scenario_b_train_tree.txt"))
# Test uses SAME tree structure as training (out-of-sample)
writeLines(model_b_train$tree, file.path(out_dir, "scenario_b_test_tree.txt"))
fwrite(data.table(
  period=c("train","test"),
  sharpe=c(model_b_train$sharpe, model_b_test$sharpe),
  mean_monthly=c(model_b_train$mean, model_b_test$mean),
  std_monthly=c(model_b_train$sd, model_b_test$sd),
  num_leaves=c(model_b_train$num_leaves, model_b_test$num_leaves)
), file.path(out_dir, "scenario_b_summary.csv"))

# Save leaf portfolios
leaf_b_test <- copy(model_b_test$leaf_portfolios)
leaf_b_test[, date := sort(unique(test_b$dt$date))]
setcolorder(leaf_b_test, c("date", setdiff(names(leaf_b_test), "date")))
setnames(leaf_b_test, old=paste0("V", 1:model_b_test$num_leaves), new=paste0("leaf_", 1:model_b_test$num_leaves))
fwrite(leaf_b_test, file.path(out_dir, "scenario_b_test_leaf_portfolios.csv"))

# ==============================================================================
# SCENARIO C: REVERSE SPLIT (Future predicting Past)
# ==============================================================================
cat("\n\n╔════════════════════════════════════════════════╗\n")
cat("║   SCENARIO C: FUTURE → PAST (2010-2020 train) ║\n")
cat("╚════════════════════════════════════════════════╝\n")

train_c <- build_train_data(dt_full[date >= split_date], keep_chars, instr)
test_c <- build_train_data(dt_full[date < split_date], keep_chars, instr)

model_c_train <- train_ptree(train_c, "Scenario C - Train (2010-2020)", num_iter=1, eta=1.0)
model_c_test <- evaluate_on_test(model_c_train, test_c, "Scenario C")

# Save outputs
fwrite(data.table(date=sort(unique(train_c$dt$date)), factor=model_c_train$ft),
       file.path(out_dir, "scenario_c_train_factor.csv"))
fwrite(data.table(date=sort(unique(test_c$dt$date)), factor=model_c_test$ft),
       file.path(out_dir, "scenario_c_test_factor.csv"))
writeLines(model_c_train$tree, file.path(out_dir, "scenario_c_train_tree.txt"))
# Test uses SAME tree structure as training (out-of-sample)
writeLines(model_c_train$tree, file.path(out_dir, "scenario_c_test_tree.txt"))
fwrite(data.table(
  period=c("train","test"),
  sharpe=c(model_c_train$sharpe, model_c_test$sharpe),
  mean_monthly=c(model_c_train$mean, model_c_test$mean),
  std_monthly=c(model_c_train$sd, model_c_test$sd),
  num_leaves=c(model_c_train$num_leaves, model_c_test$num_leaves)
), file.path(out_dir, "scenario_c_summary.csv"))

# Save leaf portfolios
leaf_c_test <- copy(model_c_test$leaf_portfolios)
leaf_c_test[, date := sort(unique(test_c$dt$date))]
setcolorder(leaf_c_test, c("date", setdiff(names(leaf_c_test), "date")))
setnames(leaf_c_test, old=paste0("V", 1:model_c_test$num_leaves), new=paste0("leaf_", 1:model_c_test$num_leaves))
fwrite(leaf_c_test, file.path(out_dir, "scenario_c_test_leaf_portfolios.csv"))

# ==============================================================================
# FINAL SUMMARY TABLE (like Table 1 in thesis)
# ==============================================================================
cat("\n\n╔════════════════════════════════════════════════╗\n")
cat("║         SUMMARY: ALL SCENARIOS                 ║\n")
cat("╚════════════════════════════════════════════════╝\n")

summary_table <- data.table(
  scenario = c("A: Full Sample", "B: Time-Split (test)", "C: Reverse Split (test)"),
  sharpe_ratio = c(model_a$sharpe, model_b_test$sharpe, model_c_test$sharpe),
  mean_monthly_pct = c(model_a$mean, model_b_test$mean, model_c_test$mean),
  std_monthly_pct = c(model_a$sd, model_b_test$sd, model_c_test$sd),
  annualized_return_pct = c(model_a$mean*12, model_b_test$mean*12, model_c_test$mean*12)
)

print(summary_table)
fwrite(summary_table, file.path(out_dir, "all_scenarios_summary.csv"))

cat("\n✓ All scenario models saved to:", normalizePath(out_dir, mustWork=FALSE), "\n")
cat("\nNOTE: CAPM and FF3 alphas will be calculated in Step 3 (evaluation)\n")
cat("\nA2 complete.\n\n")
