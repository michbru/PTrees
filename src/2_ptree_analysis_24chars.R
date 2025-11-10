############################################################################
# P-TREE ANALYSIS - 24 MATCHED CHARACTERISTICS
#
# Training P-Tree with ONLY the 24 characteristics that match the
# Cong et al. (2024) US study to compare performance.
#
# Scenario A (Full): Train on entire period 1997-2022
############################################################################

t_total = proc.time()

library(PTree)

cat(paste(rep("=", 80), collapse=""), "\n")
cat("P-TREE ANALYSIS - 24 MATCHED CHARACTERISTICS (US STUDY)\n")
cat("Following Cong et al. (2024) Journal of Financial Economics\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

###### Parameters (Scaled for Swedish Market) #####

min_leaf_size = 3  # Scaled for Swedish market
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
cat("  min_leaf_size =", min_leaf_size, "\n")
cat("  max_depth =", max_depth, "\n")
cat("  num_iter =", num_iter, "\n")
cat("  num_cutpoints =", num_cutpoints, "\n")
cat("  Regularization: lambda_cov =", lambda_cov, "\n\n")

###### Load Data #####

cat("Loading 24-characteristic dataset...\n")
data_path = "results/ptree_ready_data_24chars.csv"
data <- read.csv(data_path, stringsAsFactors = FALSE)
data$date <- as.Date(data$date, format='%Y-%m-%d')

all_chars <- names(data)[grep("^rank_", names(data))]
instruments = all_chars[1:min(5, length(all_chars))]
first_split_var = seq(0, length(all_chars)-1)
second_split_var = seq(0, length(all_chars)-1)

cat("  Total observations:", nrow(data), "\n")
cat("  Date range:", as.character(min(data$date)), "to", as.character(max(data$date)), "\n")
cat("  Unique stocks:", length(unique(data$permno)), "\n")
cat("  Characteristics:", length(all_chars), "(matched to US study)\n\n")

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

###### Helper for training trio (aligned with main script) #####

ptree_predict_oos <- function(fit, test_data, all_chars) {
  X_test <- test_data[, all_chars]
  R_test <- test_data[, "xret"]
  months_test <- as.numeric(as.factor(test_data$date)) - 1
  weight_test <- test_data[, "lag_me"]
  pred <- try(predict(fit, X_test, R_test, months_test, weight_test), silent=TRUE)
  if (inherits(pred, "try-error")) return(NULL)
  return(pred$ft)
}

train_ptree_trio <- function(train_data, scenario_name) {
  cat(paste(rep("-", 80), collapse=""), "\n")
  cat("Training 3 P-Trees for:", scenario_name, "\n")
  cat(paste(rep("-", 80), collapse=""), "\n\n")

  dl <- prepare_design(train_data, all_chars, instruments)

  cat("Training data:\n")
  cat("  Observations:", nrow(train_data), "\n")
  cat("  Months:", dl$num_months, "\n")
  cat("  Stocks:", dl$num_stocks, "\n\n")

  # Tree 1 (no benchmark)
  cat("P-Tree 1 (No Benchmark)...\n")
  Y1 = train_data[, "xret"]
  H1 = rep(0, nrow(train_data))
  t1 = proc.time()
  fit1 = PTree(dl$R, Y1, dl$X, dl$Z, H1,
               dl$portfolio_weight, dl$loss_weight,
               dl$stocks, dl$months, first_split_var, second_split_var,
               dl$num_stocks, dl$num_months,
               min_leaf_size, max_depth, num_iter, num_cutpoints,
               eta = 1, equal_weight = equal_weight,
               no_H = TRUE, abs_normalize = TRUE, weighted_loss = FALSE,
               lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
               early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
               a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
               random_split = FALSE)
  t1 = proc.time() - t1
  tree1_nodes = as.numeric(strsplit(fit1$tree, "\n")[[1]][1])
  sharpe1 = calculate_sharpe(fit1$ft)
  cat("  Nodes:", tree1_nodes, "| Sharpe:", round(sharpe1, 3), "| Time:", round(t1[3], 1), "sec\n")

  # Tree 2 (boosting)
  cat("P-Tree 2 (Boosting on P-Tree 1)...\n")
  Y2 = train_data[, "xret"]
  H2 = fit1$ft
  fit2 = PTree(dl$R, Y2, dl$X, dl$Z, H2,
               dl$portfolio_weight, dl$loss_weight,
               dl$stocks, dl$months, first_split_var, second_split_var,
               dl$num_stocks, dl$num_months,
               min_leaf_size, max_depth_boosting, num_iterB, num_cutpoints,
               eta = 1, equal_weight = equal_weight,
               no_H = FALSE, abs_normalize = TRUE, weighted_loss = FALSE,
               lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
               early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
               a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
               random_split = FALSE)
  tree2_nodes = as.numeric(strsplit(fit2$tree, "\n")[[1]][1])
  sharpe2 = calculate_sharpe(fit2$ft)
  cat("  Nodes:", tree2_nodes, "| Sharpe:", round(sharpe2, 3), "\n")

  # Tree 3 (boosting)
  cat("P-Tree 3 (Boosting on P-Trees 1-2)...\n")
  Y3 = train_data[, "xret"]
  H3 = cbind(fit1$ft, fit2$ft)
  fit3 = PTree(dl$R, Y3, dl$X, dl$Z, H3,
               dl$portfolio_weight, dl$loss_weight,
               dl$stocks, dl$months, first_split_var, second_split_var,
               dl$num_stocks, dl$num_months,
               min_leaf_size, max_depth_boosting, num_iterB, num_cutpoints,
               eta = 1, equal_weight = equal_weight,
               no_H = FALSE, abs_normalize = TRUE, weighted_loss = FALSE,
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
    sharpes = c(sharpe1, sharpe2, sharpe3)
  ))
}

