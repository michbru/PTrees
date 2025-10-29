############################################################################
# ROLLING WINDOW P-TREE ANALYSIS
#
# This is the MOST ROBUST test for overfitting:
# - Train on expanding windows of data
# - Test on next 12 months
# - Step forward month-by-month
# - Accumulate TRUE out-of-sample predictions
#
# This is MORE conservative than the original paper's single split!
############################################################################

cat(paste(rep("=", 80), collapse=""), "\n")
cat("ROLLING WINDOW P-TREE ANALYSIS - MOST ROBUST TEST\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

library(PTree)

# Parameters (same as main analysis)
min_leaf_size = 3
max_depth = 10
num_iter = 9
num_cutpoints = 4
equal_weight = FALSE
lambda_mean = 0
lambda_cov = 1e-4
lambda_mean_factor = 0
lambda_cov_factor = 1e-5

# Rolling window configuration
MIN_TRAIN_MONTHS = 60    # Minimum 5 years for training
TEST_WINDOW = 12         # Test on next 12 months
STEP_SIZE = 12           # Step forward 1 year at a time

cat("ROLLING WINDOW CONFIGURATION:\n")
cat("  Minimum training window:", MIN_TRAIN_MONTHS, "months\n")
cat("  Test window:", TEST_WINDOW, "months\n")
cat("  Step size:", STEP_SIZE, "months\n\n")

# Load data
cat("Loading data...\n")
data <- read.csv("results/ptree_ready_data_full.csv", stringsAsFactors = FALSE)
data$date <- as.Date(data$date, format='%Y-%m-%d')

all_chars <- names(data)[grep("^rank_", names(data))]
instruments = all_chars[1:min(5, length(all_chars))]
first_split_var = seq(0, length(all_chars)-1)
second_split_var = seq(0, length(all_chars)-1)

cat("  Total observations:", nrow(data), "\n")
cat("  Characteristics:", length(all_chars), "\n")
cat("  Date range:", as.character(min(data$date)), "to", as.character(max(data$date)), "\n\n")

# Get unique dates
unique_dates <- sort(unique(data$date))
n_months <- length(unique_dates)

# Calculate number of windows
n_windows <- (n_months - MIN_TRAIN_MONTHS - TEST_WINDOW) %/% STEP_SIZE + 1

cat("ANALYSIS PLAN:\n")
cat("  Total months:", n_months, "\n")
cat("  Number of rolling windows:", n_windows, "\n")
cat("  Estimated runtime:", round(n_windows * 1.5, 1), "minutes (1.5 min per window)\n\n")

if (n_windows < 1) {
  cat("ERROR: Not enough data for rolling window analysis!\n")
  cat("  Need at least", MIN_TRAIN_MONTHS + TEST_WINDOW, "months\n")
  quit(status=1)
}

# Helper function to prepare data
prepare_design <- function(df, all_chars, instruments) {
  X = df[, all_chars]
  R = df[, "xret"]
  months = as.numeric(as.factor(df$date)) - 1
  stocks = as.numeric(as.factor(df$permno)) - 1
  Z = cbind(1, df[, instruments])
  portfolio_weight = df[, "lag_me"]
  loss_weight = df[, "lag_me"]
  num_months = length(unique(months))
  num_stocks = length(unique(stocks))
  list(X=X, R=R, months=months, stocks=stocks, Z=Z,
       portfolio_weight=portfolio_weight, loss_weight=loss_weight,
       num_months=num_months, num_stocks=num_stocks)
}

# Store results
rolling_results <- list()

cat(paste(rep("=", 80), collapse=""), "\n")
cat("RUNNING ROLLING WINDOW ANALYSIS\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

for (window_idx in 1:n_windows) {

  # Define train/test periods
  train_start_idx <- (window_idx - 1) * STEP_SIZE + 1
  train_end_idx <- train_start_idx + MIN_TRAIN_MONTHS - 1 + (window_idx - 1) * STEP_SIZE
  test_start_idx <- train_end_idx + 1
  test_end_idx <- test_start_idx + TEST_WINDOW - 1

  if (test_end_idx > n_months) {
    break
  }

  train_dates <- unique_dates[train_start_idx:train_end_idx]
  test_dates <- unique_dates[test_start_idx:test_end_idx]

  train_data <- data[data$date %in% train_dates, ]
  test_data <- data[data$date %in% test_dates, ]

  cat(sprintf("\n[Window %d/%d]\n", window_idx, n_windows))
  cat("  Train:", as.character(train_dates[1]), "to", as.character(train_dates[length(train_dates)]))
  cat(" (", length(train_dates), "months,", nrow(train_data), "obs)\n")
  cat("  Test: ", as.character(test_dates[1]), "to", as.character(test_dates[length(test_dates)]))
  cat(" (", length(test_dates), "months,", nrow(test_data), "obs)\n")

  # Prepare training data
  dl_train <- prepare_design(train_data, all_chars, instruments)

  # Train P-Tree (only first tree for speed)
  cat("  Training P-Tree...")
  t_start <- proc.time()

  fit1 <- tryCatch({
    PTree(dl_train$R, train_data$xret, dl_train$X, dl_train$Z,
          rep(0, nrow(train_data)),
          dl_train$portfolio_weight, dl_train$loss_weight,
          dl_train$stocks, dl_train$months,
          first_split_var, second_split_var,
          dl_train$num_stocks, dl_train$num_months,
          min_leaf_size, max_depth, num_iter, num_cutpoints,
          eta = 1, equal_weight = equal_weight,
          no_H = TRUE, abs_normalize = TRUE, weighted_loss = FALSE,
          lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
          early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
          a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
          random_split = FALSE)
  }, error = function(e) {
    cat(" [ERROR:", e$message, "]\n")
    return(NULL)
  })

  t_elapsed <- proc.time() - t_start

  if (is.null(fit1)) {
    cat(" FAILED\n")
    next
  }

  cat(" Done (", round(t_elapsed[3], 1), "sec)\n")

  # Get test predictions
  cat("  Generating OOS predictions...")

  X_test <- test_data[, all_chars]
  R_test <- test_data[, "xret"]
  months_test <- as.numeric(as.factor(test_data$date)) - 1
  weight_test <- test_data[, "lag_me"]

  pred <- tryCatch({
    predict(fit1, X_test, R_test, months_test, weight_test)
  }, error = function(e) {
    cat(" [ERROR:", e$message, "]\n")
    return(NULL)
  })

  if (is.null(pred) || is.null(pred$ft)) {
    cat(" FAILED\n")
    next
  }

  test_returns <- pred$ft
  cat(" Done\n")

  # Calculate performance metrics
  mean_return <- mean(test_returns) * 12 * 100  # Annualized %
  sharpe <- mean(test_returns) / sd(test_returns) * sqrt(12)

  # Tree complexity
  tree_info <- strsplit(fit1$tree, "\n")[[1]][1]
  n_nodes <- as.numeric(tree_info)

  cat("  Performance: Return =", round(mean_return, 2), "% | Sharpe =", round(sharpe, 3),
      "| Nodes =", n_nodes, "\n")

  # Store results
  rolling_results[[window_idx]] <- list(
    window = window_idx,
    train_start = as.character(train_dates[1]),
    train_end = as.character(train_dates[length(train_dates)]),
    train_months = length(train_dates),
    test_start = as.character(test_dates[1]),
    test_end = as.character(test_dates[length(test_dates)]),
    test_months = length(test_dates),
    n_nodes = n_nodes,
    test_returns = test_returns,
    mean_return_ann = mean_return,
    sharpe = sharpe,
    runtime_sec = t_elapsed[3]
  )
}

cat("\n")
cat(paste(rep("=", 80), collapse=""), "\n")
cat("ROLLING WINDOW SUMMARY\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

if (length(rolling_results) == 0) {
  cat("ERROR: No successful windows!\n")
  quit(status=1)
}

# Aggregate results
all_test_returns <- unlist(lapply(rolling_results, function(x) x$test_returns))
sharpe_ratios <- sapply(rolling_results, function(x) x$sharpe)
mean_returns <- sapply(rolling_results, function(x) x$mean_return_ann)

cat("AGGREGATE OUT-OF-SAMPLE PERFORMANCE:\n")
cat("  Total test periods:", length(rolling_results), "\n")
cat("  Total OOS months:", length(all_test_returns), "\n")
cat("  Mean return:", round(mean(all_test_returns) * 12 * 100, 2), "% per year\n")
cat("  Volatility:", round(sd(all_test_returns) * sqrt(12) * 100, 2), "% per year\n")
cat("  Sharpe ratio:", round(mean(all_test_returns) / sd(all_test_returns) * sqrt(12), 3), "\n\n")

cat("PERFORMANCE STABILITY:\n")
cat("  Average window Sharpe:", round(mean(sharpe_ratios), 3), "\n")
cat("  Std dev of Sharpe:", round(sd(sharpe_ratios), 3), "\n")
cat("  Min Sharpe:", round(min(sharpe_ratios), 3), "\n")
cat("  Max Sharpe:", round(max(sharpe_ratios), 3), "\n")
cat("  Positive Sharpe windows:", sum(sharpe_ratios > 0), "/", length(sharpe_ratios), "\n\n")

cat("RETURN CONSISTENCY:\n")
cat("  Average window return:", round(mean(mean_returns), 2), "% per year\n")
cat("  Std dev of returns:", round(sd(mean_returns), 2), "%\n")
cat("  Min return:", round(min(mean_returns), 2), "%\n")
cat("  Max return:", round(max(mean_returns), 2), "%\n")
cat("  Positive return windows:", sum(mean_returns > 0), "/", length(mean_returns), "\n\n")

# Save detailed results
output_dir <- "results/robustness_checks"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# Create summary dataframe
summary_df <- data.frame(
  Window = sapply(rolling_results, function(x) x$window),
  Train_Start = sapply(rolling_results, function(x) x$train_start),
  Train_End = sapply(rolling_results, function(x) x$train_end),
  Train_Months = sapply(rolling_results, function(x) x$train_months),
  Test_Start = sapply(rolling_results, function(x) x$test_start),
  Test_End = sapply(rolling_results, function(x) x$test_end),
  Test_Months = sapply(rolling_results, function(x) x$test_months),
  N_Nodes = sapply(rolling_results, function(x) x$n_nodes),
  Mean_Return_pct = sapply(rolling_results, function(x) x$mean_return_ann),
  Sharpe_Ratio = sapply(rolling_results, function(x) x$sharpe),
  Runtime_Sec = sapply(rolling_results, function(x) x$runtime_sec)
)

write.csv(summary_df, file.path(output_dir, "rolling_window_ptree_results.csv"), row.names = FALSE)

# Save all test returns for further analysis
all_returns_df <- data.frame(
  Return = all_test_returns
)
write.csv(all_returns_df, file.path(output_dir, "rolling_window_all_returns.csv"), row.names = FALSE)

cat("RESULTS SAVED:\n")
cat("  ", file.path(output_dir, "rolling_window_ptree_results.csv"), "\n")
cat("  ", file.path(output_dir, "rolling_window_all_returns.csv"), "\n\n")

cat(paste(rep("=", 80), collapse=""), "\n")
cat("KEY FINDINGS\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

aggregate_sharpe <- mean(all_test_returns) / sd(all_test_returns) * sqrt(12)
aggregate_return <- mean(all_test_returns) * 12 * 100

cat("1. AGGREGATE OOS PERFORMANCE:\n")
cat("   - Sharpe:", round(aggregate_sharpe, 3), "\n")
cat("   - Return:", round(aggregate_return, 2), "% per year\n")
cat("   - This is the MOST ROBUST estimate (true walk-forward)\n\n")

cat("2. COMPARISON TO SINGLE SPLIT:\n")
cat("   - Single split forward (B):", 1.69, "Sharpe\n")
cat("   - Rolling window:", round(aggregate_sharpe, 3), "Sharpe\n")
if (abs(aggregate_sharpe - 1.69) < 0.3) {
  cat("   - Results are CONSISTENT (difference < 0.3)\n")
} else if (aggregate_sharpe < 1.69) {
  cat("   - Rolling window is LOWER (more conservative)\n")
} else {
  cat("   - Rolling window is HIGHER (unexpected!)\n")
}
cat("\n")

cat("3. STABILITY:\n")
if (sd(sharpe_ratios) < 0.5) {
  cat("   - Low variability (std <", 0.5, ") = STABLE performance\n")
} else if (sd(sharpe_ratios) < 1.0) {
  cat("   - Moderate variability (std <", 1.0, ") = ACCEPTABLE\n")
} else {
  cat("   - High variability (std >", 1.0, ") = UNSTABLE performance\n")
}
cat("   - Std dev of Sharpe:", round(sd(sharpe_ratios), 3), "\n\n")

cat("4. VERDICT:\n")
if (aggregate_sharpe > 1.5 && sum(sharpe_ratios > 0) >= 0.8 * length(sharpe_ratios)) {
  cat("   - ROBUST: Strong and consistent OOS performance\n")
} else if (aggregate_sharpe > 0.8 && sum(sharpe_ratios > 0) >= 0.6 * length(sharpe_ratios)) {
  cat("   - MODERATE: Positive but inconsistent OOS performance\n")
} else {
  cat("   - WEAK: Poor or unstable OOS performance\n")
}

cat("\n")
cat(paste(rep("=", 80), collapse=""), "\n")
cat("ROLLING WINDOW ANALYSIS COMPLETE\n")
cat(paste(rep("=", 80), collapse=""), "\n")
