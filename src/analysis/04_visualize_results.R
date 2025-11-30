#!/usr/bin/env Rscript

# A4: Visualize Results (Consolidated)
# -------------------------------------
# Generates all key tables and figures for the thesis:
# 1. Table 1: Descriptive Statistics
# 2. Figure 1: Cumulative Returns (P-Tree vs Market)
# 3. Figure 2: Tree Structure (Human-Readable)
# 4. Figure 3: Variable Importance
# 5. Figure 4: Performance Comparison (Sharpe Ratios)

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

# Paths
in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")
models_dir <- file.path(repo_root, "results", "models")
eval_dir <- file.path(repo_root, "results", "evaluation")
out_dir <- file.path(repo_root, "results", "visualizations")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

cat("\n=== A4: VISUALIZE RESULTS (CONSOLIDATED) ===\n")
cat("Repo root:", repo_root, "\n\n")

if (!file.exists(in_rds)) stop("Inputs RDS not found. Run Step 1 first.")
inp <- readRDS(in_rds)
dt <- copy(inp$dt)

# ==============================================================================
# 1. TABLE 1: DESCRIPTIVE STATISTICS
# ==============================================================================
cat("Generating Table 1: Descriptive Statistics...\n")

key_chars <- c("rank_mom12m", "rank_bm", "rank_me", "rank_roa",
               "rank_svar", "rank_dolvol", "rank_turn", "rank_ill")

summary_stats <- data.table(
  Characteristic = key_chars,
  Mean = sapply(key_chars, function(c) mean(dt[[c]], na.rm=TRUE)),
  Median = sapply(key_chars, function(c) median(dt[[c]], na.rm=TRUE)),
  SD = sapply(key_chars, function(c) sd(dt[[c]], na.rm=TRUE)),
  Min = sapply(key_chars, function(c) min(dt[[c]], na.rm=TRUE)),
  Max = sapply(key_chars, function(c) max(dt[[c]], na.rm=TRUE)),
  `Coverage (%)` = sapply(key_chars, function(c) mean(!is.na(dt[[c]])) * 100)
)

fwrite(summary_stats, file.path(out_dir, "table1_descriptive_stats.csv"))
cat("  Saved: table1_descriptive_stats.csv\n")

# ==============================================================================
# 2. FIGURE 1: CUMULATIVE RETURNS
# ==============================================================================
cat("Generating Figure 1: Cumulative Returns...\n")

# Load Factor Returns
factor_a <- fread(file.path(models_dir, "scenario_a_factor.csv"))
factor_a[, date := as.IDate(date)]
factor_a[, Strategy := "P-Tree (Single)"]
factor_a[, Return := factor]

# Load Market Returns (from inputs)
market <- dt[, .(Return = mean(ret_next * 100, na.rm=TRUE)), by=date] # Simple EW Market
market[, Strategy := "Market (EW)"]

combined <- rbind(factor_a[, .(date, Strategy, Return)], market[, .(date, Strategy, Return)])
combined[, Cumulative := cumprod(1 + Return/100) - 1, by=Strategy]

p1 <- ggplot(combined, aes(x=date, y=Cumulative*100, color=Strategy)) +
  geom_line(linewidth=1) +
  geom_hline(yintercept=0, linetype="dashed", color="gray50") +
  scale_color_manual(values=c("P-Tree (Single)"="#2E86AB", "Market (EW)"="#A23B72")) +
  labs(
    title="Cumulative Returns: P-Tree vs Market",
    subtitle="Swedish Stock Market (1999-2019)",
    x="", y="Cumulative Return (%)",
    caption="P-Tree Factor (Long-Short) vs Equal-Weighted Market Portfolio"
  ) +
  theme_minimal(base_size=12) +
  theme(legend.position="bottom", plot.title=element_text(face="bold"))

ggsave(file.path(out_dir, "figure1_cumulative_returns.png"), p1, width=10, height=6, dpi=300)
cat("  Saved: figure1_cumulative_returns.png\n")

# ==============================================================================
# 3. FIGURE 2: TREE STRUCTURE (DECODED)
# ==============================================================================
cat("Generating Figure 2: Tree Structure...\n")

