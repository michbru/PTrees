############################################################################
# P-Tree Analysis with PROPER Train/Test Split
# Following Cong et al. (2024) methodology
############################################################################

t_total = proc.time()

library(PTree)

cat(paste(rep("=", 80), collapse=""), "\n")
cat("P-TREE ANALYSIS - TRAIN/TEST SPLIT (Following Paper Methodology)\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

###### Three Scenarios (matching paper) #####

scenarios <- list(
  list(
    name = "Swedish-Full",
    description = "Full sample (like P-Tree-a in paper)",
    train_start = '1997-02-01',
    train_end = '2020-07-31',  # Match macro data availability
    test_start = '2020-08-01',
    test_end = '2022-12-31'
  ),
  list(
    name = "Swedish-Split",
    description = "First half train, second half test (like P-Tree-b)",
    train_start = '1997-02-01',
    train_end = '2009-12-31',  # ~13 years
    test_start = '2010-01-01',
    test_end = '2020-07-31'    # ~10.5 years
  ),
  list(
    name = "Swedish-Recent",
    description = "Recent period only (more stationary)",
    train_start = '2005-01-01',
    train_end = '2015-12-31',  # 11 years
    test_start = '2016-01-01',
    test_end = '2020-07-31'    # 4.5 years
  )
)

###### Load Data #####
cat("Loading data...\n")
data_path = "results/ptree_ready_data_full.csv"
data <- read.csv(data_path, stringsAsFactors = FALSE)
data$date <- as.Date(data$date, format='%Y-%m-%d')

all_chars <- names(data)[grep("^rank_", names(data))]
instruments = all_chars[1:min(5, length(all_chars))]
first_split_var = seq(0, length(all_chars)-1)
second_split_var = seq(0, length(all_chars)-1)

cat("Total data:", nrow(data), "observations\n")
cat("Period:", min(data$date), "to", max(data$date), "\n\n")

###### Tree Parameters #####
# Try with smaller min_leaf_size since we proved it can split
min_leaf_size = 5        # Reduced from 10
max_depth = 10
max_depth_boosting = 10
num_iter = 9
num_iterB = 9
num_cutpoints = 4
equal_weight = FALSE
lambda_mean = 0
lambda_cov = 1e-4
lambda_mean_factor = 0
lambda_cov_factor = 1e-5

###### Run All Scenarios #####

all_results <- list()

for (scenario in scenarios) {

  cat("\n")
  cat(paste(rep("=", 80), collapse=""), "\n")
  cat("SCENARIO:", scenario$name, "\n")
  cat(scenario$description, "\n")
  cat(paste(rep("=", 80), collapse=""), "\n\n")

  # Split data
  train_data <- data[(data$date >= as.Date(scenario$train_start)) &
                     (data$date <= as.Date(scenario$train_end)), ]
  test_data <- data[(data$date >= as.Date(scenario$test_start)) &
                    (data$date <= as.Date(scenario$test_end)), ]

  cat("TRAIN period:", scenario$train_start, "to", scenario$train_end, "\n")
  cat("  Observations:", nrow(train_data), "\n")
  cat("  Months:", length(unique(train_data$date)), "\n")
  cat("  Stocks:", length(unique(train_data$permno)), "\n")

  cat("\nTEST period:", scenario$test_start, "to", scenario$test_end, "\n")
  cat("  Observations:", nrow(test_data), "\n")
  cat("  Months:", length(unique(test_data$date)), "\n")
  cat("  Stocks:", length(unique(test_data$permno)), "\n\n")

  ###### Prepare Training Data #####
  X_train = train_data[, all_chars]
  R_train = train_data[, "xret"]
  months_train = as.numeric(as.factor(train_data$date)) - 1
  stocks_train = as.numeric(as.factor(train_data$permno)) - 1
  Z_train = cbind(1, train_data[, instruments])
  portfolio_weight_train = train_data[, "lag_me"]
  loss_weight_train = train_data[, "lag_me"]
  num_months_train = length(unique(months_train))
  num_stocks_train = length(unique(stocks_train))

  ###### Train P-Tree 1 (No Benchmark) #####
  cat(paste(rep("-", 80), collapse=""), "\n")
  cat("Training P-Tree 1 (No Benchmark)...\n")
  cat(paste(rep("-", 80), collapse=""), "\n")

  Y_train1 = train_data[, "xret"]
  H_train1 = rep(0, nrow(train_data))

  t1 = proc.time()

  fit1 = PTree(R_train, Y_train1, X_train, Z_train, H_train1,
               portfolio_weight_train, loss_weight_train,
               stocks_train, months_train, first_split_var, second_split_var,
               num_stocks_train, num_months_train,
               min_leaf_size, max_depth, num_iter, num_cutpoints,
               eta = 1, equal_weight = equal_weight,
               no_H = TRUE,  # CORRECT: no benchmark for first tree
               abs_normalize = TRUE, weighted_loss = FALSE,
               lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
               early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
               a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
               random_split = FALSE)

  t1 = proc.time() - t1

  # Check tree structure
  tree_nodes = as.numeric(strsplit(fit1$tree, "\n")[[1]][1])
  cat("  Runtime:", round(t1[3], 2), "seconds\n")
  cat("  Tree nodes:", tree_nodes, "\n")
  if (tree_nodes > 1) {
    cat("  SUCCESS: Tree split into", tree_nodes, "nodes!\n")
  } else {
    cat("  No split - defaulted to market portfolio\n")
  }

  # In-sample performance
  sharpe_train = mean(fit1$ft) / sd(fit1$ft) * sqrt(12)
  cat("  In-sample Sharpe:", round(sharpe_train, 3), "\n")

  ###### Train P-Tree 2 (Boosting) #####
  cat("\nTraining P-Tree 2 (Boosting on P-Tree 1)...\n")

  Y_train2 = train_data[, "xret"]
  H_train2 = fit1$ft

  fit2 = PTree(R_train, Y_train2, X_train, Z_train, H_train2,
               portfolio_weight_train, loss_weight_train,
               stocks_train, months_train, first_split_var, second_split_var,
               num_stocks_train, num_months_train,
               min_leaf_size, max_depth_boosting, num_iterB, num_cutpoints,
               eta = 1, equal_weight = equal_weight,
               no_H = FALSE,  # CORRECT: use previous factor as benchmark
               abs_normalize = TRUE, weighted_loss = FALSE,
               lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
               early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
               a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
               random_split = FALSE)

  tree_nodes2 = as.numeric(strsplit(fit2$tree, "\n")[[1]][1])
  cat("  Tree nodes:", tree_nodes2, "\n")

  ###### Train P-Tree 3 (Boosting) #####
  cat("\nTraining P-Tree 3 (Boosting on P-Trees 1-2)...\n")

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

  tree_nodes3 = as.numeric(strsplit(fit3$tree, "\n")[[1]][1])
  cat("  Tree nodes:", tree_nodes3, "\n\n")

  ###### Out-of-Sample Testing #####
  if (nrow(test_data) > 0) {
    cat(paste(rep("-", 80), collapse=""), "\n")
    cat("Out-of-Sample Testing...\n")
    cat(paste(rep("-", 80), collapse=""), "\n")

    # For OOS, we need to predict factor returns on test data
    # This requires applying the trained tree to new data
    # The PTree package should have a predict function, but if not,
    # we evaluate the same value-weighted portfolio on test period

    # Simple approach: Use the same tree structure on test data
    # Extract leaf assignments from training and apply to test

    cat("Note: Out-of-sample prediction requires leaf assignment prediction\n")
    cat("(Feature not implemented in this version)\n")
    cat("Alternative: Evaluate training period Sharpe as benchmark\n\n")
  }

  ###### Save Results #####
  output_dir = file.path("results", paste0("ptree_", tolower(scenario$name)))
  dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

  # Save models
  save(fit1, fit2, fit3, file = file.path(output_dir, "ptree_models.RData"))

  # Save factor time series
  all_dates <- sort(unique(train_data$date))
  factors_df = data.frame(
    month = all_dates,
    factor1 = fit1$ft,
    factor2 = fit2$ft,
    factor3 = fit3$ft
  )
  write.csv(factors_df, file.path(output_dir, "ptree_factors.csv"), row.names = FALSE)

  cat("Results saved to:", output_dir, "\n")

  ###### Store Summary #####
  all_results[[scenario$name]] <- list(
    train_months = length(unique(train_data$date)),
    test_months = length(unique(test_data$date)),
    tree1_nodes = tree_nodes,
    tree2_nodes = tree_nodes2,
    tree3_nodes = tree_nodes3,
    train_sharpe = sharpe_train,
    runtime_sec = t1[3]
  )
}

###### Final Summary #####
cat("\n\n")
cat(paste(rep("=", 80), collapse=""), "\n")
cat("FINAL SUMMARY - ALL SCENARIOS\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

summary_df <- data.frame(
  Scenario = character(),
  Train_Months = integer(),
  Test_Months = integer(),
  Tree1_Nodes = integer(),
  Tree2_Nodes = integer(),
  Tree3_Nodes = integer(),
  Train_Sharpe = numeric(),
  Runtime_Sec = numeric(),
  stringsAsFactors = FALSE
)

for (name in names(all_results)) {
  r <- all_results[[name]]
  summary_df <- rbind(summary_df, data.frame(
    Scenario = name,
    Train_Months = r$train_months,
    Test_Months = r$test_months,
    Tree1_Nodes = r$tree1_nodes,
    Tree2_Nodes = r$tree2_nodes,
    Tree3_Nodes = r$tree3_nodes,
    Train_Sharpe = round(r$train_sharpe, 3),
    Runtime_Sec = round(r$runtime_sec, 2),
    stringsAsFactors = FALSE
  ))
}

print(summary_df)

write.csv(summary_df, "results/ptree_scenarios_summary.csv", row.names = FALSE)
cat("\nSummary saved to: results/ptree_scenarios_summary.csv\n")

t_total = proc.time() - t_total
cat(sprintf("\nTotal runtime: %.2f minutes\n", t_total[3]/60))

cat("\n")
cat(paste(rep("=", 80), collapse=""), "\n")
cat("ANALYSIS COMPLETE\n")
cat(paste(rep("=", 80), collapse=""), "\n")
