#!/usr/bin/env Rscript

# A3: Comprehensive P-Tree Results Visualization
# -----------------------------------------------
# Creates extensive visualizations and tables for P-Tree analysis results

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(gridExtra)
  library(knitr)
  library(DiagrammeR)
  library(DiagrammeRsvg)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

# Paths
in_rds <- file.path(repo_root, "results", "analysis", "inputs", "ptree_inputs.rds")
models_dir <- file.path(repo_root, "results", "analysis", "models")
viz_dir <- file.path(repo_root, "results", "analysis", "visualizations")
dir.create(viz_dir, recursive = TRUE, showWarnings = FALSE)
eval_dir <- file.path(repo_root, "results", "analysis", "evaluation")


cat("\n╔═══════════════════════════════════════════════╗\n")
cat("║  P-TREE RESULTS VISUALIZATION & ANALYSIS      ║\n")
cat("╚═══════════════════════════════════════════════╝\n\n")

# Load data
cat("Loading data...\n")
inp <- readRDS(in_rds)
factor_dt <- fread(file.path(models_dir, "ptree_factor.csv"))
summary_dt <- fread(file.path(models_dir, "ptree_summary.csv"))
summary_dt <- fread(file.path(models_dir, "ptree_summary.csv"))
tree_txt <- readLines(file.path(models_dir, "ptree_tree.txt"))
leaf_ids <- fread(file.path(models_dir, "ptree_leaf_ids.csv"))
leaf_ports <- fread(file.path(models_dir, "ptree_leaf_portfolios.csv"))

dt <- inp$dt
X <- inp$X

# ============================================================================
# 1. FACTOR PERFORMANCE VISUALIZATIONS
# ============================================================================

cat("\n[1/8] Creating factor performance plots...\n")

# 1.1 Cumulative Returns
factor_dt[, cum_return := cumprod(1 + factor/100)]
factor_dt[, year := as.integer(format(as.Date(date), "%Y"))]

p1 <- ggplot(factor_dt, aes(x = as.Date(date), y = cum_return)) +
  geom_line(color = "steelblue", linewidth = 1) +
  geom_hline(yintercept = 1, linetype = "dashed", color = "gray50") +
  scale_y_log10() +
  labs(title = "P-Tree Factor: Cumulative Returns (Log Scale)",
       subtitle = sprintf("Sharpe: %.2f | Annual Return: %.1f%%",
                         summary_dt[metric == "sharpe_annual"]$value,
                         summary_dt[metric == "annualized_return"]$value),
       x = "Date", y = "Cumulative Return (log scale)") +
  theme_minimal() +
  theme(plot.title = element_text(face = "bold", size = 14))

ggsave(file.path(viz_dir, "1_cumulative_returns.png"), p1, width = 10, height = 6, dpi = 300)

# 1.2 Monthly Returns Distribution
p2 <- ggplot(factor_dt, aes(x = factor)) +
  geom_histogram(bins = 30, fill = "steelblue", alpha = 0.7, color = "white") +
  geom_vline(xintercept = 0, linetype = "dashed", color = "red") +
  geom_vline(xintercept = mean(factor_dt$factor), linetype = "dashed", color = "darkgreen") +
  labs(title = "P-Tree Factor: Monthly Returns Distribution",
       subtitle = sprintf("Mean: %.2f%% | Std: %.2f%%",
                         mean(factor_dt$factor), sd(factor_dt$factor)),
       x = "Monthly Return (%)", y = "Count") +
  theme_minimal() +
  theme(plot.title = element_text(face = "bold", size = 14))

ggsave(file.path(viz_dir, "2_returns_distribution.png"), p2, width = 10, height = 6, dpi = 300)

# 1.3 Rolling Sharpe Ratio (12-month window)
factor_dt[, rolling_mean := frollmean(factor, 12, align = "right")]
factor_dt[, rolling_sd := frollapply(factor, 12, sd, align = "right")]
factor_dt[, rolling_sharpe := (rolling_mean / rolling_sd) * sqrt(12)]

