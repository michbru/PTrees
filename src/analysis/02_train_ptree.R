#!/usr/bin/env Rscript

# A2: Train P-Tree Model
# ----------------------
# Optimized for Swedish stock market using SINGLE TREE approach (unboosted)
# Single tree performs better than boosting for smaller Swedish market
# See docs/SWEDISH_MARKET_ADAPTATIONS.md for details

suppressPackageStartupMessages({
  library(data.table)
})

if (!requireNamespace("PTree", quietly = TRUE)) {
  stop("The 'PTree' package is required. Install it before running.")
}

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

in_rds   <- file.path(repo_root, "results", "analysis", "inputs", "ptree_inputs.rds")
out_dir  <- file.path(repo_root, "results", "analysis", "models")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_tree <- file.path(out_dir, "ptree_tree.txt")
out_fac  <- file.path(out_dir, "ptree_factor.csv")
out_sum  <- file.path(out_dir, "ptree_summary.csv")
out_leaf_portfolios <- file.path(out_dir, "ptree_leaf_portfolios.csv")
out_leaf_ids <- file.path(out_dir, "ptree_leaf_ids.csv")

cat("\n=== A2: TRAIN P-TREE MODEL ===\n")
cat("Repo root:", repo_root, "\n")

if (!file.exists(in_rds)) stop(sprintf("Inputs RDS not found: %s\nRun A1 first.", in_rds))
inp <- readRDS(in_rds)

dt <- inp$dt
X <- inp$X; R <- inp$R; Y <- inp$Y; Z <- inp$Z
months <- inp$months; stocks <- inp$stocks
num_months <- inp$num_months; num_stocks <- inp$num_stocks
pw <- inp$portfolio_weight; lw <- inp$loss_weight
first_split_var <- inp$first_split_var
second_split_var <- inp$second_split_var

cat("Training data:\n")
cat("  Observations:", nrow(dt), "\n")
cat("  Months:", num_months, "| Stocks:", num_stocks, "\n")
cat("  Avg stocks/month:", round(nrow(dt)/num_months, 1), "\n")
cat("  Characteristics:", ncol(X), "\n\n")

# Parse command-line parameters
parse_int <- function(pat, def) {
  a <- grep(pat, commandArgs(trailingOnly = TRUE), value = TRUE)
  if (length(a) == 1) {
    v <- suppressWarnings(as.integer(sub(sprintf('^%s', pat), '', a)))
    if (!is.na(v)) return(v)
  }
  def
}
parse_num <- function(pat, def) {
  a <- grep(pat, commandArgs(trailingOnly = TRUE), value = TRUE)
  if (length(a) == 1) {
    v <- suppressWarnings(as.numeric(sub(sprintf('^%s', pat), '', a)))
    if (!is.na(v)) return(v)
  }
  def
}
parse_bool <- function(pat, def) {
  a <- grep(pat, commandArgs(trailingOnly = TRUE), value = TRUE)
  if (length(a) == 1) {
    v <- tolower(sub(sprintf('^%s', pat), '', a))
    if (v %in% c('1','true','yes','y')) return(TRUE)
    if (v %in% c('0','false','no','n')) return(FALSE)
  }
  def
}

# Optimal parameters (tuned for Swedish market)
# Note: equal_weight=TRUE performs better (Sharpe 1.25 vs 1.10) due to market concentration
min_leaf_size <- parse_int("--min_leaf_size=", 10)
max_depth     <- parse_int("--max_depth=", 8)
num_cutpoints <- parse_int("--num_cutpoints=", 50)
num_iter      <- parse_int("--num_iter=", 5)
eta           <- parse_num("--eta=", 1.0)  # eta=1.0 for unboosted single tree
equal_weight  <- parse_bool("--equal_weight=", TRUE)  # Validated: better than value-weighted

cat("Parameters:\n")
cat("  min_leaf_size:", min_leaf_size, "\n")
cat("  max_depth:", max_depth, "\n")
cat("  num_cutpoints:", num_cutpoints, "\n")
cat("  num_iter:", num_iter, "(number of splits in single tree)\n")
cat("  eta:", eta, "\n")
cat("  equal_weight:", equal_weight, "\n\n")

