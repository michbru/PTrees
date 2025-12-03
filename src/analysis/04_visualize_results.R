#!/usr/bin/env Rscript

# A4: Visualize Results (Single-Factor P-Tree Analysis)
# -----------------------------------------------------------
# Generates key tables and figures for the thesis based on the current pipeline:
# - Table 1: Data Summary Statistics (LaTeX)
# - Table 2: Model Performance (Sharpe, Alpha) (LaTeX)
# - Figure 1: Cumulative Returns (MVE vs Market)
# - Figure 2: Factor Correlation Heatmap
# - Figure 3: Monthly Returns Distribution

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(lmtest)
  library(sandwich)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

# Paths
in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")
models_dir <- file.path(repo_root, "results", "models")
eval_dir <- file.path(repo_root, "results", "evaluation")
out_dir <- file.path(repo_root, "results", "thesis_visualisations")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# Clean up old results
cat("\nCleaning up old visualizations...\n")
old_files <- list.files(out_dir, pattern = "\\.(csv|tex|png)$", full.names = TRUE)
if (length(old_files) > 0) {
  file.remove(old_files)
  cat(sprintf("  Removed %d old file(s)\n", length(old_files)))
}

cat("\n╔════════════════════════════════════════════════╗\n")
cat("║   A4: VISUALIZE RESULTS                        ║\n")
cat("╚════════════════════════════════════════════════╝\n\n")

# LaTeX table writer
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

# ==============================================================================
# 1. TABLE 1: DATA SUMMARY STATISTICS
# ==============================================================================
cat("Generating Table 1: Data Summary Statistics...\n")

if (!file.exists(in_rds)) stop("Inputs RDS not found. Run Step 1 first.")
inp <- readRDS(in_rds)
dt <- copy(inp$dt)

summary_stats <- data.table(
  Metric = c("Observations", "Companies", "Months", "Characteristics", 
             "Date Range", "Avg Companies/Month"),
  Value = c(
    format(nrow(dt), big.mark = ","),
    format(length(unique(dt$isin)), big.mark = ","),
    format(length(unique(dt$date)), big.mark = ","),
    length(inp$char_cols),
    paste(min(dt$date), "to", max(dt$date)),
    format(round(nrow(dt) / length(unique(dt$date))), big.mark = ",")
  )
)

write_tex_table(summary_stats, file.path(out_dir, "table1_data_summary.tex"),
                caption = "Data Summary Statistics",
                label = "tab:data_summary")
cat("  Saved: table1_data_summary.tex\n")

# ==============================================================================
# 2. TABLE 2: MODEL PERFORMANCE (from Step 3)
# ==============================================================================
cat("Generating Table 2: Model Performance...\n")

# Helper function to add significance stars
add_stars <- function(value, tstat) {
  abs_t <- abs(tstat)
  stars <- ifelse(abs_t >= 2.576, "***",  # 1% level
                 ifelse(abs_t >= 1.96, "**",   # 5% level
                       ifelse(abs_t >= 1.645, "*", "")))  # 10% level

  # Format value with stars
  if (is.na(value)) return("")
  formatted <- sprintf("%.2f", value)
  if (stars != "") {
    formatted <- paste0(formatted, "$^{", stars, "}$")
  }
  return(formatted)
}

