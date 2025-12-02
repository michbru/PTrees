#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")
tree_file <- file.path(repo_root, "results", "models", "scenario_a_trees.txt")

if (!file.exists(in_rds)) stop("Inputs RDS not found.")
if (!file.exists(tree_file)) stop("Tree file not found.")

cat("Loading inputs to get feature names...\n")
inp <- readRDS(in_rds)
char_cols <- inp$char_cols
cat(sprintf("Loaded %d characteristics.\n", length(char_cols)))

# Print mapping for reference
# cat("Feature Mapping (0-based index):\n")
# for (i in seq_along(char_cols)) {
#   cat(sprintf("  %d: %s\n", i-1, char_cols[i]))
# }

cat("\nReading tree file...\n")
lines <- readLines(tree_file)

current_factor <- 0
for (line in lines) {
  if (grepl("^--- Factor", line)) {
    current_factor <- as.integer(sub("--- Factor (\\d+) ---", "\\1", line))
    cat(sprintf("\n--- Factor %d ---\n", current_factor))
  } else if (grepl("^\\[1\\]", line)) {
    # This is the print output from R, usually a string literal with \n inside
    # Remove [1] " and final "
    content <- sub("^\\[1\\] \"", "", line)
    content <- sub("\"\\s*$", "", content)
    
    # Split by \n literal (which might be escaped as \\n in the file read?)
    # The file was written with sink() and print(), so it might look like:
    # [1] "5\n1 15 0.76... \n..."
    
    # Let's try to parse the content string. 
    # It contains newline characters literally if it was printed as a string.
    # But readLines might read it as literal text.
    
    # Replace literal \n with actual newlines
    content <- gsub("\\\\n", "\n", content)
    
    tree_lines <- strsplit(content, "\n")[[1]]
    
    # First line is number of nodes?
    # Format: node_id feature_idx split_val left_child right_child
    # (Checking typical PTree output format)
    
    for (tline in tree_lines) {
      parts <- strsplit(tline, "\\s+")[[1]]
      parts <- parts[parts != ""] # Remove empty
      
      if (length(parts) >= 5) {
        node_id <- parts[1]
        feat_idx <- as.integer(parts[2])
        split_val <- as.numeric(parts[3])
        
        # If feat_idx is 0 and split_val is 0, it might be a leaf or root?
        # Actually PTree usually outputs: node_id feature_index split_value ...
        
        if (!is.na(feat_idx) && feat_idx >= 0 && feat_idx < length(char_cols)) {
          feat_name <- char_cols[feat_idx + 1] # 1-based in R vector
          cat(sprintf("  Node %s: Split on %s (idx %d) at %.4f\n", 
                      node_id, feat_name, feat_idx, split_val))
        }
      }
    }
  }
}