###### Scenario A: Full Period Training (1997-2022) #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("SCENARIO A: FULL PERIOD TRAINING (24 MATCHED CHARACTERISTICS)\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

train_data <- data
fits <- train_ptree_trio(train_data, "Full Sample (24 chars)")

# Save results under separate folder to avoid interference
output_dir = "results/ptree_24chars_scenario_a_full"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)
save(fits, file = file.path(output_dir, "ptree_models.RData"))

all_dates <- sort(unique(train_data$date))
factors_df = data.frame(
  month = all_dates,
  factor1 = fits$fit1$ft,
  factor2 = fits$fit2$ft,
  factor3 = fits$fit3$ft
)
write.csv(factors_df, file.path(output_dir, "ptree_factors.csv"), row.names = FALSE)
cat("Saved to:", output_dir, "\n\n")

# Quick performance summary (Sharpe of each tree)
summary_df <- data.frame(
  Tree = c("Tree1", "Tree2", "Tree3"),
  Nodes = fits$nodes,
  Sharpe = round(fits$sharpes, 3)
)
print(summary_df)
write.csv(summary_df, "results/ptree_24chars_summary.csv", row.names = FALSE)

cat("\n")
t_total_elapsed = (proc.time() - t_total)[3]
cat(sprintf("[SUCCESS] 24-char analysis complete in %.1f seconds (%.1f minutes)\n", t_total_elapsed, t_total_elapsed/60))
cat(paste(rep("=", 80), collapse=""), "\n")