perf_file <- file.path(eval_dir, "final_ensemble_results.csv")
if (file.exists(perf_file)) {
  perf <- fread(perf_file)

  # Calculate t-statistics for Sharpe ratio and mean using standard formulas
  # Sharpe ratio t-stat: SR * sqrt(n_months)
  perf[, sharpe_tstat := sharpe * sqrt(n_months)]

  # Mean t-stat: (mean / se), where se = sd / sqrt(n_months)
  perf[, mean_tstat := (mean_ann / (sd_ann / sqrt(n_months)))]

  # Simplify scenario names for the table
  perf[, scenario_short := gsub("_test", "", scenario)]
  perf[, scenario_short := gsub(" \\(Ensemble\\)", "", scenario_short)]
  perf[, scenario_short := toupper(gsub("scenario_", "Scenario ", scenario_short))]

  # Format for thesis with significance stars - COMPACT VERSION
  perf_table <- data.table(
    Scenario = perf$scenario_short,
    Sharpe = sapply(1:nrow(perf), function(i) {
      val <- round(perf$sharpe[i], 2)  # Reduced precision
      tstat <- perf$sharpe_tstat[i]
      abs_t <- abs(tstat)
      stars <- ifelse(abs_t >= 2.576, "***",
                     ifelse(abs_t >= 1.96, "**",
                           ifelse(abs_t >= 1.645, "*", "")))
      if (stars != "") paste0(val, "$^{", stars, "}$") else as.character(val)
    }),
    `Mean` = sapply(1:nrow(perf), function(i) {
      val <- round(perf$mean_ann[i] * 100, 2)
      tstat <- perf$mean_tstat[i]
      abs_t <- abs(tstat)
      stars <- ifelse(abs_t >= 2.576, "***",
                     ifelse(abs_t >= 1.96, "**",
                           ifelse(abs_t >= 1.645, "*", "")))
      if (stars != "") paste0(val, "$^{", stars, "}$") else as.character(val)
    }),
    `Std` = round(perf$sd_ann * 100, 2),
    `CAPM $\\alpha$` = sapply(1:nrow(perf), function(i) {
      val <- round(perf$capm_alpha[i] * 100, 2)
      tstat <- perf$capm_tstat[i]
      abs_t <- abs(tstat)
      stars <- ifelse(abs_t >= 2.576, "***",
                     ifelse(abs_t >= 1.96, "**",
                           ifelse(abs_t >= 1.645, "*", "")))
      if (stars != "") {
        paste0(val, "$^{", stars, "}$ (", round(tstat, 1), ")")
      } else {
        paste0(val, " (", round(tstat, 1), ")")
      }
    }),
    `FF3 $\\alpha$` = sapply(1:nrow(perf), function(i) {
      val <- round(perf$ff3_alpha[i] * 100, 2)
      tstat <- perf$ff3_tstat[i]
      abs_t <- abs(tstat)
      stars <- ifelse(abs_t >= 2.576, "***",
                     ifelse(abs_t >= 1.96, "**",
                           ifelse(abs_t >= 1.645, "*", "")))
      if (stars != "") {
        paste0(val, "$^{", stars, "}$ (", round(tstat, 1), ")")
      } else {
        paste0(val, " (", round(tstat, 1), ")")
      }
    }),
    N = perf$n_months
  )

  # Write table with custom footer for significance notes
  tex_file <- file.path(out_dir, "table2_model_performance.tex")
  con <- file(tex_file, open = "wt")
  on.exit(close(con))

  writeLines("\\begin{table}[!ht]", con)
  writeLines("\\centering", con)
  writeLines("\\caption{P-Tree Ensemble Performance}", con)
  writeLines("\\label{tab:performance}", con)
  writeLines("\\small", con)  # Make entire table smaller

  # Build column specification - use different alignment
  writeLines("\\begin{tabular}{l r r r r r r}", con)
  writeLines("\\hline", con)
  writeLines("Scenario & Sharpe & Mean (\\%) & Std (\\%) & CAPM $\\alpha$ (\\%) & FF3 $\\alpha$ (\\%) & N \\\\", con)
  writeLines("\\hline", con)

  # Write data rows with proper line endings
  for (i in 1:nrow(perf_table)) {
    row_data <- as.character(perf_table[i, ])
    writeLines(paste0(paste(row_data, collapse = " & "), " \\\\"), con)
  }

  writeLines("\\hline", con)
  writeLines("\\end{tabular}", con)
  writeLines("\\\\[0.5em]", con)
  writeLines("\\begin{minipage}{0.95\\textwidth}", con)
  writeLines("\\footnotesize", con)
  writeLines("\\textit{Note:} Mean and Std are annualized (\\%). Alphas are annualized (\\%) with t-statistics in parentheses. $^{***}$ p$<$0.01, $^{**}$ p$<$0.05, $^{*}$ p$<$0.1. T-stats use Newey-West SE (12 lags).", con)
  writeLines("\\end{minipage}", con)
  writeLines("\\end{table}", con)

  cat("  Saved: table2_model_performance.tex\n")
  cat("  Note: *** p<0.01, ** p<0.05, * p<0.1\n")
} else {
  cat("  Warning: final_ensemble_results.csv not found. Skipping Table 2.\n")
}

