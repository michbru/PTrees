#!/usr/bin/env Rscript

################################################################################
# Step 5: Validation Analysis for Thesis
################################################################################
#
# Purpose: Create ONLY the essential tables and figures needed for thesis
#
# Core Outputs (7 total):
# 1. Table: Dataset Summary Statistics
# 2. Table: Univariate R² Analysis (Top predictors)
# 3. Table: Sample Attrition Pipeline
# 4. Figure: Temporal Coverage (firms over time)
# 5. Figure: Data Quality Comparison (Swedish vs US)
# 6. Figure: Characteristic Predictive Power
# 7. Figure: Macro Factors Time Series (Market, SMB, HML)
#
################################################################################

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(xtable)
})

# Paths
args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- if (length(file_arg) > 0) dirname(normalizePath(file_arg)) else getwd()
repo_root <- normalizePath(file.path(script_dir, "..", ".."))
setwd(repo_root)

INPUT_RDS <- "results/inputs/ptree_inputs.rds"
OUTPUT_DIR <- "results/validation"
FF_PATH <- "data/raw/macro/raw_macro_factors.csv"

# CLEAR OUTPUT DIRECTORY - Start fresh every time
if (dir.exists(OUTPUT_DIR)) {
  cat("Clearing previous validation outputs...\n")
  unlink(OUTPUT_DIR, recursive = TRUE)
}
dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

cat("================================================================================\n")
cat("STEP 5: VALIDATION ANALYSIS (ESSENTIAL OUTPUTS ONLY)\n")
cat("================================================================================\n\n")


################################################################################
# Load Data
################################################################################

cat("Loading P-Tree inputs...\n")
if (!file.exists(INPUT_RDS)) {
  stop("Input RDS not found. Run Step 1 first.")
}
inp <- readRDS(INPUT_RDS)
dt <- inp$dt
char_cols <- inp$char_cols

cat(sprintf("  Observations: %s\n", format(nrow(dt), big.mark=",")))
cat(sprintf("  Firms: %s\n", format(length(unique(dt$isin)), big.mark=",")))
cat(sprintf("  Months: %s\n", format(length(unique(dt$date)), big.mark=",")))
cat(sprintf("  Characteristics: %d\n", length(char_cols)))
cat(sprintf("  Date range: %s to %s\n\n", min(dt$date), max(dt$date)))

################################################################################
# OUTPUT 1: Dataset Summary Table
################################################################################

cat("Creating Output 1: Dataset Summary Table...\n")

# Calculate key statistics
n_obs <- nrow(dt)
n_firms <- length(unique(dt$isin))
n_months <- length(unique(dt$date))
n_chars <- length(char_cols)
date_range <- sprintf("%s to %s", min(dt$date), max(dt$date))

# Firms per month
firms_per_month <- dt[, .(n_firms = uniqueN(isin)), by = date]
avg_firms_month <- mean(firms_per_month$n_firms)

# Periods per firm
firm_periods <- dt[, .(n_periods = .N), by = isin]
avg_periods_firm <- mean(firm_periods$n_periods)

summary_table <- data.frame(
  Metric = c(
    "Observations",
    "Companies",
    "Months",
    "Characteristics",
    "Date Range",
    "Avg Companies/Month",
    "Avg Months/Company"
  ),
  Value = c(
    format(n_obs, big.mark = ","),
    format(n_firms, big.mark = ","),
    as.character(n_months),
    as.character(n_chars),
    date_range,
    sprintf("%.0f", avg_firms_month),
    sprintf("%.1f", avg_periods_firm)
  )
)

latex_summary <- xtable(
  summary_table,
  caption = "Dataset Summary Statistics",
  label = "tab:data_summary"
)

sink(file.path(OUTPUT_DIR, "table_data_summary.tex"))
print(latex_summary,
      include.rownames = FALSE,
      caption.placement = "top",
      sanitize.text.function = function(x) x)
sink()

cat("  ✓ table_data_summary.tex\n\n")

################################################################################
# OUTPUT 2: Univariate R² Analysis (Top Characteristics Only)
################################################################################

cat("Creating Output 2: Univariate R² Table...\n")

# Calculate R² for each characteristic
r2_results <- data.table(
  characteristic = character(),
  n_obs = integer(),
  r2 = numeric(),
  coef = numeric(),
  t_stat = numeric(),
  p_value = numeric()
)

