#!/usr/bin/env Rscript

################################################################################
# Step 4: Visualize Results
################################################################################
#
# Purpose: Generate essential tables and figures for thesis
#
# Outputs:
#   Tables (LaTeX):
#     - table_data_summary.tex: Dataset overview
#     - table_performance.tex: Model performance metrics
#     - table_tree_structure.tex: Tree characteristics
#   
#   Figures (PNG):
#     - figure_cumulative_returns.png: P-Tree vs Market
#     - figure_factor_timeseries.png: Monthly factor returns
#
################################################################################

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(PTree)
})

# Set seed for reproducibility
set.seed(42)

# Paths
args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- if (length(file_arg) > 0) dirname(normalizePath(file_arg)) else getwd()
repo_root <- normalizePath(file.path(script_dir, "..", ".."))
setwd(repo_root)

INPUT_RDS <- "results/inputs/ptree_inputs.rds"
MODELS_DIR <- "results/models"
EVAL_DIR <- "results/evaluation"
OUTPUT_DIR <- "results/thesis_visualisations"

# Clear output directory - start fresh
if (dir.exists(OUTPUT_DIR)) {
  cat("Clearing previous visualizations...\n")
  unlink(OUTPUT_DIR, recursive = TRUE)
}
dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

cat("================================================================================\n")
cat("STEP 4: VISUALIZE RESULTS\n")
cat("================================================================================\n\n")


################################################################################
# Table 1: Data Summary Statistics
################################################################################

cat("Generating Table 1: Data Summary...\n")

if (!file.exists(INPUT_RDS)) stop("Input file not found. Run 01_prepare_inputs.R first.")

inp <- readRDS(INPUT_RDS)
dt <- copy(inp$dt)

summary_table <- data.table(
  Metric = c(
    "Observations",
    "Firms", 
    "Time Periods (Months)",
    "Characteristics",
    "Date Range",
    "Avg Firms per Month"
  ),
  Value = c(
    format(nrow(dt), big.mark = ","),
    format(length(unique(dt$isin)), big.mark = ","),
    format(length(unique(dt$date)), big.mark = ","),
    length(inp$char_cols),
    sprintf("%s to %s", min(dt$date), max(dt$date)),
    format(round(nrow(dt) / length(unique(dt$date))), big.mark = ",")
  )
)

# Write LaTeX table
tex_file <- file.path(OUTPUT_DIR, "table_data_summary.tex")
cat("\\begin{table}[!ht]\n", file = tex_file)
cat("\\centering\n", file = tex_file, append = TRUE)
cat("\\caption{Dataset Summary Statistics}\n", file = tex_file, append = TRUE)
cat("\\label{tab:data_summary}\n", file = tex_file, append = TRUE)
cat("\\begin{tabular}{l r}\n", file = tex_file, append = TRUE)
cat("\\hline\n", file = tex_file, append = TRUE)
cat("Metric & Value \\\\\n", file = tex_file, append = TRUE)
cat("\\hline\n", file = tex_file, append = TRUE)

for (i in 1:nrow(summary_table)) {
  cat(sprintf("%s & %s \\\\\n", summary_table[i, Metric], summary_table[i, Value]),
      file = tex_file, append = TRUE)
}

cat("\\hline\n", file = tex_file, append = TRUE)
cat("\\end{tabular}\n", file = tex_file, append = TRUE)
cat("\\end{table}\n", file = tex_file, append = TRUE)

cat("  ✓ table_data_summary.tex\n")


################################################################################
# Table 2: Model Performance (from Step 3)
################################################################################

cat("Generating Table 2: Model Performance...\n")

# --- R2 Calculation Logic (Integrated) ---

# Helper to prepare data for prediction
prepare_pred_data <- function(dt_subset, char_cols) {
  X <- as.matrix(dt_subset[, .SD, .SDcols = char_cols])
  R <- as.vector(dt_subset$ret_next)
  months <- as.integer(as.factor(dt_subset$date)) - 1L
  list(X = X, R = R, months = months)
}