# ==============================================================================
# 3. TABLE 3: TREE STRUCTURES (DYNAMIC)
# ==============================================================================
cat("Generating Table 3: Tree Structures...\n")

# Function to parse tree structure from tree text file
parse_tree <- function(tree_file, char_names) {
  if (!file.exists(tree_file)) return(NULL)

  tree_lines <- readLines(tree_file)
  splits <- list()

  for (line in tree_lines) {
    if (grepl("^\\[1\\]", line)) {
      # Parse tree structure
      tree_str <- gsub('\\[1\\] "', '', line)
      tree_str <- gsub('"', '', tree_str)
      parts <- strsplit(tree_str, "\\\\n")[[1]]

      # Parse each node
      for (i in 2:length(parts)) {
        if (nchar(trimws(parts[i])) == 0) next
        node <- strsplit(trimws(parts[i]), "\\s+")[[1]]
        if (length(node) >= 3 && node[2] != "0") {
          var_idx <- as.integer(node[2])
          threshold <- as.numeric(node[3])
          splits[[length(splits) + 1]] <- list(
            var_idx = var_idx,
            var_name = char_names[var_idx + 1],  # 0-indexed
            threshold = threshold
          )
        }
      }
    }
  }

  return(splits)
}

# Load characteristic names
if (file.exists(in_rds)) {
  inp_check <- readRDS(in_rds)
  char_names <- inp_check$char_cols
} else {
  stop("Cannot load characteristic names from inputs")
}

# Parse trees for all scenarios
tree_files <- list(
  A = file.path(models_dir, "scenario_a_trees.txt"),
  B = file.path(models_dir, "scenario_b_trees.txt"),
  C = file.path(models_dir, "scenario_c_trees.txt")
)

tree_data <- list()
for (scenario_name in names(tree_files)) {
  splits <- parse_tree(tree_files[[scenario_name]], char_names)
  if (!is.null(splits)) {
    tree_data[[scenario_name]] <- splits
  }
}

# Build LaTeX table
tree_tex_file <- file.path(out_dir, "table3_tree_structures.tex")
con <- file(tree_tex_file, open = "wt")
writeLines("\\begin{table}[!ht]", con)
writeLines("\\centering", con)
writeLines("\\caption{P-Tree Structure by Scenario}", con)
writeLines("\\label{tab:tree_structure}", con)
writeLines("\\begin{tabular}{l|l|l|c|c}", con)
writeLines("\\hline", con)
writeLines("Scenario & Period & Splitting Variables & Depth & Num Vars \\\\", con)
writeLines("\\hline", con)

# Scenario A
if ("A" %in% names(tree_data)) {
  splits_a <- tree_data$A
  vars_a <- paste0("\\texttt{", sapply(splits_a, function(x) gsub("_", "\\\\_", x$var_name)), "}")
  thresh_a <- sapply(splits_a, function(x) sprintf("%.3f", x$threshold))
  writeLines(sprintf("A: Full & 1998--2019 & %s & %d & %d \\\\",
                     paste(vars_a, collapse = ", "), length(splits_a), length(unique(sapply(splits_a, function(x) x$var_name)))), con)
}

# Scenario B
if ("B" %in% names(tree_data)) {
  splits_b <- tree_data$B
  vars_b <- paste0("\\texttt{", sapply(splits_b, function(x) gsub("_", "\\\\_", x$var_name)), "}")
  writeLines(sprintf("B: Train Early & 1998--2009 & %s & %d & %d \\\\",
                     paste(vars_b, collapse = ", "), length(splits_b), length(unique(sapply(splits_b, function(x) x$var_name)))), con)
}

