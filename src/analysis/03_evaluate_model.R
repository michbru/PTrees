#!/usr/bin/env Rscript

# A3: Evaluate Model (Benchmarks & Robustness)
# --------------------------------------------
# Part A: Benchmark Regressions (CAPM, FF3, FF4)
# Part B: Robustness Checks (EW vs VW, Start Date, Parameter Sweep)

suppressPackageStartupMessages({
  library(data.table)
  library(sandwich)
  library(lmtest)
})

if (!requireNamespace("PTree", quietly = TRUE)) {
  stop("The 'PTree' package is required. Install it before running.")
}

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

# Paths
in_factor <- file.path(repo_root, "results", "analysis", "models", "ptree_factor.csv")
in_leaf_portfolios <- file.path(repo_root, "results", "analysis", "models", "ptree_leaf_portfolios.csv")
in_inputs <- file.path(repo_root, "results", "analysis", "inputs", "ptree_inputs.rds")

out_dir_bench <- file.path(repo_root, "results", "analysis", "evaluation", "benchmarks")
out_dir_robust <- file.path(repo_root, "results", "analysis", "evaluation", "robustness")
dir.create(out_dir_bench, recursive = TRUE, showWarnings = FALSE)
dir.create(out_dir_robust, recursive = TRUE, showWarnings = FALSE)

macro_default <- file.path(repo_root, "data", "raw", "FamaFrench2020", "FF4F_monthly.csv")
macro_override <- Sys.getenv("PTREE_MACRO_PATH")
macro_path <- if (nzchar(macro_override)) macro_override else macro_default

cat("\n=== A3: EVALUATE MODEL ===\n")
cat("Repo root:", repo_root, "\n")

# ==============================================================================
# PART A: BENCHMARK REGRESSIONS
# ==============================================================================
cat("\n--- Part A: Benchmark Regressions ---\n")

if (file.exists(in_factor) && file.exists(in_leaf_portfolios) && file.exists(macro_path)) {
  ptree_factor <- fread(in_factor)
  leaf_portfolios <- fread(in_leaf_portfolios)
  mac <- fread(macro_path)

  if (!"ym" %in% names(mac)) {
    if ("date" %in% names(mac)) mac[, ym := format(as.IDate(date), "%Y-%m")] else stop("Macro: need 'ym' or 'date'")
  }

  to_ym <- function(d) format(as.IDate(d), "%Y-%m")
  merge_facts <- function(df) merge(df, mac, by = "ym", all.x = TRUE, all.y = FALSE)

  ptree_factor[, ym := to_ym(date)]
  factor_m <- merge_facts(ptree_factor)

  leaf_portfolios[, ym := to_ym(date)]
  leaf_m <- merge_facts(leaf_portfolios)

  run_regs <- function(df, fact_cols, out_path_prefix) {
    res <- list()
    for (fc in fact_cols) {
      y <- df[[fc]]
      # CAPM
      capm <- lm(y ~ rm_rf, data = df)
      se1 <- sqrt(diag(NeweyWest(capm, lag=6, prewhite=FALSE)))
      # FF3
      ff3 <- lm(y ~ rm_rf + smb_vw + hml_vw, data = df)
      se3 <- sqrt(diag(NeweyWest(ff3, lag=6, prewhite=FALSE)))
      # FF4
      if ("mom_vw" %in% names(df)) {
        ff4 <- lm(y ~ rm_rf + smb_vw + hml_vw + mom_vw, data = df)
        se4 <- sqrt(diag(NeweyWest(ff4, lag=6, prewhite=FALSE)))
      } else {
        ff4 <- NULL; se4 <- NULL
      }
      summ <- data.table(
        factor = fc,
        capm_alpha = coef(capm)[1], capm_t = ifelse(!is.na(se1[1]) && se1[1]>0, coef(capm)[1]/se1[1], NA_real_),
        capm_r2    = summary(capm)$adj.r.squared,
        ff3_alpha  = coef(ff3)[1],  ff3_t  = ifelse(!is.na(se3[1]) && se3[1]>0, coef(ff3)[1]/se3[1], NA_real_),
        ff3_r2     = summary(ff3)$adj.r.squared,
        ff4_alpha  = if (!is.null(ff4)) coef(ff4)[1] else NA_real_,
        ff4_t      = if (!is.null(se4) && !is.na(se4[1]) && se4[1]>0) coef(ff4)[1]/se4[1] else NA_real_,
        ff4_r2     = if (!is.null(ff4)) summary(ff4)$adj.r.squared else NA_real_
      )
      res[[fc]] <- summ
    }
    out <- rbindlist(res)
    out[, `:=`(capm_alpha_ann = capm_alpha * 12,
               ff3_alpha_ann  = ff3_alpha  * 12,
               ff4_alpha_ann  = ff4_alpha  * 12)]
    fwrite(out, paste0(out_path_prefix, "_alphas.csv"))
    cat("Saved:", normalizePath(paste0(out_path_prefix, "_alphas.csv"), mustWork=FALSE), "\n")
  }

  run_regs(factor_m, fact_cols = "factor", out_path_prefix = file.path(out_dir_bench, "ptree_factor"))
  run_regs(leaf_m, fact_cols = grep("^leaf_", names(leaf_m), value = TRUE), out_path_prefix = file.path(out_dir_bench, "leaf_portfolios"))

} else {
  cat("Skipping Part A: Missing input files (factor, portfolios, or macro data).\n")
}

# ==============================================================================
# PART B: ROBUSTNESS CHECKS
# ==============================================================================
cat("\n--- Part B: Robustness Checks ---\n")