# Helper to calculate R2
calc_scenario_r2 <- function(model_path, dt_subset) {
  if (!file.exists(model_path)) return(NA_real_)
  
  model <- readRDS(model_path)
  data <- prepare_pred_data(dt_subset, inp$char_cols)
  
  if (!requireNamespace("PTree", quietly = TRUE)) return(NA_real_)
  
  # Predict returns leaf indices and calculates portfolio returns based on data$R
  pred <- predict(model, X = data$X, R = data$R, months = data$months)
  
  # Reconstruct predicted returns (R_hat) for each observation
  # R_hat[i] = Return of the leaf portfolio that observation i belongs to at month t
  
  if (!"portfolio" %in% names(pred) || !"leaf_index" %in% names(pred)) {
    return(NA_real_)
  }
  
  # Map leaf IDs to column indices in portfolio matrix
  leaf_map <- match(pred$leaf_index, model$leaf_id)
  
  # Map months to row indices in portfolio matrix
  unique_months <- sort(unique(data$months))
  month_map <- match(data$months, unique_months)
  
  # Extract R_hat using matrix indexing
  idx_mat <- cbind(month_map, leaf_map)
  R_hat <- pred$portfolio[idx_mat]
  
  # Handle potential NAs (if any leaf was empty/undefined, though predict handles this)
  R_hat[is.na(R_hat)] <- 0
  
  sse <- sum((data$R - R_hat)^2)
  sst_zero <- sum(data$R^2)
  
  return(1 - sse / sst_zero)
}

# Calculate R2 for each scenario
r2_map <- list()

# Scenario A (Full)
r2_map[["Scenario A (Full Sample)"]] <- calc_scenario_r2(
  file.path(MODELS_DIR, "scenario_a_model.rds"), dt
)

# Scenario B (Test)
split_date <- as.IDate("2010-01-01")
dt_test_b <- dt[date >= split_date]
r2_map[["Scenario B (Test 2010-2019)"]] <- calc_scenario_r2(
  file.path(MODELS_DIR, "scenario_b_model.rds"), dt_test_b
)

# Scenario C (Test)
dt_test_c <- dt[date < split_date]
r2_map[["Scenario C (Test 1998-2009)"]] <- calc_scenario_r2(
  file.path(MODELS_DIR, "scenario_c_model.rds"), dt_test_c
)

# --- End R2 Calculation ---

