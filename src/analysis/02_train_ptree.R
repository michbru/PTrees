#!/usr/bin/env Rscript

# A2: Train P-Tree Models (Single + Boosted) with Auto Tuning
# ------------------------------------------------------------
# - Trains both single-tree (num_iter=1) and boosted (num_iter>1) variants
# - Performs parameter tuning on a validation split (pre-2010 only)
# - Saves rich outputs: factor returns, leaf portfolios, tree text, summaries,
#   parameter choices, and descriptive statistics for table building

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

cat("\n╔════════════════════════════════════════════════╗\n")
cat("║   A2: TRAIN P-TREE MODELS (SINGLE + BOOSTED)  ║\n")
cat("╚════════════════════════════════════════════════╝\n\n")

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

# Helper function to train P-Tree with configurable params
train_ptree <- function(train_data, scenario_name,
                        num_iter=1, eta=0.10,
                        min_leaf_size=100, max_depth=3, num_cutpoints=50,
                        equal_weight=TRUE, weighted_loss=FALSE,
                        lambda_ridge=0,
                        abs_normalize=TRUE) {
  cat(sprintf("\n╔════════════════════════════════════════════════╗\n"))
  cat(sprintf("║   %s\n", scenario_name))
  cat(sprintf("╚════════════════════════════════════════════════╝\n\n"))

  cat(sprintf("  Obs: %d | Months: %d | Stocks: %d\n",
              nrow(train_data$dt), train_data$num_months, train_data$num_stocks))
  cat(sprintf("  Date range: %s to %s\n",
              as.character(min(train_data$dt$date)), as.character(max(train_data$dt$date))))
  cat(sprintf("  Parameters: num_iter=%d, eta=%.2f, min_leaf=%d, depth=%d, cuts=%d\n",
              num_iter, eta, min_leaf_size, max_depth, num_cutpoints))

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
      equal_weight = equal_weight,
      no_H = TRUE,
      abs_normalize = abs_normalize,
      weighted_loss = weighted_loss,
      lambda_mean = 0,
      lambda_cov = 0,
      lambda_mean_factor = 0,
      lambda_cov_factor = 0,
      early_stop = FALSE,
      stop_threshold = 0.999,
      lambda_ridge = lambda_ridge,
      a1 = 0, a2 = 0,
      list_K = matrix(rep(0, 3), nrow = 3, ncol = 1),
      random_split = FALSE
    )
  })

  ft <- as.numeric(fit$ft)
  mean_m <- mean(ft, na.rm=TRUE)
  std_m <- sd(ft, na.rm=TRUE)
  sharpe <- if (std_m > 0) mean_m / std_m * sqrt(12) else NA_real_
  annualized_return <- mean_m * 12

  # Extract leaf portfolios
  leaf_portfolios <- as.data.table(fit$portfolio)
  num_leaves <- ncol(leaf_portfolios)

  # Parse tree structure to count actual depth
  tree_str <- as.character(fit$tree)

  cat(sprintf("\n  ✓ RESULTS:\n"))
  cat(sprintf("    Leaves: %d | Tree Depth: %d nodes\n", num_leaves, length(tree_str)))
  cat(sprintf("    Sharpe: %.2f | Mean: %.2f%% | SD: %.2f%%\n", sharpe, mean_m, std_m))
  cat(sprintf("    Annualized Return: %.2f%%\n", annualized_return))

  list(fit=fit, ft=ft, mean=mean_m, sd=std_m, sharpe=sharpe,
       tree=tree_str, leaf_portfolios=leaf_portfolios, num_leaves=num_leaves,
       annualized_return=annualized_return)
}

