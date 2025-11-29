#!/usr/bin/env Rscript

# A3: Comprehensive P-Tree Results Visualization
# -----------------------------------------------
# Creates extensive visualizations and tables for P-Tree analysis results

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(gridExtra)
  library(knitr)
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

cat("\n╔═══════════════════════════════════════════════╗\n")
cat("║  P-TREE RESULTS VISUALIZATION & ANALYSIS      ║\n")
cat("╚═══════════════════════════════════════════════╝\n\n")

# Load data
cat("Loading data...\n")
inp <- readRDS(in_rds)
factor_dt <- fread(file.path(models_dir, "ptree_factor.csv"))
summary_dt <- fread(file.path(models_dir, "ptree_summary.csv"))
tree_txt <- readLines(file.path(models_dir, "ptree_tree.txt"))

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

ggsave(file.path(viz_dir, "4_annual_returns.png"), p4, width = 10, height = 6, dpi = 300)

# ============================================================================
# 2. TREE STRUCTURE VISUALIZATION
# ============================================================================

cat("[2/8] Creating tree structure visualization...\n")

# Parse tree structure
num_nodes <- as.integer(tree_txt[1])
node_data <- lapply(2:(num_nodes + 1), function(i) {
  parts <- strsplit(trimws(tree_txt[i]), "\\s+")[[1]]
  if (length(parts) >= 5) {
    data.table(
      node_id = as.integer(parts[1]),
      split_var = as.integer(parts[2]),
      split_val = as.numeric(parts[3]),
      left_child = as.integer(parts[4]),
      right_child = as.integer(parts[5])
    )
  } else {
    NULL
  }
})
tree_dt <- rbindlist(node_data)

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

# ============================================================================
# 4. DRAWDOWN ANALYSIS
# ============================================================================

cat("[4/8] Creating drawdown analysis...\n")

# Calculate drawdowns
factor_dt[, peak := cummax(cum_return)]
factor_dt[, drawdown := (cum_return / peak - 1) * 100]

p7 <- ggplot(factor_dt, aes(x = as.Date(date), y = drawdown)) +
  geom_area(fill = "red", alpha = 0.5) +
  geom_line(color = "darkred") +
  labs(title = "P-Tree Factor: Drawdown Over Time",
       subtitle = sprintf("Max Drawdown: %.1f%%", min(factor_dt$drawdown)),
       x = "Date", y = "Drawdown (%)") +
  theme_minimal() +
  theme(plot.title = element_text(face = "bold", size = 14))

ggsave(file.path(viz_dir, "7_drawdown.png"), p7, width = 10, height = 6, dpi = 300)

# ============================================================================
# 5. RETURN STATISTICS TABLE
# ============================================================================

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

cat("[7/8] Creating characteristic distribution plots...\n")

# Plot distributions of characteristics used in tree
used_chars <- char_usage$char_name
if (length(used_chars) > 0) {
  char_plots <- lapply(1:min(length(used_chars), 6), function(i) {
    char <- used_chars[i]
    char_idx <- which(colnames(X) == char)
    char_data <- data.table(value = X[, char_idx], return = inp$R)

    ggplot(char_data, aes(x = value, y = return)) +
      geom_hex(bins = 30) +
      geom_smooth(method = "loess", color = "red", se = FALSE) +
      scale_fill_gradient(low = "lightblue", high = "darkblue") +
      labs(title = char, x = "Characteristic Value", y = "Return (%)") +
      theme_minimal()
  })

  p9 <- do.call(grid.arrange, c(char_plots, ncol = 2))
  ggsave(file.path(viz_dir, "9_characteristic_distributions.png"), p9,
         width = 12, height = 9, dpi = 300)
}

# ============================================================================
# 8. SUMMARY REPORT
# ============================================================================

cat("[8/8] Generating HTML summary report...\n")

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
cat("  📊 1_cumulative_returns.png\n")
cat("  📊 2_returns_distribution.png\n")
cat("  📊 3_rolling_sharpe.png\n")
cat("  📊 4_annual_returns.png\n")
cat("  📊 5_characteristic_usage.png\n")
cat("  📊 6_characteristic_importance.png\n")
cat("  📊 7_drawdown.png\n")
cat("  📊 8_calendar_heatmap.png\n")
cat("  📊 9_characteristic_distributions.png\n")
cat("  📄 performance_statistics.csv\n")
cat("  📄 data_statistics.csv\n")
cat("  🌐 index.html (open in browser)\n\n")

cat("To view the HTML report:\n")
cat(sprintf("  open %s\n", file.path(viz_dir, "index.html")))
cat("\nVisualization complete!\n\n")
