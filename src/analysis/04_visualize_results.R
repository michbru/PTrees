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

  # Calculate market Sharpe ratio
  market_returns <- dt[, .(market_return = mean(ret_next, na.rm = TRUE)), by = date]
  market_mean <- mean(market_returns$market_return, na.rm = TRUE)
  market_sd <- sd(market_returns$market_return, na.rm = TRUE)
  market_sharpe <- (market_mean / market_sd) * sqrt(12)  # Annualized

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

  # Format table with significance stars
  perf_table <- perf[, .(
    Scenario = scenario,
    Sharpe = sprintf("%.2f", sharpe_ratio),
    CAPM_Alpha = sprintf("%.2f%s (%.2f)",
                         capm_alpha * 12 * 100,  # Annualize and convert to percentage
                         add_stars(capm_tstat),
                         capm_tstat),
    FF3_Alpha = sprintf("%.2f%s (%.2f)",
                        ff3_alpha * 12 * 100,  # Annualize and convert to percentage
                        add_stars(ff3_tstat),
                        ff3_tstat),
    Total_R2 = Total_R2,
    N = n_months
  )]

  # Add market benchmark row
  market_row <- data.table(
    Scenario = "Market Benchmark (EW)",
    Sharpe = sprintf("%.2f", market_sharpe),
    CAPM_Alpha = "--",
    FF3_Alpha = "--",
    Total_R2 = "--",
    N = nrow(market_returns)
  )

  perf_table <- rbind(market_row, perf_table)
  
  # Write LaTeX table
  tex_file <- file.path(OUTPUT_DIR, "table_performance.tex")
  cat("\\begin{table}[!ht]\n", file = tex_file)
  cat("\\centering\n", file = tex_file, append = TRUE)
  cat("\\caption{P-Tree Model Performance}\n", file = tex_file, append = TRUE)
  cat("\\label{tab:performance}\n", file = tex_file, append = TRUE)
  cat("\\begin{tabular}{l c c c c c}\n", file = tex_file, append = TRUE)
  cat("\\hline\n", file = tex_file, append = TRUE)
  cat("Scenario & Sharpe & CAPM $\\alpha$ (\\%) & FF3 $\\alpha$ (\\%) & Total $R^2$ & N \\\\\n",
      file = tex_file, append = TRUE)
  cat("\\hline\n", file = tex_file, append = TRUE)
  
  for (i in 1:nrow(perf_table)) {
    cat(sprintf("%s & %s & %s & %s & %s & %d \\\\\n",
                perf_table[i, Scenario],
                perf_table[i, Sharpe],
                perf_table[i, CAPM_Alpha],
                perf_table[i, FF3_Alpha],
                perf_table[i, Total_R2],
                perf_table[i, N]),
        file = tex_file, append = TRUE)
  }
  
  cat("\\hline\n", file = tex_file, append = TRUE)
  cat("\\end{tabular}\n", file = tex_file, append = TRUE)
  cat("\\\\[0.5em]\n", file = tex_file, append = TRUE)
  cat("\\begin{minipage}{0.95\\textwidth}\n", file = tex_file, append = TRUE)
  cat("\\footnotesize\n", file = tex_file, append = TRUE)
  cat("\\textit{Note:} Alphas are annualized (\\%) with t-statistics in parentheses (Newey-West SE, 12 lags). ",
      file = tex_file, append = TRUE)
  cat("Significance levels: *** $p<0.01$, ** $p<0.05$, * $p<0.10$. Total $R^2$ is the out-of-sample predictive $R^2$ vs zero benchmark.\n",
      file = tex_file, append = TRUE)
  cat("\\end{minipage}\n", file = tex_file, append = TRUE)
  cat("\\end{table}\n", file = tex_file, append = TRUE)
  
  cat("  ✓ table_performance.tex\n")
}


################################################################################
# Table 3: Tree Structure Summary
################################################################################

cat("Generating Table 3: Tree Structure...\n")

# Parse tree files to extract splits and characteristics
tree_summary <- list()

