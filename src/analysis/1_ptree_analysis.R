############################################################################
# COMPREHENSIVE P-TREE ANALYSIS
# Following Cong et al. (2024) Journal of Financial Economics
#
# This script performs TWO types of validation:
#
# PART 1: Three-Scenario Validation (Traditional Approach)
#   - Scenario A: Full sample (1997-2022)
#   - Scenario B: Time split (Train 1997-2010, Test 2010-2022)
#   - Scenario C: Reverse split (Train 2010-2022, Test 1997-2010)
#
# PART 2: Rolling Window Validation (Anti-Overfitting)
#   - 20 independent train-test windows
#   - Train: 5 years, Test: 1 year, Roll: 1 year
#   - More robust validation with multiple OOS tests
#
############################################################################

cat("================================================================================\n")
cat("COMPREHENSIVE P-TREE ANALYSIS WITH 34 CHARACTERISTICS\n")
cat("Following Cong et al. (2024) Journal of Financial Economics\n")
cat("================================================================================\n\n")

library(PTree)

###### CONSERVATIVE PARAMETERS (ANTI-OVERFITTING) #####

# Tuned for Swedish market (~300 stocks vs ~2,500 in US)
min_leaf_size = 10         # Conservative (doubled from 5)
max_depth = 5              # Shallow trees (reduced from 8)
num_iter = 3               # Minimal boosting (reduced from 6)
num_cutpoints = 3          # Reduced from 4
equal_weight = FALSE
lambda_cov = 1e-3          # Strong regularization (doubled)
lambda_cov_factor = 1e-4   # Strong regularization (doubled)

cat("ANTI-OVERFITTING PARAMETERS:\n")
cat("  min_leaf_size     =", min_leaf_size, "(doubled from 5)\n")
cat("  max_depth         =", max_depth, "(reduced from 8)\n")
cat("  num_iter          =", num_iter, "(reduced from 6)\n")
cat("  lambda_cov        =", lambda_cov, "(doubled regularization)\n")
cat("  equal_weight      = FALSE (value-weighted portfolios)\n")
cat("  Rationale: Smaller Swedish market requires more conservative parameters\n\n")

###### LOAD DATA #####

cat("Loading P-Tree ready data...\n")
data_path <- "../../results/ptree_34chars/ptree_ready_data_34chars.csv"
data <- read.csv(data_path, stringsAsFactors = FALSE)
data$date <- as.Date(data$date, format='%Y-%m-%d')
data <- data[order(data$date), ]

all_chars <- names(data)[grep("^rank_", names(data))]
instruments <- all_chars[1:min(5, length(all_chars))]

cat("  Total observations:", nrow(data), "\n")
cat("  Date range:", as.character(min(data$date)), "to", as.character(max(data$date)), "\n")
cat("  Unique stocks:", length(unique(data$permno)), "\n")
cat("  Characteristics:", length(all_chars), "\n\n")

###### HELPER FUNCTIONS #####

calculate_sharpe <- function(returns) {
  if(length(returns) < 2 || all(is.na(returns))) return(NA)
  mean_ret <- mean(returns, na.rm = TRUE)
  sd_ret <- sd(returns, na.rm = TRUE)
  if(sd_ret == 0) return(0)
  return(mean_ret / sd_ret * sqrt(12))
}