p3 <- ggplot(factor_dt[!is.na(rolling_sharpe)], aes(x = as.Date(date), y = rolling_sharpe)) +
  geom_line(color = "steelblue", linewidth = 0.8) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
  geom_hline(yintercept = summary_dt[metric == "sharpe_annual"]$value,
             linetype = "dashed", color = "darkgreen", linewidth = 1) +
  labs(title = "P-Tree Factor: Rolling 12-Month Sharpe Ratio",
       subtitle = "Green line = Full-sample Sharpe",
       x = "Date", y = "Sharpe Ratio (12-month rolling)") +
  theme_minimal() +
  theme(plot.title = element_text(face = "bold", size = 14))

ggsave(file.path(viz_dir, "3_rolling_sharpe.png"), p3, width = 10, height = 6, dpi = 300)

# 1.4 Annual Returns Bar Chart
annual_stats <- factor_dt[, .(
  annual_return = (prod(1 + factor/100) - 1) * 100,
  n_months = .N
), by = year]

p4 <- ggplot(annual_stats, aes(x = year, y = annual_return, fill = annual_return > 0)) +
  geom_col() +
  geom_hline(yintercept = 0, color = "black") +
  scale_fill_manual(values = c("TRUE" = "darkgreen", "FALSE" = "red"), guide = "none") +
  labs(title = "P-Tree Factor: Annual Returns",
       subtitle = sprintf("Win Rate: %d/%d years (%.1f%%)",
                         sum(annual_stats$annual_return > 0),
                         nrow(annual_stats),
                         100 * mean(annual_stats$annual_return > 0)),
       x = "Year", y = "Annual Return (%)") +
  theme_minimal() +
  theme(plot.title = element_text(face = "bold", size = 14))

# ============================================================================
# 2. TREE STRUCTURE VISUALIZATION
# ============================================================================

cat("[2/8] Creating tree structure visualization...\n")

# Parse tree structure
num_nodes <- as.integer(tree_txt[1])
node_data <- lapply(2:(num_nodes + 1), function(i) {
  parts <- strsplit(trimws(tree_txt[i]), "\\s+")[[1]]
  if (length(parts) >= 3) {
    data.table(
      node_id = as.integer(parts[1]),
      split_var = as.integer(parts[2]),
      split_val = as.numeric(parts[3])
    )
  } else {
    NULL
  }
})
tree_dt <- rbindlist(node_data)

# Infer children (Binary Heap Structure)
tree_dt[, left_child := node_id * 2]
tree_dt[, right_child := node_id * 2 + 1]

# Add characteristic names
tree_dt[split_var > 0, char_name := colnames(X)[split_var + 1]]
tree_dt[split_var == 0, char_name := "LEAF"]
tree_dt[, is_leaf := split_var == 0]

# Count usage of each characteristic
char_usage <- tree_dt[is_leaf == FALSE, .N, by = char_name][order(-N)]

p5 <- ggplot(char_usage, aes(x = reorder(char_name, N), y = N)) +
  geom_col(fill = "steelblue") +
  coord_flip() +
  labs(title = "P-Tree: Characteristic Usage in Tree Splits",
       subtitle = sprintf("%d characteristics used out of %d available",
                         nrow(char_usage), ncol(X)),
       x = "Characteristic", y = "Number of Splits") +
  theme_minimal() +
  theme(plot.title = element_text(face = "bold", size = 14))

ggsave(file.path(viz_dir, "5_characteristic_usage.png"), p5, width = 10, height = 6, dpi = 300)

# ============================================================================
# 3. CHARACTERISTIC IMPORTANCE ANALYSIS
# ============================================================================

cat("[3/8] Analyzing characteristic importance...\n")

# Correlation with returns
char_cors <- sapply(1:ncol(X), function(i) {
  cor(X[, i], inp$R, use = "complete.obs")
})

importance_dt <- data.table(
  characteristic = colnames(X),
  correlation = char_cors,
  abs_correlation = abs(char_cors),
  in_tree = colnames(X) %in% char_usage$char_name
)
setorder(importance_dt, -abs_correlation)

