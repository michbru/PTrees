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

if (!file.exists(ff_path)) stop("Factor file not found")

ff <- fread(ff_path)
cat(sprintf("Loaded factor data: %d months\n\n", nrow(ff)))

# Helper function for alphas
calc_alpha <- function(factor_file, scenario_name) {
  if (!file.exists(factor_file)) {
    cat(sprintf("  ✗ File not found: %s\n", basename(factor_file)))
    return(NULL)
  }

  f <- fread(factor_file)
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

  # Scale factors to percent if they look like decimals (|x|<10 is a safe heuristic)
  for (col in c("mkt_rf","smb","hml")) {
    if (col %in% names(reg_data)) {
      rng <- reg_data[[col]]
      if (is.numeric(rng) && max(abs(rng), na.rm = TRUE) < 10) {
        reg_data[[col]] <- reg_data[[col]] * 100
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
  capm_alpha <- coef(capm)["(Intercept)"] * 12  # Annualized
  capm_tstat <- capm_nw["(Intercept)", "t value"]

  # FF3
  ff3 <- lm(factor ~ mkt_rf + smb + hml, data = reg_data)
  ff3_nw <- coeftest(ff3, vcov = NeweyWest(ff3, lag = nw_lags))
  ff3_alpha <- coef(ff3)["(Intercept)"] * 12
  ff3_tstat <- ff3_nw["(Intercept)", "t value"]

  cat(sprintf("  CAPM Alpha: %.2f%% (t=%.2f)\n", capm_alpha, capm_tstat))
  cat(sprintf("  FF3 Alpha:  %.2f%% (t=%.2f)\n\n", ff3_alpha, ff3_tstat))

  data.table(
    scenario = scenario_name,
    capm_alpha = capm_alpha,
    capm_tstat = capm_tstat,
    ff3_alpha = ff3_alpha,
    ff3_tstat = ff3_tstat,
    n_months = nrow(reg_data)
  )
}

scenarios <- list(
  list(name = "A: Full Sample (Single)",  file = file.path(models_dir, "scenario_a_single_factor.csv")),
  list(name = "A: Full Sample (Boosted)", file = file.path(models_dir, "scenario_a_boosted_factor.csv")),
  list(name = "B: Time-Split (Single)",   file = file.path(models_dir, "scenario_b_single_test_factor.csv")),
  list(name = "B: Time-Split (Boosted)",  file = file.path(models_dir, "scenario_b_boosted_test_factor.csv")),
  list(name = "C: Reverse Split (Single)",file = file.path(models_dir, "scenario_c_single_test_factor.csv")),
  list(name = "C: Reverse Split (Boosted)",file = file.path(models_dir, "scenario_c_boosted_test_factor.csv"))
)

alpha_list <- list()
for (sc in scenarios) {
  cat("\n╔════════════════════════════════════════════════╗\n")
  cat(sprintf("║   %s\n", sc$name))
  cat("╚════════════════════════════════════════════════╝\n\n")
  a <- calc_alpha(sc$file, sc$name)
  if (!is.null(a)) alpha_list[[length(alpha_list)+1]] <- a
}

# Combine with summary
summary <- fread(file.path(models_dir, "all_scenarios_summary.csv"))
summary_keep <- summary[scenario %in% sapply(scenarios, `[[`, "name")]

results <- rbindlist(alpha_list, fill = TRUE)

final <- merge(summary_keep[, .(scenario, sharpe, return_pct, leaves)],
               results, by = "scenario", all = TRUE)

cat("\n╔════════════════════════════════════════════════╗\n")
cat("║   FINAL RESULTS TABLE                         ║\n")
cat("╚════════════════════════════════════════════════╝\n\n")

print(final)

fwrite(results, file.path(out_dir, "benchmark_regressions.csv"))
fwrite(final, file.path(out_dir, "final_results_table.csv"))

# Also export LaTeX tables for thesis/appendix use
write_tex_table(results, file.path(out_dir, "benchmark_regressions.tex"),
                caption = "CAPM and FF3 regressions (Newey–West)",
                label = "tab:benchmark-regs")
write_tex_table(final, file.path(out_dir, "final_results_table.tex"),
                caption = "Performance and alpha benchmarks (Newey–West)",
                label = "tab:final-results")

cat(sprintf("\n✓ Results saved to: %s\n\n", out_dir))
