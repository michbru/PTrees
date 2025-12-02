#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(data.table)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)
in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")
inp <- readRDS(in_rds)
dt <- inp$dt[date < "2008-01-01"]

cat("DT dimensions:", dim(dt), "\n")
cat("Instrument columns:", paste(inp$instr_cols, collapse=", "), "\n")

cat("Constructing Z...\n")
Z <- cbind(Intercept = 1, if (length(inp$instr_cols)>0) as.matrix(dt[, ..inp$instr_cols]) else NULL)

cat("Z dimensions:", dim(Z), "\n")
cat("Z columns:", colnames(Z), "\n")

# Check correlation
if (ncol(Z) > 1) {
  cat("Correlation matrix of Z (excluding intercept):\n")
  print(cor(Z[,-1]))
  
  cat("\nEigenvalues of Z'Z:\n")
  ev <- eigen(t(Z) %*% Z)$values
  print(ev)
  cat("Condition number:", max(ev)/min(ev), "\n")
} else {
  cat("Z only has intercept.\n")
}