p6 <- ggplot(importance_dt[1:20], aes(x = reorder(characteristic, abs_correlation),
                                       y = correlation,
                                       fill = in_tree)) +
  geom_col() +
  coord_flip() +
  scale_fill_manual(values = c("TRUE" = "darkgreen", "FALSE" = "steelblue"),
                    name = "Used in Tree") +
  labs(title = "Top 20 Characteristics by Correlation with Returns",
       subtitle = "Green = Selected by P-Tree model",
       x = "Characteristic", y = "Correlation with Returns") +
  theme_minimal() +
  theme(plot.title = element_text(face = "bold", size = 14))

ggsave(file.path(viz_dir, "6_characteristic_importance.png"), p6, width = 10, height = 8, dpi = 300)

cat("[5/8] Creating statistics tables...\n")

# Performance statistics
perf_stats <- data.table(
  Metric = c("Mean Monthly Return", "Std Monthly Return", "Sharpe Ratio (Annual)",
             "Annualized Return", "Annualized Volatility", "Max Drawdown",
             "Win Rate (months)", "Best Month", "Worst Month",
             "Skewness", "Kurtosis"),
  Value = c(
    sprintf("%.2f%%", mean(factor_dt$factor)),
    sprintf("%.2f%%", sd(factor_dt$factor)),
    sprintf("%.2f", summary_dt[metric == "sharpe_annual"]$value),
    sprintf("%.2f%%", summary_dt[metric == "annualized_return"]$value),
    sprintf("%.2f%%", summary_dt[metric == "annualized_vol"]$value),
    sprintf("%.2f%%", min(factor_dt$drawdown)),
    sprintf("%.1f%%", 100 * mean(factor_dt$factor > 0)),
    sprintf("%.2f%%", max(factor_dt$factor)),
    sprintf("%.2f%%", min(factor_dt$factor)),
    sprintf("%.2f", e1071::skewness(factor_dt$factor)),
    sprintf("%.2f", e1071::kurtosis(factor_dt$factor))
  )
)

fwrite(perf_stats, file.path(viz_dir, "performance_statistics.csv"))

# Data coverage statistics
data_stats <- data.table(
  Metric = c("Time Period", "Number of Months", "Number of Stocks",
             "Total Observations", "Avg Stocks/Month",
             "Characteristics Available", "Characteristics Used in Tree"),
  Value = c(
    sprintf("%s to %s", min(factor_dt$date), max(factor_dt$date)),
    sprintf("%d", inp$num_months),
    sprintf("%d", inp$num_stocks),
    sprintf("%d", nrow(dt)),
    sprintf("%.1f", nrow(dt) / inp$num_months),
    sprintf("%d", ncol(X)),
    sprintf("%d", nrow(char_usage))
  )
)

fwrite(data_stats, file.path(viz_dir, "data_statistics.csv"))

# ============================================================================
# 6. CALENDAR HEATMAP
# ============================================================================

cat("[6/8] Creating calendar heatmap...\n")

factor_dt[, year_month := format(as.Date(date), "%Y-%m")]
factor_dt[, month := as.integer(format(as.Date(date), "%m"))]

# Monthly heatmap
p8 <- ggplot(factor_dt, aes(x = month, y = year, fill = factor)) +
  geom_tile(color = "white") +
  scale_fill_gradient2(low = "red", mid = "white", high = "darkgreen",
                       midpoint = 0, name = "Return (%)") +
  scale_x_continuous(breaks = 1:12, labels = month.abb) +
  labs(title = "P-Tree Factor: Monthly Returns Heatmap",
       x = "Month", y = "Year") +
  theme_minimal() +
  theme(plot.title = element_text(face = "bold", size = 14))

ggsave(file.path(viz_dir, "8_calendar_heatmap.png"), p8, width = 12, height = 8, dpi = 300)

# ============================================================================
# 7. CHARACTERISTIC DISTRIBUTIONS
# ============================================================================

cat("[7/8] Creating characteristic distribution plots (SKIPPED per user request)...\n")

# used_chars <- char_usage$char_name
# if (length(used_chars) > 0) {
#   ... (code commented out for speed) ...
# }

# ============================================================================
# 8. BENCHMARK & ROBUSTNESS VISUALIZATION
# ============================================================================