train_simple_ptree <- function(train_data, desc = "") {
  # Prepare data
  X_train <- train_data[, all_chars]
  R_train <- train_data[, "xret"]
  months_train <- as.numeric(as.factor(train_data$date)) - 1
  stocks_train <- as.numeric(as.factor(train_data$permno)) - 1
  Z_train <- cbind(1, train_data[, instruments])
  portfolio_weight <- train_data[, "lag_me"]
  loss_weight <- train_data[, "lag_me"]
  num_months_train <- length(unique(months_train))
  num_stocks_train <- length(unique(stocks_train))

  if(desc != "") cat("  Training P-Tree for", desc, "...\n")

  Y_train <- train_data[, "xret"]
  H_train <- rep(0, nrow(train_data))
  first_split_var <- seq(0, length(all_chars) - 1)
  second_split_var <- seq(0, length(all_chars) - 1)

  t_start <- proc.time()
  fit <- tryCatch({
    PTree(R_train, Y_train, X_train, Z_train, H_train,
          portfolio_weight, loss_weight,
          stocks_train, months_train, first_split_var, second_split_var,
          num_stocks_train, num_months_train,
          min_leaf_size, max_depth, num_iter, num_cutpoints,
          eta = 1, equal_weight = equal_weight,
          no_H = TRUE, abs_normalize = TRUE, weighted_loss = FALSE,
          0, lambda_cov, 0, lambda_cov_factor,
          early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
          a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
          random_split = FALSE)
  }, error = function(e) {
    cat("    ERROR:", e$message, "\n")
    return(NULL)
  })

  t_elapsed <- (proc.time() - t_start)[3]

  if(!is.null(fit)) {
    sharpe_is <- calculate_sharpe(fit$ft)
    nodes <- as.numeric(strsplit(fit$tree, "\n")[[1]][1])
    cat("    [OK] Nodes:", nodes, "| IS Sharpe:", round(sharpe_is, 3), "| Time:", round(t_elapsed, 1), "s\n")
  }

  return(fit)
}

predict_ptree_oos <- function(fit, test_data, desc = "") {
  if(is.null(fit)) return(NULL)

  if(desc != "") cat("  Predicting OOS for", desc, "...\n")

  X_test <- test_data[, all_chars]
  R_test <- test_data[, "xret"]
  months_test <- as.numeric(as.factor(test_data$date)) - 1
  weight_test <- test_data[, "lag_me"]

  pred <- tryCatch({
    predict(fit, X_test, R_test, months_test, weight_test)
  }, error = function(e) {
    cat("    ERROR:", e$message, "\n")
    return(NULL)
  })

  if(!is.null(pred)) {
    sharpe_oos <- calculate_sharpe(pred$ft)
    cat("    [OK] OOS Sharpe:", round(sharpe_oos, 3), "\n")
    return(pred$ft)
  }
  return(NULL)
}

############################################################################
# PART 1: THREE-SCENARIO VALIDATION (Traditional Approach)
############################################################################

cat("\n")
cat("================================================================================\n")
cat("PART 1: THREE-SCENARIO VALIDATION\n")
cat("================================================================================\n\n")

split_date <- as.Date('2010-01-01')

# --- Scenario A: Full Sample ---
cat("Scenario A: Full Sample (1997-2022)\n")
cat("--------------------------------------------------------------------------------\n")
fit_a <- train_simple_ptree(data, "Full Sample")
output_dir_a <- "../../results/ptree_34chars/scenario_a_full"
dir.create(output_dir_a, showWarnings = FALSE, recursive = TRUE)
if(!is.null(fit_a)) {
  factors_a <- data.frame(
    month = sort(unique(data$date)),
    factor = fit_a$ft
  )
  write.csv(factors_a, file.path(output_dir_a, "ptree_factors.csv"), row.names = FALSE)

  # Save tree structure
  writeLines(fit_a$tree, file.path(output_dir_a, "ptree_structure.txt"))

  cat("  [SAVED]", output_dir_a, "\n")
}
cat("\n")

# --- Scenario B: Time Split ---
cat("Scenario B: Time Split (Train 1997-2010, Test 2010-2022)\n")
cat("--------------------------------------------------------------------------------\n")
train_b <- data[data$date < split_date, ]
test_b <- data[data$date >= split_date, ]
cat("  Train: 1997-2010 (", nrow(train_b), "obs )\n")
cat("  Test:  2010-2022 (", nrow(test_b), "obs )\n")

