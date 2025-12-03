#!/usr/bin/env Rscript

################################################################################
# Step 3: Evaluate P-Tree Models
################################################################################
#
# Purpose: Compute CAPM and FF3 alphas for P-Tree factor returns from Step 2
#
# Input: results/models/scenario_X_1_factor.csv (train + test)
# Output: results/evaluation/performance_metrics.csv + LaTeX table
#
# Benchmark: Fama-French factors from Swedish market (Shof et al. 2020)
# - Market (Rm-Rf)
# - Size (SMB)
# - Value (HML)
#
################################################################################

suppressPackageStartupMessages({
  library(data.table)
  library(sandwich)
  library(lmtest)
})

# Set seed for reproducibility
set.seed(42)

# Paths
args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- if (length(file_arg) > 0) dirname(normalizePath(file_arg)) else getwd()
repo_root <- normalizePath(file.path(script_dir, "..", ".."))
setwd(repo_root)

MODELS_DIR <- "results/models"
OUTPUT_DIR <- "results/evaluation"

# Clear output directory - start fresh
if (dir.exists(OUTPUT_DIR)) {
  cat("Clearing previous evaluation outputs...\n")
  unlink(OUTPUT_DIR, recursive = TRUE)
}
dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

cat("================================================================================\n")
cat("STEP 3: EVALUATE P-TREE MODELS\n")
cat("================================================================================\n\n")

# Load Fama-French factors (Swedish market)
FF_PATH <- "data/raw/macro/raw_macro_factors.csv"
if (!file.exists(FF_PATH)) {
  stop("Fama-French factors not found. Expected: ", FF_PATH)
}

ff <- fread(FF_PATH)
cat(sprintf("Loaded Fama-French factors: %d months\n", nrow(ff)))
cat(sprintf("Date range: %s to %s\n\n", min(ff$date), max(ff$date)))


################################################################################
# Helper: Calculate Alpha and T-Statistics
################################################################################