cat("[8/9] Visualizing benchmarks and robustness...\n")

# Load Benchmarks
bench_files <- list.files(file.path(eval_dir, "benchmarks"), pattern = "_alphas.csv", full.names = TRUE)
bench_dt <- rbindlist(lapply(bench_files, fread), fill = TRUE)

# Load Robustness
robust_ew_vw <- fread(file.path(eval_dir, "robustness", "robust_ew_vs_vw.csv"))
robust_start <- fread(file.path(eval_dir, "robustness", "robust_start_date.csv"))
robust_param <- fread(file.path(eval_dir, "robustness", "robust_param_sweep.csv"))

# Plot Robustness: Parameter Sweep
p10 <- ggplot(robust_param, aes(x = as.factor(min_leaf_size), y = sharpe_annual, fill = as.factor(num_iter))) +
  geom_col(position = "dodge") +
  labs(title = "Robustness: Parameter Sensitivity",
       subtitle = "Sharpe Ratio by Tree Depth and Leaf Size",
       x = "Min Leaf Size", y = "Annualized Sharpe Ratio", fill = "Num Iterations") +
  theme_minimal()

ggsave(file.path(viz_dir, "10_robustness_sweep.png"), p10, width = 8, height = 6, dpi = 300)

# ============================================================================
# 10. DECISION TREE DIAGRAM (DiagrammeR/Graphviz)
# ============================================================================

cat("[10/10] Creating decision tree diagram...\n")

# Calculate leaf statistics
leaf_stats <- data.table(leaf_number = 1:(ncol(leaf_ports)-1))
leaf_stats[, mean_ret := sapply(leaf_number, function(i) mean(leaf_ports[[paste0("leaf_", i)]], na.rm=TRUE))]
leaf_stats <- merge(leaf_stats, leaf_ids, by="leaf_number")

# Build Graphviz DOT string
dot_lines <- c("digraph PTree {")
dot_lines <- c(dot_lines, "  rankdir=TB;")
dot_lines <- c(dot_lines, "  node [fontname=\"Arial\"];")
dot_lines <- c(dot_lines, "  edge [fontname=\"Arial\", fontsize=10];")
dot_lines <- c(dot_lines, "")

# Assign sequential node numbers (N1, N2, etc.) in tree order
tree_dt[, node_num := paste0("N", 1:.N)]

for(i in 1:nrow(tree_dt)) {
  nid <- tree_dt$node_id[i]
  node_num <- tree_dt$node_num[i]
  
  if(tree_dt$is_leaf[i]) {
    # Leaf node - show portfolio number
    leaf_num <- leaf_stats[node_id == nid]$leaf_number
    port_label <- if(length(leaf_num)>0) sprintf("#%d", leaf_num) else "#?"
    
    dot_lines <- c(dot_lines, sprintf(
      "  n%d [label=\"%s\\n%s\", shape=box, style=filled, fillcolor=\"white\", fontsize=10];",
      nid, node_num, port_label
    ))
  } else {
    # Split node - show characteristic and condition
    char_label <- toupper(gsub("rank_", "", tree_dt$char_name[i]))
    split_cond <- sprintf("%s ≤ %.1f", char_label, tree_dt$split_val[i])
    
    dot_lines <- c(dot_lines, sprintf(
      "  n%d [label=\"%s\\n%s\", shape=box, style=filled, fillcolor=\"white\", fontsize=10];",
      nid, node_num, split_cond
    ))
    
    # Add edges with Y/N labels
    if(tree_dt$left_child[i] %in% tree_dt$node_id) {
      dot_lines <- c(dot_lines, sprintf(
        "  n%d -> n%d [label=\"Y\", fontsize=10];",
        nid, tree_dt$left_child[i]
      ))
    }
    if(tree_dt$right_child[i] %in% tree_dt$node_id) {
      dot_lines <- c(dot_lines, sprintf(
        "  n%d -> n%d [label=\"N\", fontsize=10];",
        nid, tree_dt$right_child[i]
      ))
    }
  }
}

dot_lines <- c(dot_lines, "}")
dot_string <- paste(dot_lines, collapse="\n")