fit_b <- train_simple_ptree(train_b, "Time Split (IS)")
output_dir_b <- "../../results/ptree_34chars/scenario_b_split"
dir.create(output_dir_b, showWarnings = FALSE, recursive = TRUE)

if(!is.null(fit_b)) {
  # Save IS factors
  factors_b_is <- data.frame(
    month = sort(unique(train_b$date)),
    factor = fit_b$ft
  )
  write.csv(factors_b_is, file.path(output_dir_b, "ptree_factors_is.csv"), row.names = FALSE)

  # Save tree structure
  writeLines(fit_b$tree, file.path(output_dir_b, "ptree_structure.txt"))

  # Predict OOS
  oos_b <- predict_ptree_oos(fit_b, test_b, "Time Split (OOS)")
  if(!is.null(oos_b)) {
    factors_b_oos <- data.frame(
      month = sort(unique(test_b$date)),
      factor = oos_b
    )
    write.csv(factors_b_oos, file.path(output_dir_b, "ptree_factors_oos.csv"), row.names = FALSE)
  }
  cat("  [SAVED]", output_dir_b, "\n")
}
cat("\n")

# --- Scenario C: Reverse Split ---
cat("Scenario C: Reverse Split (Train 2010-2022, Test 1997-2010)\n")
cat("--------------------------------------------------------------------------------\n")
train_c <- data[data$date >= split_date, ]
test_c <- data[data$date < split_date, ]
cat("  Train: 2010-2022 (", nrow(train_c), "obs )\n")
cat("  Test:  1997-2010 (", nrow(test_c), "obs )\n")

fit_c <- train_simple_ptree(train_c, "Reverse Split (IS)")
output_dir_c <- "../../results/ptree_34chars/scenario_c_reverse"
dir.create(output_dir_c, showWarnings = FALSE, recursive = TRUE)

if(!is.null(fit_c)) {
  # Save IS factors
  factors_c_is <- data.frame(
    month = sort(unique(train_c$date)),
    factor = fit_c$ft
  )
  write.csv(factors_c_is, file.path(output_dir_c, "ptree_factors_is.csv"), row.names = FALSE)

  # Save tree structure
  writeLines(fit_c$tree, file.path(output_dir_c, "ptree_structure.txt"))

  # Predict OOS
  oos_c <- predict_ptree_oos(fit_c, test_c, "Reverse Split (OOS)")
  if(!is.null(oos_c)) {
    factors_c_oos <- data.frame(
      month = sort(unique(test_c$date)),
      factor = oos_c
    )
    write.csv(factors_c_oos, file.path(output_dir_c, "ptree_factors_oos.csv"), row.names = FALSE)
  }
  cat("  [SAVED]", output_dir_c, "\n")
}
cat("\n")

############################################################################
# PART 2: ROLLING WINDOW VALIDATION (Anti-Overfitting)
############################################################################

cat("\n")
cat("================================================================================\n")
cat("PART 2: ROLLING WINDOW VALIDATION (ANTI-OVERFITTING)\n")
cat("================================================================================\n\n")

# Window configuration
all_dates <- sort(unique(data$date))
n_months <- length(all_dates)
train_window <- 60  # 5 years
test_window <- 12   # 1 year
roll_step <- 12     # 1 year
max_start <- n_months - train_window - test_window
n_windows <- floor(max_start / roll_step) + 1

cat("CONFIGURATION:\n")
cat("  Total months:     ", n_months, "\n")
cat("  Training window:  ", train_window, "months (5 years)\n")
cat("  Test window:      ", test_window, "months (1 year)\n")
cat("  Roll step:        ", roll_step, "months (1 year)\n")
cat("  Number of windows:", n_windows, "\n\n")

results_list <- list()