# Helper to evaluate factor on test data
evaluate_on_test <- function(train_model, test_data, scenario_name) {
  cat(sprintf("\n--- OUT-OF-SAMPLE Evaluation: %s ---\n", scenario_name))
  cat(sprintf("  Test obs: %d | Months: %d | Stocks: %d\n",
              nrow(test_data$dt), test_data$num_months, test_data$num_stocks))

  pred <- predict(train_model$fit, test_data$X, test_data$R, test_data$months, test_data$pw)

  ft <- as.numeric(pred$ft)
  mean_m <- mean(ft, na.rm=TRUE)
  std_m <- sd(ft, na.rm=TRUE)
  sharpe <- if (std_m > 0) mean_m / std_m * sqrt(12) else NA_real_
  annualized_return <- mean_m * 12

  cat(sprintf("  ✓ OUT-OF-SAMPLE Sharpe: %.2f | Mean: %.2f%% | SD: %.2f%%\n",
              sharpe, mean_m, std_m))
  cat(sprintf("  Annualized Return: %.2f%%\n", annualized_return))

  list(ft=ft, mean=mean_m, sd=std_m, sharpe=sharpe, annualized_return=annualized_return)
}

# Helper to compute descriptive statistics for factor time series
factor_descriptives <- function(ft) {
  x <- as.numeric(ft)
  x <- x[is.finite(x)]
  if (!length(x)) return(data.table())
  ann <- 12
  m <- mean(x)
  s <- sd(x)
  data.table(
    mean_monthly = m,
    sd_monthly = s,
    sharpe = ifelse(s > 0, m/s*sqrt(ann), NA_real_),
    ann_return = m*ann,
    min = min(x),
    p05 = as.numeric(quantile(x, 0.05)),
    median = median(x),
    p95 = as.numeric(quantile(x, 0.95)),
    max = max(x)
  )
}

# Helper to save results
save_scenario_results <- function(model, eval_results, scenario_name, train_data, test_data=NULL, is_test=FALSE, params=list()) {
  suffix <- if (is_test) "_test" else ""

  # Factor returns
  factor_dt <- data.table(
    date = if (is_test) unique(test_data$dt$date) else unique(train_data$dt$date),
    factor = if (is_test) eval_results$ft else model$ft
  )
  fwrite(factor_dt, file.path(out_dir, sprintf("%s%s_factor.csv", scenario_name, suffix)))

  # Leaf portfolios
  fwrite(model$leaf_portfolios, file.path(out_dir, sprintf("%s%s_leaf_portfolios.csv", scenario_name, suffix)))

  # Tree structure
  writeLines(model$tree, file.path(out_dir, sprintf("%s%s_tree.txt", scenario_name, suffix)))

  # Summary stats
  summary <- data.table(
    scenario = scenario_name,
    test = is_test,
    sharpe_ratio = if (is_test) eval_results$sharpe else model$sharpe,
    mean_monthly_pct = if (is_test) eval_results$mean else model$mean,
    std_monthly_pct = if (is_test) eval_results$sd else model$sd,
    annualized_return_pct = if (is_test) eval_results$annualized_return else model$annualized_return,
    num_leaves = model$num_leaves
  )
  fwrite(summary, file.path(out_dir, sprintf("%s%s_summary.csv", scenario_name, suffix)))

  # Descriptive statistics for factor series
  desc <- factor_descriptives(factor_dt$factor)
  fwrite(desc, file.path(out_dir, sprintf("%s%s_descriptives.csv", scenario_name, suffix)))

  # Parameter snapshot (for reproducibility)
  if (length(params)) {
    params_dt <- as.data.table(params)
    fwrite(params_dt, file.path(out_dir, sprintf("%s_params%s.csv", scenario_name, suffix)))
  }

  # Save trained model object (RDS) for downstream evaluation/visualization
  # Only save once per base scenario (without _test suffix)
  model_rds <- file.path(out_dir, sprintf("%s_model.rds", scenario_name))
  if (!file.exists(model_rds)) {
    saveRDS(model$fit, model_rds)
  }
}

# Build time-based CV folds within a dataset (pre-2010)
make_time_folds <- function(dt_sub, val_window_months = 24L, num_folds = 3L, min_train_months = 60L) {
  months <- sort(unique(dt_sub$date))
  n_months <- length(months)
  folds <- list()
  for (k in seq_len(num_folds)) {
    val_end_idx <- n_months - (num_folds - k) * val_window_months
    val_start_idx <- val_end_idx - val_window_months + 1
    if (val_start_idx <= 1) next
    train_end_idx <- val_start_idx - 1
    if (train_end_idx < min_train_months) next
    tr_start <- months[1]
    tr_end   <- months[train_end_idx]
    va_start <- months[val_start_idx]
    va_end   <- months[val_end_idx]
    folds[[length(folds) + 1]] <- list(
      name = sprintf("Fold %d: %s..%s | %s..%s", k, as.character(tr_start), as.character(tr_end), as.character(va_start), as.character(va_end)),
      train = dt_sub[date >= tr_start & date <= tr_end],
      val   = dt_sub[date >= va_start & date <= va_end]
    )
  }
  folds
}

