############################################################################
# CHARACTERISTIC IMPORTANCE ANALYSIS
#
# Extracts which characteristics are most important in P-Tree splits
# Analyzes tree structure to count:
# 1. How many times each characteristic is used in splits
# 2. At what depth characteristics appear (earlier = more important)
# 3. Which characteristics appear in the first few critical splits
#
# This validates that the P-Tree is using economically meaningful
# characteristics rather than just noise.
############################################################################

library(PTree)

cat(paste(rep("=", 80), collapse=""), "\n")
cat("CHARACTERISTIC IMPORTANCE ANALYSIS\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

###### Load Results #####

scenarios <- list(
  list(name = "Scenario A: Full Sample",
       path = "../../results/ptree_34chars/scenario_a_full/ptree_models.RData"),
  list(name = "Scenario B: Time Split",
       path = "../../results/ptree_34chars/scenario_b_split/ptree_models.RData"),
  list(name = "Scenario C: Reverse Split",
       path = "../../results/ptree_34chars/scenario_c_reverse/ptree_models.RData")
)

# Load data to get characteristic names
data <- read.csv("../../results/ptree_34chars/ptree_ready_data_34chars.csv", stringsAsFactors = FALSE)
all_chars <- names(data)[grep("^rank_", names(data))]
char_names <- gsub("^rank_", "", all_chars)

cat("Loaded", length(char_names), "characteristics\n\n")

###### Parse Tree Structure #####

parse_tree_structure <- function(tree_string) {
  """
  Parse P-Tree structure string to extract split variables

  The tree string format is:
  Line 1: Number of nodes
  Following lines: Node information including split variables

  Returns: Vector of split variable indices
  """
  lines <- strsplit(tree_string, "\n")[[1]]

  # First line is number of nodes
  n_nodes <- as.numeric(lines[1])

  if (n_nodes <= 1) {
    return(integer(0))
  }

  split_vars <- c()

  # Parse remaining lines for split variables
  # Format varies, but we look for numeric values that could be variable indices
  for (i in 2:min(length(lines), n_nodes + 1)) {
    line <- lines[i]
    # Extract numbers from line
    numbers <- as.numeric(unlist(strsplit(line, " ")))
    numbers <- numbers[!is.na(numbers)]

    # First number after node ID is often the split variable
    # (This is a heuristic - actual format may vary)
    if (length(numbers) >= 2) {
      split_var <- numbers[2]
      if (split_var >= 0 && split_var < length(char_names)) {
        split_vars <- c(split_vars, split_var)
      }
    }
  }

  return(split_vars)
}

extract_importance <- function(fit, char_names) {
  """
  Extract characteristic importance from fitted P-Tree

  Returns: Data frame with characteristic usage counts
  """

  if (is.null(fit$tree)) {
    cat("WARNING: No tree structure found\n")
    return(NULL)
  }

  # Parse tree structure
  split_vars <- parse_tree_structure(fit$tree)

  if (length(split_vars) == 0) {
    cat("WARNING: Could not parse tree structure\n")
    return(NULL)
  }

  # Count usage of each characteristic
  importance <- data.frame(
    characteristic = char_names,
    usage_count = 0,
    stringsAsFactors = FALSE
  )

  for (var_idx in split_vars) {
    if (var_idx >= 0 && var_idx < nrow(importance)) {
      importance$usage_count[var_idx + 1] <- importance$usage_count[var_idx + 1] + 1
    }
  }

  # Calculate percentage
  total_splits <- sum(importance$usage_count)
  if (total_splits > 0) {
    importance$usage_pct <- importance$usage_count / total_splits * 100
  } else {
    importance$usage_pct <- 0
  }

  # Sort by usage
  importance <- importance[order(-importance$usage_count), ]

  return(importance)
}

###### Analyze Each Scenario #####

all_importance <- list()

for (scenario in scenarios) {
  cat(paste(rep("-", 80), collapse=""), "\n")
  cat(scenario$name, "\n")
  cat(paste(rep("-", 80), collapse=""), "\n\n")

  if (!file.exists(scenario$path)) {
    cat("WARNING: File not found:", scenario$path, "\n\n")
    next
  }

  # Load results
  load(scenario$path)

  # Get the results object (name varies by scenario)
  if (exists("results_a")) {
    results <- results_a
  } else if (exists("results_b")) {
    results <- results_b
  } else if (exists("results_c")) {
    results <- results_c
  } else {
    cat("WARNING: No results object found\n\n")
    next
  }

  # Analyze Tree 1 (most important - non-boosted)
  cat("Analyzing Tree 1 (primary factor)...\n")

  tree_info <- results$fit1
  tree_nodes <- as.numeric(strsplit(tree_info$tree, "\n")[[1]][1])

  cat("  Tree nodes:", tree_nodes, "\n")
  cat("  Sharpe ratio:", round(calculate_sharpe(tree_info$ft), 3), "\n\n")

  # Note: P-Tree structure is complex and may not expose split variables directly
  # Alternative: Use tree summary or plot functions if available

  cat("NOTE: P-Tree package may not expose internal split structure\n")
  cat("For detailed importance analysis, consider:\n")
  cat("1. Manual inspection of tree structure (if available)\n")
  cat("2. Permutation importance (refit with shuffled characteristics)\n")
  cat("3. Correlation analysis between characteristics and factor returns\n\n")

  # Clean up
  rm(results_a, results_b, results_c, envir = .GlobalEnv)
}

###### Alternative: Correlation-Based Importance #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("ALTERNATIVE: CORRELATION-BASED IMPORTANCE\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

cat("Analyzing characteristic correlations with P-Tree factor returns...\n\n")

for (scenario in scenarios) {
  cat(paste(rep("-", 80), collapse=""), "\n")
  cat(scenario$name, "\n")
  cat(paste(rep("-", 80), collapse=""), "\n\n")

  # Determine factor file based on scenario
  scenario_dir <- dirname(scenario$path)

  # Try both factor file names
  factor_files <- c(
    file.path(scenario_dir, "ptree_factors.csv"),
    file.path(scenario_dir, "ptree_factors_is.csv")
  )

  factor_file <- NULL
  for (f in factor_files) {
    if (file.exists(f)) {
      factor_file <- f
      break
    }
  }

  if (is.null(factor_file)) {
    cat("WARNING: No factor file found\n\n")
    next
  }

  # Load factor returns
  factors <- read.csv(factor_file, stringsAsFactors = FALSE)
  factors$month <- as.Date(factors$month)

  # Merge with original data
  data_with_factors <- merge(data, factors, by.x = "date", by.y = "month")

  # Calculate correlations between ranked characteristics and Tree 1 returns
  correlations <- data.frame(
    characteristic = char_names,
    correlation = NA,
    abs_correlation = NA,
    stringsAsFactors = FALSE
  )

  for (i in 1:length(char_names)) {
    rank_col <- paste0("rank_", char_names[i])
    if (rank_col %in% names(data_with_factors)) {
      # Calculate correlation
      cor_val <- cor(data_with_factors[[rank_col]],
                     data_with_factors$factor1,
                     use = "complete.obs")
      correlations$correlation[i] <- cor_val
      correlations$abs_correlation[i] <- abs(cor_val)
    }
  }

  # Sort by absolute correlation
  correlations <- correlations[order(-correlations$abs_correlation), ]

  cat("Top 10 Most Correlated Characteristics with Tree 1:\n\n")
  print(head(correlations, 10))

  # Save results
  output_file <- file.path(scenario_dir, "characteristic_correlations.csv")
  write.csv(correlations, output_file, row.names = FALSE)
  cat("\nSaved to:", output_file, "\n\n")

  all_importance[[scenario$name]] <- correlations
}

###### Summary Across Scenarios #####

cat(paste(rep("=", 80), collapse=""), "\n")
cat("TOP CHARACTERISTICS ACROSS ALL SCENARIOS\n")
cat(paste(rep("=", 80), collapse=""), "\n\n")

if (length(all_importance) > 0) {
  # Combine importance across scenarios
  combined_importance <- data.frame(
    characteristic = char_names,
    avg_abs_correlation = 0,
    stringsAsFactors = FALSE
  )

  for (scenario_name in names(all_importance)) {
    imp <- all_importance[[scenario_name]]
    for (i in 1:nrow(combined_importance)) {
      char <- combined_importance$characteristic[i]
      char_row <- imp[imp$characteristic == char, ]
      if (nrow(char_row) > 0 && !is.na(char_row$abs_correlation)) {
        combined_importance$avg_abs_correlation[i] <-
          combined_importance$avg_abs_correlation[i] + char_row$abs_correlation
      }
    }
  }

  combined_importance$avg_abs_correlation <-
    combined_importance$avg_abs_correlation / length(all_importance)

  combined_importance <- combined_importance[order(-combined_importance$avg_abs_correlation), ]

  cat("Top 15 Characteristics (by average absolute correlation):\n\n")
  print(head(combined_importance, 15))

  # Save combined results
  write.csv(combined_importance,
            "../../results/ptree_34chars/characteristic_importance_combined.csv",
            row.names = FALSE)

  cat("\n\nKey Findings:\n")
  cat("These characteristics have the strongest correlations with P-Tree factor returns.\n")
  cat("High correlation suggests these are the key drivers of P-Tree performance.\n")
  cat("\nExpected top characteristics from Cong et al. (2024):\n")
  cat("  - SUE (Standardized Unexpected Earnings)\n")
  cat("  - DOLVOL (Dollar Trading Volume)\n")
  cat("  - BM_IA (Industry-Adjusted Book-to-Market)\n")
  cat("  - ME_IA (Industry-Adjusted Market Equity)\n")
  cat("  - ROE (Return on Equity)\n")
  cat("  - ZEROTRADE (Zero Trading Days)\n\n")
}

###### Helper Function #####

calculate_sharpe <- function(returns) {
  return(mean(returns) / sd(returns) * sqrt(12))
}

cat(paste(rep("=", 80), collapse=""), "\n")
cat("CHARACTERISTIC IMPORTANCE ANALYSIS COMPLETE\n")
cat(paste(rep("=", 80), collapse=""), "\n")
