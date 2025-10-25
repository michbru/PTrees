############################################################################
# Test P-Tree with AGGRESSIVE parameters to force splits
############################################################################

library(PTree)

cat("TESTING WITH AGGRESSIVE PARAMETERS\n")
cat("===================================\n\n")

# Load data
data_path = "results/ptree_ready_data_full.csv"
data <- read.csv(data_path, stringsAsFactors = FALSE)
data$date <- as.Date(data$date, format='%Y-%m-%d')

# Use subset of data (first 100 months) for speed
start_date = as.Date('1997-02-01')
end_date = as.Date('2005-04-01')  # ~100 months
data1 <- data[(data$date >= start_date) & (data$date <= end_date), ]

cat("Data: ", nrow(data1), "observations\n")
cat("Period:", min(data1$date), "to", max(data1$date), "\n")
cat("Months:", length(unique(data1$date)), "\n\n")

# Prepare training data
all_chars <- names(data)[grep("^rank_", names(data))]
instruments = all_chars[1:min(5, length(all_chars))]
splitting_chars <- all_chars

X_train = data1[, splitting_chars]
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

cat("Training setup:\n")
cat("  Stocks:", num_stocks, "\n")
cat("  Months:", num_months, "\n")
cat("  Characteristics:", ncol(X_train), "\n\n")

# AGGRESSIVE PARAMETERS
params <- list(
  list(name="Very Small Leaves", min_leaf_size=2, num_cutpoints=10, num_iter=15),
  list(name="Tiny Leaves", min_leaf_size=1, num_cutpoints=10, num_iter=15),
  list(name="Many Cutpoints", min_leaf_size=5, num_cutpoints=20, num_iter=15),
  list(name="Original (control)", min_leaf_size=10, num_cutpoints=4, num_iter=9)
)

results <- list()

for (p in params) {
  cat("\n")
  cat(paste(rep("=", 70), collapse=""), "\n")
  cat("TEST:", p$name, "\n")
  cat("  min_leaf_size =", p$min_leaf_size, "\n")
  cat("  num_cutpoints =", p$num_cutpoints, "\n")
  cat("  num_iter =", p$num_iter, "\n")
  cat(paste(rep("-", 70), collapse=""), "\n")

  Y_train = data1[, "xret"]
  H_train = rep(0, nrow(data1))

  start_time <- Sys.time()

  fit <- tryCatch({
    PTree(R_train, Y_train, X_train, Z_train, H_train, portfolio_weight_train,
          loss_weight_train, stocks_train, months_train, first_split_var, second_split_var,
          num_stocks, num_months,
          min_leaf_size = p$min_leaf_size,
          max_depth = 10,
          num_iter = p$num_iter,
          num_cutpoints = p$num_cutpoints,
          eta = 1,
          equal_weight = FALSE,
          no_H1 = TRUE,
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
  }, error = function(e) {
    cat("ERROR:", e$message, "\n")
    return(NULL)
  })

  end_time <- Sys.time()
  runtime <- as.numeric(difftime(end_time, start_time, units="secs"))

  cat("Runtime:", round(runtime, 2), "seconds\n")

  if (!is.null(fit)) {
    cat("Tree structure:", fit$tree, "\n")

    # Check for splits
    tree_parts <- strsplit(fit$tree, "\n")[[1]]
    num_nodes <- as.numeric(tree_parts[1])

    cat("Number of nodes:", num_nodes, "\n")

    if (num_nodes > 1) {
      cat("SUCCESS: TREE SPLIT!\n")
    } else {
      cat("No split - single node\n")
    }

    # Calculate Sharpe
    sharpe <- mean(fit$ft) / sd(fit$ft) * sqrt(12)
    cat("Sharpe Ratio:", round(sharpe, 3), "\n")
  }
}

cat("\n")
cat(paste(rep("=", 70), collapse=""), "\n")
cat("ANALYSIS COMPLETE\n")
cat(paste(rep("=", 70), collapse=""), "\n")