perf_file <- file.path(EVAL_DIR, "performance_metrics.csv")
if (!file.exists(perf_file)) {
  cat("  Warning: performance_metrics.csv not found. Run 03_evaluate_model.R first.\n")
} else {
  perf <- fread(perf_file)

  # Load Fama-French data for value-weighted market benchmark
  FF_PATH <- "data/raw/macro/raw_macro_factors.csv"
  if (!file.exists(FF_PATH)) stop("Fama-French factors not found")
  ff_data <- fread(FF_PATH)
  ff_data[, date := as.IDate(date)]
  
  # Use rm (value-weighted market return) as benchmark
  market_returns <- ff_data[, .(date, market_return = rm)]
  market_mean <- mean(market_returns$market_return, na.rm = TRUE)
  market_sd <- sd(market_returns$market_return, na.rm = TRUE)
  market_sharpe <- (market_mean / market_sd) * sqrt(12)  # Annualized
  
  # Calculate Market Cumulative Return and Volatility
  market_cum_ret <- prod(1 + market_returns$market_return) - 1
  market_vol_ann <- market_sd * sqrt(12)

  # Helper function to add significance stars (vectorized)
  add_stars <- function(tstat) {
    sapply(tstat, function(t) {
      abs_t <- abs(t)
      if (abs_t >= 2.576) return("***")      # 1% significance
      if (abs_t >= 1.96) return("**")        # 5% significance
      if (abs_t >= 1.645) return("*")        # 10% significance
      return("")
    })
  }

  # Add R2 column
  perf[, Total_R2 := sapply(scenario, function(s) {
    val <- r2_map[[s]]
    if (is.null(val) || is.na(val)) return("--")
    sprintf("%.2f\\%%", val * 100)
  })]
  
  # Calculate Cumulative Return for each scenario
  # Map scenario names to file paths
  scenario_files <- list(
    "Scenario A (Full Sample)" = file.path(MODELS_DIR, "scenario_a_1_factor.csv"),
    "Scenario B (Train 1998-2009)" = file.path(MODELS_DIR, "scenario_b_1_factor.csv"),
    "Scenario B (Test 2010-2019)" = file.path(MODELS_DIR, "scenario_b_test_1_factor.csv"),
    "Scenario C (Train 2010-2019)" = file.path(MODELS_DIR, "scenario_c_1_factor.csv"),
    "Scenario C (Test 1998-2009)" = file.path(MODELS_DIR, "scenario_c_test_1_factor.csv")
  )
  
  perf[, Ann_Ret := sapply(scenario, function(s) {
    fpath <- scenario_files[[s]]
    if (!is.null(fpath) && file.exists(fpath)) {
      d <- fread(fpath)
      cum_r <- prod(1 + d$factor_return) - 1
      n_months <- nrow(d)
      # Annualize: (1 + cum_r)^(12/n_months) - 1
      ann_r <- (1 + cum_r)^(12/n_months) - 1
      return(sprintf("%.2f\\%%", ann_r * 100))
    }
    return("--")
  })]
  
  # Calculate Annualized Volatility
  perf[, Volatility := sprintf("%.2f\\%%", sd_monthly * sqrt(12) * 100)]

  # Format table with significance stars
  perf_table <- perf[, .(
    Scenario = scenario,
    Ann_Ret = Ann_Ret,
    Volatility = Volatility,
    Sharpe = sprintf("%.2f", sharpe_ratio),
    Beta = sprintf("%.2f", capm_beta),
    CAPM_Alpha = sprintf("%.2f%s (%.2f)",
                         capm_alpha * 12 * 100,  # Annualize and convert to percentage
                         add_stars(capm_tstat),
                         capm_tstat),
    FF3_Alpha = sprintf("%.2f%s (%.2f)",
                        ff3_alpha * 12 * 100,  # Annualize and convert to percentage
                        add_stars(ff3_tstat),
                        ff3_tstat),
    Total_R2 = Total_R2
  )]
  
  # Simplify scenario names - remove time periods
  perf_table[, Scenario := gsub(" 1998-2009", "", Scenario)]
  perf_table[, Scenario := gsub(" 2010-2019", "", Scenario)]
  perf_table[, Scenario := gsub("Full Sample", "", Scenario)]
  perf_table[, Scenario := gsub(" \\(\\)", "", Scenario)]  # Remove empty parentheses
  perf_table[, Scenario := gsub("  ", " ", Scenario)]  # Remove double spaces
  perf_table[, Scenario := trimws(Scenario)]  # Trim whitespace

  # Add market benchmark row
  # Calculate annualized market return
  market_ann_ret <- (1 + market_cum_ret)^(12/nrow(market_returns)) - 1
  
  market_row <- data.table(
    Scenario = "Market Benchmark (VW)",
    Ann_Ret = sprintf("%.2f\\%%", market_ann_ret * 100),
    Volatility = sprintf("%.2f\\%%", market_vol_ann * 100),
    Sharpe = sprintf("%.2f", market_sharpe),
    Beta = "1.00",
    CAPM_Alpha = "--",
    FF3_Alpha = "--",
    Total_R2 = "--"
  )

  perf_table <- rbind(market_row, perf_table)
  
  # Write LaTeX table
  tex_file <- file.path(OUTPUT_DIR, "table_performance.tex")
  cat("\\begin{table}[!ht]\n", file = tex_file)
  cat("\\centering\n", file = tex_file, append = TRUE)
  cat("\\caption{P-Tree Model Performance}\n", file = tex_file, append = TRUE)
  cat("\\label{tab:performance}\n", file = tex_file, append = TRUE)
  cat("\\begin{tabular}{l *{7}{c}}\n", file = tex_file, append = TRUE)  # Left-align scenario, center rest
  cat("\\hline\n", file = tex_file, append = TRUE)
  cat("Scenario & Ann. Ret & Vol (Ann.) & Sharpe & Beta & CAPM $\\alpha$ (\\%) & FF3 $\\alpha$ (\\%) & Total $R^2$ \\\\\n",
      file = tex_file, append = TRUE)
  cat("\\hline\n", file = tex_file, append = TRUE)
  
  for (i in 1:nrow(perf_table)) {
    cat(sprintf("%s & %s & %s & %s & %s & %s & %s & %s \\\\\n",
                perf_table[i, Scenario],
                perf_table[i, Ann_Ret],
                perf_table[i, Volatility],
                perf_table[i, Sharpe],
                perf_table[i, Beta],
                perf_table[i, CAPM_Alpha],
                perf_table[i, FF3_Alpha],
                perf_table[i, Total_R2]),
        file = tex_file, append = TRUE)
  }
  
  cat("\\hline\n", file = tex_file, append = TRUE)
  cat("\\end{tabular}\n", file = tex_file, append = TRUE)
  cat("\\\\[0.5em]\n", file = tex_file, append = TRUE)
  cat("\\begin{minipage}{0.95\\textwidth}\n", file = tex_file, append = TRUE)
  cat("\\footnotesize\n", file = tex_file, append = TRUE)
  cat("\\textit{Note:} Ann. Ret is the annualized return (geometric mean). Vol (Ann.) is the annualized volatility. Sharpe is the annualized Sharpe ratio. Beta is the CAPM beta. Alphas are annualized (\\%) with t-statistics in parentheses (Newey-West SE, 12 lags). ",
      file = tex_file, append = TRUE)
  cat("Significance levels: *** $p<0.01$, ** $p<0.05$, * $p<0.10$. Total $R^2$ is the out-of-sample $R^2$ vs zero benchmark (test periods only).\n",
      file = tex_file, append = TRUE)
  cat("\\end{minipage}\n", file = tex_file, append = TRUE)
  cat("\\end{table}\n", file = tex_file, append = TRUE)
  
  cat("  ✓ table_performance.tex\n")
}


