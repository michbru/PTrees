#!/usr/bin/env Rscript

# A1: Prepare Inputs for P-Tree Training (Swedish)
# ------------------------------------------------
# - Loads data/processed/ptree_dataset_monthly.csv
# - Filters period and characteristics by coverage
# - Builds matrices/vectors required by PTree
# - Saves RDS to results/inputs/ptree_inputs.rds

suppressPackageStartupMessages({
  library(data.table)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

in_path  <- file.path(repo_root, "data", "processed", "ptree_dataset_monthly.csv")
out_dir  <- file.path(repo_root, "results", "inputs")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_rds  <- file.path(out_dir, "ptree_inputs.rds")

min_date <- as.IDate("1997-10-01")   # start date used in analysis
max_date <- as.IDate("2019-12-31")   # end date (match FF factor coverage)
cov_thr  <- 0.30                      # 30% non-zero coverage threshold
use_excess <- tolower(Sys.getenv("PTREE_USE_EXCESS")) %in% c("1","true","yes","y")
macro_path <- Sys.getenv("PTREE_MACRO_PATH")
if (use_excess && !nzchar(macro_path)) {
  # Default expected location if not overridden
  macro_path <- file.path(repo_root, "data", "raw", "FamaFrench2020", "FF4F_monthly.csv")
}

cat("\n=== A1: PREPARE P-TREE INPUTS ===\n")
cat("Repo root:", repo_root, "\n")

if (!file.exists(in_path)) {
  stop(sprintf("Input not found: %s\nRun Step 6 first to create the monthly dataset.", in_path))
}

dt <- fread(in_path)
if (!"date" %in% names(dt)) stop("Column 'date' missing in monthly dataset")
dt[, date := as.IDate(date)]

cat("Loaded:", nrow(dt), "rows x", ncol(dt), "cols\n")

# Filter sample period to match Fama-French factor coverage
dt <- dt[date >= min_date & date <= max_date]
cat("Filtered period:", as.character(min_date), "to", as.character(max_date), "->", nrow(dt), "rows\n")
cat("  (Constrained by Fama-French factor availability through 2019-12)\n\n")


# Identify characteristics
char_cols <- grep("^rank_", names(dt), value = TRUE)

# Force numeric conversion for characteristics
# This handles cases where "NA" strings or other issues caused character loading
cat("Ensuring all characteristics are numeric...\n")
for (col in char_cols) {
  if (!is.numeric(dt[[col]])) {
    cat("  Converting", col, "to numeric...\n")
    set(dt, j=col, value=as.numeric(dt[[col]]))
  }
}

# Remove zero-variance characteristics (e.g. rank_zerotrade)
# This prevents issues with models that expect variation
vars <- sapply(dt[, ..char_cols], function(x) var(x, na.rm = TRUE))
drop_zero_var_chars <- names(vars)[vars == 0 | is.na(vars)]
if (length(drop_zero_var_chars) > 0) {
  cat("Dropping zero-variance characteristics:", paste(drop_zero_var_chars, collapse=", "), "\n")
  char_cols <- setdiff(char_cols, drop_zero_var_chars)
}

# Characteristic coverage filter
nonzero_share <- sapply(char_cols, function(c) mean(dt[[c]] != 0, na.rm = TRUE))
keep_chars <- names(nonzero_share)[nonzero_share >= cov_thr]
drop_low_coverage_chars <- setdiff(char_cols, keep_chars)

cat("All characteristics (after zero-variance filter):", length(char_cols), "\n")
# Drop known collinear feature
if ("rank_chcsho" %in% keep_chars && "rank_ni" %in% keep_chars) {
  keep_chars <- setdiff(keep_chars, "rank_chcsho")
  cat("Dropped collinear feature: rank_chcsho\n")
}
cat("Kept (>=", cov_thr * 100, "%) :", length(keep_chars), "\n")
if (length(drop_low_coverage_chars)) {
  cat("Dropped (coverage <", cov_thr, "):", paste(drop_low_coverage_chars, collapse=", "), "\n")
}
cat("\n")

# Instruments (subset of characteristics + intercept)
cand_instr <- c("rank_me", "rank_bm", "rank_mom12m", "rank_roa", "rank_gma", "rank_op")
instr <- intersect(cand_instr, keep_chars)
cat("Instruments:", ifelse(length(instr)>0, paste(instr, collapse = ", "), "<none>"), "\n\n")

# Build returns: excess or raw
ret_col <- "ret_monthly"
if (use_excess) {
  if (!file.exists(macro_path)) stop(sprintf("PTREE_USE_EXCESS=TRUE but macro file not found: %s", macro_path))
  macro <- fread(macro_path)
  if (!"ym" %in% names(macro)) {
    if ("date" %in% names(macro)) macro[, ym := format(as.IDate(date), "%Y-%m")] else stop("Macro file must have 'ym' or 'date'")
  }
  dt[, ym := format(date, "%Y-%m")]
  if (!("RF" %in% names(macro) || "rf" %in% names(macro))) stop("Macro file must contain risk-free column 'RF' or 'rf'")
  rfcol <- if ("RF" %in% names(macro)) "RF" else "rf"
  rf <- macro[, .(ym, rf = get(rfcol))]
  dt <- merge(dt, rf, by = "ym", all.x = TRUE)
  if (dt$rf[1] > 1) dt[, rf := rf/100]  # handle percent format
  dt[, xret := ret_monthly - rf]
  ret_col <- "xret"
  cat("Using EXCESS returns (xret) computed from risk-free in:", macro_path, "\n")
}

# Fix Look-Ahead Bias: Predict NEXT month's return
cat("Creating lead returns (target = t+1)...\n")
setkey(dt, isin, date)
dt[, ret_next := shift(get(ret_col), type = "lead"), by = isin]

# Remove rows where target is NA (last month of each stock)
dt <- dt[!is.na(ret_next)]
cat("Filtered NA targets ->", nrow(dt), "rows\n")

# Winsorize returns at 1% and 99% (following PTrees paper methodology)
cat("Winsorizing returns at 1% and 99% percentiles...\n")
q01 <- quantile(dt$ret_next, 0.01, na.rm = TRUE)
q99 <- quantile(dt$ret_next, 0.99, na.rm = TRUE)
n_winsorized <- sum(dt$ret_next < q01 | dt$ret_next > q99, na.rm = TRUE)
dt[, ret_next := pmax(pmin(ret_next, q99), q01)]
cat(sprintf("  Winsorized %d observations (%.2f%%) to [%.4f, %.4f]\n",
            n_winsorized, n_winsorized/nrow(dt)*100, q01, q99))

# Build objects for PTree
X <- as.matrix(dt[, ..keep_chars])
# Scale returns to PERCENT to match P-Tree defaults
R <- as.vector(dt$ret_next) * 100
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
cat("Observations:", nrow(dt), "| Months:", num_months, "| Stocks:", num_stocks, "\n")
cat("Target: next-month return (lead of", ret_col, ") scaled to percent\n\n")
