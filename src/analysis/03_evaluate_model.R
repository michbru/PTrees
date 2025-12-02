#!/usr/bin/env Rscript

# A3: Benchmark P-Tree Models (Single + Boosted)
# ----------------------------------------------
# Computes CAPM and FF3 alphas for factor series generated in Step 2
# Uses Fama-French factors from data/raw (scaled to percent to match)

suppressPackageStartupMessages({
  library(data.table)
  library(sandwich)
  library(lmtest)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

models_dir <- file.path(repo_root, "results", "models")
out_dir <- file.path(repo_root, "results", "evaluation")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# Minimal LaTeX table writer (for benchmarking tables)
write_tex_table <- function(dt, file, caption = NULL, label = NULL, digits = 3) {
  if (!inherits(dt, "data.table")) dt <- as.data.table(dt)
  for (cn in names(dt)) if (is.numeric(dt[[cn]])) dt[[cn]] <- round(dt[[cn]], digits)
  cols <- names(dt)
  con <- file(file, open = "wt"); on.exit(close(con))
  writeLines("\\begin{table}[!ht]", con)
  writeLines("\\centering", con)
  if (!is.null(caption)) writeLines(paste0("\\caption{", caption, "}"), con)
  if (!is.null(label)) writeLines(paste0("\\label{", label, "}"), con)
  writeLines(paste0("\\begin{tabular}{", paste(rep("l", length(cols)), collapse = "|"), "}"), con)
  writeLines("\\hline", con)
  writeLines(paste(cols, collapse = " & "), con)
  writeLines("\\\\\\hline", con)
  apply(dt, 1, function(row) writeLines(paste(row, collapse = " & "), con))
  writeLines("\\\\\\hline", con)
  writeLines("\\end{tabular}", con)
  writeLines("\\end{table}", con)
}

ff_path <- Sys.getenv("PTREE_FF_CSV")
if (!nzchar(ff_path)) {
  shof_default <- file.path(repo_root, "data", "raw", "macro", "raw_macro_factors.csv")
  if (file.exists(shof_default)) {
    ff_path <- shof_default
  } else {
    ff_path <- file.path(repo_root, "data", "raw", "FamaFrench2020", "FF4F_monthly.csv")
  }
}

nw_lags <- 12

cat("\n╔════════════════════════════════════════════════╗\n")
cat("║   A3: EVALUATE P-TREE MODELS                  ║\n")
cat("╚════════════════════════════════════════════════╝\n\n")
cat("Factor file:", ff_path, "\n")
cat("Newey-West lags:", nw_lags, "\n\n")
cat("Factor file:", ff_path, "\n")
cat("Newey-West lags:", nw_lags, "\n\n")

if (!file.exists(ff_path)) stop("Factor file not found")

ff <- fread(ff_path)
cat(sprintf("Loaded factor data: %d months\n\n", nrow(ff)))

# Helper function to construct MVE portfolio
construct_mve <- function(factors_mat, lambda_cov = 1e-4) {
  # factors_mat: T x K matrix of factor returns
  mu <- colMeans(factors_mat)
  Sigma <- cov(factors_mat)
  
  # Regularize covariance
  Sigma_reg <- Sigma + diag(lambda_cov, ncol(Sigma))
  
  # Solve for weights: w = Sigma^-1 * mu
  w <- solve(Sigma_reg, mu)
  
  # Normalize to sum to 1 (optional, but standard for portfolio)
  # Original paper does w = w / sum(w)
  w <- w / sum(w)
  
  # Construct portfolio returns
  mve_ret <- factors_mat %*% w
  
  list(ret = as.vector(mve_ret), weights = w)
}

# Helper function for alphas
calc_alpha <- function(factor_dt, name) {
  # factor_dt should have columns: date, factor
  f <- copy(factor_dt)
  f[, ym := format(as.IDate(date), "%Y-%m")]

  ff_sub <- copy(ff)
  if (!"ym" %in% names(ff_sub)) {
    if ("date" %in% names(ff_sub)) ff_sub[, ym := format(as.IDate(date), "%Y-%m")]
  }

  reg_data <- merge(f, ff_sub, by = "ym", all.x = TRUE)

  # Handle different column names (Swedish vs US data)
  if ("rm_rf" %in% names(reg_data) && !"mkt_rf" %in% names(reg_data)) reg_data[, mkt_rf := rm_rf]
  if ("smb_ew" %in% names(reg_data) && !"smb" %in% names(reg_data)) reg_data[, smb := smb_ew]
  if ("hml_ew" %in% names(reg_data) && !"hml" %in% names(reg_data)) reg_data[, hml := hml_ew]

  # Scale FF factors to decimal if they are in percent (heuristic)
  # Our P-Tree factors are now DECIMAL (we removed *100).
  # FF data is usually percent. We should convert FF to decimal.
  for (col in c("mkt_rf","smb","hml")) {
    if (col %in% names(reg_data)) {
      rng <- reg_data[[col]]
      if (is.numeric(rng) && max(abs(rng), na.rm = TRUE) > 1) {
        # Likely percent, convert to decimal
        reg_data[[col]] <- reg_data[[col]] / 100
      }
    }
  }

  reg_data <- reg_data[complete.cases(reg_data[, .(factor, mkt_rf, smb, hml)])]

  if (nrow(reg_data) < 24) {
    cat(sprintf("  ✗ Insufficient data: %d months\n", nrow(reg_data)))
    return(NULL)
  }

  cat(sprintf("  Date range: %s to %s (%d months)\n",
              min(reg_data$ym), max(reg_data$ym), nrow(reg_data)))

  # CAPM
  capm <- lm(factor ~ mkt_rf, data = reg_data)
  capm_nw <- coeftest(capm, vcov = NeweyWest(capm, lag = nw_lags))
  capm_alpha <- coef(capm)["(Intercept)"] * 12 
  capm_tstat <- capm_nw["(Intercept)", "t value"]

  # FF3
  ff3 <- lm(factor ~ mkt_rf + smb + hml, data = reg_data)
  ff3_nw <- coeftest(ff3, vcov = NeweyWest(ff3, lag = nw_lags))
  ff3_alpha <- coef(ff3)["(Intercept)"] * 12
  ff3_tstat <- ff3_nw["(Intercept)", "t value"]
  
  # SR
  m <- mean(reg_data$factor)
  s <- sd(reg_data$factor)
  sr <- if(s>0) m/s*sqrt(12) else NA

  cat(sprintf("  Mean: %.2f%% | SD: %.2f%% | SR: %.2f\n", m*100, s*100, sr))
  cat(sprintf("  CAPM Alpha: %.2f%% (t=%.2f)\n", capm_alpha*100, capm_tstat))
  cat(sprintf("  FF3 Alpha:  %.2f%% (t=%.2f)\n\n", ff3_alpha*100, ff3_tstat))

  data.table(
    scenario = name,
    sharpe = sr,
    mean_ann = m*12,
    sd_ann = s*sqrt(12),
    capm_alpha = capm_alpha,
    capm_tstat = capm_tstat,
    ff3_alpha = ff3_alpha,
    ff3_tstat = ff3_tstat,
    n_months = nrow(reg_data)
  )
}

# Main Evaluation Loop
files <- list.files(models_dir, pattern = "_20_factors.csv", full.names = TRUE)

results_list <- list()

for (fpath in files) {
  fname <- basename(fpath)
  scenario <- sub("_20_factors.csv", "", fname)
  
  cat("\n╔════════════════════════════════════════════════╗\n")
  cat(sprintf("║   EVALUATING: %s\n", scenario))
  cat("╚════════════════════════════════════════════════╝\n\n")
  
  dt_factors <- fread(fpath)
  date_col <- dt_factors$date
  factors_mat <- as.matrix(dt_factors[, -1]) # Exclude date
  
  # 1. Construct MVE
  cat("Constructing MVE portfolio from 20 factors...\n")
  mve <- construct_mve(factors_mat)
  
  # 2. Evaluate MVE
  mve_dt <- data.table(date = date_col, factor = mve$ret)
  res <- calc_alpha(mve_dt, paste0(scenario, " (MVE)"))
  
  if (!is.null(res)) results_list[[length(results_list)+1]] <- res
  
  # 3. Save MVE series
  fwrite(mve_dt, file.path(out_dir, paste0(scenario, "_mve_factor.csv")))
}

final <- rbindlist(results_list)
print(final)
fwrite(final, file.path(out_dir, "final_mve_results.csv"))

cat(sprintf("\n✓ Results saved to: %s\n\n", out_dir))