# Time-based CV tuner: averages OOS Sharpe across folds
tune_params_cv <- function(dt_for_tuning, keep_chars, instr, model_type = c("single","boosted"),
                           val_window_months = 24L, num_folds = 3L, min_train_months = 60L) {
  model_type <- match.arg(model_type)
  grid <- list()
  if (model_type == "single") {
    grid <- CJ(
      num_iter = 1L,
      eta = 0.10,
      min_leaf_size = c(50L, 100L),
      max_depth = c(2L, 3L),
      num_cutpoints = 50L
    )
  } else {
    grid <- CJ(
      num_iter = c(25L, 50L),
      eta = c(0.05, 0.10),
      min_leaf_size = c(10L, 25L),
      max_depth = c(4L, 6L),
      num_cutpoints = 50L
    )
  }

  folds <- make_time_folds(dt_for_tuning, val_window_months, num_folds, min_train_months)
  cat(sprintf("\nUsing %d time-based CV folds (val window %d months)\n", length(folds), val_window_months))
  for (f in folds) cat("  ", f$name, "\n")

  res_rows <- list()
  best <- NULL
  best_sharpe <- -Inf

  for (i in seq_len(nrow(grid))) {
    g <- grid[i]
    cat(sprintf("\n[TUNE %s] %d/%d: iter=%d eta=%.2f min_leaf=%d depth=%d cuts=%d\n",
                toupper(model_type), i, nrow(grid), g$num_iter, g$eta,
                g$min_leaf_size, g$max_depth, g$num_cutpoints))
    fold_sharpes <- c()
    for (fi in seq_along(folds)) {
      fdef <- folds[[fi]]
      tr <- build_train_data(fdef$train, keep_chars, instr)
      va <- build_train_data(fdef$val, keep_chars, instr)
      fit <- train_ptree(
        tr, sprintf("TUNE %s | %s", toupper(model_type), fdef$name),
        num_iter = g$num_iter,
        eta = g$eta,
        min_leaf_size = g$min_leaf_size,
        max_depth = g$max_depth,
        num_cutpoints = g$num_cutpoints
      )
      ev <- evaluate_on_test(fit, va, sprintf("Val %s", model_type))
      fold_sharpes <- c(fold_sharpes, ev$sharpe)
    }
    mean_sharpe <- mean(fold_sharpes, na.rm = TRUE)
    res_rows[[length(res_rows) + 1]] <- data.table(
      num_iter = g$num_iter, eta = g$eta, min_leaf_size = g$min_leaf_size,
      max_depth = g$max_depth, num_cutpoints = g$num_cutpoints,
      mean_val_sharpe = mean_sharpe
    )
    if (is.finite(mean_sharpe) && mean_sharpe > best_sharpe) {
      best_sharpe <- mean_sharpe
      best <- list(
        num_iter = g$num_iter,
        eta = g$eta,
        min_leaf_size = g$min_leaf_size,
        max_depth = g$max_depth,
        num_cutpoints = g$num_cutpoints,
        val_sharpe = mean_sharpe
      )
    }
  }

  res_dt <- rbindlist(res_rows)
  out_name <- file.path(out_dir, sprintf("tuning_%s_cv.csv", model_type))
  fwrite(res_dt, out_name)
  cat(sprintf("\nBest %s params by mean CV Sharpe: %s\n",
              model_type, paste(names(best), unlist(best), sep='=', collapse=', ')))
  best
}

# ============================================================================
# MAIN TRAINING LOOP
# ============================================================================

dt <- copy(inp$dt)
split_date <- as.IDate("2010-01-01")
val_split_date <- as.IDate("2007-01-01")