calc_alpha <- function(factor_dt, ff_data, scenario_name, nw_lags = 12) {
  cat(sprintf("\n--- Evaluating: %s ---\n", scenario_name))
  
  # Prepare factor data - ensure clean data.table
  f <- as.data.table(factor_dt)
  f[, date := as.IDate(date)]
  f[, ym := format(date, "%Y-%m")]
  
  # Rename column to "factor" for consistency (handle both "factor" and "factor_return")
  if ("factor_return" %in% names(f) && !"factor" %in% names(f)) {
    setnames(f, "factor_return", "factor")
  }
  
  # Keep only needed columns
  f <- f[, .(ym, factor)]
  
  # Prepare FF data
  ff_sub <- as.data.table(ff_data)
  if (!"ym" %in% names(ff_sub)) {
    if ("date" %in% names(ff_sub)) {
      ff_sub[, date := as.IDate(date)]
      ff_sub[, ym := format(date, "%Y-%m")]
    } else {
      stop("FF data must have 'date' or 'ym' column")
    }
  }
  
  # Handle column name variations (Swedish vs US data)
  if ("rm_rf" %in% names(ff_sub) && !"mkt_rf" %in% names(ff_sub)) {
    ff_sub[, mkt_rf := rm_rf]
  }
  if ("smb_ew" %in% names(ff_sub) && !"smb" %in% names(ff_sub)) {
    ff_sub[, smb := smb_ew]
  }
  if ("hml_ew" %in% names(ff_sub) && !"hml" %in% names(ff_sub)) {
    ff_sub[, hml := hml_ew]
  }
  
  # Keep only needed FF columns
  ff_sub <- ff_sub[, .(ym, mkt_rf, smb, hml)]
  
  # Merge
  reg_data <- merge(f, ff_sub, by = "ym", all.x = TRUE)
  
  # Remove missing values
  reg_data <- reg_data[complete.cases(reg_data[, .(factor, mkt_rf, smb, hml)])]
  
  if (nrow(reg_data) < 24) {
    cat(sprintf("  Warning: Only %d months available (< 24)\n", nrow(reg_data)))
    return(NULL)
  }
  
  cat(sprintf("  Date range: %s to %s (%d months)\n",
              min(reg_data$ym), max(reg_data$ym), nrow(reg_data)))
  
  # Calculate basic statistics
  mean_monthly <- mean(reg_data$factor, na.rm = TRUE)
  sd_monthly <- sd(reg_data$factor, na.rm = TRUE)
  sharpe <- if (sd_monthly > 0) mean_monthly / sd_monthly * sqrt(12) else NA_real_
  
  cat(sprintf("  Mean monthly: %.4f (%.2f%%)\n", mean_monthly, mean_monthly * 100))
  cat(sprintf("  Monthly SD: %.4f (%.2f%%)\n", sd_monthly, sd_monthly * 100))
  cat(sprintf("  Sharpe ratio: %.3f\n", sharpe))
  
  # CAPM regression: factor ~ mkt_rf
  capm_model <- lm(factor ~ mkt_rf, data = reg_data)
  capm_nw <- coeftest(capm_model, vcov = NeweyWest(capm_model, lag = nw_lags))
  capm_alpha_monthly <- coef(capm_model)["(Intercept)"]
  capm_alpha_annual <- capm_alpha_monthly * 12
  capm_tstat <- capm_nw["(Intercept)", "t value"]
  capm_r2 <- summary(capm_model)$r.squared
  
  cat(sprintf("  CAPM alpha: %.4f (%.2f%% annual, t=%.2f)\n",
              capm_alpha_monthly, capm_alpha_annual * 100, capm_tstat))
  
  # FF3 regression: factor ~ mkt_rf + smb + hml
  ff3_model <- lm(factor ~ mkt_rf + smb + hml, data = reg_data)
  ff3_nw <- coeftest(ff3_model, vcov = NeweyWest(ff3_model, lag = nw_lags))
  ff3_alpha_monthly <- coef(ff3_model)["(Intercept)"]
  ff3_alpha_annual <- ff3_alpha_monthly * 12
  ff3_tstat <- ff3_nw["(Intercept)", "t value"]
  ff3_r2 <- summary(ff3_model)$r.squared
  
  cat(sprintf("  FF3 alpha: %.4f (%.2f%% annual, t=%.2f)\n",
              ff3_alpha_monthly, ff3_alpha_annual * 100, ff3_tstat))
  
  # Return results
  data.table(
    scenario = scenario_name,
    n_months = nrow(reg_data),
    mean_monthly = mean_monthly,
    sd_monthly = sd_monthly,
    sharpe_ratio = sharpe,
    capm_alpha = capm_alpha_annual,
    capm_tstat = capm_tstat,
    capm_r2 = capm_r2,
    ff3_alpha = ff3_alpha_annual,
    ff3_tstat = ff3_tstat,
    ff3_r2 = ff3_r2
  )
}


################################################################################
# Main Evaluation Loop
################################################################################

results_list <- list()

# Scenario A: Full sample
cat("\n")
cat("================================================================================\n")
cat("SCENARIO A: FULL SAMPLE\n")
cat("================================================================================\n")

file_a <- file.path(MODELS_DIR, "scenario_a_1_factor.csv")
if (file.exists(file_a)) {
  factor_a <- fread(file_a)
  res_a <- calc_alpha(factor_a, ff, "Scenario A (Full Sample)")
  if (!is.null(res_a)) results_list[[length(results_list) + 1]] <- res_a
} else {
  cat("  Warning: scenario_a_1_factor.csv not found\n")
}

# Scenario B: Train (1998-2009)
cat("\n")
cat("================================================================================\n")
cat("SCENARIO B: TIME SPLIT\n")
cat("================================================================================\n")

file_b_train <- file.path(MODELS_DIR, "scenario_b_1_factor.csv")
if (file.exists(file_b_train)) {
  factor_b_train <- fread(file_b_train)
  res_b_train <- calc_alpha(factor_b_train, ff, "Scenario B (Train 1998-2009)")
  if (!is.null(res_b_train)) results_list[[length(results_list) + 1]] <- res_b_train
} else {
  cat("  Warning: scenario_b_1_factor.csv not found\n")
}

# Scenario B: Test (2010-2019)
file_b_test <- file.path(MODELS_DIR, "scenario_b_test_1_factor.csv")
if (file.exists(file_b_test)) {
  factor_b_test <- fread(file_b_test)
  res_b_test <- calc_alpha(factor_b_test, ff, "Scenario B (Test 2010-2019)")
  if (!is.null(res_b_test)) results_list[[length(results_list) + 1]] <- res_b_test
} else {
  cat("  Warning: scenario_b_test_1_factor.csv not found\n")
}

