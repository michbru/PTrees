#!/usr/bin/env Rscript

# A4: Robustness Checks (Minimal)
# -------------------------------
# Runs a few lightweight robustness checks:
#  - Equal-weight vs value-weight (unboosted)
#  - Start-date sensitivity (1999-06 vs 2003-01)
#  - Small parameter sweep (min_leaf_size, num_cutpoints) for unboosted

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
out_dir  <- file.path(repo_root, "results", "analysis", "robustness")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

cat("\n=== A4: ROBUSTNESS CHECKS ===\n")
cat("Repo root:", repo_root, "\n")

if (!file.exists(in_rds)) stop(sprintf("Inputs RDS not found: %s\nRun A1 first.", in_rds))
inp <- readRDS(in_rds)

dt <- copy(inp$dt)

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

run_unboosted <- function(dt_sub, keep_chars, instr, equal_weight=FALSE,
                          min_leaf_size=3, num_cutpoints=10) {
  tr <- build_train(dt_sub, keep_chars, instr)
  pw <- as.vector(dt_sub$lag_me); lw <- as.vector(dt_sub$lag_me)
  fit <- PTree::PTree(tr$R, tr$Y, tr$X, tr$Z, rep(0, nrow(tr$X)),
                      pw, lw, tr$stocks, tr$months, 
                      seq(0L, ncol(tr$X)-1L), seq(0L, ncol(tr$X)-1L),
                      tr$num_stocks, tr$num_months,
                      min_leaf_size, 12, 1, num_cutpoints,
                      eta=1, equal_weight=equal_weight, no_H=TRUE,
                      abs_normalize=TRUE, weighted_loss=FALSE,
                      lambda_mean=0, lambda_cov=1e-5, lambda_mean_factor=0, lambda_cov_factor=1e-6,
                      early_stop=FALSE, stop_threshold=1, lambda_ridge=0,
                      a1=0, a2=0, list_K=matrix(rep(0,3), nrow=3, ncol=1), random_split=FALSE)
  ft <- as.numeric(fit$ft)
  c(mean=mean(ft, na.rm=TRUE), sd=sd(ft, na.rm=TRUE), sharpe_ann=ifelse(sd(ft,na.rm=TRUE)>0, mean(ft,na.rm=TRUE)/sd(ft,na.rm=TRUE)*sqrt(12), NA))
}

keep_chars <- inp$char_cols
instr <- inp$instr_cols

# 1) EW vs VW (1999-06 start)
dt1 <- dt[date >= as.IDate("1999-06-01")]
res_vw <- run_unboosted(dt1, keep_chars, instr, equal_weight=FALSE)
res_ew <- run_unboosted(dt1, keep_chars, instr, equal_weight=TRUE)
rb1 <- data.table(method=c("VW","EW"),
                  mean_monthly=round(c(res_vw["mean"], res_ew["mean"]) * 100,3),
                  std_monthly=round(c(res_vw["sd"], res_ew["sd"]) * 100,3),
                  sharpe_annual=round(c(res_vw["sharpe_ann"], res_ew["sharpe_ann"]),3))
fwrite(rb1, file.path(out_dir, "robust_ew_vs_vw.csv"))
cat("Saved:", normalizePath(file.path(out_dir, "robust_ew_vs_vw.csv"), mustWork=FALSE), "\n")

# 2) Start date sensitivity (1999-06 vs 2003-01), VW
dt2 <- dt[date >= as.IDate("2003-01-01")]
res_1999 <- run_unboosted(dt1, keep_chars, instr, equal_weight=FALSE)
res_2003 <- run_unboosted(dt2, keep_chars, instr, equal_weight=FALSE)
rb2 <- data.table(start=c("1999-06","2003-01"),
                  mean_monthly=round(c(res_1999["mean"], res_2003["mean"]) * 100,3),
                  std_monthly=round(c(res_1999["sd"], res_2003["sd"]) * 100,3),
                  sharpe_annual=round(c(res_1999["sharpe_ann"], res_2003["sharpe_ann"]),3))
fwrite(rb2, file.path(out_dir, "robust_start_date.csv"))
cat("Saved:", normalizePath(file.path(out_dir, "robust_start_date.csv"), mustWork=FALSE), "\n")

# 3) Small parameter sweep (min_leaf_size x num_cutpoints), VW
grid <- CJ(min_leaf_size=c(3,5), num_cutpoints=c(5,10))
res_list <- list()
for (i in seq_len(nrow(grid))) {
  g <- grid[i]
  m <- run_unboosted(dt1, keep_chars, instr, equal_weight=FALSE,
                     min_leaf_size=g$min_leaf_size, num_cutpoints=g$num_cutpoints)
  res_list[[i]] <- data.table(min_leaf_size=g$min_leaf_size, num_cutpoints=g$num_cutpoints,
                              mean_monthly=round(m["mean"] * 100,3),
                              std_monthly=round(m["sd"] * 100,3),
                              sharpe_annual=round(m["sharpe_ann"],3))
}
rb3 <- rbindlist(res_list)
fwrite(rb3, file.path(out_dir, "robust_param_sweep.csv"))
cat("Saved:", normalizePath(file.path(out_dir, "robust_param_sweep.csv"), mustWork=FALSE), "\n\n")

cat("A4 complete.\n\n")