cat("Data availability:\n")
cat(sprintf("  Full range: %s to %s (%d months)\n",
            min(dt$date), max(dt$date), length(unique(dt$date))))
cat(sprintf("  Split date: %s\n", split_date))
cat(sprintf("  Validation split (within train): %s\n", val_split_date))

dt_period1 <- dt[date < split_date]
dt_period2 <- dt[date >= split_date]

cat(sprintf("  Period 1 (train B): %s to %s (%d months)\n",
            min(dt_period1$date), max(dt_period1$date), length(unique(dt_period1$date))))
cat(sprintf("  Period 2 (train C): %s to %s (%d months)\n\n",
            min(dt_period2$date), max(dt_period2$date), length(unique(dt_period2$date))))

# ============================================================================
# TUNING
# ============================================================================

cat("\n\n╔════════════════════════════════════════════════╗\n")
cat("║                HYPERPARAMETER TUNING          ║\n")
cat("╚════════════════════════════════════════════════╝\n\n")

best_single  <- tune_params_cv(dt_period1, inp$char_cols, inp$instr_cols, model_type = "single",
                               val_window_months = 24L, num_folds = 3L, min_train_months = 60L)
best_boosted <- tune_params_cv(dt_period1, inp$char_cols, inp$instr_cols, model_type = "boosted",
                               val_window_months = 24L, num_folds = 3L, min_train_months = 60L)

# ============================================================================
# SCENARIO A: FULL SAMPLE (re-estimate for reference)
# ============================================================================

train_a <- build_train_data(dt, inp$char_cols, inp$instr_cols)
model_a_single <- train_ptree(train_a, "SCENARIO A: FULL SAMPLE (SINGLE)",
                              num_iter = best_single$num_iter, eta = best_single$eta,
                              min_leaf_size = best_single$min_leaf_size,
                              max_depth = best_single$max_depth,
                              num_cutpoints = best_single$num_cutpoints)
save_scenario_results(model_a_single, NULL, "scenario_a_single", train_a, is_test=FALSE, params=best_single)

model_a_boosted <- train_ptree(train_a, "SCENARIO A: FULL SAMPLE (BOOSTED)",
                               num_iter = best_boosted$num_iter, eta = best_boosted$eta,
                               min_leaf_size = best_boosted$min_leaf_size,
                               max_depth = best_boosted$max_depth,
                               num_cutpoints = best_boosted$num_cutpoints)
save_scenario_results(model_a_boosted, NULL, "scenario_a_boosted", train_a, is_test=FALSE, params=best_boosted)

# ============================================================================
# SCENARIO B: TIME-SPLIT (train on past, test on future)
# ============================================================================

train_b <- build_train_data(dt_period1, inp$char_cols, inp$instr_cols)
test_b  <- build_train_data(dt_period2, inp$char_cols, inp$instr_cols)

# Single
model_b_single <- train_ptree(train_b, "SCENARIO B (SINGLE): PAST→FUTURE (Train)",
                              num_iter = best_single$num_iter, eta = best_single$eta,
                              min_leaf_size = best_single$min_leaf_size,
                              max_depth = best_single$max_depth,
                              num_cutpoints = best_single$num_cutpoints)
eval_b_single <- evaluate_on_test(model_b_single, test_b, "Scenario B (Single)")
save_scenario_results(model_b_single, list(ft=eval_b_single$ft, sharpe=eval_b_single$sharpe,
                                           mean=eval_b_single$mean, sd=eval_b_single$sd, annualized_return=eval_b_single$annualized_return),
                      "scenario_b_single", train_b, test_b, is_test=TRUE, params=best_single)

# Boosted
model_b_boosted <- train_ptree(train_b, "SCENARIO B (BOOSTED): PAST→FUTURE (Train)",
                               num_iter = best_boosted$num_iter, eta = best_boosted$eta,
                               min_leaf_size = best_boosted$min_leaf_size,
                               max_depth = best_boosted$max_depth,
                               num_cutpoints = best_boosted$num_cutpoints)