# Scenario C: Train (2010-2019)
cat("\n")
cat("================================================================================\n")
cat("SCENARIO C: REVERSE SPLIT\n")
cat("================================================================================\n")

file_c_train <- file.path(MODELS_DIR, "scenario_c_1_factor.csv")
if (file.exists(file_c_train)) {
  factor_c_train <- fread(file_c_train)
  res_c_train <- calc_alpha(factor_c_train, ff, "Scenario C (Train 2010-2019)")
  if (!is.null(res_c_train)) results_list[[length(results_list) + 1]] <- res_c_train
} else {
  cat("  Warning: scenario_c_1_factor.csv not found\n")
}

# Scenario C: Test (1998-2009)
file_c_test <- file.path(MODELS_DIR, "scenario_c_test_1_factor.csv")
if (file.exists(file_c_test)) {
  factor_c_test <- fread(file_c_test)
  res_c_test <- calc_alpha(factor_c_test, ff, "Scenario C (Test 1998-2009)")
  if (!is.null(res_c_test)) results_list[[length(results_list) + 1]] <- res_c_test
} else {
  cat("  Warning: scenario_c_test_1_factor.csv not found\n")
}


################################################################################
# Combine Results and Save
################################################################################

cat("\n")
cat("================================================================================\n")
cat("FINAL RESULTS\n")
cat("================================================================================\n\n")

if (length(results_list) == 0) {
  stop("No results to save. Run 02_train_ptree.R first.")
}

final_results <- rbindlist(results_list)

# Print summary table
print(final_results, digits = 4)

# Save CSV
output_csv <- file.path(OUTPUT_DIR, "performance_metrics.csv")
fwrite(final_results, output_csv)

cat("\n")
cat(sprintf("Results saved to: %s\n", normalizePath(OUTPUT_DIR)))
cat(sprintf("  - performance_metrics.csv\n"))

# Create LaTeX table
output_tex <- file.path(OUTPUT_DIR, "table_performance_metrics.tex")

# Format for LaTeX (round to appropriate decimal places)
tex_dt <- copy(final_results)
tex_dt[, scenario := gsub("_", "\\\\_", scenario)]
tex_dt[, sharpe_ratio := sprintf("%.2f", sharpe_ratio)]
tex_dt[, capm_alpha := sprintf("%.2f", capm_alpha * 100)]  # Convert to %
tex_dt[, capm_tstat := sprintf("(%.2f)", capm_tstat)]
tex_dt[, ff3_alpha := sprintf("%.2f", ff3_alpha * 100)]   # Convert to %
tex_dt[, ff3_tstat := sprintf("(%.2f)", ff3_tstat)]

# Select columns for table
tex_dt <- tex_dt[, .(scenario, sharpe_ratio, capm_alpha, capm_tstat, ff3_alpha, ff3_tstat)]

# Write LaTeX
cat("\\begin{table}[!ht]\n", file = output_tex)
cat("\\centering\n", file = output_tex, append = TRUE)
cat("\\caption{P-Tree Model Performance}\n", file = output_tex, append = TRUE)
cat("\\label{tab:performance}\n", file = output_tex, append = TRUE)
cat("\\begin{tabular}{l c c c c c}\n", file = output_tex, append = TRUE)
cat("\\hline\n", file = output_tex, append = TRUE)
cat("Scenario & Sharpe & CAPM $\\alpha$ (\\%) & t-stat & FF3 $\\alpha$ (\\%) & t-stat \\\\\n",
    file = output_tex, append = TRUE)
cat("\\hline\n", file = output_tex, append = TRUE)

for (i in 1:nrow(tex_dt)) {
  cat(sprintf("%s & %s & %s & %s & %s & %s \\\\\n",
              tex_dt[i, scenario],
              tex_dt[i, sharpe_ratio],
              tex_dt[i, capm_alpha],
              tex_dt[i, capm_tstat],
              tex_dt[i, ff3_alpha],
              tex_dt[i, ff3_tstat]),
      file = output_tex, append = TRUE)
}

cat("\\hline\n", file = output_tex, append = TRUE)
cat("\\end{tabular}\n", file = output_tex, append = TRUE)
cat("\\end{table}\n", file = output_tex, append = TRUE)

cat(sprintf("  - table_performance_metrics.tex\n\n"))

cat("================================================================================\n")
