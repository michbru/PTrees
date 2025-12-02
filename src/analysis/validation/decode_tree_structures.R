#!/usr/bin/env Rscript

# Decode Tree Structures and Create Variable Importance Table
# Interprets the raw tree output and creates human-readable summaries

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", "..", ".."), mustWork = FALSE)

# Paths
in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")
models_dir <- file.path(repo_root, "results", "models")
out_dir <- file.path(repo_root, "results", "thesis_visualisations")

cat("\n╔════════════════════════════════════════════════╗\n")
cat("║   TREE STRUCTURE ANALYSIS                      ║\n")
cat("╚════════════════════════════════════════════════╝\n\n")

# Load inputs to get characteristic names
inp <- readRDS(in_rds)
char_map <- setNames(inp$char_cols, as.character(0:(length(inp$char_cols)-1)))

# Read tree file
tree_file <- file.path(models_dir, "scenario_a_trees.txt")
if (!file.exists(tree_file)) {
  stop("Tree file not found: ", tree_file)
}

tree_lines <- readLines(tree_file)

# Parse trees
parse_tree <- function(tree_str) {
  # Remove quotes and split by newline
  tree_str <- gsub('"', '', tree_str)
  tree_str <- gsub('\\[1\\] ', '', tree_str)
  lines <- strsplit(tree_str, "\\\\n")[[1]]
  
  if (length(lines) < 2) return(NULL)
  
  # Parse each node
  nodes <- list()
  for (i in 2:length(lines)) {
    if (nchar(lines[i]) == 0) next
    parts <- as.numeric(strsplit(trimws(lines[i]), "\\s+")[[1]])
    if (length(parts) >= 5) {
      nodes[[length(nodes)+1]] <- list(
        node_id = parts[1],
        var_id = parts[2],
        threshold = parts[3],
        left_child = parts[4],
        right_child = parts[5]
      )
    }
  }
  nodes
}

# Extract all trees
trees <- list()
current_factor <- NULL
current_tree_str <- ""

for (line in tree_lines) {
  if (grepl("^--- Factor", line)) {
    # Save previous tree
    if (!is.null(current_factor) && nchar(current_tree_str) > 0) {
      trees[[current_factor]] <- parse_tree(current_tree_str)
    }
    # Start new tree
    current_factor <- as.integer(sub("--- Factor (\\d+) ---", "\\1", line))
    current_tree_str <- ""
  } else {
    current_tree_str <- paste0(current_tree_str, line, "\n")
  }
}
# Save last tree
if (!is.null(current_factor) && nchar(current_tree_str) > 0) {
  trees[[current_factor]] <- parse_tree(current_tree_str)
}

cat(sprintf("Parsed %d trees\n\n", length(trees)))

# Analyze splits
split_counts <- list()
for (factor_id in names(trees)) {
  tree <- trees[[factor_id]]
  if (is.null(tree)) next
  
  for (node in tree) {
    if (node$var_id > 0) {  # Actual split (not leaf)
      var_name <- char_map[as.character(node$var_id)]
      if (is.null(split_counts[[var_name]])) {
        split_counts[[var_name]] <- 0
      }
      split_counts[[var_name]] <- split_counts[[var_name]] + 1
    }
  }
}

# Create variable importance table
if (length(split_counts) > 0) {
  importance_dt <- data.table(
    Characteristic = names(split_counts),
    `Split Count` = unlist(split_counts)
  )
  setorder(importance_dt, -`Split Count`)
  
  cat("Variable Importance (Split Counts):\n")
  print(importance_dt)
  cat("\n")
  
  # Save table
  fwrite(importance_dt, file.path(out_dir, "table4_variable_importance.csv"))
  
  # Create LaTeX table
  con <- file(file.path(out_dir, "table4_variable_importance.tex"), "wt")
  writeLines("\\begin{table}[!ht]", con)
  writeLines("\\centering", con)
  writeLines("\\caption{Variable Importance: Split Frequency Across 20 P-Tree Factors}", con)
  writeLines("\\label{tab:variable_importance}", con)
  writeLines("\\begin{tabular}{lc}", con)
  writeLines("\\hline", con)
  writeLines("Characteristic & Split Count \\\\", con)
  writeLines("\\hline", con)
  for (i in 1:nrow(importance_dt)) {
    writeLines(sprintf("%s & %d \\\\", importance_dt[i, Characteristic], importance_dt[i, `Split Count`]), con)
  }
  writeLines("\\hline", con)
  writeLines("\\end{tabular}", con)
  writeLines("\\\\[0.5em]", con)
  writeLines("\\begin{minipage}{\\textwidth}", con)
  writeLines("\\small", con)
  writeLines("\\textit{Notes:} Split count represents the number of times each characteristic was used as a splitting variable across all 20 boosted P-Tree factors.", con)
  writeLines("\\end{minipage}", con)
  writeLines("\\end{table}", con)
  close(con)
  
  cat("✓ Saved: table4_variable_importance.csv\n")
  cat("✓ Saved: table4_variable_importance.tex\n\n")
  
  # Create bar plot
  p <- ggplot(importance_dt, aes(x = reorder(Characteristic, `Split Count`), y = `Split Count`)) +
    geom_bar(stat = "identity", fill = "#2E86AB", width = 0.7) +
    coord_flip() +
    labs(title = "Variable Importance: P-Tree Split Frequency",
         x = "", y = "Number of Splits (out of 20 factors)") +
    theme_minimal(base_size = 12) +
    theme(plot.title = element_text(face = "bold"))
  
  ggsave(file.path(out_dir, "figure4_variable_importance.png"), p, width = 8, height = 6, dpi = 300)
  cat("✓ Saved: figure4_variable_importance.png\n\n")
} else {
  cat("Warning: No splits found in trees\n")
}

# Decode first tree as example
if (length(trees) > 0) {
  cat("Example Tree Structure (Factor 1):\n")
  cat("=====================================\n")
  tree1 <- trees[[1]]
  if (!is.null(tree1) && length(tree1) > 0) {
    for (node in tree1) {
      if (node$var_id > 0) {
        var_name <- char_map[as.character(node$var_id)]
        cat(sprintf("Node %d: Split on %s (threshold: %.3f)\n", 
                    node$node_id, var_name, node$threshold))
        cat(sprintf("  → Left child (≤ %.3f): Node %d\n", node$threshold, node$left_child))
        cat(sprintf("  → Right child (> %.3f): Node %d\n", node$threshold, node$right_child))
      } else {
        cat(sprintf("Node %d: Leaf node\n", node$node_id))
      }
    }
  }
  cat("\n")
}

cat("Analysis complete!\n")