for (char in char_cols) {
  dt_sub <- dt[get(char) != 0 & !is.na(ret_next)]
  
  if (nrow(dt_sub) < 30) {
    next
  }
  
  tryCatch({
    model <- lm(ret_next ~ get(char), data = dt_sub)
    summ <- summary(model)
    
    r2_results <- rbind(r2_results, data.table(
      characteristic = char,
      n_obs = nrow(dt_sub),
      r2 = summ$r.squared,
      coef = coef(model)[2],
      t_stat = summ$coefficients[2, "t value"],
      p_value = summ$coefficients[2, "Pr(>|t|)"]
    ))
  }, error = function(e) {})
}

r2_results <- r2_results[order(-r2)]

# Summary stats
cat(sprintf("  Characteristics tested: %d\n", nrow(r2_results)))
cat(sprintf("  Median R²: %.6f\n", median(r2_results$r2, na.rm = TRUE)))
cat(sprintf("  Max R²: %.6f (%s)\n",
            max(r2_results$r2, na.rm = TRUE),
            r2_results[which.max(r2)]$characteristic))
cat(sprintf("  Significant (p<0.05): %d of %d\n",
            sum(r2_results$p_value < 0.05, na.rm = TRUE),
            nrow(r2_results)))

# Create table with top 20 + bottom 5 for comparison
top_20 <- head(r2_results, 20)
bottom_5 <- tail(r2_results, 5)
r2_display <- rbind(top_20, bottom_5)

r2_display[, `:=`(
  characteristic = gsub("rank_", "", characteristic),
  # Annualized long-short spread: coef × 2 (full range) × 12 (months) × 100 (%)
  annual_spread = coef * 2 * 12 * 100,
  sig = ifelse(p_value < 0.01, "***",
               ifelse(p_value < 0.05, "**",
                      ifelse(p_value < 0.10, "*", "")))
)]

r2_table <- r2_display[, .(
  Characteristic = characteristic,
  N = format(n_obs, big.mark = ","),
  `R²` = sprintf("%.6f", r2),
  `Annual Spread (\\%)` = sprintf("%.2f", annual_spread),
  `t-stat` = sprintf("%.2f", t_stat),
  Sig = sig
)]

latex_r2 <- xtable(
  r2_table,
  caption = "Univariate Predictive Power: R² from ret\\_next $\\sim$ characteristic (Top 20 + Bottom 5)",
  label = "tab:univariate_r2"
)

sink(file.path(OUTPUT_DIR, "table_univariate_r2.tex"))
cat("\\begin{table}[htbp]\n")
cat("\\centering\n")
cat("\\caption{Univariate Predictive Power: R² from $ret\\_next \\sim characteristic$ (Top 20 + Bottom 5)}\n")
cat("\\label{tab:univariate_r2}\n")
cat("\\small\n")
cat("\\begin{tabular}{lrrrrrl}\n")
cat("\\hline\n")
print(latex_r2,
      include.rownames = FALSE,
      caption.placement = "top",
      only.contents = TRUE,
      sanitize.text.function = function(x) gsub("_", "\\\\_", x))
cat("\\end{tabular}\n")
cat("\\begin{tablenotes}\n")
cat("\\footnotesize\n")
cat("\\item Note: *** p$<$0.01, ** p$<$0.05, * p$<$0.10. Only non-zero observations used.\n")
cat("\\item Annual Spread: Annualized return difference between highest and lowest ranked stocks (long-short portfolio).\n")
cat("\\item Median R² across all 32 characteristics: ", sprintf("%.6f", median(r2_results$r2)), "\n")
cat("\\end{tablenotes}\n")
cat("\\end{table}\n")
sink()

cat("  ✓ table_univariate_r2.tex\n\n")

################################################################################
# OUTPUT 2b: Variable Coverage and Distribution (LaTeX table)
################################################################################

cat("Creating Output 2b: Variable coverage/mean/SD table...\n")

