#!/usr/bin/env Rscript

# Debug Script: Investigate P-Tree Depth vs Stop Threshold
# --------------------------------------------------------

suppressPackageStartupMessages({
  library(data.table)
  library(PTree)
})

# Paths
repo_root <- normalizePath(file.path("."), mustWork = FALSE)
in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")

if (!file.exists(in_rds)) stop("Inputs RDS not found.")
inp <- readRDS(in_rds)


# Prepare Data (Scenario A: Full Sample)
dt_full <- copy(inp$dt)
setDT(dt_full) # Ensure it is a data.table

# Type Checks
cat("Checking input types...\n")
char_cols <- inp$char_cols
cat("Number of char_cols:", length(char_cols), "\n")
cat("First few char_cols:", paste(head(char_cols), collapse=", "), "\n")

# Inspect subset
subset_dt <- dt_full[, ..char_cols]
cat("Subset class:", class(subset_dt), "\n")
cat("Subset dim:", paste(dim(subset_dt), collapse=" x "), "\n")
cat("Subset str (first 2 cols):\n")
str(subset_dt[, 1:2])

bad_cols <- names(dt_full)[sapply(dt_full, is.character)]
cat("Character columns in dt_full:", paste(bad_cols, collapse=", "), "\n")



# Construct Matrices
cat("Constructing X matrix from subset_dt (via data.frame)...\n")
# We already created subset_dt above
if (!exists("subset_dt")) subset_dt <- dt_full[, ..char_cols]

X <- as.matrix(as.data.frame(subset_dt))
Z <- cbind(Intercept = 1, if (length(inp$instr_cols)>0) as.matrix(as.data.frame(dt_full[, ..inp$instr_cols])) else NULL)

cat("X mode:", mode(X), "\n")
cat("X class:", class(X), "\n")
cat("X dim:", paste(dim(X), collapse=" x "), "\n")

if (any(is.na(X))) {
  cat("WARNING: X contains NAs. Count:", sum(is.na(X)), "\n")
  X[is.na(X)] <- 0
}

cat("X summary (first 5 cols):\n")
print(summary(X[, 1:5]))

R <- as.vector(dt_full$ret_next) * 100
Y <- R
months <- as.integer(as.factor(dt_full$date)) - 1L
stocks <- as.integer(as.factor(dt_full$isin)) - 1L
pw <- as.vector(dt_full$lag_me)
lw <- as.vector(dt_full$lag_me)

num_months <- length(unique(months))
num_stocks <- length(unique(stocks))

# Helper to train with specific threshold
train_debug <- function(threshold) {
  cat(sprintf("\n--- Testing stop_threshold = %.4f ---\n", threshold))
  
  fit <- PTree::PTree(
    R, Y, X, Z,
    H = rep(0, num_months),
    pw, lw,
    stocks, months,
    seq(0L, ncol(X)-1L), seq(0L, ncol(X)-1L),
    num_stocks, num_months,
    min_leaf_size = 10,
    max_depth = 6,
    num_iter = 1,
    num_cutpoints = 100,
    eta = 1.0,
    equal_weight = TRUE,
    no_H = TRUE,
    abs_normalize = TRUE,
    weighted_loss = FALSE,
    lambda_mean = 0,
    lambda_cov = 0,
    lambda_mean_factor = 0,
    lambda_cov_factor = 0,
    early_stop = FALSE,
    stop_threshold = threshold,   # <--- VARIABLE
    lambda_ridge = 0,
    a1 = 0, a2 = 0,
    list_K = matrix(rep(0, 3), nrow = 3, ncol = 1),
    random_split = FALSE
  )
  
  # Parse tree depth
  tree_str <- as.character(fit$tree)
  splits <- length(grep("Split", unlist(strsplit(tree_str, "\n"))))
  
  cat("  Tree Structure:\n")
  cat(paste("  ", unlist(strsplit(tree_str, "\n")), collapse="\n"))
  cat(sprintf("\n  Total Splits: %d\n", splits))
  
  ft <- as.numeric(fit$ft)
  mean_m <- mean(ft, na.rm=TRUE)
  std_m <- sd(ft, na.rm=TRUE)
  sharpe <- if (std_m > 0) mean_m / std_m * sqrt(12) else NA_real_
  cat(sprintf("  Sharpe: %.2f\n", sharpe))
  
  return(list(threshold=threshold, splits=splits, sharpe=sharpe))
}

# Run Experiments
results <- list()
thresholds <- c(0.95, 0.99, 0.999, 0.9999)

for (thr in thresholds) {
  results[[as.character(thr)]] <- train_debug(thr)
}

cat("\n=== SUMMARY ===\n")
print(rbindlist(results))
