#!/usr/bin/env Rscript

# Run Complete P-Tree Analysis Pipeline
# --------------------------------------
# Executes all analysis steps in sequence

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())

cat("\n╔════════════════════════════════════════════╗\n")
cat("║  P-TREE ANALYSIS PIPELINE (SWEDISH DATA)  ║\n")
cat("╚════════════════════════════════════════════╝\n\n")

scripts <- c(
  "01_prepare_inputs.R",
  "02_train_ptree.R"
)

for (script in scripts) {
  script_path <- file.path(script_dir, script)
  if (!file.exists(script_path)) {
    stop(sprintf("Script not found: %s", script_path))
  }

  cat(sprintf("\n▶ Running %s...\n", script))
  cat(strrep("─", 50), "\n")

  result <- system2("Rscript", args = script_path, stdout = TRUE, stderr = TRUE)
  cat(paste(result, collapse = "\n"), "\n")

  if (!is.null(attr(result, "status")) && attr(result, "status") != 0) {
    stop(sprintf("Script %s failed with status %d", script, attr(result, "status")))
  }
}

cat("\n╔════════════════════════════════════════════╗\n")
cat("║         PIPELINE COMPLETED SUCCESSFULLY    ║\n")
cat("╚════════════════════════════════════════════╝\n\n")
