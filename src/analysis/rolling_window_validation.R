############################################################################
# ROLLING WINDOW VALIDATION FOR P-TREE
#
# Implements rolling window cross-validation:
# - Training window: 10 years
# - Testing window: 2 years
# - Roll forward: 1 year at a time
#
# This provides ~15 out-of-sample tests instead of just 2 (Scenarios B & C)
# Helps assess consistency of P-Tree performance across different time periods
############################################################################

library(PTree)

cat(paste(rep("=", 80), collapse=""), "\n")
cat("ROLLING WINDOW VALIDATION\n")
cat("Train: 10 years | Test: 2 years | Roll: 1 year\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

###### Parameters (Conservative) #####

min_leaf_size = 5
max_depth = 8
num_iter = 6
num_cutpoints = 4
equal_weight = FALSE
lambda_mean = 0
lambda_cov = 5e-4
lambda_mean_factor = 0
lambda_cov_factor = 5e-5

###### Load Data #####

cat("Loading data...\n")
data <- read.csv("../../results/ptree_34chars/ptree_ready_data_34chars.csv", stringsAsFactors = FALSE)
data$date <- as.Date(data$date, format='%Y-%m-%d')

all_chars <- names(data)[grep("^rank_", names(data))]
instruments = all_chars[1:min(5, length(all_chars))]
first_split_var = seq(0, length(all_chars)-1)
second_split_var = seq(0, length(all_chars)-1)

cat("  Total observations:", nrow(data), "\n")
cat("  Date range:", as.character(min(data$date)), "to", as.character(max(data$date)), "\n")
cat("  Unique stocks:", length(unique(data$permno)), "\n\n")

###### Helper Functions #####

calculate_sharpe <- function(returns) {
  return(mean(returns) / sd(returns) * sqrt(12))
}

calculate_stats <- function(returns) {
  list(
    mean_annual = mean(returns) * 12 * 100,  # Annualized %
    vol_annual = sd(returns) * sqrt(12) * 100,  # Annualized %
    sharpe = calculate_sharpe(returns),
    t_stat = mean(returns) / (sd(returns) / sqrt(length(returns))) * sqrt(12)
  )
}

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

ptree_predict_oos <- function(fit, test_data, all_chars) {
  X_test <- test_data[, all_chars]
  R_test <- test_data[, "xret"]
  months_test <- as.numeric(as.factor(test_data$date)) - 1
  weight_test <- test_data[, "lag_me"]

  pred <- try(predict(fit, X_test, R_test, months_test, weight_test), silent=TRUE)

  if (inherits(pred, "try-error")) {
    return(NULL)
  }

  return(pred$ft)
}

###### Rolling Window Analysis #####

# Define rolling windows
train_years = 10
test_years = 2
roll_years = 1

start_year = as.numeric(format(min(data$date), "%Y"))
end_year = as.numeric(format(max(data$date), "%Y"))

# Create windows
windows <- list()
for (train_start in seq(start_year, end_year - train_years - test_years + 1, by = roll_years)) {
  train_end <- train_start + train_years
  test_end <- train_end + test_years

  windows[[length(windows) + 1]] <- list(
    train_start = train_start,
    train_end = train_end,
    test_start = train_end,
    test_end = test_end
  )
}

cat("Created", length(windows), "rolling windows\n\n")

# Results storage
results_list <- list()

# Run rolling window validation
for (i in 1:length(windows)) {
  w <- windows[[i]]

  cat(paste(rep("-", 80), collapse=""), "\n")
  cat(sprintf("Window %d/%d: Train %d-%d | Test %d-%d\n",
              i, length(windows), w$train_start, w$train_end, w$test_start, w$test_end))
  cat(paste(rep("-", 80), collapse=""), "\n\n")

  # Split data
  train_data <- data[as.numeric(format(data$date, "%Y")) >= w$train_start &
                     as.numeric(format(data$date, "%Y")) < w$train_end, ]
  test_data <- data[as.numeric(format(data$date, "%Y")) >= w$test_start &
                    as.numeric(format(data$date, "%Y")) < w$test_end, ]

  if (nrow(train_data) == 0 || nrow(test_data) == 0) {
    cat("Skipping - insufficient data\n\n")
    next
  }

  cat("Train obs:", nrow(train_data), "| Test obs:", nrow(test_data), "\n")

  # Prepare training data
  dl_train <- prepare_design(train_data, all_chars, instruments)

  # Train P-Tree 1 (No Benchmark)
  cat("Training P-Tree 1 (Tree 1, no benchmark)...\n")
  Y_train1 = train_data[, "xret"]
  H_train1 = rep(0, nrow(train_data))

  fit1 = try(PTree(dl_train$R, Y_train1, dl_train$X, dl_train$Z, H_train1,
                   dl_train$portfolio_weight, dl_train$loss_weight,
                   dl_train$stocks, dl_train$months, first_split_var, second_split_var,
                   dl_train$num_stocks, dl_train$num_months,
                   min_leaf_size, max_depth, num_iter, num_cutpoints,
                   eta = 1, equal_weight = equal_weight,
                   no_H = TRUE,
                   abs_normalize = TRUE, weighted_loss = FALSE,
                   lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
                   early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
                   a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
                   random_split = FALSE), silent=TRUE)

  if (inherits(fit1, "try-error")) {
    cat("ERROR: Training failed\n\n")
    next
  }

  # In-sample performance
  is_stats <- calculate_stats(fit1$ft)
  cat(sprintf("  IS: Sharpe = %.2f | Mean = %.1f%% | Vol = %.1f%%\n",
              is_stats$sharpe, is_stats$mean_annual, is_stats$vol_annual))

  # Out-of-sample prediction
  cat("Predicting on test data...\n")
  ft_oos <- ptree_predict_oos(fit1, test_data, all_chars)

  if (is.null(ft_oos)) {
    cat("ERROR: OOS prediction failed\n\n")
    next
  }

  # Out-of-sample performance
  oos_stats <- calculate_stats(ft_oos)
  cat(sprintf("  OOS: Sharpe = %.2f | Mean = %.1f%% | Vol = %.1f%%\n",
              oos_stats$sharpe, oos_stats$mean_annual, oos_stats$vol_annual))

  # Calculate degradation
  sharpe_degradation <- (is_stats$sharpe - oos_stats$sharpe) / is_stats$sharpe * 100
  cat(sprintf("  Degradation: %.1f%%\n\n", sharpe_degradation))

  # Store results
  results_list[[i]] <- data.frame(
    window = i,
    train_start = w$train_start,
    train_end = w$train_end,
    test_start = w$test_start,
    test_end = w$test_end,
    is_sharpe = is_stats$sharpe,
    is_mean = is_stats$mean_annual,
    is_vol = is_stats$vol_annual,
    is_tstat = is_stats$t_stat,
    oos_sharpe = oos_stats$sharpe,
    oos_mean = oos_stats$mean_annual,
    oos_vol = oos_stats$vol_annual,
    oos_tstat = oos_stats$t_stat,
    degradation_pct = sharpe_degradation
  )
}

###### Aggregate Results #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("ROLLING WINDOW SUMMARY\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

if (length(results_list) > 0) {
  results_df <- do.call(rbind, results_list)

  cat("Average Performance Across All Windows:\n")
  cat(sprintf("  IS Sharpe:  %.2f (SD: %.2f)\n", mean(results_df$is_sharpe), sd(results_df$is_sharpe)))
  cat(sprintf("  OOS Sharpe: %.2f (SD: %.2f)\n", mean(results_df$oos_sharpe), sd(results_df$oos_sharpe)))
  cat(sprintf("  Degradation: %.1f%% (SD: %.1f%%)\n",
              mean(results_df$degradation_pct), sd(results_df$degradation_pct)))
  cat(sprintf("  Positive OOS Sharpe: %d/%d windows (%.1f%%)\n",
              sum(results_df$oos_sharpe > 0), nrow(results_df),
              sum(results_df$oos_sharpe > 0) / nrow(results_df) * 100))
  cat(sprintf("  OOS Sharpe > 1.0: %d/%d windows (%.1f%%)\n\n",
              sum(results_df$oos_sharpe > 1.0), nrow(results_df),
              sum(results_df$oos_sharpe > 1.0) / nrow(results_df) * 100))

  # Print full results
  print(results_df)

  # Save results
  output_dir <- "../../results/ptree_34chars/rolling_window"
  dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)
  write.csv(results_df, file.path(output_dir, "rolling_window_results.csv"), row.names = FALSE)

  cat("\nResults saved to:", file.path(output_dir, "rolling_window_results.csv"), "\n")

  # Create visualization data
  viz_data <- data.frame(
    period = paste(results_df$test_start, results_df$test_end, sep="-"),
    is_sharpe = results_df$is_sharpe,
    oos_sharpe = results_df$oos_sharpe,
    degradation = results_df$degradation_pct
  )
  write.csv(viz_data, file.path(output_dir, "rolling_window_viz.csv"), row.names = FALSE)

} else {
  cat("No successful windows - check data availability\n")
}

cat("\n")
cat(paste(rep("=", 80), collapse=""), "\n")
cat("ROLLING WINDOW VALIDATION COMPLETE\n")
cat(paste(rep("=", 80), collapse=""), "\n")