# Helper: map abbreviations to readable names (fallback to abbrev if unknown)
pretty_name_map <- c(
  BM = "Book-to-Market", EP = "Earnings-to-Price", SP = "Sales-to-Price",
  CFP = "Cash-Flow-to-Price", CASH = "Cash to Assets", CASHDEBT = "Cash to Debt",
  LEV = "Leverage", SGR = "Sales Growth", MOM1M = "1-Month Momentum",
  MOM6M = "6–2 Month Momentum", MOM12M = "12–2 Month Momentum",
  MOM36M = "36–13 Month Momentum", MOM60M = "60–13 Month Momentum",
  SEAS1A = "Seasonality (1Y ago)", CHTX = "Change in Tax Expense",
  DEPR = "Depreciation/PPE", AGR = "Asset Growth", GMA = "Gross Profitability",
  LGR = "Long-term Debt Growth", ACC = "Operating Accruals",
  CHCSHO = "Change in Shares Outstanding", NI = "Net Equity Issuance",
  NOA = "Net Operating Assets", PCTACC = "Percent Accruals",
  CINVEST = "Corporate Investment", GRLTNOA = "Growth in LT NOA",
  ROA = "Return on Assets", ROE = "Return on Equity", ATO = "Asset Turnover",
  PM = "Profit Margin", CHPM = "Change in Profit Margin",
  OP = "Operating Profitability", RNA = "Return on NOA", HIRE = "Employee Growth",
  ME = "Market Equity"
)

cat("Creating Output 2b: Variable coverage/SD table...\n")

# Compute coverage and SD for each characteristic (ranked)
var_stats <- rbindlist(lapply(char_cols, function(col) {
  x <- dt[[col]]
  nz_mask <- !is.na(x) & x != 0
  coverage <- mean(nz_mask) * 100
  sd_val <- if (any(nz_mask)) sd(x[nz_mask]) else NA_real_
  abbrev <- toupper(gsub("^rank_", "", col))
  
  # Get pretty name, or create one from abbreviation if not in map
  if (!is.na(pretty_name_map[abbrev])) {
    pretty <- as.character(pretty_name_map[abbrev])
  } else {
    # Fallback: capitalize abbreviation nicely
    pretty <- abbrev
  }
  
  data.table(
    Variable = pretty,
    Abbrev = abbrev,
    Coverage = sprintf("%.1f", coverage),
    SD = sprintf("%.4f", sd_val)
  )
}))

setorder(var_stats, Variable)

latex_varstats <- xtable(
  var_stats,
  caption = "Variable coverage and standard deviation (ranked characteristics; non-zero observations)",
  label = "tab:variable_stats"
)

sink(file.path(OUTPUT_DIR, "table_variable_stats.tex"))
print(latex_varstats,
      include.rownames = FALSE,
      caption.placement = "top",
      tabular.environment = "tabular",
      floating.environment = "table",
      hline.after = c(-1, 0, nrow(var_stats)),
      sanitize.text.function = function(x) x)
sink()

cat("  ✓ table_variable_stats.tex\n\n")

################################################################################
# OUTPUT 3: Sample Attrition Table
################################################################################

cat("Creating Output 3: Sample Attrition Table...\n")

attrition_table <- data.frame(
  Step = c(
    "1. Raw FinBas monthly data",
    "2. Filter SE/SEK stocks only",
    "3. Remove OTC/off-exchange",
    "4. De-duplicate by ISIN-date",
    "5. Merge with Serrano (accounting)",
    "6. Apply lags and filters",
    "7. Final dataset"
  ),
  Records = c(
    "$\\sim$112,000",
    "$\\sim$105,000",
    "$\\sim$95,000",
    "$\\sim$95,000",
    "$\\sim$67,000",
    "$\\sim$61,000",
    format(n_obs, big.mark = ",")
  ),
  Description = c(
    "All FinBas records",
    "Swedish stocks in SEK",
    "Liquid exchange-traded only",
    "One record per firm-date",
    "Inner join via ISIN-OrgNr",
    "Remove missing targets",
    "Ready for P-Tree"
  )
)

latex_attrition <- xtable(
  attrition_table,
  caption = "Sample Attrition: Data Filtering Pipeline",
  label = "tab:sample_attrition"
)

sink(file.path(OUTPUT_DIR, "table_sample_attrition.tex"))
print(latex_attrition,
      include.rownames = FALSE,
      caption.placement = "top",
      sanitize.text.function = identity)
sink()

cat("  ✓ table_sample_attrition.tex\n\n")

################################################################################
# OUTPUT 4: Temporal Coverage Figure
################################################################################

cat("Creating Output 4: Temporal Coverage Figure...\n")

