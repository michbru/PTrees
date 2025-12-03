#!/usr/bin/env Rscript

################################################################################
# Step 1: Prepare Inputs for P-Tree Training
################################################################################
#
# Purpose: Load and prepare data for P-Tree model training
#
# Input: data/processed/ptree_dataset_monthly.csv
# Output: results/inputs/ptree_inputs.rds
#
# Key steps:
#   1. Load monthly panel data
#   2. Filter time period (1997-2019, matching FF factor availability)
#   3. Select characteristics with sufficient coverage (>=30% non-zero)
#   4. Create lead returns (predict t+1)
#   5. Winsorize returns to handle outliers
#   6. Prepare matrices for PTree package
#
################################################################################

suppressPackageStartupMessages({
  library(data.table)
})

# Set seed for reproducibility
set.seed(42)

# Paths
args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- if (length(file_arg) > 0) dirname(normalizePath(file_arg)) else getwd()
repo_root <- normalizePath(file.path(script_dir, "..", ".."))
setwd(repo_root)

INPUT_CSV <- "data/processed/ptree_dataset_monthly.csv"
OUTPUT_DIR <- "results/inputs"
OUTPUT_RDS <- file.path(OUTPUT_DIR, "ptree_inputs.rds")

# Clear output directory - start fresh
if (dir.exists(OUTPUT_DIR)) {
  cat("Clearing previous input preparation outputs...\n")
  unlink(OUTPUT_DIR, recursive = TRUE)
}
dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

cat("================================================================================\n")
cat("STEP 1: PREPARE P-TREE INPUTS\n")
cat("================================================================================\n\n")

# Parameters
MIN_DATE <- as.IDate("1997-10-01")  # Start date
MAX_DATE <- as.IDate("2019-12-31")  # End date (match FF factor availability)
COVERAGE_THRESHOLD <- 0.30          # Keep characteristics with >= 30% non-zero values

if (!file.exists(INPUT_CSV)) {
  stop("Input file not found: ", INPUT_CSV, "\nRun data preparation pipeline first.")
}

dt <- fread(INPUT_CSV)
dt[, date := as.IDate(date)]

cat(sprintf("Loaded dataset: %s rows, %s columns\n", 
            format(nrow(dt), big.mark = ","), ncol(dt)))


################################################################################
# Filter Time Period
################################################################################

dt <- dt[date >= MIN_DATE & date <= MAX_DATE]

cat(sprintf("Filtered to %s - %s: %s observations\n\n",
            as.character(MIN_DATE), as.character(MAX_DATE),
            format(nrow(dt), big.mark = ",")))


################################################################################
# Select and Validate Characteristics
################################################################################

cat("Processing characteristics...\n")

# Identify all rank_ columns
char_cols <- grep("^rank_", names(dt), value = TRUE)

# Force numeric conversion (handle any string/factor issues)
for (col in char_cols) {
  if (!is.numeric(dt[[col]])) {
    cat(sprintf("  Converting %s to numeric\n", col))
    set(dt, j = col, value = as.numeric(as.character(dt[[col]])))
  }
}

# Remove zero-variance characteristics
vars <- sapply(dt[, ..char_cols], function(x) var(x, na.rm = TRUE))
zero_var_chars <- names(vars)[vars == 0 | is.na(vars)]
if (length(zero_var_chars) > 0) {
  cat(sprintf("  Dropping %d zero-variance characteristics: %s\n",
              length(zero_var_chars), paste(zero_var_chars, collapse = ", ")))
  char_cols <- setdiff(char_cols, zero_var_chars)
}

# Filter by coverage (>=30% non-zero)
nonzero_share <- sapply(char_cols, function(c) mean(dt[[c]] != 0, na.rm = TRUE))
keep_chars <- names(nonzero_share)[nonzero_share >= COVERAGE_THRESHOLD]
drop_chars <- setdiff(char_cols, keep_chars)

if (length(drop_chars) > 0) {
  cat(sprintf("  Dropping %d low-coverage characteristics (<%d%% non-zero)\n",
              length(drop_chars), COVERAGE_THRESHOLD * 100))
}

cat(sprintf("  Final: %d characteristics\n\n", length(keep_chars)))

# Instrument variables (subset of characteristics for portfolio construction)
candidate_instr <- c("rank_me", "rank_bm", "rank_mom12m", "rank_roa", "rank_gma", "rank_op")
instr_cols <- intersect(candidate_instr, keep_chars)

cat(sprintf("Instrument variables: %s\n\n", 
            ifelse(length(instr_cols) > 0, paste(instr_cols, collapse = ", "), "none")))


################################################################################
# Create Target Variable (Lead Returns)
################################################################################

cat("Creating target variable (t+1 returns)...\n")