for (scenario in c("a", "b", "c")) {
  tree_file <- file.path(MODELS_DIR, sprintf("scenario_%s_trees.txt", scenario))

  if (file.exists(tree_file)) {
    tree_text <- readLines(tree_file)[1]

    # Parse tree text - split by \n
    lines <- strsplit(tree_text, "\\\\n")[[1]]

    split_char <- ""
    split_threshold <- NA
    num_splits <- 0

    if (length(lines) >= 2) {
      # Parse split line: "node char_idx threshold left_child right_child"
      split_parts <- strsplit(lines[2], " ")[[1]]
      split_parts <- split_parts[split_parts != ""]

      if (length(split_parts) >= 3) {
        char_idx <- as.numeric(split_parts[2])
        split_threshold <- as.numeric(split_parts[3])

        if (!is.na(char_idx) && char_idx > 0 && char_idx <= length(inp$char_cols)) {
          num_splits <- 1
          # Remove "rank_" prefix for display
          split_char <- gsub("^rank_", "", inp$char_cols[char_idx])
        }
      }
    }

    num_leaves <- num_splits + 1

    scenario_name <- switch(scenario,
                           "a" = "A: Full Sample",
                           "b" = "B: Train (1998-2009)",
                           "c" = "C: Train (2010-2019)")

    tree_summary[[length(tree_summary) + 1]] <- data.table(
      Scenario = scenario_name,
      Num_Splits = num_splits,
      Num_Leaves = num_leaves,
      Split_Char = split_char,
      Split_Threshold = split_threshold
    )
  }
}

if (length(tree_summary) > 0) {
  tree_table <- rbindlist(tree_summary)

  # Write LaTeX table
  tex_file <- file.path(OUTPUT_DIR, "table_tree_structure.tex")
  cat("\\begin{table}[!ht]\n", file = tex_file)
  cat("\\centering\n", file = tex_file, append = TRUE)
  cat("\\caption{P-Tree Structure by Scenario}\n", file = tex_file, append = TRUE)
  cat("\\label{tab:tree_structure}\n", file = tex_file, append = TRUE)
  cat("\\begin{tabular}{l c c l c}\n", file = tex_file, append = TRUE)
  cat("\\hline\n", file = tex_file, append = TRUE)
  cat("Scenario & Splits & Leaves & Split Variable & Threshold \\\\\n", file = tex_file, append = TRUE)
  cat("\\hline\n", file = tex_file, append = TRUE)

  for (i in 1:nrow(tree_table)) {
    threshold_str <- if (!is.na(tree_table[i, Split_Threshold])) {
      sprintf("%.2f", tree_table[i, Split_Threshold])
    } else {
      "--"
    }

    cat(sprintf("%s & %d & %d & %s & %s \\\\\n",
                tree_table[i, Scenario],
                tree_table[i, Num_Splits],
                tree_table[i, Num_Leaves],
                tree_table[i, Split_Char],
                threshold_str),
        file = tex_file, append = TRUE)
  }

  cat("\\hline\n", file = tex_file, append = TRUE)
  cat("\\end{tabular}\n", file = tex_file, append = TRUE)
  cat("\\end{table}\n", file = tex_file, append = TRUE)

  cat("  ✓ table_tree_structure.tex\n")
}


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

  # Write LaTeX table
  tex_file <- file.path(OUTPUT_DIR, "table_leaf_weights.tex")
  cat("\\begin{table}[!ht]\n", file = tex_file)
  cat("\\centering\n", file = tex_file, append = TRUE)
  cat("\\caption{Leaf Portfolio Weights (Tangency Portfolio)}\n", file = tex_file, append = TRUE)
  cat("\\label{tab:leaf_weights}\n", file = tex_file, append = TRUE)
  cat("\\begin{tabular}{l c l c c}\n", file = tex_file, append = TRUE)
  cat("\\hline\n", file = tex_file, append = TRUE)
  cat("Scenario & Leaf & Description & Weight & Weight (\\%) \\\\\n", file = tex_file, append = TRUE)
  cat("\\hline\n", file = tex_file, append = TRUE)

  for (i in 1:nrow(weights_table)) {
    cat(sprintf("%s & %d & %s & %.4f & %.2f\\%% \\\\\n",
                weights_table[i, Scenario],
                weights_table[i, Leaf_ID],
                weights_table[i, Leaf_Description],
                weights_table[i, Weight],
                weights_table[i, Weight_Pct]),
        file = tex_file, append = TRUE)
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

# Add market benchmark
market <- dt[, .(factor_return = mean(ret_next, na.rm = TRUE)), by = date]
market[, Scenario := "Market (EW)"]
plot_data_list[[1]] <- market

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
      "Market (EW)" = "#A23B72"
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
cat("  - table_tree_structure.tex\n")
cat("  - table_leaf_weights.tex (NEW)\n\n")

cat("Tables (CSV):\n")
cat("  - table_leaf_weights.csv (NEW)\n\n")

cat("Figures (PNG):\n")
cat("  - figure_cumulative_returns.png\n")
cat("  - figure_factor_timeseries.png\n\n")

cat("================================================================================\n")