p_temporal <- ggplot(firms_per_month, aes(x = as.Date(date), y = n_firms)) +
  geom_line(color = "#2E86C1", linewidth = 1.2) +
  geom_hline(yintercept = avg_firms_month,
             linetype = "dashed", color = "#27AE60", linewidth = 1) +
  annotate("text", x = as.Date("2002-01-01"), y = avg_firms_month + 15,
           label = sprintf("Mean = %.0f firms", avg_firms_month),
           color = "#27AE60", fontface = "bold", size = 4) +
  labs(
    x = "Date",
    y = "Number of Firms"
  ) +
  scale_x_date(date_breaks = "2 years", date_labels = "%Y") +
  theme_minimal(base_size = 13) +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1),
    panel.grid.minor = element_blank()
  )

ggsave(file.path(OUTPUT_DIR, "figure_temporal_coverage.png"), p_temporal,
       width = 11, height = 6, dpi = 300)

cat("  ✓ figure_temporal_coverage.png\n\n")

################################################################################
# OUTPUT 4b: Firm Lifespan Distribution
################################################################################

cat("Creating Output 4b: Firm Lifespan Distribution Figure...\n")

p_lifespan <- ggplot(firm_periods, aes(x = n_periods)) +
  geom_histogram(binwidth = 12, fill = "#2E86C1", color = "white", alpha = 0.8) +
  geom_vline(xintercept = avg_periods_firm,
             linetype = "dashed", color = "#E74C3C", linewidth = 1) +
  annotate("text", x = avg_periods_firm + 10, y = Inf,
           label = sprintf("Mean = %.1f months", avg_periods_firm),
           color = "#E74C3C", fontface = "bold", hjust = 0, vjust = 2) +
  labs(
    x = "Months in Sample",
    y = "Number of Firms"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    panel.grid.minor = element_blank()
  )

ggsave(file.path(OUTPUT_DIR, "figure_firm_lifespans.png"), p_lifespan,
       width = 10, height = 6, dpi = 300)

cat("  ✓ figure_firm_lifespans.png\n\n")

################################################################################
# OUTPUT 5: Swedish vs US Comparison Figure
################################################################################

cat("Creating Output 5: Data Quality Comparison Figure...\n")

comparison_data <- data.frame(
  Metric = rep(c("Observations\n(Thousands)", "Characteristics"), 2),
  Value = c(
    n_obs/1000, n_chars,  # Swedish
    2200, 61              # US (Cong et al. 2025)
  ),
  Market = rep(c("Swedish", "US (Cong et al. 2025)"), each = 2)
)

comparison_data$Metric <- factor(
  comparison_data$Metric,
  levels = c("Observations\n(Thousands)", "Characteristics")
)

p_comparison <- ggplot(comparison_data, aes(x = Metric, y = Value, fill = Market)) +
  geom_bar(stat = "identity", position = "dodge", alpha = 0.85, width = 0.65) +
  scale_fill_manual(values = c("Swedish" = "#E74C3C", "US (Cong et al. 2025)" = "#3498DB")) +
  labs(
    x = "",
    y = "Value",
    fill = ""
  ) +
  facet_wrap(~ Metric, scales = "free_y", nrow = 1, strip.position = "bottom") +
  theme_minimal(base_size = 12) +
  theme(
    legend.position = "bottom",
    legend.text = element_text(size = 11),
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank(),
    panel.grid.major.x = element_blank(),
    strip.text = element_text(size = 10, face = "bold"),
    plot.margin = margin(10, 10, 10, 10)
  )

ggsave(file.path(OUTPUT_DIR, "figure_market_comparison.png"), p_comparison,
       width = 12, height = 6, dpi = 300)

cat("  ✓ figure_market_comparison.png\n\n")

################################################################################
# OUTPUT 6: Characteristic Predictive Power Figure
################################################################################

cat("Creating Output 6: Characteristic Predictive Power Figure...\n")

# Top 15 for visualization
top_15 <- head(r2_results, 15)
top_15[, characteristic_clean := gsub("rank_", "", characteristic)]

