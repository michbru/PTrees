#!/usr/bin/env Rscript

# A2: Train Unboosted P-Tree (Single Tree)
# ----------------------------------------
# - Loads prepared inputs from A1
# - Trains a single P-Tree without a benchmark (no boosting)
# - Saves factor time series and summary

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
out_fac  <- file.path(out_dir, "ptree_factor_unboosted.csv")
out_tree <- file.path(out_dir, "ptree_unboosted_tree.txt")
out_sum  <- file.path(out_dir, "ptree_unboosted_summary.csv")

cat("\n=== A2: TRAIN UNBOOSTED P-TREE ===\n")
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
cat("  Months:", num_months, "| Stocks:", num_stocks, "\n\n")

# Parameters (conservative defaults)
min_leaf_size <- 3
max_depth     <- 12
num_iter      <- 1     # single tree
num_cutpoints <- 10

lambda_mean         <- 0
lambda_cov          <- 1e-5
lambda_mean_factor  <- 0
lambda_cov_factor   <- 1e-6

equal_weight   <- FALSE
abs_normalize  <- TRUE
weighted_loss  <- FALSE
early_stop     <- FALSE
stop_threshold <- 1
lambda_ridge   <- 0
a1 <- 0; a2 <- 0
list_K <- matrix(rep(0, 3), nrow = 3, ncol = 1)
random_split <- FALSE

# No benchmark for first tree
H <- rep(0, nrow(X))

cat("Fitting single P-Tree...\n")
t0 <- proc.time()
fit <- PTree::PTree(R, Y, X, Z, H,
                    pw, lw,
                    stocks, months, first_split_var, second_split_var,
                    num_stocks, num_months,
                    min_leaf_size, max_depth, num_iter, num_cutpoints,
                    eta = 1, equal_weight = equal_weight,
                    no_H = TRUE,
                    abs_normalize = abs_normalize, weighted_loss = weighted_loss,
                    lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
                    early_stop = early_stop, stop_threshold = stop_threshold, lambda_ridge = lambda_ridge,
                    a1 = a1, a2 = a2, list_K = list_K,
                    random_split = random_split)
elapsed <- (proc.time() - t0)[3]
cat("Done. Elapsed:", round(elapsed, 2), "sec\n\n")

# Save tree text
writeLines(as.character(fit$tree), con = out_tree)
cat("Saved tree:\n", normalizePath(out_tree, mustWork = FALSE), "\n")

# Factor time series (monthly)
if (!"date" %in% names(dt)) stop("Column 'date' missing in inputs dt")
date_labels <- sort(unique(dt$date))
stopifnot(length(fit$ft) == length(date_labels))
fac_dt <- data.table(date = date_labels, factor_unboosted = as.numeric(fit$ft))
fwrite(fac_dt, out_fac)
cat("Saved factor TS:\n", normalizePath(out_fac, mustWork = FALSE), "\n")

# Summary
mu <- mean(fac_dt$factor_unboosted, na.rm = TRUE)
sdm <- sd(fac_dt$factor_unboosted, na.rm = TRUE)
shp_ann <- if (sdm > 0) mu / sdm * sqrt(12) else NA_real_
summary_dt <- data.table(
  Mean_Monthly = round(mu * 100, 3),
  Std_Monthly  = round(sdm * 100, 3),
  Sharpe_Annual = round(shp_ann, 3),
  Months = nrow(fac_dt)
)
fwrite(summary_dt, out_sum)
cat("Saved summary:\n", normalizePath(out_sum, mustWork = FALSE), "\n\n")

cat("A2 complete.\n\n")