################################################################################
# Table 3: Leaf Portfolio Weights with Tree Structure
################################################################################

cat("Generating Table 3: Leaf Portfolio Weights...\n")


################################################################################
# Table 4: Leaf Portfolio Weights (Tangency Portfolio Weights)
################################################################################

cat("Generating Table 4: Leaf Portfolio Weights...\n")

# Extract leaf weights from each model
weights_summary <- list()

for (scenario in c("a", "b", "c")) {
  model_file <- file.path(MODELS_DIR, sprintf("scenario_%s_model.rds", scenario))

  if (file.exists(model_file)) {
    model <- readRDS(model_file)

    scenario_name <- switch(scenario,
                           "a" = "A: Full Sample",
                           "b" = "B: Train (1998-2009)",
                           "c" = "C: Train (2010-2019)")

    # Get leaf weights (tangency portfolio weights)
    if ("leaf_weight" %in% names(model) && "leaf_id" %in% names(model)) {
      leaf_weights <- as.numeric(model$leaf_weight)
      leaf_ids <- as.numeric(model$leaf_id)

      # Get split characteristic for interpretation
      tree_text <- readLines(file.path(MODELS_DIR, sprintf("scenario_%s_trees.txt", scenario)))[1]
      lines <- strsplit(tree_text, "\\\\n")[[1]]
      split_char <- ""
      split_threshold <- NA

      if (length(lines) >= 2) {
        split_parts <- strsplit(lines[2], " ")[[1]]
        split_parts <- split_parts[split_parts != ""]

        if (length(split_parts) >= 3) {
          char_idx <- as.numeric(split_parts[2])
          split_threshold <- as.numeric(split_parts[3])

          if (!is.na(char_idx) && char_idx > 0 && char_idx <= length(inp$char_cols)) {
            split_char <- gsub("^rank_", "", inp$char_cols[char_idx])
          }
        }
      }

      # Create interpretation labels for each leaf
      if (length(leaf_weights) == 2 && split_char != "") {
        leaf_descriptions <- c(
          sprintf("Low %s (< %.2f)", split_char, split_threshold),
          sprintf("High %s ($\\geq$ %.2f)", split_char, split_threshold)
        )
      } else {
        leaf_descriptions <- paste("Leaf", leaf_ids)
      }

      # Store weights for this scenario
      for (i in seq_along(leaf_weights)) {
        weights_summary[[length(weights_summary) + 1]] <- data.table(
          Scenario = scenario_name,
          Split_Var = split_char,
          Split_Threshold = split_threshold,
          Leaf_ID = leaf_ids[i],
          Leaf_Description = leaf_descriptions[i],
          Weight = leaf_weights[i],
          Weight_Pct = leaf_weights[i] * 100
        )
      }
    }
  }
}