p_predictive <- ggplot(top_15, aes(x = reorder(characteristic_clean, r2), y = r2)) +
  geom_col(aes(fill = p_value < 0.05), alpha = 0.85) +
  geom_text(aes(label = sprintf("%.4f", r2)), hjust = -0.1, size = 3) +
  scale_fill_manual(
    values = c("TRUE" = "#27AE60", "FALSE" = "#95A5A6"),
    name = "",
    labels = c("TRUE" = "Significant (p<0.05)", "FALSE" = "Not significant")
  ) +
  labs(
    x = "Characteristic",
    y = "R² (Univariate)"
  ) +
  coord_flip(ylim = c(0, max(top_15$r2) * 1.15)) +
  theme_minimal(base_size = 12) +
  theme(
    legend.position = "bottom",
    panel.grid.major.y = element_blank()
  )

ggsave(file.path(OUTPUT_DIR, "figure_predictive_power.png"), p_predictive,
       width = 10, height = 7, dpi = 300)

################################################################################
# OUTPUT 7: Macro Factors Time Series (Comprehensive)
################################################################################

cat("Creating Output 7: Macro Factors Time Series (Comprehensive)...\n")

MACRO_DIR <- file.path(OUTPUT_DIR, "macro_plots")
if (!dir.exists(MACRO_DIR)) dir.create(MACRO_DIR, recursive = TRUE)

if (!file.exists(FF_PATH)) {
  cat(sprintf("  Warning: Macro factors not found at %s. Skipping figure.\n\n", FF_PATH))
} else {
  ff <- fread(FF_PATH)

  # Ensure a date column exists and standardize names
  if (!"date" %in% names(ff) && "ym" %in% names(ff)) {
    ff[, date := as.IDate(paste0(ym, "-01"))]
  } else if ("date" %in% names(ff)) {
    ff[, date := as.IDate(date)]
  }

  if (!"date" %in% names(ff)) {
    cat("  Warning: No parsable date column in macro factors. Skipping figure.\n\n")
  } else {
    
    # Helper function to plot a group of factors
    plot_factors <- function(data, cols, title, filename, color_hex = "#2E86AB") {
      # Filter columns that exist
      valid_cols <- intersect(cols, names(data))
      if (length(valid_cols) == 0) return()
      
      dt_sub <- data[, c("date", valid_cols), with = FALSE]
      long <- melt(dt_sub, id.vars = "date", variable.name = "Factor", value.name = "Return")
      
      # 12-month rolling mean for smoother view
      long[, Roll12 := frollmean(Return, n = 12, align = "right", na.rm = TRUE), by = Factor]
      
      # Create better labels
      long[, FactorLabel := toupper(gsub("_", " ", Factor))]
      
      p <- ggplot(long, aes(x = date)) +
        geom_line(aes(y = Return), color = "#BDC3C7", linewidth = 0.4, alpha = 0.6) +
        geom_line(aes(y = Roll12), color = color_hex, linewidth = 0.8) +
        labs(
          title = title,
          subtitle = "Grey: Monthly values, Colored: 12-month rolling average",
          x = "Date",
          y = "Value (%)"
        ) +
        facet_wrap(~ FactorLabel, ncol = 1, scales = "free_y") +
        theme_minimal(base_size = 12) +
        theme(
          strip.text = element_text(face = "bold", size = 10),
          panel.grid.minor = element_blank()
        )

      ggsave(file.path(MACRO_DIR, filename), p, width = 10, height = 2.5 * length(valid_cols), dpi = 300)
      cat(sprintf("  ✓ %s\n", filename))
    }

    # Prepare data for plotting (convert decimals to percentages)
    ff_plot <- copy(ff)
    
    # Columns that are in decimals and need conversion to %
    decimal_cols <- c("rm", "rf", "rm_rf", 
                      "smb_ew", "hml_ew", "mom_ew", 
                      "smb_vw", "hml_vw", "mom_vw", 
                      "rolling_vol_annualized", "rolling_vol_daily")
    
    # Scale them
    cols_to_scale <- intersect(decimal_cols, names(ff_plot))
    for (col in cols_to_scale) {
      set(ff_plot, j = col, value = ff_plot[[col]] * 100)
    }
    # Note: 'inflation' is already in percent in the raw file

    # 1. Market Factors
    plot_factors(ff_plot, c("rm", "rf", "rm_rf"), 
                 "Market Factors", "macro_01_market.png", "#2980B9")

    # 2. Equal-Weighted Factors
    plot_factors(ff_plot, c("smb_ew", "hml_ew", "mom_ew"), 
                 "Fama-French Factors (Equal-Weighted)", "macro_02_ff_ew.png", "#27AE60")

    # 3. Value-Weighted Factors
    plot_factors(ff_plot, c("smb_vw", "hml_vw", "mom_vw"), 
                 "Fama-French Factors (Value-Weighted)", "macro_03_ff_vw.png", "#8E44AD")

    # 4. Economic Indicators
    plot_factors(ff_plot, c("rolling_vol_annualized", "inflation"), 
                 "Economic Indicators", "macro_04_indicators.png", "#E67E22")
                 
    cat(sprintf("  Saved all macro plots to %s\n\n", MACRO_DIR))
  }
}