# Characteristic mapping
char_map <- setNames(inp$char_cols, as.character(0:(length(inp$char_cols)-1)))

# Simple parser
parse_tree_text <- function(tree_file) {
  lines <- readLines(tree_file)
  if (length(lines) < 2) return("Single Node Tree")
  
  desc <- c("Root Node")
  for (i in 2:length(lines)) {
    parts <- as.numeric(strsplit(trimws(lines[i]), "\\s+")[[1]])
    if (length(parts) < 5 || parts[2] == 0) next
    
    var_name <- char_map[as.character(parts[2])]
    threshold <- parts[3]
    desc <- c(desc, sprintf("|-- Split on %s (Threshold: %.2f)", var_name, threshold))
  }
  paste(desc, collapse="\n")
}

tree_text <- parse_tree_text(file.path(models_dir, "scenario_a_tree.txt"))
writeLines(tree_text, file.path(out_dir, "figure2_tree_structure.txt"))
cat("  Saved: figure2_tree_structure.txt\n")

# ==============================================================================
# 4. FIGURE 3: VARIABLE IMPORTANCE
# ==============================================================================
cat("Generating Figure 3: Variable Importance...\n")

# Count splits in Scenario A tree
tree_lines <- readLines(file.path(models_dir, "scenario_a_tree.txt"))
counts <- table(sapply(tree_lines[-1], function(x) {
  parts <- as.numeric(strsplit(trimws(x), "\\s+")[[1]])
  if (length(parts) >= 5 && parts[2] != 0) char_map[as.character(parts[2])] else NA
}))

importance <- data.table(Characteristic = names(counts), Count = as.numeric(counts))
importance <- importance[!is.na(Characteristic)]
setorder(importance, -Count)

if (nrow(importance) > 0) {
  p3 <- ggplot(importance, aes(x=reorder(Characteristic, Count), y=Count)) +
    geom_bar(stat="identity", fill="#2E86AB", width=0.6) +
    coord_flip() +
    labs(
      title="Variable Importance (Scenario A)",
      subtitle="Number of splits in the Single Tree model",
      x="", y="Split Count"
    ) +
    theme_minimal(base_size=12) +
    theme(plot.title=element_text(face="bold"))
  
  ggsave(file.path(out_dir, "figure3_variable_importance.png"), p3, width=8, height=6, dpi=300)
  cat("  Saved: figure3_variable_importance.png\n")
} else {
  cat("  Warning: No splits found for variable importance plot.\n")
}

# ==============================================================================
# 5. FIGURE 4: PERFORMANCE COMPARISON
# ==============================================================================
cat("Generating Figure 4: Performance Comparison...\n")

results <- fread(file.path(eval_dir, "table1_thesis_results.csv"))
results[, Type := ifelse(grepl("Test", Scenario), "Out-of-Sample", "In-Sample")]

p4 <- ggplot(results, aes(x=Scenario, y=`Sharpe Ratio`, fill=Type)) +
  geom_bar(stat="identity", width=0.6) +
  geom_hline(yintercept=0, color="black") +
  scale_fill_manual(values=c("In-Sample"="#2E86AB", "Out-of-Sample"="#A23B72")) +
  labs(
    title="Model Performance Across Scenarios",
    subtitle="Sharpe Ratio Comparison",
    x="", y="Sharpe Ratio"
  ) +
  theme_minimal(base_size=12) +
  theme(legend.position="bottom", plot.title=element_text(face="bold"))

ggsave(file.path(out_dir, "figure4_performance_comparison.png"), p4, width=8, height=6, dpi=300)
cat("  Saved: figure4_performance_comparison.png\n")

# ==============================================================================
# 6. FIGURE 5: CHARACTERISTIC CORRELATION HEATMAP
# ==============================================================================
cat("Generating Figure 5: Characteristic Correlation Heatmap...\n")