# Generate diagram
grViz(dot_string) %>%
  DiagrammeRsvg::export_svg() %>%
  charToRaw() %>%
  rsvg::rsvg_png(file.path(viz_dir, "11_tree_diagram.png"), width = 1600, height = 1200)

cat("[11/11] Creating comprehensive metrics table...\n")

# Combine Factor Stats + Regression Metrics
metrics_final <- data.table(Metric = character(), Value = character())

# 1. Factor Stats
metrics_final <- rbind(metrics_final, 
  data.table(Metric = "--- Factor Performance ---", Value = ""),
  data.table(Metric = "Annualized Return", Value = sprintf("%.2f%%", summary_dt[metric == "annualized_return"]$value)),
  data.table(Metric = "Annualized Volatility", Value = sprintf("%.2f%%", summary_dt[metric == "annualized_vol"]$value)),
  data.table(Metric = "Sharpe Ratio", Value = sprintf("%.2f", summary_dt[metric == "sharpe_annual"]$value)),
  data.table(Metric = "Max Drawdown", Value = sprintf("%.2f%%", min(factor_dt$drawdown))),
  data.table(Metric = "Skewness", Value = sprintf("%.2f", e1071::skewness(factor_dt$factor))),
  data.table(Metric = "Kurtosis", Value = sprintf("%.2f", e1071::kurtosis(factor_dt$factor)))
)

# 2. Regression Metrics (if available)
if (exists("bench_dt")) {
  # Assuming first row is the P-Tree factor
  bf <- bench_dt[factor == "factor"]
  if (nrow(bf) > 0) {
    metrics_final <- rbind(metrics_final,
      data.table(Metric = "--- Regression Alphas ---", Value = ""),
      data.table(Metric = "CAPM Alpha (Ann.)", Value = sprintf("%.2f%% (t=%.2f)", bf$capm_alpha_ann, bf$capm_t)),
      data.table(Metric = "FF3 Alpha (Ann.)", Value = sprintf("%.2f%% (t=%.2f)", bf$ff3_alpha_ann, bf$ff3_t)),
      data.table(Metric = "FF4 Alpha (Ann.)", Value = sprintf("%.2f%% (t=%.2f)", bf$ff4_alpha_ann, bf$ff4_t)),
      data.table(Metric = "--- Model Fit (R-Squared) ---", Value = ""),
      data.table(Metric = "CAPM Adj. R2", Value = sprintf("%.3f", bf$capm_r2)),
      data.table(Metric = "FF3 Adj. R2", Value = sprintf("%.3f", bf$ff3_r2)),
      data.table(Metric = "FF4 Adj. R2", Value = sprintf("%.3f", bf$ff4_r2))
    )
  }
}

fwrite(metrics_final, file.path(viz_dir, "comprehensive_metrics.csv"))


# ============================================================================
# 11. SUMMARY REPORT
# ============================================================================

cat("[11/11] Generating HTML summary report...\n")

