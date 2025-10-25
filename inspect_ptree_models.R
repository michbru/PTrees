############################################################################
# Inspect P-Tree Models to Check for Splits
############################################################################

cat(paste(rep("=", 70), collapse=""), "\n")
cat("P-TREE MODEL INSPECTION\n")
cat(paste(rep("=", 70), collapse=""), "\n\n")

# Load the saved models
load('results/ptree_models.RData')

cat("CHECKING FIT1 (First P-Tree):\n")
cat(paste(rep("-", 70), collapse=""), "\n")
cat("Class:", class(fit1), "\n")
cat("Structure names:", names(fit1), "\n\n")

# Check key components
if (!is.null(fit1$tree)) {
  cat("Tree structure:\n")
  print(fit1$tree)
  cat("\n")
}

if (!is.null(fit1$leaves)) {
  cat("Number of leaves:", length(unique(fit1$leaves)), "\n")
  cat("Leaf distribution:\n")
  print(table(fit1$leaves))
  cat("\n")
}

if (!is.null(fit1$split_var)) {
  cat("Split variables used:\n")
  print(fit1$split_var)
  cat("\n")
}

if (!is.null(fit1$split_val)) {
  cat("Split values:\n")
  print(fit1$split_val)
  cat("\n")
}

# Check factor output
cat("Factor time series:\n")
cat("  Length:", length(fit1$ft), "\n")
cat("  Mean:", mean(fit1$ft), "\n")
cat("  Std:", sd(fit1$ft), "\n")
cat("  First 5 values:", fit1$ft[1:5], "\n\n")

# Most important: check the actual tree structure
cat(paste(rep("=", 70), collapse=""), "\n")
cat("DETAILED STRUCTURE:\n")
cat(paste(rep("=", 70), collapse=""), "\n")
str(fit1, max.level = 2)

cat("\n")
cat(paste(rep("=", 70), collapse=""), "\n")
cat("INTERPRETATION:\n")
cat(paste(rep("=", 70), collapse=""), "\n")
if (!is.null(fit1$leaves) && length(unique(fit1$leaves)) == 1) {
  cat("WARNING: Only 1 unique leaf - NO SPLITS OCCURRED\n")
  cat("Tree defaulted to single portfolio (market)\n")
} else if (!is.null(fit1$leaves)) {
  cat("Number of leaf portfolios:", length(unique(fit1$leaves)), "\n")
  cat("Splits DID occur\n")
} else {
  cat("Cannot determine - no leaf information\n")
}