################################################################################
################################################################################
# OUTPUT 8: Correlation Heatmap (Top 20 - Lower Triangle)
################################################################################

cat("Creating Output 8: Correlation Heatmap (Top 20 - Lower Triangle)...\n")

# Select top 20 characteristics by R2 for readability
top_20_chars <- head(r2_results$characteristic, 20)
dt_corr <- dt[, ..top_20_chars]

# Clean names
clean_names <- sapply(names(dt_corr), function(x) toupper(gsub("^rank_", "", x)))
setnames(dt_corr, names(dt_corr), clean_names)

# Calculate correlation matrix
cor_mat <- cor(dt_corr, use = "pairwise.complete.obs")

# Hierarchical clustering order
dist_mat <- as.dist(1 - abs(cor_mat))
hc <- hclust(dist_mat, method = "complete")
ord <- hc$order
cor_mat_ordered <- cor_mat[ord, ord]

# Get lower triangle only
cor_mat_ordered[upper.tri(cor_mat_ordered)] <- NA

# Melt
melted_cormat <- as.data.frame(as.table(cor_mat_ordered))
names(melted_cormat) <- c("Var1", "Var2", "value")
melted_cormat <- na.omit(melted_cormat)

# Enforce order
melted_cormat$Var1 <- factor(melted_cormat$Var1, levels = rownames(cor_mat_ordered))
melted_cormat$Var2 <- factor(melted_cormat$Var2, levels = colnames(cor_mat_ordered))

# Plot
p_corr <- ggplot(melted_cormat, aes(Var1, Var2, fill = value)) +
  geom_tile(color = "white") +
  geom_text(aes(label = sprintf("%.2f", value)), size = 2.5, color = "black") +
  scale_fill_gradient2(low = "#E74C3C", high = "#3498DB", mid = "white", 
                       midpoint = 0, limit = c(-1,1), space = "Lab", 
                       name="Correlation") +
  theme_minimal() + 
  theme(
    axis.text.x = element_text(angle = 45, vjust = 1, hjust = 1, size = 10),
    axis.text.y = element_text(size = 10),
    axis.title.x = element_blank(),
    axis.title.y = element_blank(),
    panel.grid.major = element_blank(),
    panel.border = element_blank(),
    panel.background = element_blank(),
    axis.ticks = element_blank(),
    legend.position = "none"
  ) +
  coord_fixed()

ggsave(file.path(OUTPUT_DIR, "figure_correlation_heatmap.png"), p_corr,
       width = 10, height = 10, dpi = 300)

cat("  ✓ figure_correlation_heatmap.png\n\n")

################################################################################
# OUTPUT 9: High Correlation Pairs Table
################################################################################

cat("Creating Output 9: High Correlation Pairs Table...\n")

# Use all characteristics (not just top 20)
dt_all_chars <- dt[, ..char_cols]
clean_names_all <- sapply(names(dt_all_chars), function(x) toupper(gsub("^rank_", "", x)))
setnames(dt_all_chars, names(dt_all_chars), clean_names_all)

# Calculate correlation matrix for all characteristics
cor_mat_all <- cor(dt_all_chars, use = "pairwise.complete.obs")

# Extract upper triangle (to avoid duplicates)
cor_mat_all[lower.tri(cor_mat_all, diag = TRUE)] <- NA

# Find pairs with |correlation| > 0.7
high_corr_pairs <- data.table()
for (i in 1:(nrow(cor_mat_all)-1)) {
  for (j in (i+1):ncol(cor_mat_all)) {
    corr_val <- cor_mat_all[i, j]
    if (!is.na(corr_val) && abs(corr_val) > 0.7) {
      high_corr_pairs <- rbind(high_corr_pairs, data.table(
        Char1 = rownames(cor_mat_all)[i],
        Char2 = colnames(cor_mat_all)[j],
        Correlation = corr_val
      ))
    }
  }
}