eval_b_boosted <- evaluate_on_test(model_b_boosted, test_b, "Scenario B (Boosted)")
save_scenario_results(model_b_boosted, list(ft=eval_b_boosted$ft, sharpe=eval_b_boosted$sharpe,
                                            mean=eval_b_boosted$mean, sd=eval_b_boosted$sd, annualized_return=eval_b_boosted$annualized_return),
                      "scenario_b_boosted", train_b, test_b, is_test=TRUE, params=best_boosted)

# ============================================================================
# SCENARIO C: REVERSE SPLIT (train on future, test on past)
# ============================================================================

train_c <- build_train_data(dt_period2, inp$char_cols, inp$instr_cols)
test_c  <- build_train_data(dt_period1, inp$char_cols, inp$instr_cols)

# Single
model_c_single <- train_ptree(train_c, "SCENARIO C (SINGLE): FUTURE→PAST (Train)",
                              num_iter = best_single$num_iter, eta = best_single$eta,
                              min_leaf_size = best_single$min_leaf_size,
                              max_depth = best_single$max_depth,
                              num_cutpoints = best_single$num_cutpoints)
eval_c_single <- evaluate_on_test(model_c_single, test_c, "Scenario C (Single)")
save_scenario_results(model_c_single, list(ft=eval_c_single$ft, sharpe=eval_c_single$sharpe,
                                           mean=eval_c_single$mean, sd=eval_c_single$sd, annualized_return=eval_c_single$annualized_return),
                      "scenario_c_single", train_c, test_c, is_test=TRUE, params=best_single)

# Boosted
model_c_boosted <- train_ptree(train_c, "SCENARIO C (BOOSTED): FUTURE→PAST (Train)",
                               num_iter = best_boosted$num_iter, eta = best_boosted$eta,
                               min_leaf_size = best_boosted$min_leaf_size,
                               max_depth = best_boosted$max_depth,
                               num_cutpoints = best_boosted$num_cutpoints)
eval_c_boosted <- evaluate_on_test(model_c_boosted, test_c, "Scenario C (Boosted)")
save_scenario_results(model_c_boosted, list(ft=eval_c_boosted$ft, sharpe=eval_c_boosted$sharpe,
                                            mean=eval_c_boosted$mean, sd=eval_c_boosted$sd, annualized_return=eval_c_boosted$annualized_return),
                      "scenario_c_boosted", train_c, test_c, is_test=TRUE, params=best_boosted)

# ============================================================================
# SUMMARY TABLE
# ============================================================================

cat("\n\n╔════════════════════════════════════════════════╗\n")
cat("║         FINAL SUMMARY (ALL SCENARIOS)         ║\n")
cat("╚════════════════════════════════════════════════╝\n\n")

summary_all <- rbind(
  data.table(scenario="A: Full Sample (Single)", period="Train", sharpe=model_a_single$sharpe,
             return_pct=model_a_single$annualized_return, leaves=model_a_single$num_leaves),
  data.table(scenario="A: Full Sample (Boosted)", period="Train", sharpe=model_a_boosted$sharpe,
             return_pct=model_a_boosted$annualized_return, leaves=model_a_boosted$num_leaves),
  data.table(scenario="B: Time-Split (Single)", period="Test (OOS)", sharpe=eval_b_single$sharpe,
             return_pct=eval_b_single$annualized_return, leaves=model_b_single$num_leaves),
  data.table(scenario="B: Time-Split (Boosted)", period="Test (OOS)", sharpe=eval_b_boosted$sharpe,
             return_pct=eval_b_boosted$annualized_return, leaves=model_b_boosted$num_leaves),
  data.table(scenario="C: Reverse Split (Single)", period="Test (OOS)", sharpe=eval_c_single$sharpe,
             return_pct=eval_c_single$annualized_return, leaves=model_c_single$num_leaves),
  data.table(scenario="C: Reverse Split (Boosted)", period="Test (OOS)", sharpe=eval_c_boosted$sharpe,
             return_pct=eval_c_boosted$annualized_return, leaves=model_c_boosted$num_leaves)
)

print(summary_all)
fwrite(summary_all, file.path(out_dir, "all_scenarios_summary.csv"))

cat(sprintf("\n✓ All results saved to: %s\n", normalizePath(out_dir)))
cat("\n✓ A2 complete - P-TREE MODELS (single + boosted) with auto tuning.\n\n")
