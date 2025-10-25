############################################################################
# Test P-Tree on FULL PERIOD with CORRECTED min_leaf_size
############################################################################

library(PTree)

cat("TESTING FULL 311-MONTH PERIOD WITH CORRECTED PARAMETERS\n")
cat("========================================================\n\n")

# Load data
data_path = "results/ptree_ready_data_full.csv"
data <- read.csv(data_path, stringsAsFactors = FALSE)
data$date <- as.Date(data$date, format='%Y-%m-%d')

# Use FULL period (like P-Tree-a in paper)
data1 <- data

cat("Full data:\n")
cat("  Observations:", nrow(data1), "\n")
cat("  Period:", min(data1$date), "to", max(data1$date), "\n")
cat("  Months:", length(unique(data1$date)), "\n")
cat("  Stocks:", length(unique(data1$permno)), "\n\n")

# Prepare training data
all_chars <- names(data)[grep("^rank_", names(data))]
instruments = all_chars[1:min(5, length(all_chars))]
first_split_var = seq(0, length(all_chars)-1)
second_split_var = seq(0, length(all_chars)-1)

X_train = data1[, all_chars]
R_train = data1[, "xret"]
months_train = as.numeric(as.factor(data1$date)) - 1
stocks_train = as.numeric(as.factor(data1$permno)) - 1
Z_train = cbind(1, data1[, instruments])
portfolio_weight_train = data1[, "lag_me"]
loss_weight_train = data1[, "lag_me"]
num_months = length(unique(months_train))
num_stocks = length(unique(stocks_train))

# Calculate proper min_leaf_size
# US: ~2500 stocks/month with min_leaf=20
# Swedish: ~300 stocks/month
avg_stocks_per_month <- mean(aggregate(stocks_train, by=list(months_train),
                                       FUN=function(x) length(unique(x)))$x)

us_stocks <- 2500
us_min_leaf <- 20
scaled_min_leaf <- round((avg_stocks_per_month / us_stocks) * us_min_leaf)

cat("Parameter calculation:\n")
cat("  US market: ~", us_stocks, "stocks/month, min_leaf_size =", us_min_leaf, "\n")
cat("  Swedish market: ~", round(avg_stocks_per_month), "stocks/month\n")
cat("  Scaled min_leaf_size:", scaled_min_leaf, "\n\n")

# Test with scaled parameter
cat(paste(rep("=", 70), collapse=""), "\n")
cat("TEST: Full 311 months with min_leaf_size =", scaled_min_leaf, "\n")
cat(paste(rep("=", 70), collapse=""), "\n")

Y_train = data1[, "xret"]
H_train = rep(0, nrow(data1))

t1 = proc.time()

fit1 = PTree(R_train, Y_train, X_train, Z_train, H_train,
             portfolio_weight_train, loss_weight_train,
             stocks_train, months_train, first_split_var, second_split_var,
             num_stocks, num_months,
             min_leaf_size = scaled_min_leaf,
             max_depth = 10,
             num_iter = 9,
             num_cutpoints = 4,
             eta = 1,
             equal_weight = FALSE,
             no_H = TRUE,
             abs_normalize = TRUE,
             weighted_loss = FALSE,
             lambda_mean = 0,
             lambda_cov = 1e-4,
             lambda_mean_factor = 0,
             lambda_cov_factor = 1e-5,
             early_stop = FALSE,
             stop_threshold = 1,
             lambda_ridge = 0,
             a1 = 0, a2 = 0,
             list_K = matrix(rep(0,3), nrow = 3, ncol = 1),
             random_split = FALSE)

t1 = proc.time() - t1

cat("\nResults:\n")
cat("  Runtime:", round(t1[3], 2), "seconds\n")

# Parse tree structure
tree_parts <- strsplit(fit1$tree, "\n")[[1]]
num_nodes <- as.numeric(tree_parts[1])

cat("  Tree nodes:", num_nodes, "\n")

if (num_nodes > 1) {
  cat("  SUCCESS: Tree split into", num_nodes, "nodes!\n")
  cat("\nTree structure:\n")
  cat(fit1$tree, "\n")
} else {
  cat("  No split - defaulted to market portfolio\n")
}

# Calculate performance
sharpe <- mean(fit1$ft) / sd(fit1$ft) * sqrt(12)
cat("\n  Sharpe Ratio:", round(sharpe, 3), "\n")
cat("  Mean monthly return:", round(mean(fit1$ft)*100, 2), "%\n")
cat("  Monthly volatility:", round(sd(fit1$ft)*100, 2), "%\n")

cat("\n")
cat(paste(rep("=", 70), collapse=""), "\n")
cat("CONCLUSION\n")
cat(paste(rep("=", 70), collapse=""), "\n")

if (num_nodes > 1) {
  cat("\nWith properly scaled min_leaf_size =", scaled_min_leaf, "\n")
  cat("P-Trees CAN split on the full 311-month Swedish dataset!\n\n")
  cat("This confirms:\n")
  cat("  1. The methodology is correct\n")
  cat("  2. Parameter scaling is crucial for smaller markets\n")
  cat("  3. Swedish market has enough data for P-Tree analysis\n")
} else {
  cat("\nEven with scaled parameters, no split occurred.\n")
  cat("This suggests:\n")
  cat("  1. Swedish market characteristics may not predict returns across full period\n")
  cat("  2. Or regime changes prevent stable splits\n")
  cat("  3. Sub-period analysis may be more appropriate\n")
}