for(w in 1:n_windows) {
  # Calculate indices
  train_start_idx <- (w - 1) * roll_step + 1
  train_end_idx <- train_start_idx + train_window - 1
  test_start_idx <- train_end_idx + 1
  test_end_idx <- test_start_idx + test_window - 1

  if(test_end_idx > n_months) {
    cat("Window", w, ": Insufficient data, skipping\n")
    break
  }

  # Get data
  train_dates <- all_dates[train_start_idx:train_end_idx]
  test_dates <- all_dates[test_start_idx:test_end_idx]
  train_data <- data[data$date %in% train_dates, ]
  test_data <- data[data$date %in% test_dates, ]

  cat(sprintf("Window %d/%d: Train %s to %s | Test %s to %s\n",
              w, n_windows,
              as.character(min(train_dates)), as.character(max(train_dates)),
              as.character(min(test_dates)), as.character(max(test_dates))))

  # Train and predict
  fit <- train_simple_ptree(train_data, sprintf("Window %d", w))
  if(is.null(fit)) {
    cat("  [FAILED]\n\n")
    next
  }

  is_sharpe <- calculate_sharpe(fit$ft)
  oos_factors <- predict_ptree_oos(fit, test_data, sprintf("Window %d", w))

  if(is.null(oos_factors)) {
    cat("  [FAILED OOS]\n\n")
    next
  }

  oos_sharpe <- calculate_sharpe(oos_factors)
  degradation <- if(is_sharpe != 0) (oos_sharpe - is_sharpe) / is_sharpe * 100 else NA

  # Store results
  results_list[[w]] <- data.frame(
    window = w,
    train_start = as.character(min(train_dates)),
    train_end = as.character(max(train_dates)),
    test_start = as.character(min(test_dates)),
    test_end = as.character(max(test_dates)),
    is_sharpe = is_sharpe,
    oos_sharpe = oos_sharpe,
    degradation_pct = degradation,
    stringsAsFactors = FALSE
  )
  cat("\n")
}

# Aggregate results
results_df <- do.call(rbind, results_list)

cat("================================================================================\n")
cat("ROLLING WINDOW SUMMARY\n")
cat("================================================================================\n\n")
cat(sprintf("Windows tested:        %d\n", nrow(results_df)))
cat(sprintf("Avg IS Sharpe:         %.3f\n", mean(results_df$is_sharpe, na.rm = TRUE)))
cat(sprintf("Avg OOS Sharpe:        %.3f\n", mean(results_df$oos_sharpe, na.rm = TRUE)))
cat(sprintf("Median OOS Sharpe:     %.3f\n", median(results_df$oos_sharpe, na.rm = TRUE)))
cat(sprintf("Std Dev OOS Sharpe:    %.3f\n", sd(results_df$oos_sharpe, na.rm = TRUE)))
cat(sprintf("Avg Degradation:       %.1f%%\n", mean(results_df$degradation_pct, na.rm = TRUE)))
cat(sprintf("Positive OOS:          %.0f%% (%d/%d)\n",
            sum(results_df$oos_sharpe > 0, na.rm = TRUE) / nrow(results_df) * 100,
            sum(results_df$oos_sharpe > 0, na.rm = TRUE),
            nrow(results_df)))

# Save
output_dir_rolling <- "../../results/ptree_34chars/rolling_window"
dir.create(output_dir_rolling, showWarnings = FALSE, recursive = TRUE)
write.csv(results_df, file.path(output_dir_rolling, "rolling_window_results.csv"), row.names = FALSE)
cat(sprintf("\n[SAVED] %s\n", output_dir_rolling))

############################################################################
# FINAL SUMMARY
############################################################################

cat("\n")
cat("================================================================================\n")
cat("ANALYSIS COMPLETE\n")
cat("================================================================================\n\n")
cat("Results saved to: ../../results/ptree_34chars/\n")
cat("  - scenario_a_full/\n")
cat("  - scenario_b_split/\n")
cat("  - scenario_c_reverse/\n")
cat("  - rolling_window/\n")
cat("\nNext step: Run 7_validate_results.py to verify OOS performance\n")
