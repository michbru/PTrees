#!/usr/bin/env Rscript

# A1: Prepare Inputs for P-Tree Training (Swedish)
# ------------------------------------------------
# - Loads data/processed/ptree_dataset_monthly.csv
# - Filters period and characteristics by coverage
# - Builds matrices/vectors required by PTree
# - Saves RDS to results/analysis/inputs/ptree_inputs.rds

suppressPackageStartupMessages({
  library(data.table)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

in_path  <- file.path(repo_root, "data", "processed", "ptree_dataset_monthly.csv")
out_dir  <- file.path(repo_root, "results", "analysis", "inputs")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_rds  <- file.path(out_dir, "ptree_inputs.rds")

min_date <- as.IDate("1999-06-01")   # start date used in analysis
cov_thr  <- 0.30                      # 30% non-zero coverage threshold

cat("\n=== A1: PREPARE P-TREE INPUTS ===\n")
cat("Repo root:", repo_root, "\n")

if (!file.exists(in_path)) {
  stop(sprintf("Input not found: %s\nRun Step 6 first to create the monthly dataset.", in_path))
}

dt <- fread(in_path)
if (!"date" %in% names(dt)) stop("Column 'date' missing in monthly dataset")
dt[, date := as.IDate(date)]

cat("Loaded:", nrow(dt), "rows x", ncol(dt), "cols\n")

# Filter sample period
dt <- dt[date >= min_date]
cat("Filtered from", as.character(min_date), "->", nrow(dt), "rows\n\n")

# Characteristic coverage filter
char_cols <- grep("^rank_", names(dt), value = TRUE)
nonzero_share <- sapply(char_cols, function(c) mean(dt[[c]] != 0, na.rm = TRUE))
keep_chars <- names(nonzero_share)[nonzero_share >= cov_thr]
drop_chars <- setdiff(char_cols, keep_chars)

cat("All characteristics:", length(char_cols), "\n")
cat("Kept (>=", cov_thr * 100, "%) :", length(keep_chars), "\n")
if (length(drop_chars)) {
  cat("Dropped (low coverage):", paste(drop_chars, collapse = ", "), "\n")
}
cat("\n")

# Instruments (subset of characteristics + intercept)
cand_instr <- c("rank_me", "rank_bm", "rank_mom12m", "rank_roa", "rank_gma", "rank_op")
instr <- intersect(cand_instr, keep_chars)
cat("Instruments:", ifelse(length(instr)>0, paste(instr, collapse = ", "), "<none>"), "\n\n")

# Build objects for PTree
X <- as.matrix(dt[, ..keep_chars])
R <- as.vector(dt$ret_monthly)
Y <- R
Z <- cbind(Intercept = 1, if (length(instr)>0) as.matrix(dt[, ..instr]) else NULL)

# Indices (0-indexed)
months <- as.integer(as.factor(dt$date)) - 1L
stocks <- as.integer(as.factor(dt$isin)) - 1L
num_months <- length(unique(months))
num_stocks <- length(unique(stocks))

# Weights
if (!"lag_me" %in% names(dt)) stop("Column 'lag_me' missing in monthly dataset")
portfolio_weight <- as.vector(dt$lag_me)
loss_weight      <- as.vector(dt$lag_me)

# Split variable indices (0-indexed)
first_split_var  <- seq(0L, ncol(X) - 1L)
second_split_var <- seq(0L, ncol(X) - 1L)

inputs <- list(
  dt = dt,
  char_cols = keep_chars,
  instr_cols = instr,
  X = X, R = R, Y = Y, Z = Z,
  months = months, stocks = stocks,
  num_months = num_months, num_stocks = num_stocks,
  portfolio_weight = portfolio_weight,
  loss_weight = loss_weight,
  first_split_var = first_split_var,
  second_split_var = second_split_var
)

saveRDS(inputs, out_rds)
cat("Saved:", normalizePath(out_rds, mustWork = FALSE), "\n")
cat("Observations:", nrow(dt), "| Months:", num_months, "| Stocks:", num_stocks, "\n\n")