if (length(weights_summary) > 0) {
  weights_table <- rbindlist(weights_summary)

  # Write LaTeX table with split information
  tex_file <- file.path(OUTPUT_DIR, "table_leaf_weights.tex")
  cat("\\begin{table}[!ht]\n", file = tex_file)
  cat("\\centering\n", file = tex_file, append = TRUE)
  cat("\\caption{P-Tree Portfolio Weights and Structure}\n", file = tex_file, append = TRUE)
  cat("\\label{tab:leaf_weights}\n", file = tex_file, append = TRUE)
  cat("\\begin{tabular}{l l l c r}\n", file = tex_file, append = TRUE)
  cat("\\hline\n", file = tex_file, append = TRUE)
  cat("Scenario & Split Variable & Portfolio & Threshold & Weight (\\%) \\\\\n", file = tex_file, append = TRUE)
  cat("\\hline\n", file = tex_file, append = TRUE)

  # Group by scenario to add split info
  scenarios <- unique(weights_table$Scenario)
  for (scen in scenarios) {
    scen_rows <- weights_table[Scenario == scen]
    
    # Get split info (same for all rows in scenario)
    split_var <- scen_rows[1, Split_Var]
    
    for (i in 1:nrow(scen_rows)) {
      # Only show split variable on first row of each scenario
      split_display <- if (i == 1) split_var else ""
      
      cat(sprintf("%s & %s & %s & %.2f & %.2f\\%% \\\\\n",
                  scen_rows[i, Scenario],
                  split_display,
                  scen_rows[i, Leaf_Description],
                  scen_rows[i, Split_Threshold],
                  scen_rows[i, Weight_Pct]),
          file = tex_file, append = TRUE)
    }
    
    # Add spacing between scenarios
    if (scen != scenarios[length(scenarios)]) {
      cat("\\hline\n", file = tex_file, append = TRUE)
    }
  }

  cat("\\hline\n", file = tex_file, append = TRUE)
  cat("\\end{tabular}\n", file = tex_file, append = TRUE)
  cat("\\\\[0.5em]\n", file = tex_file, append = TRUE)
  cat("\\begin{minipage}{0.95\\textwidth}\n", file = tex_file, append = TRUE)
  cat("\\footnotesize\n", file = tex_file, append = TRUE)
  cat("\\textit{Note:} Weights represent the tangency portfolio allocation across leaf portfolios, ",
      file = tex_file, append = TRUE)
  cat("optimized to maximize the Sharpe ratio. Within each leaf, stocks are value-weighted by market capitalization.\n",
      file = tex_file, append = TRUE)
  cat("\\end{minipage}\n", file = tex_file, append = TRUE)
  cat("\\end{table}\n", file = tex_file, append = TRUE)

  cat("  ✓ table_leaf_weights.tex\n")

  # Also save as CSV for easy reference
  csv_file <- file.path(OUTPUT_DIR, "table_leaf_weights.csv")
  fwrite(weights_table, csv_file)
  cat("  ✓ table_leaf_weights.csv\n")
}


################################################################################
# Figure 1: Cumulative Returns (P-Tree vs Market)
################################################################################

cat("Generating Figure 1: Cumulative Returns...\n")