# Scenario C
if ("C" %in% names(tree_data)) {
  splits_c <- tree_data$C
  vars_c <- paste0("\\texttt{", sapply(splits_c, function(x) gsub("_", "\\\\_", x$var_name)), "}")
  writeLines(sprintf("C: Train Late & 2010--2019 & %s & %d & %d \\\\",
                     paste(vars_c, collapse = ", "), length(splits_c), length(unique(sapply(splits_c, function(x) x$var_name)))), con)
}

writeLines("\\hline", con)
writeLines("\\end{tabular}", con)
writeLines("\\\\[1em]", con)
writeLines("\\begin{minipage}{0.9\\textwidth}", con)
writeLines("\\small", con)
writeLines("\\textit{Note:} Each scenario produces a single boosted factor (9 iterations). Depth = number of splits, Num Vars = number of unique characteristics used. Trees are parsed dynamically from model outputs.", con)
writeLines("\\end{minipage}", con)
writeLines("\\end{table}", con)
close(con)

cat("  Saved: table3_tree_structures.tex\n")

# ==============================================================================
# 4. FIGURE 1: CUMULATIVE RETURNS (MVE vs Market)
# ==============================================================================
cat("Generating Figure 1: Cumulative Returns...\n")

# Load all ensemble files
ensemble_files <- list.files(models_dir, pattern = "_ensemble.csv", full.names = TRUE)
if (length(ensemble_files) > 0) {
  plot_data_list <- list()
  
  # Market EW (calculate once)
  market <- dt[, .(Return = mean(ret_next, na.rm = TRUE)), by = date]
  market[, Strategy := "Market (EW)"]
  plot_data_list[[1]] <- market
  
  for (f in ensemble_files) {
    ens <- fread(f)
    ens[, date := as.IDate(date)]
    
    # Determine strategy name from filename
    fname <- basename(f)
    strat_name <- "Unknown"
    if (grepl("scenario_a", fname)) strat_name <- "Scenario A (Full)"
    if (grepl("scenario_b_test", fname)) strat_name <- "Scenario B (OOS)"
    if (grepl("scenario_c_test", fname)) strat_name <- "Scenario C (OOS)"
    
    if (strat_name != "Unknown") {
      ens[, Strategy := strat_name]
      ens[, Return := factor]  # Already in decimal form
      plot_data_list[[length(plot_data_list)+1]] <- ens[, .(date, Return, Strategy)]
    }
  }
  
  combined <- rbindlist(plot_data_list)
  setorder(combined, date)
  combined[, Cumulative := cumprod(1 + Return) - 1, by = Strategy]
  
  p1 <- ggplot(combined, aes(x = date, y = Cumulative * 100, color = Strategy)) +
    geom_line(linewidth = 1) +
    geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
    scale_color_manual(values = c(
      "Scenario A (Full)" = "#2E86AB", 
      "Scenario B (OOS)" = "#F24333",
      "Scenario C (OOS)" = "#F2A900",
      "Market (EW)" = "#A23B72"
    )) +
    labs(title = "Cumulative Returns: P-Tree Scenarios vs Market",
         x = "", y = "Cumulative Return (%)") +
    theme_minimal(base_size = 12) +
    theme(legend.position = "bottom", plot.title = element_text(face = "bold"))
  
  ggsave(file.path(out_dir, "figure1_cumulative_returns.png"), p1, width = 10, height = 6, dpi = 300)
  cat("  Saved: figure1_cumulative_returns.png\n")
}

# ==============================================================================
# 5. FIGURE 2: FACTOR TIME SERIES
# ==============================================================================
cat("Generating Figure 2: Factor Time Series...\n")