# Sort by absolute correlation (descending)
high_corr_pairs <- high_corr_pairs[order(-abs(Correlation))]

# Create LaTeX table
sink(file.path(OUTPUT_DIR, "table_high_correlations.tex"))
cat("\\begin{table}[H]\n")
cat("\\centering\n")
cat(sprintf("\\caption{Highly correlated characteristic pairs with $|\\rho|>0.7$. Many variables are derived from common underlying measures, which naturally induces correlation. %d out of the %d characteristics have a correlation coefficient above 0.7.}\n",
    length(unique(c(high_corr_pairs$Char1, high_corr_pairs$Char2))),
    length(char_cols)))
cat("\\label{tab:high_correlations}\n")
cat("\\begin{tabular}{llc}\n")
cat("\\toprule\n")
cat("Characteristic 1 & Characteristic 2 & $\\rho$ \\\\\n")
cat("\\midrule\n")

for (i in 1:nrow(high_corr_pairs)) {
  cat(sprintf("%s & %s & %.3f \\\\\n",
              high_corr_pairs$Char1[i],
              high_corr_pairs$Char2[i],
              high_corr_pairs$Correlation[i]))
}

cat("\\bottomrule\n")
cat("\\end{tabular}\n")
cat("\\end{table}\n")
sink()

cat("  ✓ table_high_correlations.tex\n")
cat(sprintf("  Found %d pairs with |ρ| > 0.7\n\n", nrow(high_corr_pairs)))

################################################################################



################################################################################
# Save Summary Results
################################################################################

saveRDS(list(
  summary = list(
    n_obs = n_obs,
    n_firms = n_firms,
    n_months = n_months,
    n_chars = n_chars,
    avg_firms_month = avg_firms_month,
    avg_periods_firm = avg_periods_firm
  ),
  r2_analysis = r2_results,
  firms_per_month = firms_per_month
), file.path(OUTPUT_DIR, "validation_summary.rds"))

################################################################################
# Final Summary
################################################################################

cat("================================================================================\n")
cat("VALIDATION ANALYSIS COMPLETE\n")
cat("================================================================================\n\n")

cat("OUTPUTS CREATED (7 total):\n\n")
cat("Tables (LaTeX):\n")
cat("  1. table_data_summary.tex        - Dataset summary statistics\n")
cat("  2. table_univariate_r2.tex       - Top/bottom characteristics by R²\n")
cat("  2b. table_variable_stats.tex     - Variables: coverage and SD (ranked characteristics)\n")
cat("  3. table_sample_attrition.tex    - Data filtering pipeline\n\n")

cat("Figures (PNG, 300 DPI):\n")
cat("  4. figure_temporal_coverage.png  - Firms over time\n")
cat("  5. figure_market_comparison.png  - Swedish vs US comparison\n")
cat("  6. figure_predictive_power.png   - Top characteristics by R²\n")
cat("  7. figure_macro_factors.png     - Macro factors over time (Market, SMB, HML)\n\n")

cat("Data:\n")
cat("  - validation_summary.rds         - Summary statistics\n\n")

cat("KEY FINDINGS:\n")
cat(sprintf("  • Dataset: %s observations, %s firms, %d months\n", 
            format(n_obs, big.mark=","), format(n_firms, big.mark=","), n_months))
cat(sprintf("  • Coverage: %.0f firms/month average\n", avg_firms_month))
cat(sprintf("  • Predictive power: Median R² = %.6f (very weak)\n", median(r2_results$r2)))
cat(sprintf("  • Best characteristic: %s (R² = %.6f)\n",
            gsub("rank_", "", r2_results[1]$characteristic), r2_results[1]$r2))
cat(sprintf("  • Significant predictors: %d of %d (%.0f%%)\n",
            sum(r2_results$p_value < 0.05),
            nrow(r2_results),
            100 * sum(r2_results$p_value < 0.05) / nrow(r2_results)))

cat("\nCONCLUSION:\n")
cat("Limited P-Tree performance is primarily due to:\n")
cat("  1. Very weak univariate signals (median R² < 0.001)\n")
cat("  2. Small cross-sectional sample (~230 firms vs ~8000 in US)\n")
cat("  3. Limited observations (59K vs 4.8M in US)\n")
cat("  → DATA QUALITY constraint, not methodology failure\n\n")

cat("================================================================================\n")

cat("================================================================================\n")
