#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(data.table)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)
in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")

cat("Loading inputs from:", in_rds, "\n")
inp <- readRDS(in_rds)
dt <- inp$dt

cat("Checking column types in dt...\n")
non_num_cols <- names(dt)[sapply(dt, function(c) !is.numeric(c))]
cat("Non-numeric columns in dt:", paste(non_num_cols, collapse=", "), "\n")

cat("Constructing X from char_cols...\n")
cat("Structure of inp$char_cols:\n")
str(inp$char_cols)

cat("Trying .SDcols...\n")
X_sd <- as.matrix(dt[, .SD, .SDcols = inp$char_cols])
cat("Dim of X_sd:", dim(X_sd), "\n")

cat("Trying .. syntax...\n")
X <- as.matrix(dt[, ..inp$char_cols])

cat("Dim of X:", dim(X), "\n")
cat("Mode of X:", mode(X), "\n")
cat("Class of X:", class(X), "\n")
cat("First element class:", class(X[1,1]), "\n")
cat("is.numeric(X):", is.numeric(X), "\n")

if (!is.numeric(X)) {
  cat("X is NOT numeric. Summary of first col:\n")
  print(summary(X[,1]))
  print(head(X[,1]))
}

cat("\nChecking Z...\n")
Z <- inp$Z
if (!is.numeric(Z)) {
  cat("Z is NOT numeric. Checking columns of Z...\n")
  for (j in 1:ncol(Z)) {
    if (!is.numeric(Z[,j])) {
      cat(sprintf("  Col '%s' is %s. Head: %s\n", 
                  colnames(Z)[j], class(Z[,j]), paste(head(Z[,j]), collapse=", ")))
    }
  }
} else {
  cat("Z IS numeric.\n")
}
