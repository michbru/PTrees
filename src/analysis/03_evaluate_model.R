#!/usr/bin/env Rscript

# A3: Evaluate P-Tree Models - Benchmark Regressions
# ---------------------------------------------------
# Calculates CAPM and Fama-French 3-factor alphas and t-statistics
# for all three scenarios (A, B, C) to complete Table 1 in thesis
#
# Methodology:
# - Time-series regressions of P-Tree factor returns on benchmark factors
# - Newey-West standard errors with 3 lags (as per thesis specification)
# - Monthly alphas converted to annualized percentages

suppressPackageStartupMessages({
  library(data.table)
  library(sandwich)   # For NeweyWest
  library(lmtest)     # For coeftest
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

# Input paths
models_dir <- file.path(repo_root, "results", "analysis", "models")
out_dir <- file.path(repo_root, "results", "analysis", "evaluation")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# Fama-French data
ff_path <- file.path(repo_root, "data", "raw", "FamaFrench2020", "FF4F_monthly.csv")

cat("\n═══════════════════════════════════════════════════════\n")
cat("   A3: BENCHMARK REGRESSIONS (CAPM & FF3)\n")
cat("═══════════════════════════════════════════════════════\n\n")
cat("Repo root:", repo_root, "\n")

# Load Fama-French factors
if (!file.exists(ff_path)) {
  stop("Fama-French data not found at: ", ff_path)
}

ff <- fread(ff_path)
cat("Loaded Fama-French factors:", nrow(ff), "months (", min(ff$ym), "to", max(ff$ym), ")\n")

# Helper function to run regressions
run_benchmark_regressions <- function(factor_data, scenario_name, date_range) {
  cat("\n--- ", scenario_name, " ---\n", sep="")
  cat("Date range:", date_range, "\n")

  # Merge with FF factors
  factor_data[, ym := format(as.IDate(date), "%Y-%m")]
  merged <- merge(factor_data, ff, by = "ym", all.x = TRUE, all.y = FALSE)

  # Check for missing FF data
  n_missing <- sum(is.na(merged$rm_rf))
  if (n_missing > 0) {
    cat(sprintf("Warning: %d months missing FF factors (2020 data)\n", n_missing))
    merged <- merged[!is.na(rm_rf)]
  }

  cat("Observations for regression:", nrow(merged), "\n")

  if (nrow(merged) < 24) {
    cat("ERROR: Insufficient data for regression (need at least 24 months)\n")
    return(NULL)
  }

  # CAPM regression: factor = alpha + beta * rm_rf
  capm_model <- lm(factor ~ rm_rf, data = merged)
  capm_nw <- NeweyWest(capm_model, lag = 3, prewhite = FALSE)
  capm_se <- sqrt(diag(capm_nw))
  capm_alpha <- coef(capm_model)[1]
  capm_t <- capm_alpha / capm_se[1]
  capm_r2 <- summary(capm_model)$adj.r.squared

  # Fama-French 3-factor: factor = alpha + b1*rm_rf + b2*smb + b3*hml
  ff3_model <- lm(factor ~ rm_rf + smb_vw + hml_vw, data = merged)
  ff3_nw <- NeweyWest(ff3_model, lag = 3, prewhite = FALSE)
  ff3_se <- sqrt(diag(ff3_nw))
  ff3_alpha <- coef(ff3_model)[1]
  ff3_t <- ff3_alpha / ff3_se[1]
  ff3_r2 <- summary(ff3_model)$adj.r.squared

  # Print results
  cat(sprintf("  CAPM Alpha:  %.2f%% monthly (%.2f%% annualized), t-stat: %.2f\n",
              capm_alpha, capm_alpha * 12, capm_t))
  cat(sprintf("  FF3 Alpha:   %.2f%% monthly (%.2f%% annualized), t-stat: %.2f\n",
              ff3_alpha, ff3_alpha * 12, ff3_t))

  # Return results
  data.table(
    scenario = scenario_name,
    n_months = nrow(merged),
    capm_alpha_monthly = capm_alpha,
    capm_alpha_annual = capm_alpha * 12,
    capm_t_stat = capm_t,
    capm_r2 = capm_r2,
    ff3_alpha_monthly = ff3_alpha,
    ff3_alpha_annual = ff3_alpha * 12,
    ff3_t_stat = ff3_t,
    ff3_r2 = ff3_r2
  )
}

# ==============================================================================
# SCENARIO A: FULL SAMPLE
# ==============================================================================
cat("\n╔══════════════════════════════════════════════════════╗\n")
cat("║   SCENARIO A: FULL SAMPLE (1999-06 to 2020-11)      ║\n")
cat("╚══════════════════════════════════════════════════════╝\n")

factor_a <- fread(file.path(models_dir, "scenario_a_factor.csv"))
results_a <- run_benchmark_regressions(factor_a, "A: Full Sample", "1999-06 to 2020-11")

# ==============================================================================
# SCENARIO B: TIME-SPLIT (TEST PERIOD)
# ==============================================================================
cat("\n╔══════════════════════════════════════════════════════╗\n")
cat("║   SCENARIO B: TIME-SPLIT TEST (2010-01 to 2020-11)  ║\n")
cat("╚══════════════════════════════════════════════════════╝\n")

factor_b_test <- fread(file.path(models_dir, "scenario_b_test_factor.csv"))
results_b <- run_benchmark_regressions(factor_b_test, "B: Time-Split (test)", "2010-01 to 2020-11")

# ==============================================================================
# SCENARIO C: REVERSE SPLIT (TEST PERIOD)
# ==============================================================================
cat("\n╔══════════════════════════════════════════════════════╗\n")
cat("║   SCENARIO C: REVERSE SPLIT TEST (1999-06 to 2009-12)║\n")
cat("╚══════════════════════════════════════════════════════╝\n")

factor_c_test <- fread(file.path(models_dir, "scenario_c_test_factor.csv"))
results_c <- run_benchmark_regressions(factor_c_test, "C: Reverse Split (test)", "1999-06 to 2009-12")

# ==============================================================================
# COMBINE RESULTS AND CREATE TABLE 1
# ==============================================================================
cat("\n\n╔══════════════════════════════════════════════════════╗\n")
cat("║          TABLE 1: BENCHMARK REGRESSION RESULTS       ║\n")
cat("╚══════════════════════════════════════════════════════╝\n\n")

# Combine all results
all_results <- rbindlist(list(results_a, results_b, results_c))

# Load Sharpe ratios from Step 2
sharpe_summary <- fread(file.path(models_dir, "all_scenarios_summary.csv"))

# Merge Sharpe ratios with alpha results
table1 <- merge(
  sharpe_summary[, .(scenario, sharpe_ratio, mean_monthly_pct, annualized_return_pct)],
  all_results[, .(scenario, n_months,
                  capm_alpha_monthly, capm_alpha_annual, capm_t_stat,
                  ff3_alpha_monthly, ff3_alpha_annual, ff3_t_stat)],
  by = "scenario"
)

# Format for thesis Table 1
table1_formatted <- table1[, .(
  Scenario = scenario,
  `Sharpe Ratio` = round(sharpe_ratio, 2),
  `CAPM Alpha (%)` = round(capm_alpha_annual, 2),
  `CAPM t-stat` = round(capm_t_stat, 2),
  `FF3 Alpha (%)` = round(ff3_alpha_annual, 2),
  `FF3 t-stat` = round(ff3_t_stat, 2),
  `N months` = n_months
)]

print(table1_formatted)

# Save results
fwrite(all_results, file.path(out_dir, "benchmark_regressions_detailed.csv"))
fwrite(table1_formatted, file.path(out_dir, "table1_thesis_results.csv"))

cat("\n✓ Results saved to:\n")
cat("  -", normalizePath(file.path(out_dir, "benchmark_regressions_detailed.csv"), mustWork=FALSE), "\n")
cat("  -", normalizePath(file.path(out_dir, "table1_thesis_results.csv"), mustWork=FALSE), "\n")

cat("\nNotes:\n")
cat("  - Alphas represent monthly excess returns in percent\n")
cat("  - t-statistics calculated using Newey-West standard errors (3 lags)\n")
cat("  - FF data coverage: 1999-06 to 2019-12 (2020 data excluded from alphas)\n")

cat("\nA3 complete.\n\n")