###### Scenario B: Time Split (Train: 1997-2010, Test: 2010-2020) #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("SCENARIO B: TIME SPLIT (24 MATCHED CHARACTERISTICS)\n")
cat("Train: 1997-2010 | Test: 2010-2020\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

split_date <- as.Date('2010-01-01')
train_data_b <- data[data$date < split_date, ]
test_data_b <- data[data$date >= split_date, ]

cat("Split date:", as.character(split_date), "\n\n")

fits_b <- train_ptree_trio(train_data_b, "Time Split (First Half, 24 chars)")

output_dir_b = "results/ptree_24chars_scenario_b_split"
dir.create(output_dir_b, showWarnings = FALSE, recursive = TRUE)
save(fits_b, file = file.path(output_dir_b, "ptree_models.RData"))

all_dates_b <- sort(unique(train_data_b$date))
factors_b_is = data.frame(
  month = all_dates_b,
  factor1 = fits_b$fit1$ft,
  factor2 = fits_b$fit2$ft,
  factor3 = fits_b$fit3$ft
)
write.csv(factors_b_is, file.path(output_dir_b, "ptree_factors_is.csv"), row.names = FALSE)

factors_b_oos <- try(ptree_predict_oos(fits_b$fit1, test_data_b, all_chars), silent=TRUE)
if (!inherits(factors_b_oos, "try-error") && !is.null(factors_b_oos)) {
  # Apply for each tree
  ft1 <- factors_b_oos
  ft2 <- ptree_predict_oos(fits_b$fit2, test_data_b, all_chars)
  ft3 <- ptree_predict_oos(fits_b$fit3, test_data_b, all_chars)
  if (!is.null(ft2) && !is.null(ft3)) {
    oos_df <- data.frame(
      month = sort(unique(test_data_b$date)),
      factor1 = as.numeric(ft1),
      factor2 = as.numeric(ft2),
      factor3 = as.numeric(ft3)
    )
    write.csv(oos_df, file.path(output_dir_b, "ptree_factors_oos.csv"), row.names = FALSE)
    cat("Saved IS+OOS to:", output_dir_b, "(B)\n\n")
  } else {
    write.csv(factors_b_is, file.path(output_dir_b, "ptree_factors.csv"), row.names = FALSE)
    cat("Note: OOS prediction partially unavailable. Wrote IS only.\n\n")
  }
} else {
  write.csv(factors_b_is, file.path(output_dir_b, "ptree_factors.csv"), row.names = FALSE)
  cat("Note: OOS prediction unavailable. Wrote IS only.\n\n")
}

###### Scenario C: Reverse Split (Train: 2010-2020, Test: 1997-2010) #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("SCENARIO C: REVERSE SPLIT (24 MATCHED CHARACTERISTICS)\n")
cat("Train: 2010-2020 | Test: 1997-2010\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

train_data_c <- data[data$date >= split_date, ]
test_data_c <- data[data$date < split_date, ]

fits_c <- train_ptree_trio(train_data_c, "Reverse Split (Second Half, 24 chars)")

output_dir_c = "results/ptree_24chars_scenario_c_reverse"
dir.create(output_dir_c, showWarnings = FALSE, recursive = TRUE)
save(fits_c, file = file.path(output_dir_c, "ptree_models.RData"))

all_dates_c <- sort(unique(train_data_c$date))
factors_c_is = data.frame(
  month = all_dates_c,
  factor1 = fits_c$fit1$ft,
  factor2 = fits_c$fit2$ft,
  factor3 = fits_c$fit3$ft
)
write.csv(factors_c_is, file.path(output_dir_c, "ptree_factors_is.csv"), row.names = FALSE)

factors_c_oos <- try(ptree_predict_oos(fits_c$fit1, test_data_c, all_chars), silent=TRUE)
if (!inherits(factors_c_oos, "try-error") && !is.null(factors_c_oos)) {
  ft1 <- factors_c_oos
  ft2 <- ptree_predict_oos(fits_c$fit2, test_data_c, all_chars)
  ft3 <- ptree_predict_oos(fits_c$fit3, test_data_c, all_chars)
  if (!is.null(ft2) && !is.null(ft3)) {
    oos_df <- data.frame(
      month = sort(unique(test_data_c$date)),
      factor1 = as.numeric(ft1),
      factor2 = as.numeric(ft2),
      factor3 = as.numeric(ft3)
    )
    write.csv(oos_df, file.path(output_dir_c, "ptree_factors_oos.csv"), row.names = FALSE)
    cat("Saved IS+OOS to:", output_dir_c, "(C)\n\n")
  } else {
    write.csv(factors_c_is, file.path(output_dir_c, "ptree_factors.csv"), row.names = FALSE)
    cat("Note: OOS prediction partially unavailable. Wrote IS only.\n\n")
  }
} else {
  write.csv(factors_c_is, file.path(output_dir_c, "ptree_factors.csv"), row.names = FALSE)
  cat("Note: OOS prediction unavailable. Wrote IS only.\n\n")
}

###### Final Summary (24 chars) #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("FINAL SUMMARY - 24 MATCHED CHARACTERISTICS (A/B/C)\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

summary_24 <- data.frame(
  Scenario = c("A: Full Sample", "B: Time Split", "C: Reverse Split"),
  Period = c(
    paste(min(train_data$date), "to", max(train_data$date)),
    paste(min(train_data_b$date), "to", max(train_data_b$date)),
    paste(min(train_data_c$date), "to", max(train_data_c$date))
  ),
  Months = c(
    length(unique(train_data$date)),
    length(unique(train_data_b$date)),
    length(unique(train_data_c$date))
  ),
  Tree1_Nodes = c(fits$nodes[1], fits_b$nodes[1], fits_c$nodes[1]),
  Tree1_Sharpe = round(c(fits$sharpes[1], fits_b$sharpes[1], fits_c$sharpes[1]), 3),
  Tree2_Sharpe = round(c(fits$sharpes[2], fits_b$sharpes[2], fits_c$sharpes[2]), 3),
  Tree3_Sharpe = round(c(fits$sharpes[3], fits_b$sharpes[3], fits_c$sharpes[3]), 3)
)

print(summary_24)
write.csv(summary_24, "results/ptree_24chars_all_scenarios_summary.csv", row.names = FALSE)
cat("\nSummary saved to: results/ptree_24chars_all_scenarios_summary.csv\n")