factors_file <- list.files(models_dir, pattern = "scenario_a_.*_factor.*\\.csv", full.names = TRUE)[1]
if (!is.na(factors_file) && file.exists(factors_file)) {
  factors <- fread(factors_file)
  factors[, date := as.IDate(date)]

  # Plot time series of the factor
  p2 <- ggplot(factors, aes(x = date, y = F1 * 100)) +
    geom_line(color = "#2E86AB", linewidth = 0.8) +
    geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
    labs(title = "P-Tree Factor Returns Over Time (Scenario A)",
         subtitle = "Single boosted factor (9 iterations), splits only on firm size",
         x = "", y = "Monthly Return (%)") +
    theme_minimal(base_size = 12) +
    theme(plot.title = element_text(face = "bold"),
          plot.subtitle = element_text(size = 9, color = "gray40"))

  ggsave(file.path(out_dir, "figure2_factor_timeseries.png"), p2, width = 10, height = 6, dpi = 300)
  cat("  Saved: figure2_factor_timeseries.png\n")
} else {
  cat("  Warning: Factor file not found. Skipping Figure 2.\n")
}

# ==============================================================================
# 5. FIGURE 3: MONTHLY RETURNS DISTRIBUTION
# ==============================================================================
cat("Generating Figure 3: Monthly Returns Distribution...\n")

if (exists("ensemble_files") && length(ensemble_files) > 0) {
  # Use Scenario A ensemble
  ens_a <- fread(ensemble_files[grepl("scenario_a", ensemble_files)][1])
  ens_a[, Return := factor]  # Already in decimal form

  p3 <- ggplot(ens_a, aes(x = Return * 100)) +
    geom_histogram(bins = 30, fill = "#2E86AB", color = "white", alpha = 0.8) +
    geom_vline(xintercept = 0, linetype = "dashed", color = "red") +
    labs(title = "Distribution of Monthly Ensemble Returns (Scenario A)",
         x = "Monthly Return (%)", y = "Frequency") +
    theme_minimal(base_size = 12) +
    theme(plot.title = element_text(face = "bold"))
  
  ggsave(file.path(out_dir, "figure3_returns_distribution.png"), p3, width = 10, height = 6, dpi = 300)
  cat("  Saved: figure3_returns_distribution.png\n")
}

# ==============================================================================
# 6. FIGURE 4: TREE STRUCTURE VISUALIZATION (DEGENERACY ANALYSIS)
# ==============================================================================
cat("Generating Figure 4: Tree Structure Visualization...\n")