html_report <- sprintf('
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>P-Tree Analysis Results - Swedish Stock Market</title>
<style>
body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }
.summary-box { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.metric { display: inline-block; margin: 10px 20px; }
.metric-label { font-size: 12px; color: #7f8c8d; text-transform: uppercase; }
.metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
.positive { color: #27ae60; }
.negative { color: #e74c3c; }
table { width: 100%%; border-collapse: collapse; background: white; margin: 20px 0; }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
th { background-color: #3498db; color: white; }
tr:hover { background-color: #f5f5f5; }
img { max-width: 100%%; height: auto; border-radius: 4px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.chart-container { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; }
</style>
</head>
<body>

<h1>P-Tree Analysis Results - Swedish Stock Market</h1>

<div class="summary-box">
<h2>Executive Summary</h2>
<div class="metric">
  <div class="metric-label">Sharpe Ratio</div>
  <div class="metric-value positive">%.2f</div>
</div>
<div class="metric">
  <div class="metric-label">Annual Return</div>
  <div class="metric-value positive">%.2f%%</div>
</div>
<div class="metric">
  <div class="metric-label">Annual Volatility</div>
  <div class="metric-value">%.2f%%</div>
</div>
<div class="metric">
  <div class="metric-label">Max Drawdown</div>
  <div class="metric-value negative">%.2f%%</div>
</div>
</div>

<h2>Performance Statistics</h2>
%s

<h2>Data Coverage</h2>
%s

<h2>Visual Analysis</h2>

<div class="chart-container">
<h3>Cumulative Returns</h3>
<img src="1_cumulative_returns.png" alt="Cumulative Returns">
</div>

<div class="chart-container">
<h3>Returns Distribution</h3>
<img src="2_returns_distribution.png" alt="Returns Distribution">
</div>

<div class="chart-container">
<h3>Rolling Sharpe Ratio</h3>
<img src="3_rolling_sharpe.png" alt="Rolling Sharpe">
</div>

<div class="chart-container">
<h3>Annual Returns</h3>
<img src="4_annual_returns.png" alt="Annual Returns">
</div>

<div class="chart-container">
<h3>Characteristic Usage</h3>
<img src="5_characteristic_usage.png" alt="Characteristic Usage">
</div>

<div class="chart-container">
<h3>Characteristic Importance</h3>
<img src="6_characteristic_importance.png" alt="Characteristic Importance">
</div>

<div class="chart-container">
<h3>Drawdown Analysis</h3>
<img src="7_drawdown.png" alt="Drawdown">
</div>

<div class="chart-container">
<h3>Calendar Heatmap</h3>
<img src="8_calendar_heatmap.png" alt="Calendar Heatmap">
</div>

<div class="chart-container">
<h3>Characteristic Distributions</h3>
<img src="9_characteristic_distributions.png" alt="Characteristic Distributions">
</div>

<h2>Tree Structure</h2>
<div class="summary-box">
<pre>%s</pre>
</div>

<h2>Model Configuration</h2>
<div class="summary-box">
<ul>
<li><strong>Boosting Iterations:</strong> 5</li>
<li><strong>Min Leaf Size:</strong> 3</li>
<li><strong>Max Depth:</strong> 8</li>
<li><strong>Num Cutpoints:</strong> 50</li>
<li><strong>Learning Rate (eta):</strong> 0.3</li>
<li><strong>Equal Weight:</strong> TRUE</li>
<li><strong>Regularization:</strong> None (lambda_cov = 0)</li>
</ul>
</div>

<p style="text-align: center; color: #7f8c8d; margin-top: 50px;">
Generated: %s
</p>

</body>
</html>
',
  summary_dt[metric == "sharpe_annual"]$value,
  summary_dt[metric == "annualized_return"]$value,
  summary_dt[metric == "annualized_vol"]$value,
  min(factor_dt$drawdown),
  knitr::kable(perf_stats, format = "html"),
  knitr::kable(data_stats, format = "html"),
  if (exists("metrics_final")) knitr::kable(metrics_final, format = "html", caption = "Comprehensive ML Metrics") else "",
  if (exists("bench_dt")) knitr::kable(bench_dt, format = "html", caption = "Benchmark Alphas") else "",
  if (exists("robust_ew_vw")) knitr::kable(robust_ew_vw, format = "html", caption = "Robustness: EW vs VW") else "",
  if (exists("p11")) '<div class="chart-container"><h3>Decision Tree Diagram</h3><img src="11_tree_diagram.png" alt="Tree Diagram"></div>' else "",
  paste(tree_txt, collapse = "\n"),
  format(Sys.time(), "%Y-%m-%d %H:%M:%S")
)

writeLines(html_report, file.path(viz_dir, "index.html"))

# ============================================================================
# FINAL SUMMARY
# ============================================================================

cat("\n╔═══════════════════════════════════════════════╗\n")
cat("║           VISUALIZATION COMPLETE              ║\n")
cat("╚═══════════════════════════════════════════════╝\n\n")

cat("Output directory:", normalizePath(viz_dir), "\n\n")
cat("Files generated:\n")
cat("  📄 comprehensive_metrics.csv\n")
cat("  📊 1_cumulative_returns.png\n")
cat("  📊 2_returns_distribution.png\n")
cat("  📊 11_tree_diagram.png\n")
cat("\nVisualization complete!\n\n")