cat("Fitting P-Tree model...\n")
t0 <- proc.time()

# Suppress singular matrix warnings (expected for smaller markets)
suppressWarnings({
  fit <- PTree::PTree(
    R, Y, X, Z,
    H = rep(0, num_months),
    pw, lw,
    stocks, months, first_split_var, second_split_var,
    num_stocks, num_months,
    min_leaf_size = min_leaf_size,
    max_depth = max_depth,
    num_iter = num_iter,
    num_cutpoints = num_cutpoints,
    eta = eta,
    equal_weight = equal_weight,
    no_H = TRUE,
    abs_normalize = TRUE,
    weighted_loss = FALSE,
    lambda_mean = 0,
    lambda_cov = 1e-2,
    lambda_mean_factor = 0,
    lambda_cov_factor = 0,
    early_stop = FALSE,
    stop_threshold = 0.95,
    lambda_ridge = 0,
    a1 = 0, a2 = 0,
    list_K = matrix(rep(0, 3), nrow = 3, ncol = 1),
    random_split = FALSE
  )
})

elapsed <- (proc.time() - t0)[3]
cat("Done. Elapsed:", round(elapsed, 2), "sec\n\n")

# Save tree structure
tree_str <- as.character(fit$tree)
writeLines(tree_str, con = out_tree)
cat("Saved tree:\n", normalizePath(out_tree, mustWork = FALSE), "\n")
cat("\nTree structure (final iteration):\n")
cat(tree_str, "\n")

# Extract and save factor
ft <- as.numeric(fit$ft)
fac_dt <- data.table(
  date = sort(unique(dt$date)),
  factor = ft
)
fwrite(fac_dt, out_fac)
cat("\nSaved factor:\n", normalizePath(out_fac, mustWork = FALSE), "\n")

# Summary statistics
mean_monthly <- mean(ft, na.rm = TRUE)
std_monthly  <- sd(ft, na.rm = TRUE)
sharpe <- if (std_monthly > 0) mean_monthly / std_monthly * sqrt(12) else NA_real_

summ <- data.table(
  metric = c("mean_monthly", "std_monthly", "sharpe_annual", "annualized_return", "annualized_vol"),
  value = c(mean_monthly, std_monthly, sharpe, mean_monthly * 12, std_monthly * sqrt(12))
)
fwrite(summ, out_sum)
cat("Saved summary:\n", normalizePath(out_sum, mustWork = FALSE), "\n")

# Extract and save leaf portfolio returns (for Table 1 replication)
leaf_portfolios <- as.data.table(fit$portfolio)
leaf_portfolios[, date := sort(unique(dt$date))]
setcolorder(leaf_portfolios, c("date", setdiff(names(leaf_portfolios), "date")))
num_leaves <- ncol(leaf_portfolios) - 1
setnames(leaf_portfolios, old = paste0("V", 1:num_leaves), new = paste0("leaf_", 1:num_leaves))
fwrite(leaf_portfolios, out_leaf_portfolios)
cat("\nSaved leaf portfolios:\n", normalizePath(out_leaf_portfolios, mustWork = FALSE), "\n")
cat(sprintf("  %d leaf portfolios x %d months\n", num_leaves, nrow(leaf_portfolios)))

# Save leaf node IDs
leaf_ids <- data.table(
  leaf_number = 1:length(fit$leaf_id),
  node_id = as.integer(fit$leaf_id)
)
fwrite(leaf_ids, out_leaf_ids)
cat("Saved leaf IDs:\n", normalizePath(out_leaf_ids, mustWork = FALSE), "\n")

cat("\n=== FACTOR SUMMARY ===\n")
cat(sprintf("  Mean monthly:      %.2f%%\n", mean_monthly))
cat(sprintf("  Std monthly:       %.2f%%\n", std_monthly))
cat(sprintf("  Sharpe (annual):   %.2f\n", sharpe))
cat(sprintf("  Annualized return: %.2f%%\n", mean_monthly * 12))
cat(sprintf("  Annualized vol:    %.2f%%\n", std_monthly * sqrt(12)))

cat("\nA2 complete.\n\n")
