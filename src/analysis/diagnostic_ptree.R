#!/usr/bin/env Rscript

# Diagnostic Script: Test P-Tree Splitting Behavior
# ------------------------------------------------
# Tests 5 configurations to identify why trees are not splitting.

suppressPackageStartupMessages({
  library(data.table)
  library(PTree)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")
if (!file.exists(in_rds)) stop("Inputs RDS not found.")

cat("Loading inputs...\n")
inp <- readRDS(in_rds)

# Subset for speed (first 10 years)
dt_sub <- inp$dt[date < "2008-01-01"]
cat(sprintf("Subset data: %d rows, %d months\n", nrow(dt_sub), length(unique(dt_sub$date))))

# Helper to build data
build_data <- function(dt, scale_percent=TRUE) {
  # Debug column types
  cat("Checking column types in dt...\n")
  non_num_cols <- names(dt)[sapply(dt, function(c) !is.numeric(c))]
  cat("Non-numeric columns in dt:", paste(non_num_cols, collapse=", "), "\n")
  
  cat("Char cols:", paste(inp$char_cols, collapse=", "), "\n")
  X <- as.matrix(dt[, .SD, .SDcols = inp$char_cols])
  
  if (!is.numeric(X)) {
    cat("X is NOT numeric. Checking columns...\n")
    for (j in 1:ncol(X)) {
      if (!is.numeric(X[,j])) {
        cat(sprintf("  Col %s is %s\n", colnames(X)[j], class(X[,j])))
      }
    }
  }
  R <- as.vector(dt$ret_next)
  if (scale_percent) R <- R * 100
  Y <- R
  Z <- cbind(Intercept = 1, if (length(inp$instr_cols)>0) as.matrix(dt[, ..inp$instr_cols]) else NULL)
  
  months <- as.integer(as.factor(dt$date)) - 1L
  stocks <- as.integer(as.factor(dt$isin)) - 1L
  pw <- as.vector(dt$lag_me)
  lw <- as.vector(dt$lag_me)
  
  # Ensure X is numeric
  if (!is.numeric(X)) {
    cat("Warning: X is not numeric. Converting...\n")
    
    # Debug: print what kind of non-numeric stuff is there
    # Sample a few columns
    for (j in 1:min(5, ncol(X))) {
      if (!is.numeric(X[,j])) {
        cat(sprintf("Column %s is %s. Head: %s\n", colnames(X)[j], class(X[,j]), paste(head(X[,j]), collapse=", ")))
      }
    }

    # Force conversion
    mode(X) <- "numeric"
    
    if (!is.numeric(X)) {
      stop("Failed to convert X to numeric.")
    }
  }
  
  # Handle NAs in X
  if (any(is.na(X))) {
    cat(sprintf("Warning: X contains %d NAs after conversion. Filling with 0...\n", sum(is.na(X))))
    X[is.na(X)] <- 0
  }

  # Check other inputs
  if (!is.numeric(R)) { cat("Warning: R is not numeric. Converting...\n"); R <- as.numeric(R) }
  if (!is.numeric(Y)) { cat("Warning: Y is not numeric. Converting...\n"); Y <- as.numeric(Y) }
  if (!is.numeric(Z)) { cat("Warning: Z is not numeric. Converting...\n"); mode(Z) <- "numeric" }
  if (!is.numeric(pw)) { cat("Warning: pw is not numeric. Converting...\n"); pw <- as.numeric(pw) }
  if (!is.numeric(lw)) { cat("Warning: lw is not numeric. Converting...\n"); lw <- as.numeric(lw) }
  
  # Check for NAs in other inputs
  if (any(is.na(R))) stop("R contains NAs")
  if (any(is.na(Y))) stop("Y contains NAs")
  if (any(is.na(Z))) { cat("Warning: Z contains NAs. Filling with 0...\n"); Z[is.na(Z)] <- 0 }
  if (any(is.na(pw))) stop("pw contains NAs")
  if (any(is.na(lw))) stop("lw contains NAs")

  # Data Inspection
  cat("\n--- Data Inspection ---\n")
  cat("R summary:\n"); print(summary(R))
  cat("X variances (head):\n")
  x_vars <- apply(X, 2, var)
  print(head(x_vars))
  cat("Num zero-variance X cols:", sum(x_vars == 0), "\n")
  if (sum(x_vars == 0) > 0) {
    cat("Zero-variance cols:", names(x_vars)[x_vars == 0], "\n")
  }
  cat("Z summary:\n"); print(summary(Z))
  cat("-----------------------\n\n")

  list(dt=dt, X=X, R=R, Y=Y, Z=Z, months=months, stocks=stocks, 
       num_months=length(unique(months)), num_stocks=length(unique(stocks)), 
       pw=pw, lw=lw)
}

run_test <- function(name, scale_percent, eta, min_leaf_size, lambda_cov=0) {
  d <- build_data(dt_sub, scale_percent)

  # Sample Size Check
  cat("Checking sample size...\n")
  if (is.matrix(d$months)) d$months <- as.vector(d$months)
  stocks_per_month <- table(d$months)
  cat("Stocks per month summary:\n")
  print(summary(as.numeric(stocks_per_month)))
  cat("Min stocks/month:", min(stocks_per_month), "\n")
  
  if (min(stocks_per_month) < 2 * min_leaf_size) {
    cat(sprintf("WARNING: Min stocks/month (%d) < 2 * min_leaf_size (%d). Splitting might be impossible in some months.\n", 
                min(stocks_per_month), 2 * min_leaf_size))
  }

  cat(sprintf("\n--- TEST: %s ---\n", name))
  cat(sprintf("  Scale: %s | Eta: %.2f | MinLeaf: %d | LambdaCov: %.1e\n", 
              ifelse(scale_percent, "Percent", "Decimal"), eta, min_leaf_size, lambda_cov))
  
  t_start <- proc.time()
  fit <- PTree::PTree(
    d$R, d$Y, d$X, d$Z,
    H = rep(0, d$num_months),
    d$pw, d$lw,
    d$stocks, d$months,
    seq(0L, ncol(d$X)-1L), seq(0L, ncol(d$X)-1L),
    d$num_stocks, d$num_months,
    min_leaf_size = min_leaf_size,
    max_depth = 3,
    num_iter = 1,     # Single tree
    num_cutpoints = 50,
    eta = eta,
    equal_weight = TRUE,
    no_H = TRUE,
    abs_normalize = TRUE,
    weighted_loss = FALSE,
    lambda_mean = 0,
    lambda_cov = lambda_cov, 
    lambda_mean_factor = 0,
    lambda_cov_factor = 0,
    early_stop = FALSE,
    stop_threshold = 1.0, # Try 1.0 to allow ANY improvement
    lambda_ridge = 1e-4,  # Add ridge to prevent singularity
    a1 = 0, a2 = 0,
    list_K = matrix(rep(0, 3), nrow = 3, ncol = 1),
    random_split = FALSE
  )
  dur <- (proc.time() - t_start)[3]
  
  tree_str <- as.character(fit$tree)
  num_leaves <- ncol(fit$portfolio)
  
  cat(sprintf("  Result: %d leaves | Depth: %d nodes | Time: %.2fs\n", num_leaves, length(tree_str), dur))
  if (num_leaves > 1) {
    cat("  SPLIT SUCCESSFUL!\n")
  } else {
    cat("  NO SPLIT.\n")
  }
}

# 1. Baseline (Percent, Eta=0.1, Leaf=100)
# 1. Baseline (Percent, Eta=0.1, Leaf=100)
# run_test("1. Baseline (Percent, Leaf=100)", scale_percent=TRUE, eta=0.1, min_leaf_size=100)

# 2. Small Leaf + Regularization
run_test("2. Small Leaf + Reg (Percent, Leaf=20, L=1e-2)", scale_percent=TRUE, eta=0.1, min_leaf_size=20, lambda_cov=1e-2)

# 3. Decimal + Small Leaf + Regularization
run_test("3. Decimal + Reg (Decimal, Leaf=20, L=1e-2)", scale_percent=FALSE, eta=0.1, min_leaf_size=20, lambda_cov=1e-2)

# 4. Heavy Regularization
run_test("4. Heavy Reg (Percent, Leaf=20, L=1.0)", scale_percent=TRUE, eta=0.1, min_leaf_size=20, lambda_cov=1.0)