# Select numeric columns starting with "rank_"
char_cols <- grep("^rank_", names(dt), value=TRUE)
# Filter to key characteristics to avoid overcrowding
key_chars_ext <- unique(c(key_chars, "rank_op", "rank_inv", "rank_lev", "rank_mom1m", "rank_mom36m"))
key_chars_ext <- intersect(key_chars_ext, char_cols)

dt_corr <- dt[, ..key_chars_ext]
dt_corr <- dt_corr[complete.cases(dt_corr)]

if (nrow(dt_corr) > 0) {
  cor_matrix <- cor(dt_corr)
  cor_dt <- as.data.table(cor_matrix, keep.rownames = TRUE)
  cor_melt <- melt(cor_dt, id.vars = "rn", variable.name = "Var2", value.name = "value")
  setnames(cor_melt, "rn", "Var1")
  
  p5 <- ggplot(cor_melt, aes(Var1, Var2, fill=value)) +
    geom_tile() +
    scale_fill_gradient2(low="#A23B72", mid="white", high="#2E86AB", midpoint=0, limit=c(-1,1)) +
    theme_minimal(base_size=10) +
    theme(axis.text.x = element_text(angle=45, vjust=1, hjust=1),
          axis.title = element_blank(),
          plot.title = element_text(face="bold")) +
    labs(title="Characteristic Correlation Matrix")
  
  ggsave(file.path(out_dir, "figure5_correlation_heatmap.png"), p5, width=10, height=8, dpi=300)
  cat("  Saved: figure5_correlation_heatmap.png\n")
}

# ==============================================================================
# 7. TABLE 2: DETAILED VARIABLE COVERAGE
# ==============================================================================
cat("Generating Table 2: Detailed Variable Coverage...\n")

coverage_stats <- data.table(
  Characteristic = char_cols,
  `Coverage (%)` = sapply(char_cols, function(c) mean(!is.na(dt[[c]])) * 100),
  `Mean` = sapply(char_cols, function(c) mean(dt[[c]], na.rm=TRUE)),
  `SD` = sapply(char_cols, function(c) sd(dt[[c]], na.rm=TRUE))
)
setorder(coverage_stats, -`Coverage (%)`)

fwrite(coverage_stats, file.path(out_dir, "table2_variable_coverage.csv"))
cat("  Saved: table2_variable_coverage.csv\n")

# ==============================================================================
# 8. FIGURE 6: TIME PERIOD SPLIT DIAGRAM
# ==============================================================================
cat("Generating Figure 6: Time Period Split Diagram...\n")

# Define periods
periods <- data.table(
  Scenario = c("A: Full Sample", "A: Full Sample", 
               "B: Time-Split", "B: Time-Split", 
               "C: Reverse Split", "C: Reverse Split"),
  Type = c("Train", "Test (In-Sample)", 
           "Train", "Test (Out-of-Sample)", 
           "Test (Out-of-Sample)", "Train"),
  Start = as.Date(c("1999-06-01", "1999-06-01", 
                    "1999-06-01", "2010-01-01", 
                    "1999-06-01", "2010-01-01")),
  End = as.Date(c("2019-12-31", "2019-12-31", 
                  "2009-12-31", "2019-12-31", 
                  "2009-12-31", "2019-12-31"))
)

# Order scenarios for plotting
periods[, Scenario := factor(Scenario, levels=c("C: Reverse Split", "B: Time-Split", "A: Full Sample"))]

p6 <- ggplot(periods, aes(y=Scenario, x=Start, xend=End, color=Type)) +
  geom_segment(linewidth=6) +
  scale_color_manual(values=c("Train"="#2E86AB", "Test (Out-of-Sample)"="#A23B72", "Test (In-Sample)"="#6D9DC5")) +
  scale_x_date(date_breaks="2 years", date_labels="%Y") +
  labs(
    title="Data Splitting Scenarios",
    subtitle="Training and Testing Periods",
    x="", y=""
  ) +
  theme_minimal(base_size=12) +
  theme(legend.position="bottom", plot.title=element_text(face="bold"))

ggsave(file.path(out_dir, "figure6_time_splits.png"), p6, width=10, height=5, dpi=300)
cat("  Saved: figure6_time_splits.png\n")

cat("\nAll visualizations completed.\n")