if (file.exists(in_inputs)) {
  inp <- readRDS(in_inputs)
  dt <- copy(inp$dt)
  keep_chars <- inp$char_cols
  instr <- inp$instr_cols

  build_train <- function(dt_sub, keep_chars, instr) {
    X <- as.matrix(dt_sub[, ..keep_chars])
    R <- as.vector(dt_sub$ret_monthly)
    Y <- R
    Z <- cbind(Intercept = 1, if (length(instr)>0) as.matrix(dt_sub[, ..instr]) else NULL)
    months <- as.integer(as.factor(dt_sub$date)) - 1L
    stocks <- as.integer(as.factor(dt_sub$isin)) - 1L
    list(X=X,R=R,Y=Y,Z=Z,months=months,stocks=stocks,
         num_months=length(unique(months)), num_stocks=length(unique(stocks)))
  }

  run_unboosted <- function(dt_sub, keep_chars, instr, equal_weight=TRUE,
                            min_leaf_size=10, num_cutpoints=50, num_iter=5) {
    tr <- build_train(dt_sub, keep_chars, instr)
    pw <- as.vector(dt_sub$lag_me); lw <- as.vector(dt_sub$lag_me)
    suppressWarnings({
      fit <- PTree::PTree(tr$R, tr$Y, tr$X, tr$Z, rep(0, tr$num_months),
                          pw, lw, tr$stocks, tr$months,
                          seq(0L, ncol(tr$X)-1L), seq(0L, ncol(tr$X)-1L),
                          tr$num_stocks, tr$num_months,
                          min_leaf_size, 8, num_iter, num_cutpoints,
                          eta=1, equal_weight=equal_weight, no_H=TRUE,
                          abs_normalize=TRUE, weighted_loss=FALSE,
                          lambda_mean=0, lambda_cov=1e-2, lambda_mean_factor=0, lambda_cov_factor=0,
                          early_stop=FALSE, stop_threshold=0.95, lambda_ridge=0,
                          a1=0, a2=0, list_K=matrix(rep(0,3), nrow=3, ncol=1), random_split=FALSE)
    })
    ft <- as.numeric(fit$ft)
    c(mean=mean(ft, na.rm=TRUE), sd=sd(ft, na.rm=TRUE), sharpe_ann=ifelse(sd(ft,na.rm=TRUE)>0, mean(ft,na.rm=TRUE)/sd(ft,na.rm=TRUE)*sqrt(12), NA))
  }

  # 1) EW vs VW
  dt1 <- dt[date >= as.IDate("1999-06-01")]
  cat("\n1. Testing EW vs VW...\n")
  res_vw <- run_unboosted(dt1, keep_chars, instr, equal_weight=FALSE, num_iter=5)
  res_ew <- run_unboosted(dt1, keep_chars, instr, equal_weight=TRUE, num_iter=5)
  rb1 <- data.table(method=c("VW","EW"),
                    mean_monthly=round(c(res_vw["mean"], res_ew["mean"]) * 100,3),
                    std_monthly=round(c(res_vw["sd"], res_ew["sd"]) * 100,3),
                    sharpe_annual=round(c(res_vw["sharpe_ann"], res_ew["sharpe_ann"]),3))
  fwrite(rb1, file.path(out_dir_robust, "robust_ew_vs_vw.csv"))
  cat("Saved:", normalizePath(file.path(out_dir_robust, "robust_ew_vs_vw.csv"), mustWork=FALSE), "\n")

  # 2) Start Date
  cat("2. Testing start date sensitivity...\n")
  dt2 <- dt[date >= as.IDate("2003-01-01")]
  res_1999 <- run_unboosted(dt1, keep_chars, instr, equal_weight=TRUE, num_iter=5)
  res_2003 <- run_unboosted(dt2, keep_chars, instr, equal_weight=TRUE, num_iter=5)
  rb2 <- data.table(start=c("1999-06","2003-01"),
                    mean_monthly=round(c(res_1999["mean"], res_2003["mean"]) * 100,3),
                    std_monthly=round(c(res_1999["sd"], res_2003["sd"]) * 100,3),
                    sharpe_annual=round(c(res_1999["sharpe_ann"], res_2003["sharpe_ann"]),3))
  fwrite(rb2, file.path(out_dir_robust, "robust_start_date.csv"))
  cat("Saved:", normalizePath(file.path(out_dir_robust, "robust_start_date.csv"), mustWork=FALSE), "\n")

  # 3) Parameter Sweep (simplified for speed)
  cat("3. Testing parameter sensitivity (simplified)...\n")
  grid <- CJ(min_leaf_size=c(10), num_iter=c(3,7))  # Just 2 runs instead of 6
  res_list <- list()
  for (i in seq_len(nrow(grid))) {
    g <- grid[i]
    cat(sprintf("  Run %d/%d: min_leaf=%d, iter=%d\n", i, nrow(grid), g$min_leaf_size, g$num_iter))
    m <- run_unboosted(dt1, keep_chars, instr, equal_weight=TRUE,
                       min_leaf_size=g$min_leaf_size, num_iter=g$num_iter)
    res_list[[i]] <- data.table(min_leaf_size=g$min_leaf_size, num_iter=g$num_iter,
                                mean_monthly=round(m["mean"] * 100,3),
                                std_monthly=round(m["sd"] * 100,3),
                                sharpe_annual=round(m["sharpe_ann"],3))
  }
  rb3 <- rbindlist(res_list)
  fwrite(rb3, file.path(out_dir_robust, "robust_param_sweep.csv"))
  cat("Saved:", normalizePath(file.path(out_dir_robust, "robust_param_sweep.csv"), mustWork=FALSE), "\n")

} else {
  cat("Skipping Part B: Missing inputs RDS.\n")
}

cat("\nA3 complete.\n\n")
