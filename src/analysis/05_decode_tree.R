#!/usr/bin/env Rscript

# A5: Decode P-Tree Structure - Make Trees Human-Readable
# --------------------------------------------------------
# Converts numeric tree output to readable format with characteristic names
# Generates:
# - Human-readable tree structure
# - Characteristic importance/usage summary
# - Leaf composition statistics

suppressPackageStartupMessages({
  library(data.table)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

in_rds <- file.path(repo_root, "results", "analysis", "inputs", "ptree_inputs.rds")
models_dir <- file.path(repo_root, "results", "analysis", "models")
out_dir <- file.path(repo_root, "results", "analysis", "interpretation")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

cat("\n=== A5: DECODE P-TREE STRUCTURE ===\n")
cat("Repo root:", repo_root, "\n\n")

# Load inputs to get characteristic names
if (!file.exists(in_rds)) stop("Inputs RDS not found")
inp <- readRDS(in_rds)

# Create characteristic mapping
char_map <- setNames(inp$char_cols, as.character(0:(length(inp$char_cols)-1)))

# Characteristic name lookup with descriptions
char_descriptions <- list(
  rank_acc = "Accruals",
  rank_agr = "Asset Growth",
  rank_ato = "Asset Turnover",
  rank_baspread = "Bid-Ask Spread",
  rank_bm = "Book-to-Market",
  rank_cash = "Cash Holdings",
  rank_cashdebt = "Cash-to-Debt",
  rank_cfp = "Cash Flow-to-Price",
  rank_chpm = "Change in Profit Margin",
  rank_chtx = "Change in Tax",
  rank_dolvol = "Dollar Volume",
  rank_ep = "Earnings-to-Price",
  rank_gma = "Gross Profitability",
  rank_grltnoa = "Growth in Long-Term NOA",
  rank_hire = "Employee Growth",
  rank_ill = "Illiquidity",
  rank_lev = "Leverage",
  rank_lgr = "Liabilities Growth",
  rank_maxret = "Maximum Return",
  rank_me = "Market Equity (Size)",
  rank_mom12m = "12-Month Momentum",
  rank_mom1m = "1-Month Momentum",
  rank_mom36m = "36-Month Momentum",
  rank_mom60m = "60-Month Momentum",
  rank_mom6m = "6-Month Momentum",
  rank_ni = "Net Income",
  rank_noa = "Net Operating Assets",
  rank_op = "Operating Profitability",
  rank_pctacc = "Percent Accruals",
  rank_pm = "Profit Margin",
  rank_rna = "Revenue-to-Assets",
  rank_roa = "Return on Assets",
  rank_roe = "Return on Equity",
  rank_seas1a = "Seasonality (1-year)",
  rank_sgr = "Sales Growth",
  rank_sp = "Sales-to-Price",
  rank_std_dolvol = "Volatility of Dollar Volume",
  rank_std_turn = "Volatility of Turnover",
  rank_svar = "Specific Variance",
  rank_turn = "Share Turnover"
)

# Function to parse tree format
# Tree format (from PTree package):
# Line 1: number of splits
# Following lines: node_id var_id threshold left_child right_child
parse_tree <- function(tree_lines, char_map) {
  num_splits <- as.integer(tree_lines[1])

  if (num_splits == 0 || length(tree_lines) < 2) {
    return(list(splits = data.table(), num_splits = 0))
  }

  splits <- list()
  for (i in 2:length(tree_lines)) {
    line <- trimws(tree_lines[i])
    if (nchar(line) == 0) next

    parts <- as.numeric(strsplit(line, "\\s+")[[1]])
    if (length(parts) < 5) next

    node_id <- parts[1]
    var_id <- parts[2]
    threshold <- parts[3]
    left_child <- parts[4]
    right_child <- parts[5]

    # Skip leaf nodes (var_id = 0)
    if (var_id == 0) next

    char_name <- char_map[as.character(var_id)]
    char_desc <- char_descriptions[[char_name]]
    if (is.null(char_desc)) char_desc <- char_name

    splits[[length(splits) + 1]] <- data.table(
      split_num = length(splits) + 1,
      node_id = node_id,
      var_id = var_id,
      var_name = char_name,
      var_description = char_desc,
      threshold = threshold,
      left_child = left_child,
      right_child = right_child
    )
  }

  if (length(splits) == 0) {
    return(list(splits = data.table(), num_splits = 0))
  }

  list(splits = rbindlist(splits), num_splits = num_splits)
}

# Function to create human-readable tree description
describe_tree <- function(parsed) {
  if (nrow(parsed$splits) == 0) {
    return("No splits (single node tree)")
  }

  desc <- character()
  desc <- c(desc, sprintf("P-Tree with %d splits:", parsed$num_splits))
  desc <- c(desc, "")

  for (i in 1:nrow(parsed$splits)) {
    s <- parsed$splits[i]
    desc <- c(desc, sprintf("Split %d: %s (%s)",
                           s$split_num,
                           s$var_description,
                           s$var_name))
    desc <- c(desc, sprintf("  Threshold: %.3f", s$threshold))
    desc <- c(desc, sprintf("  Left (≤ %.3f): Node %d", s$threshold, s$left_child))
    desc <- c(desc, sprintf("  Right (> %.3f): Node %d", s$threshold, s$right_child))
    desc <- c(desc, "")
  }

  paste(desc, collapse = "\n")
}

# Process all scenarios
scenarios <- c("scenario_a", "scenario_b_train", "scenario_c_train")
scenario_names <- c("A: Full Sample", "B: Time-Split (Train)", "C: Reverse Split (Train)")

all_char_usage <- list()
all_decoded <- list()

for (i in seq_along(scenarios)) {
  scenario <- scenarios[i]
  scenario_name <- scenario_names[i]

  tree_file <- file.path(models_dir, paste0(scenario, "_tree.txt"))

  if (!file.exists(tree_file)) {
    cat(sprintf("Warning: %s not found, skipping\n", tree_file))
    next
  }

  cat(sprintf("\n--- %s ---\n", scenario_name))

  tree_lines <- readLines(tree_file)
  parsed <- parse_tree(tree_lines, char_map)

  # Save human-readable version
  readable <- describe_tree(parsed)
  cat(readable)
  cat("\n")

  out_file <- file.path(out_dir, paste0(scenario, "_readable.txt"))
  writeLines(readable, out_file)

  # Save structured table
  if (nrow(parsed$splits) > 0) {
    fwrite(parsed$splits, file.path(out_dir, paste0(scenario, "_splits.csv")))
    all_decoded[[scenario_name]] <- parsed$splits

    # Track characteristic usage
    char_usage <- parsed$splits[, .(count = .N), by = .(var_name, var_description)]
    char_usage[, scenario := scenario_name]
    all_char_usage[[scenario_name]] <- char_usage
  }
}

# Create characteristic importance summary
if (length(all_char_usage) > 0) {
  cat("\n\n╔════════════════════════════════════════════════╗\n")
  cat("║     CHARACTERISTIC IMPORTANCE SUMMARY          ║\n")
  cat("╚════════════════════════════════════════════════╝\n\n")

  combined_usage <- rbindlist(all_char_usage)

  # Overall importance (across all scenarios)
  overall <- combined_usage[, .(total_usage = sum(count)), by = .(var_name, var_description)]
  setorder(overall, -total_usage)

  cat("Most Important Characteristics (Total Usage Across Scenarios):\n")
  print(overall[1:min(10, nrow(overall))])

  fwrite(overall, file.path(out_dir, "characteristic_importance_overall.csv"))

  # By scenario
  by_scenario <- dcast(combined_usage, var_description + var_name ~ scenario,
                       value.var = "count", fill = 0)
  setorder(by_scenario, -`A: Full Sample`)

  cat("\n\nCharacteristic Usage By Scenario:\n")
  print(by_scenario)

  fwrite(by_scenario, file.path(out_dir, "characteristic_importance_by_scenario.csv"))
}

cat("\n\n✓ Tree interpretation saved to:", normalizePath(out_dir, mustWork=FALSE), "\n")
cat("\nFiles created:\n")
cat("  - *_readable.txt: Human-readable tree descriptions\n")
cat("  - *_splits.csv: Structured split information\n")
cat("  - characteristic_importance_*.csv: Importance summaries\n")
cat("\nA5 complete.\n\n")