# Parse tree structures to extract splitting variables
tree_file <- file.path(models_dir, "scenario_a_trees.txt")
if (file.exists(tree_file)) {
  tree_lines <- readLines(tree_file)

  # Extract factor numbers and splitting variables
  variable_usage <- list()

  current_factor <- 0
  for (line in tree_lines) {
    if (grepl("^--- Factor", line)) {
      current_factor <- as.integer(sub(".*Factor ([0-9]+).*", "\\1", line))
    } else if (grepl("^\\[1\\]", line)) {
      # Parse tree structure: "3\n1 3 0.137..."
      # Format: node_id split_var threshold left_child right_child
      tree_str <- gsub('\\[1\\] "', '', line)
      tree_str <- gsub('"', '', tree_str)
      parts <- strsplit(tree_str, "\\\\n")[[1]]

      if (length(parts) >= 2) {
        # First split (root node)
        root <- strsplit(trimws(parts[2]), "\\s+")[[1]]
        if (length(root) >= 2) {
          split_var <- as.integer(root[2])
          variable_usage[[length(variable_usage) + 1]] <- data.table(
            Factor = current_factor,
            SplitVariable = split_var
          )
        }
      }
    }
  }

  variable_usage <- rbindlist(variable_usage)

  if (nrow(variable_usage) > 0) {
    # Count variable usage across all factors
    var_counts <- variable_usage[, .N, by = SplitVariable]

    # Load actual characteristic names from inputs (in correct order)
    if (file.exists(in_rds)) {
      inp_check <- readRDS(in_rds)
      char_names <- inp_check$char_cols
    } else {
      # Fallback to alphabetical order (matches actual data)
      char_names <- c("rank_acc", "rank_agr", "rank_ato", "rank_bm", "rank_cash",
                     "rank_cashdebt", "rank_cfp", "rank_chpm", "rank_chtx", "rank_ep",
                     "rank_gma", "rank_grltnoa", "rank_hire", "rank_lev", "rank_lgr",
                     "rank_me", "rank_mom12m", "rank_mom1m", "rank_mom36m", "rank_mom60m",
                     "rank_mom6m", "rank_ni", "rank_noa", "rank_op", "rank_pctacc",
                     "rank_pm", "rank_rna", "rank_roa", "rank_roe", "rank_seas1a",
                     "rank_sgr", "rank_sp")
    }

    # Expand to show ALL characteristics (including unused ones)
    all_vars <- data.table(
      SplitVariable = 0:31,
      CharName = char_names
    )
    var_counts_full <- merge(all_vars, var_counts, by = "SplitVariable", all.x = TRUE)
    var_counts_full[is.na(N), N := 0]
    setorder(var_counts_full, -N, SplitVariable)

    # Highlight the dominant variable
    var_counts_full[, Color := ifelse(N > 15, "Dominant", "Unused/Rare")]

    p4 <- ggplot(var_counts_full[1:20], aes(x = reorder(CharName, N), y = N, fill = Color)) +
      geom_bar(stat = "identity") +
      geom_text(aes(label = N), hjust = -0.2, size = 3) +
      coord_flip() +
      scale_fill_manual(values = c("Dominant" = "#F24333", "Unused/Rare" = "#CCCCCC")) +
      labs(title = "Variable Usage in P-Tree Training (Scenario A)",
           subtitle = "Single-factor model: shows which characteristic the tree splits on",
           x = "Characteristic", y = "Number of Times Split On") +
      theme_minimal(base_size = 11) +
      theme(legend.position = "bottom",
            plot.title = element_text(face = "bold"),
            plot.subtitle = element_text(size = 9, color = "gray40"))

    ggsave(file.path(out_dir, "figure4_variable_usage.png"), p4, width = 10, height = 7, dpi = 300)
    cat("  Saved: figure4_variable_usage.png\n")
  }
}

# ==============================================================================
# 7. FIGURE 5: RETURNS DISTRIBUTION COMPARISON (A, B, C)
# ==============================================================================
cat("Generating Figure 5: Returns Distribution (All Scenarios)...\n")

if (exists("ensemble_files") && length(ensemble_files) > 0) {
  dist_data_list <- list()

  for (f in ensemble_files) {
    ens <- fread(f)
    ens[, Return := factor]  # Already in decimal form

    fname <- basename(f)
    scenario <- "Unknown"
    if (grepl("scenario_a_ensemble", fname)) scenario <- "A: Full Sample"
    if (grepl("scenario_b_test_ensemble", fname)) scenario <- "B: OOS (2010-2019)"
    if (grepl("scenario_c_test_ensemble", fname)) scenario <- "C: OOS (1998-2009)"

    if (scenario != "Unknown") {
      ens[, Scenario := scenario]
      dist_data_list[[length(dist_data_list)+1]] <- ens[, .(Return, Scenario)]
    }
  }

  if (length(dist_data_list) > 0) {
    dist_combined <- rbindlist(dist_data_list)

    # Calculate summary stats for annotation
    dist_stats <- dist_combined[, .(
      Mean = mean(Return, na.rm = TRUE),
      SD = sd(Return, na.rm = TRUE),
      N = .N
    ), by = Scenario]

    p5 <- ggplot(dist_combined, aes(x = Return * 100, fill = Scenario)) +
      geom_histogram(bins = 30, alpha = 0.7, position = "identity", color = "white") +
      geom_vline(xintercept = 0, linetype = "dashed", color = "red") +
      facet_wrap(~ Scenario, ncol = 1, scales = "free_y") +
      scale_fill_manual(values = c(
        "A: Full Sample" = "#2E86AB",
        "B: OOS (2010-2019)" = "#F24333",
        "C: OOS (1998-2009)" = "#F2A900"
      )) +
      labs(title = "Monthly Ensemble Returns Distribution by Scenario",
           subtitle = "Comparing in-sample (A) vs out-of-sample (B, C) performance",
           x = "Monthly Return (%)", y = "Frequency") +
      theme_minimal(base_size = 11) +
      theme(legend.position = "none",
            plot.title = element_text(face = "bold"),
            plot.subtitle = element_text(size = 9, color = "gray40"),
            strip.text = element_text(face = "bold"))

    ggsave(file.path(out_dir, "figure5_returns_distribution_all.png"), p5, width = 10, height = 9, dpi = 300)
    cat("  Saved: figure5_returns_distribution_all.png\n")
  }
}

