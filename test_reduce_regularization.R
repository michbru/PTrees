############################################################################
# Test P-Tree with REDUCED regularization
############################################################################

library(PTree)

cat("TESTING WITH REDUCED REGULARIZATION\n")
cat("====================================\n\n")

# Load data (use subset for speed)
data_path = "results/ptree_ready_data_full.csv"
data <- read.csv(data_path, stringsAsFactors = FALSE)
data$date <- as.Date(data$date, format='%Y-%m-%d')

# Use 100 months
data1 <- data[(data$date >= as.Date('2000-01-01')) & (data$date <= as.Date('2008-04-01')), ]

cat("Data:", nrow(data1), "observations,", length(unique(data1$permno)), "stocks,", length(unique(data1$date)), "months\n\n")

# Prepare training data
all_chars <- names(data)[grep("^rank_", names(data))]
instruments = all_chars[1:min(5, length(all_chars))]

X_train = data1[, all_chars]
R_train = data1[, "xret"]
months_train = as.numeric(as.factor(data1$date)) - 1
stocks_train = as.numeric(as.factor(data1$permno)) - 1
Z_train = cbind(1, data1[, instruments])
portfolio_weight_train = data1[, "lag_me"]
loss_weight_train = data1[, "lag_me"]
num_months = length(unique(months_train))
num_stocks = length(unique(stocks_train))
first_split_var = seq(0, length(all_chars)-1)
second_split_var = seq(0, length(all_chars)-1)

Y_train = data1[, "xret"]
H_train = rep(0, nrow(data1))

# TEST 1: Original parameters
cat(paste(rep("=", 70), collapse=""), "\n")
cat("TEST 1: Original parameters (baseline)\n")
cat("min_leaf_size=10, lambda_cov=1e-4\n")
cat(paste(rep("-", 70), collapse=""), "\n")

fit1 <- PTree(R_train, Y_train, X_train, Z_train, H_train, portfolio_weight_train,
              loss_weight_train, stocks_train, months_train, first_split_var, second_split_var,
              num_stocks, num_months,
              min_leaf_size = 10, max_depth = 10, num_iter = 9, num_cutpoints = 4,
              eta = 1, equal_weight = FALSE, no_H = TRUE,
              abs_normalize = TRUE, weighted_loss = FALSE,
              lambda_mean = 0, lambda_cov = 1e-4,
              lambda_mean_factor = 0, lambda_cov_factor = 1e-5,
              early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
              a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
              random_split = FALSE)

cat("Result:", fit1$tree, "\n\n")

# TEST 2: Smaller min_leaf_size
cat(paste(rep("=", 70), collapse=""), "\n")
cat("TEST 2: Smaller min_leaf_size\n")
cat("min_leaf_size=3, lambda_cov=1e-4\n")
cat(paste(rep("-", 70), collapse=""), "\n")

fit2 <- PTree(R_train, Y_train, X_train, Z_train, H_train, portfolio_weight_train,
              loss_weight_train, stocks_train, months_train, first_split_var, second_split_var,
              num_stocks, num_months,
              min_leaf_size = 3, max_depth = 10, num_iter = 9, num_cutpoints = 4,
              eta = 1, equal_weight = FALSE, no_H = TRUE,
              abs_normalize = TRUE, weighted_loss = FALSE,
              lambda_mean = 0, lambda_cov = 1e-4,
              lambda_mean_factor = 0, lambda_cov_factor = 1e-5,
              early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
              a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
              random_split = FALSE)

cat("Result:", fit2$tree, "\n\n")

# TEST 3: Much smaller regularization
cat(paste(rep("=", 70), collapse=""), "\n")
cat("TEST 3: Reduced regularization\n")
cat("min_leaf_size=10, lambda_cov=1e-6\n")
cat(paste(rep("-", 70), collapse=""), "\n")

fit3 <- PTree(R_train, Y_train, X_train, Z_train, H_train, portfolio_weight_train,
              loss_weight_train, stocks_train, months_train, first_split_var, second_split_var,
              num_stocks, num_months,
              min_leaf_size = 10, max_depth = 10, num_iter = 9, num_cutpoints = 4,
              eta = 1, equal_weight = FALSE, no_H = TRUE,
              abs_normalize = TRUE, weighted_loss = FALSE,
              lambda_mean = 0, lambda_cov = 1e-6,
              lambda_mean_factor = 0, lambda_cov_factor = 1e-7,
              early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
              a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
              random_split = FALSE)

cat("Result:", fit3$tree, "\n\n")

# TEST 4: Both smaller
cat(paste(rep("=", 70), collapse=""), "\n")
cat("TEST 4: Smaller min_leaf AND less regularization\n")
cat("min_leaf_size=3, lambda_cov=1e-6\n")
cat(paste(rep("-", 70), collapse=""), "\n")

fit4 <- PTree(R_train, Y_train, X_train, Z_train, H_train, portfolio_weight_train,
              loss_weight_train, stocks_train, months_train, first_split_var, second_split_var,
              num_stocks, num_months,
              min_leaf_size = 3, max_depth = 10, num_iter = 9, num_cutpoints = 4,
              eta = 1, equal_weight = FALSE, no_H = TRUE,
              abs_normalize = TRUE, weighted_loss = FALSE,
              lambda_mean = 0, lambda_cov = 1e-6,
              lambda_mean_factor = 0, lambda_cov_factor = 1e-7,
              early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
              a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
              random_split = FALSE)

cat("Result:", fit4$tree, "\n\n")

# TEST 5: NO regularization
cat(paste(rep("=", 70), collapse=""), "\n")
cat("TEST 5: ZERO regularization\n")
cat("min_leaf_size=5, lambda_cov=0\n")
cat(paste(rep("-", 70), collapse=""), "\n")

fit5 <- PTree(R_train, Y_train, X_train, Z_train, H_train, portfolio_weight_train,
              loss_weight_train, stocks_train, months_train, first_split_var, second_split_var,
              num_stocks, num_months,
              min_leaf_size = 5, max_depth = 10, num_iter = 9, num_cutpoints = 4,
              eta = 1, equal_weight = FALSE, no_H = TRUE,
              abs_normalize = TRUE, weighted_loss = FALSE,
              lambda_mean = 0, lambda_cov = 0,
              lambda_mean_factor = 0, lambda_cov_factor = 0,
              early_stop = FALSE, stop_threshold = 1, lambda_ridge = 0,
              a1 = 0, a2 = 0, list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
              random_split = FALSE)

cat("Result:", fit5$tree, "\n\n")

cat(paste(rep("=", 70), collapse=""), "\n")
cat("SUMMARY\n")
cat(paste(rep("=", 70), collapse=""), "\n")
cat("Did any configuration produce splits?\n")
for (i in 1:5) {
  fit <- get(paste0("fit", i))
  num_nodes <- as.numeric(strsplit(fit$tree, "\n")[[1]][1])
  cat("Test", i, ":", num_nodes, "node(s)")
  if (num_nodes > 1) {
    cat(" - SUCCESS: SPLIT!\n")
  } else {
    cat(" - No split\n")
  }
}
