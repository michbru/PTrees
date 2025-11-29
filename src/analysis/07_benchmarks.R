#!/usr/bin/env Rscript

# A7: Benchmark Regressions (CAPM, FF3, FF4)
# ------------------------------------------
# - Compares unboosted and boosted P-Tree factors to Swedish benchmark factors
# - Computes alphas (monthly and annualized), t-stats with Newey-West SEs

suppressPackageStartupMessages({
  library(data.table)
})

if (!requireNamespace("sandwich", quietly = TRUE)) stop("Install 'sandwich'")
if (!requireNamespace("lmtest", quietly = TRUE)) stop("Install 'lmtest'")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

in_unb   <- file.path(repo_root, "results", "analysis", "models", "ptree_factor_unboosted.csv")
in_boost <- file.path(repo_root, "results", "analysis", "models", "ptree_factors_boosted.csv")
macro_default <- file.path(repo_root, "data", "raw", "FamaFrench2020", "FF4F_monthly.csv")
macro_override <- Sys.getenv("PTREE_MACRO_PATH")
macro_path <- if (nzchar(macro_override)) macro_override else macro_default

out_dir  <- file.path(repo_root, "results", "analysis", "benchmarks")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

cat("\n=== A7: BENCHMARK REGRESSIONS ===\n")
cat("Repo root:", repo_root, "\n")

if (!file.exists(in_unb)) {
  cat("Unboosted factor CSV not found. Skipping unboosted benchmarks.\n")
  unb <- NULL
} else {
  
}
if (!file.exists(in_boost)) stop(sprintf("Boosted factor CSV not found: %s", in_boost))
if (!file.exists(macro_path)) stop(sprintf("Macro CSV not found: %s\nSet PTREE_MACRO_PATH or place file under data/raw/FamaFrench2020/", macro_path))

unb <- if (!is.null(unb)) unb else NULL # Already handled above? No, unb is NULL or fread result.
# Actually, unb is set in lines 32-37.
# Remove line 41.

bst <- fread(in_boost)
mac <- fread(macro_path)

# Expect columns in macro: date or ym; rm_rf (market excess), smb_vw, hml_vw, mom_vw, rf
if (!"ym" %in% names(mac)) {
  if ("date" %in% names(mac)) mac[, ym := format(as.IDate(date), "%Y-%m")] else stop("Macro: need 'ym' or 'date'")
}

to_ym <- function(d) format(as.IDate(d), "%Y-%m")
merge_facts <- function(df) merge(df, mac, by = "ym", all.x = TRUE, all.y = FALSE)

if (!is.null(unb)) {
  unb[, ym := to_ym(date)]
  unb_m <- merge_facts(unb)
}
bst[, ym := to_ym(date)]
bst_m <- merge_facts(bst)

run_regs <- function(df, fact_cols, out_path_prefix) {
  library(sandwich); library(lmtest)
  res <- list()
  for (fc in fact_cols) {
    y <- df[[fc]]
    # CAPM
    capm <- lm(y ~ rm_rf, data = df)
    se1 <- sqrt(diag(NeweyWest(capm, lag=6, prewhite=FALSE)))
    # FF3
    ff3 <- lm(y ~ rm_rf + smb_vw + hml_vw, data = df)
    se3 <- sqrt(diag(NeweyWest(ff3, lag=6, prewhite=FALSE)))
    # FF4 (include momentum if present)
    if ("mom_vw" %in% names(df)) {
      ff4 <- lm(y ~ rm_rf + smb_vw + hml_vw + mom_vw, data = df)
      se4 <- sqrt(diag(NeweyWest(ff4, lag=6, prewhite=FALSE)))
    } else {
      ff4 <- NULL; se4 <- NULL
    }
    summ <- data.table(
      factor = fc,
      capm_alpha = coef(capm)[1], capm_t = ifelse(!is.na(se1[1]) && se1[1]>0, coef(capm)[1]/se1[1], NA_real_),
      ff3_alpha  = coef(ff3)[1],  ff3_t  = ifelse(!is.na(se3[1]) && se3[1]>0, coef(ff3)[1]/se3[1], NA_real_),
      ff4_alpha  = if (!is.null(ff4)) coef(ff4)[1] else NA_real_,
      ff4_t      = if (!is.null(se4) && !is.na(se4[1]) && se4[1]>0) coef(ff4)[1]/se4[1] else NA_real_
    )
    res[[fc]] <- summ
  }
  out <- rbindlist(res)
  # Add annualized alpha (approx 12 * monthly alpha)
  out[, `:=`(capm_alpha_ann = capm_alpha * 12,
             ff3_alpha_ann  = ff3_alpha  * 12,
             ff4_alpha_ann  = ff4_alpha  * 12)]
  fwrite(out, paste0(out_path_prefix, "_alphas.csv"))
  cat("Saved:", normalizePath(paste0(out_path_prefix, "_alphas.csv"), mustWork=FALSE), "\n")
}

# Unboosted
if (!is.null(unb)) {
  run_regs(unb_m, fact_cols = setdiff(names(unb), c("date","ym")),
           out_path_prefix = file.path(out_dir, "unboosted"))
}

# Boosted
run_regs(bst_m, fact_cols = setdiff(names(bst), c("date","ym")),
         out_path_prefix = file.path(out_dir, "boosted"))

cat("\nA7 complete.\n\n")