# Use raw monthly returns (not excess returns)
ret_col <- "ret_monthly"

# Create lead returns (predict next month)
setkey(dt, isin, date)
dt[, ret_next := shift(get(ret_col), type = "lead"), by = isin]

# Remove rows where target is NA (last observation per stock)
n_before <- nrow(dt)
dt <- dt[!is.na(ret_next)]
n_after <- nrow(dt)

cat(sprintf("  Removed %s observations with missing target\n", 
            format(n_before - n_after, big.mark = ",")))
cat(sprintf("  Final: %s observations\n\n", format(n_after, big.mark = ",")))


################################################################################
# Winsorize Returns
################################################################################

cat("Winsorizing returns at 1% and 99% percentiles...\n")

q01 <- quantile(dt$ret_next, 0.01, na.rm = TRUE)
q99 <- quantile(dt$ret_next, 0.99, na.rm = TRUE)
n_winsorized <- sum(dt$ret_next < q01 | dt$ret_next > q99, na.rm = TRUE)

dt[, ret_next := pmax(pmin(ret_next, q99), q01)]

cat(sprintf("  Winsorized %s observations (%.2f%%) to [%.4f, %.4f]\n\n",
            format(n_winsorized, big.mark = ","),
            n_winsorized / n_after * 100, q01, q99))


################################################################################
# Prepare Matrices for PTree Package
################################################################################

cat("Building matrices for PTree...\n")

# Characteristics matrix (cross-sectionally ranked)
X <- as.matrix(dt[, .SD, .SDcols = keep_chars])
if (!is.numeric(X)) {
  cat("  Warning: Forcing X to numeric\n")
  mode(X) <- "numeric"
}
if (any(is.na(X))) {
  n_na <- sum(is.na(X))
  cat(sprintf("  Warning: Filling %s NAs in X with 0\n", format(n_na, big.mark = ",")))
  X[is.na(X)] <- 0
}

# Returns (target variable, in decimal form)
R <- as.vector(dt$ret_next)
Y <- R  # Y = R for standard P-Tree

# Instruments matrix (with intercept)
if (length(instr_cols) > 0) {
  Z_instr <- as.matrix(dt[, .SD, .SDcols = instr_cols])
} else {
  Z_instr <- NULL
}
Z <- cbind(Intercept = 1, Z_instr)

if (!is.numeric(Z)) {
  cat("  Warning: Forcing Z to numeric\n")
  mode(Z) <- "numeric"
}
if (any(is.na(Z))) {
  n_na <- sum(is.na(Z))
  cat(sprintf("  Warning: Filling %s NAs in Z with 0\n", format(n_na, big.mark = ",")))
  Z[is.na(Z)] <- 0
}

# Indices (0-indexed for PTree package)
months <- as.integer(as.factor(dt$date)) - 1L
stocks <- as.integer(as.factor(dt$isin)) - 1L
num_months <- length(unique(months))
num_stocks <- length(unique(stocks))

# Weights (market equity)
if (!"lag_me" %in% names(dt)) stop("Column 'lag_me' missing in dataset")
pw <- as.vector(dt$lag_me)  # Portfolio weights
lw <- as.vector(dt$lag_me)  # Loss weights

cat(sprintf("  X: %s x %d (characteristics)\n", format(nrow(X), big.mark = ","), ncol(X)))
cat(sprintf("  R: %s (returns)\n", format(length(R), big.mark = ",")))
cat(sprintf("  Z: %s x %d (instruments + intercept)\n", format(nrow(Z), big.mark = ","), ncol(Z)))
cat(sprintf("  Time periods: %d months\n", num_months))
cat(sprintf("  Cross-section: %d firms\n\n", num_stocks))


################################################################################
# Save Results
################################################################################

inputs <- list(
  dt = dt,
  char_cols = keep_chars,
  instr_cols = instr_cols,
  X = X,
  R = R,
  Y = Y,
  Z = Z,
  months = months,
  stocks = stocks,
  num_months = num_months,
  num_stocks = num_stocks,
  pw = pw,
  lw = lw
)

saveRDS(inputs, OUTPUT_RDS)

cat("================================================================================\n")
cat("INPUT PREPARATION COMPLETE\n")
cat("================================================================================\n\n")

cat(sprintf("Saved to: %s\n\n", normalizePath(OUTPUT_RDS)))

cat("Summary:\n")
cat(sprintf("  Observations: %s\n", format(nrow(dt), big.mark = ",")))
cat(sprintf("  Firms: %s\n", format(num_stocks, big.mark = ",")))
cat(sprintf("  Months: %d\n", num_months))
cat(sprintf("  Characteristics: %d\n", length(keep_chars)))
cat(sprintf("  Period: %s to %s\n\n", min(dt$date), max(dt$date)))

cat("================================================================================\n")