# Collect all factor files
factor_files <- list(
  "A (Full)" = file.path(MODELS_DIR, "scenario_a_1_factor.csv"),
  "B (Test)" = file.path(MODELS_DIR, "scenario_b_test_1_factor.csv"),
  "C (Test)" = file.path(MODELS_DIR, "scenario_c_test_1_factor.csv")
)

plot_data_list <- list()

# Add market benchmark (value-weighted from Fama-French)
FF_PATH <- "data/raw/macro/raw_macro_factors.csv"
if (file.exists(FF_PATH)) {
  ff_data <- fread(FF_PATH)
  ff_data[, date := as.IDate(date)]
  market <- ff_data[, .(date, factor_return = rm)]
  market[, Scenario := "Market (VW)"]
  plot_data_list[[1]] <- market
}

# Add P-Tree factors
for (name in names(factor_files)) {
  fpath <- factor_files[[name]]
  if (file.exists(fpath)) {
    factor_dt <- fread(fpath)
    factor_dt[, date := as.IDate(date)]
    factor_dt[, Scenario := name]
    plot_data_list[[length(plot_data_list) + 1]] <- factor_dt[, .(date, factor_return, Scenario)]
  }
}

if (length(plot_data_list) > 1) {
  combined <- rbindlist(plot_data_list)
  setorder(combined, Scenario, date)
  
  # Ensure factor_return is numeric
  combined[, factor_return := as.numeric(factor_return)]
  
  # Calculate cumulative returns
  combined[, Cumulative := cumprod(1 + factor_return) - 1, by = Scenario]
  
  # Plot
  p1 <- ggplot(combined, aes(x = date, y = Cumulative * 100, color = Scenario)) +
    geom_line(linewidth = 1) +
    geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
    scale_color_manual(values = c(
      "A (Full)" = "#2E86AB",
      "B (Test)" = "#F24333", 
      "C (Test)" = "#F2A900",
      "Market (VW)" = "#A23B72"
    )) +
    labs(
      x = "Date",
      y = "Cumulative Return (%)"
    ) +
    theme_minimal(base_size = 12) +
    theme(
      legend.position = "bottom"
    )
  
  ggsave(file.path(OUTPUT_DIR, "figure_cumulative_returns.png"), 
         p1, width = 10, height = 6, dpi = 300)
  
  cat("  ✓ figure_cumulative_returns.png\n")
}


################################################################################
# Figure 2: Factor Time Series (Scenario A)
################################################################################

cat("Generating Figure 2: Factor Time Series...\n")

factor_a_file <- file.path(MODELS_DIR, "scenario_a_1_factor.csv")
if (file.exists(factor_a_file)) {
  factor_a <- fread(factor_a_file)
  factor_a[, date := as.IDate(date)]
  factor_a[, factor_return := as.numeric(factor_return)]
  
  # Plot monthly returns
  p2 <- ggplot(factor_a, aes(x = date, y = factor_return * 100)) +
    geom_line(color = "#2E86AB", linewidth = 0.8) +
    geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
    labs(
      x = "Date",
      y = "Monthly Return (%)"
    ) +
    theme_minimal(base_size = 12)
  
  ggsave(file.path(OUTPUT_DIR, "figure_factor_timeseries.png"),
         p2, width = 10, height = 6, dpi = 300)
  
  cat("  ✓ figure_factor_timeseries.png\n")
}


################################################################################
# Summary
################################################################################

cat("\n")
cat("================================================================================\n")
cat("VISUALIZATION COMPLETE\n")
cat("================================================================================\n\n")

cat(sprintf("Results saved to: %s\n\n", normalizePath(OUTPUT_DIR)))

cat("Tables (LaTeX):\n")
cat("  - table_data_summary.tex\n")
cat("  - table_performance.tex\n")
cat("  - table_leaf_weights.tex (includes tree structure)\n\n")

cat("Tables (CSV):\n")
cat("  - table_leaf_weights.csv (NEW)\n\n")

cat("Figures (PNG):\n")
cat("  - figure_cumulative_returns.png\n")
cat("  - figure_factor_timeseries.png\n\n")

cat("================================================================================\n")