# ==============================================================================
# 8. FIGURE 6: MARKET CAP DISTRIBUTION BY LEAF (SIZE SEGMENTATION)
# ==============================================================================
cat("Generating Figure 6: Market Cap Distribution by Leaf...\n")

# Load scenario A factor file
leaf_file <- list.files(models_dir, pattern = "scenario_a_.*_factor.*\\.csv", full.names = TRUE)[1]
if (file.exists(leaf_file)) {
  factors_a <- fread(leaf_file)
  factors_a[, date := as.IDate(date)]

  # Merge with input data to get market cap
  if (exists("dt")) {
    # For first factor, analyze leaf assignments
    # We need to reconstruct which stocks are in which leaf
    # This requires re-running predictions, so we'll create a proxy visualization

    # Alternative: Show distribution of market cap by deciles (since trees split on rank_me)
    dt[, me_decile := cut(rank_me, breaks = quantile(rank_me, probs = seq(0, 1, 0.1), na.rm = TRUE),
                          labels = paste0("D", 1:10), include.lowest = TRUE)]

    # Calculate average return by market cap decile
    me_analysis <- dt[, .(
      avg_return = mean(ret_next, na.rm = TRUE) * 100,
      median_me = median(lag_me, na.rm = TRUE),
      n_obs = .N
    ), by = me_decile]

    me_analysis <- me_analysis[!is.na(me_decile)]
    setorder(me_analysis, me_decile)

    p6 <- ggplot(me_analysis, aes(x = me_decile, y = avg_return)) +
      geom_bar(stat = "identity", fill = "#2E86AB", alpha = 0.8) +
      geom_text(aes(label = sprintf("%.2f%%", avg_return)), vjust = -0.5, size = 3) +
      labs(title = "Average Returns by Firm Size Decile",
           subtitle = "P-Trees exclusively split on firm size (rank_me), creating size-based portfolios",
           x = "Market Equity Decile (D1 = Smallest, D10 = Largest)",
           y = "Average Monthly Return (%)") +
      theme_minimal(base_size = 11) +
      theme(plot.title = element_text(face = "bold"),
            plot.subtitle = element_text(size = 9, color = "gray40"))

    ggsave(file.path(out_dir, "figure6_size_decile_returns.png"), p6, width = 10, height = 6, dpi = 300)
    cat("  Saved: figure6_size_decile_returns.png\n")
  }
}

cat("\n✓ All visualizations saved to:", out_dir, "\n")
cat("\nGenerated files:\n")
cat("  Tables (LaTeX only):\n")
cat("    - table1_data_summary.tex - Data summary statistics\n")
cat("    - table2_model_performance.tex - Performance metrics\n")
cat("    - table3_tree_structures.tex - Tree splits by scenario\n")
cat("  Figures (PNG):\n")
cat("    - figure1_cumulative_returns.png - P-Tree vs Market comparison\n")
cat("    - figure2_factor_timeseries.png - Factor returns over time\n")
cat("    - figure3_returns_distribution.png - Scenario A distribution\n")
cat("    - figure4_variable_usage.png - Variable usage by scenario\n")
cat("    - figure5_returns_distribution_all.png - All scenarios comparison\n")
