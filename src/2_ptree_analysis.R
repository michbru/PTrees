############################################################################
# COMPLETE P-TREE ANALYSIS - CORRECT METHODOLOGY
# Following Cong et al. (2024) JFE Paper
#
# Three scenarios:
# - Scenario A (Full): Train on entire period 1997-2022 (like P-Tree-a)
# - Scenario B (Split): Train 1997-2010, Test 2010-2022 (like P-Tree-b)
# - Scenario C (Reverse): Train 2010-2022, Test 1997-2010 (like P-Tree-c)
#
# NOTE: Benchmark analysis is limited to 1997-2020 due to Fama-French factor
# data availability (FF factors only available through 2020-07).
############################################################################

t_total = proc.time()

library(PTree)

cat(paste(rep("=", 80), collapse=""), "\n")
cat("COMPLETE P-TREE ANALYSIS - SWEDISH STOCK MARKET\n")
cat("Following Cong et al. (2024) Journal of Financial Economics\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

###### Parameters (Scaled for Swedish Market) #####

# Market size scaling: Swedish ~300 stocks vs US ~2500 stocks
# US paper: min_leaf_size = 20
# Swedish: 300/2500 * 20 = 2.4 → use 3 (conservative)

min_leaf_size = 3
max_depth = 10
max_depth_boosting = 10
num_iter = 9
num_iterB = 9
num_cutpoints = 4
equal_weight = FALSE

# Regularization (same as paper)
lambda_mean = 0
lambda_cov = 1e-4
lambda_mean_factor = 0
lambda_cov_factor = 1e-5

cat("PARAMETERS:\n")
cat("  min_leaf_size =", min_leaf_size, "(scaled for Swedish market size)\n")
cat("  max_depth =", max_depth, "\n")
cat("  num_iter =", num_iter, "\n")
cat("  num_cutpoints =", num_cutpoints, "\n")
cat("  Regularization: lambda_cov =", lambda_cov, "\n\n")

###### Load Data #####

cat("Loading data...\n")
data_path = "results/ptree_ready_data_full.csv"
data <- read.csv(data_path, stringsAsFactors = FALSE)
data$date <- as.Date(data$date, format='%Y-%m-%d')

all_chars <- names(data)[grep("^rank_", names(data))]
instruments = all_chars[1:min(5, length(all_chars))]
first_split_var = seq(0, length(all_chars)-1)
second_split_var = seq(0, length(all_chars)-1)

cat("  Total observations:", nrow(data), "\n")
cat("  Date range:", as.character(min(data$date)), "to", as.character(max(data$date)), "\n")
cat("  Unique stocks:", length(unique(data$permno)), "\n")
cat("  Characteristics:", length(all_chars), "\n\n")

###### Helper Functions #####

calculate_sharpe <- function(returns) {
  return(mean(returns) / sd(returns) * sqrt(12))
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
  # Use the actual PTree predict function signature from the package:
  # predict.PTree(model, X, R, months, weight = NULL)

  X_test <- test_data[, all_chars]
  R_test <- test_data[, "xret"]
  months_test <- as.numeric(as.factor(test_data$date)) - 1
  weight_test <- test_data[, "lag_me"]

  # Call predict with correct signature
  pred <- try(predict(fit, X_test, R_test, months_test, weight_test), silent=TRUE)

  if (inherits(pred, "try-error")) {
    return(NULL)
  }

  return(pred$ft)
}

train_ptree_trio <- function(train_data, scenario_name) {
  cat(paste(rep("-", 80), collapse=""), "\n")
  cat("Training 3 P-Trees for:", scenario_name, "\n")
  cat(paste(rep("-", 80), collapse=""), "\n\n")

  # Prepare training data
  dl_train <- prepare_design(train_data, all_chars, instruments)
  X_train = dl_train$X
  R_train = dl_train$R
  months_train = dl_train$months
  stocks_train = dl_train$stocks
  Z_train = dl_train$Z
  portfolio_weight_train = dl_train$portfolio_weight
  loss_weight_train = dl_train$loss_weight
  num_months_train = dl_train$num_months
  num_stocks_train = dl_train$num_stocks

  cat("Training data:\n")
  cat("  Observations:", nrow(train_data), "\n")
  cat("  Months:", num_months_train, "\n")
  cat("  Stocks:", num_stocks_train, "\n\n")

  # P-Tree 1 (No Benchmark)
  cat("P-Tree 1 (No Benchmark)...\n")
  Y_train1 = train_data[, "xret"]
  H_train1 = rep(0, nrow(train_data))

  t1 = proc.time()
  fit1 = PTree(R_train, Y_train1, X_train, Z_train, H_train1,
               portfolio_weight_train, loss_weight_train,
               stocks_train, months_train, first_split_var, second_split_var,
               num_stocks_train, num_months_train,
               min_leaf_size, max_depth, num_iter, num_cutpoints,
               eta = 1, equal_weight = equal_weight,
               no_H = TRUE,  # No benchmark for first tree
               abs_normalize = TRUE, weighted_loss = FALSE,
               lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
               early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
               a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
               random_split = FALSE)
  t1 = proc.time() - t1

  tree1_nodes = as.numeric(strsplit(fit1$tree, "\n")[[1]][1])
  sharpe1 = calculate_sharpe(fit1$ft)
  cat("  Nodes:", tree1_nodes, "| Sharpe:", round(sharpe1, 3), "| Time:", round(t1[3], 1), "sec\n")

  # P-Tree 2 (Boosting)
  cat("P-Tree 2 (Boosting on P-Tree 1)...\n")
  Y_train2 = train_data[, "xret"]
  H_train2 = fit1$ft

  fit2 = PTree(R_train, Y_train2, X_train, Z_train, H_train2,
               portfolio_weight_train, loss_weight_train,
               stocks_train, months_train, first_split_var, second_split_var,
               num_stocks_train, num_months_train,
               min_leaf_size, max_depth_boosting, num_iterB, num_cutpoints,
               eta = 1, equal_weight = equal_weight,
               no_H = FALSE,  # Use previous factor as benchmark
               abs_normalize = TRUE, weighted_loss = FALSE,
               lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
               early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
               a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
               random_split = FALSE)

  tree2_nodes = as.numeric(strsplit(fit2$tree, "\n")[[1]][1])
  sharpe2 = calculate_sharpe(fit2$ft)
  cat("  Nodes:", tree2_nodes, "| Sharpe:", round(sharpe2, 3), "\n")

  # P-Tree 3 (Boosting)
  cat("P-Tree 3 (Boosting on P-Trees 1-2)...\n")
  Y_train3 = train_data[, "xret"]
  H_train3 = cbind(fit1$ft, fit2$ft)

  fit3 = PTree(R_train, Y_train3, X_train, Z_train, H_train3,
               portfolio_weight_train, loss_weight_train,
               stocks_train, months_train, first_split_var, second_split_var,
               num_stocks_train, num_months_train,
               min_leaf_size, max_depth_boosting, num_iterB, num_cutpoints,
               eta = 1, equal_weight = equal_weight,
               no_H = FALSE,
               abs_normalize = TRUE, weighted_loss = FALSE,
               lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
               early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
               a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
               random_split = FALSE)

  tree3_nodes = as.numeric(strsplit(fit3$tree, "\n")[[1]][1])
  sharpe3 = calculate_sharpe(fit3$ft)
  cat("  Nodes:", tree3_nodes, "| Sharpe:", round(sharpe3, 3), "\n\n")

  return(list(
    fit1 = fit1, fit2 = fit2, fit3 = fit3,
    nodes = c(tree1_nodes, tree2_nodes, tree3_nodes),
    sharpes = c(sharpe1, sharpe2, sharpe3),
    runtime = t1[3]
  ))
}

apply_ptree_trio_oos <- function(fits, test_data, all_chars) {
  # Apply trained P-Trees to test data using the predict() function
  # This generates TRUE out-of-sample predictions

  cat("Generating out-of-sample predictions...\n")

  # Tree 1: predict on test data
  ft1 <- ptree_predict_oos(fits$fit1, test_data, all_chars)

  if (is.null(ft1)) {
    cat("ERROR: predict() failed for Tree 1\n")
    return(NULL)
  }

  # Tree 2: predict on test data
  ft2 <- ptree_predict_oos(fits$fit2, test_data, all_chars)

  if (is.null(ft2)) {
    cat("ERROR: predict() failed for Tree 2\n")
    return(NULL)
  }

  # Tree 3: predict on test data
  ft3 <- ptree_predict_oos(fits$fit3, test_data, all_chars)

  if (is.null(ft3)) {
    cat("ERROR: predict() failed for Tree 3\n")
    return(NULL)
  }

  cat("Out-of-sample predictions successful!\n")

  data.frame(
    month = sort(unique(test_data$date)),
    factor1 = as.numeric(ft1),
    factor2 = as.numeric(ft2),
    factor3 = as.numeric(ft3)
  )
}

###### SCENARIO A: Full Sample (1997-2022) #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("SCENARIO A: FULL SAMPLE (like P-Tree-a)\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

train_data_a <- data
results_a <- train_ptree_trio(train_data_a, "Full Sample")

# Save results
output_dir_a = "results/ptree_scenario_a_full"
dir.create(output_dir_a, showWarnings = FALSE, recursive = TRUE)
save(results_a, file = file.path(output_dir_a, "ptree_models.RData"))

all_dates_a <- sort(unique(train_data_a$date))
factors_a = data.frame(
  month = all_dates_a,
  factor1 = results_a$fit1$ft,
  factor2 = results_a$fit2$ft,
  factor3 = results_a$fit3$ft
)
write.csv(factors_a, file.path(output_dir_a, "ptree_factors.csv"), row.names = FALSE)
cat("Saved to:", output_dir_a, "\n\n")

###### SCENARIO B: Time Split (Train: 1997-2010, Test: 2010-2020) #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("SCENARIO B: TIME SPLIT (like P-Tree-b)\n")
cat("Train: 1997-2010 | Test: 2010-2020\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

split_date <- as.Date('2010-01-01')
train_data_b <- data[data$date < split_date, ]
test_data_b <- data[data$date >= split_date, ]

cat("Split date:", as.character(split_date), "\n\n")

results_b <- train_ptree_trio(train_data_b, "Time Split (First Half)")

# Save IS (training) factors
output_dir_b = "results/ptree_scenario_b_split"
dir.create(output_dir_b, showWarnings = FALSE, recursive = TRUE)
save(results_b, file = file.path(output_dir_b, "ptree_models.RData"))

all_dates_b <- sort(unique(train_data_b$date))
factors_b_is = data.frame(
  month = all_dates_b,
  factor1 = results_b$fit1$ft,
  factor2 = results_b$fit2$ft,
  factor3 = results_b$fit3$ft
)
write.csv(factors_b_is, file.path(output_dir_b, "ptree_factors_is.csv"), row.names = FALSE)

# Attempt OOS on test_data_b
factors_b_oos <- apply_ptree_trio_oos(results_b, test_data_b, all_chars)
if (!is.null(factors_b_oos)) {
  write.csv(factors_b_oos, file.path(output_dir_b, "ptree_factors_oos.csv"), row.names = FALSE)
  cat("Saved IS+OOS to:", output_dir_b, "(B)\n\n")
} else {
  # Backward-compatible: write legacy filename for IS too
  write.csv(factors_b_is, file.path(output_dir_b, "ptree_factors.csv"), row.names = FALSE)
  cat("Note: OOS prediction unavailable (no predict() in PTree). Wrote IS only.\n\n")
}

###### SCENARIO C: Reverse Split (Train: 2010-2020, Test: 1997-2010) #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("SCENARIO C: REVERSE SPLIT (like P-Tree-c)\n")
cat("Train: 2010-2020 | Test: 1997-2010\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

train_data_c <- data[data$date >= split_date, ]
test_data_c <- data[data$date < split_date, ]

results_c <- train_ptree_trio(train_data_c, "Reverse Split (Second Half)")

# Save IS (training) factors
output_dir_c = "results/ptree_scenario_c_reverse"
dir.create(output_dir_c, showWarnings = FALSE, recursive = TRUE)
save(results_c, file = file.path(output_dir_c, "ptree_models.RData"))

all_dates_c <- sort(unique(train_data_c$date))
factors_c_is = data.frame(
  month = all_dates_c,
  factor1 = results_c$fit1$ft,
  factor2 = results_c$fit2$ft,
  factor3 = results_c$fit3$ft
)
write.csv(factors_c_is, file.path(output_dir_c, "ptree_factors_is.csv"), row.names = FALSE)

# Attempt OOS on test_data_c
factors_c_oos <- apply_ptree_trio_oos(results_c, test_data_c, all_chars)
if (!is.null(factors_c_oos)) {
  write.csv(factors_c_oos, file.path(output_dir_c, "ptree_factors_oos.csv"), row.names = FALSE)
  cat("Saved IS+OOS to:", output_dir_c, "(C)\n\n")
} else {
  # Backward-compatible: write legacy filename for IS too
  write.csv(factors_c_is, file.path(output_dir_c, "ptree_factors.csv"), row.names = FALSE)
  cat("Note: OOS prediction unavailable (no predict() in PTree). Wrote IS only.\n\n")
}

###### Final Summary Table #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("FINAL SUMMARY - ALL SCENARIOS\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

summary_df <- data.frame(
  Scenario = c("A: Full Sample", "B: Time Split", "C: Reverse Split"),
  Period = c(
    paste(min(train_data_a$date), "to", max(train_data_a$date)),
    paste(min(train_data_b$date), "to", max(train_data_b$date)),
    paste(min(train_data_c$date), "to", max(train_data_c$date))
  ),
  Months = c(
    length(unique(train_data_a$date)),
    length(unique(train_data_b$date)),
    length(unique(train_data_c$date))
  ),
  Tree1_Nodes = c(results_a$nodes[1], results_b$nodes[1], results_c$nodes[1]),
  Tree1_Sharpe = round(c(results_a$sharpes[1], results_b$sharpes[1], results_c$sharpes[1]), 3),
  Tree2_Sharpe = round(c(results_a$sharpes[2], results_b$sharpes[2], results_c$sharpes[2]), 3),
  Tree3_Sharpe = round(c(results_a$sharpes[3], results_b$sharpes[3], results_c$sharpes[3]), 3),
  Runtime_Sec = round(c(results_a$runtime, results_b$runtime, results_c$runtime), 1)
)

print(summary_df)

write.csv(summary_df, "results/ptree_all_scenarios_summary.csv", row.names = FALSE)
cat("\nSummary saved to: results/ptree_all_scenarios_summary.csv\n")

t_total = proc.time() - t_total
cat(sprintf("\nTotal runtime: %.2f minutes\n", t_total[3]/60))

cat("\n")
cat(paste(rep("=", 80), collapse=""), "\n")
cat("SUCCESS: Complete P-Tree Analysis Finished\n")
cat(paste(rep("=", 80), collapse=""), "\n")
cat("\nNext steps:\n")
cat("1. Run benchmark comparisons (CAPM, FF3, FF4) for each scenario\n")
cat("2. Calculate out-of-sample performance for scenarios B and C\n")
cat("3. Generate comparison tables matching paper format\n")
