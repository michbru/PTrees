#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")
if (!file.exists(in_rds)) stop("Inputs RDS not found.")

cat("Loading inputs...\n")
inp <- readRDS(in_rds)
dt <- inp$dt
char_cols <- inp$char_cols

cat(sprintf("Loaded %d rows, %d characteristics.\n", nrow(dt), length(char_cols)))

# Create summary table
stats_list <- list()

for (col in char_cols) {
  x <- dt[[col]]
  
  # Ensure numeric (handling the issue we fixed in prep, but double checking raw dt)
  if (!is.numeric(x)) {
    x <- as.numeric(as.character(x))
  }
  
  stats_list[[length(stats_list)+1]] <- data.table(
    characteristic = col,
    n_missing = sum(is.na(x)),
    n_zero = sum(x == 0, na.rm=TRUE),
    mean = mean(x, na.rm=TRUE),
    sd = sd(x, na.rm=TRUE),
    min = min(x, na.rm=TRUE),
    p25 = quantile(x, 0.25, na.rm=TRUE),
    median = median(x, na.rm=TRUE),
    p75 = quantile(x, 0.75, na.rm=TRUE),
    max = max(x, na.rm=TRUE)
  )
}

stats_dt <- rbindlist(stats_list)

# Print all rows
print(stats_dt, nrows=100)

# Check correlation with rank_me
cat("\nCorrelation with rank_me:\n")
if ("rank_me" %in% char_cols) {
  me <- as.numeric(dt$rank_me)
  cors <- sapply(char_cols, function(col) {
    x <- as.numeric(dt[[col]])
    cor(x, me, use="complete.obs")
  })
  print(sort(cors))
} else {
  cat("rank_me not found in char_cols.\n")
}
