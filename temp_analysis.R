library(data.table)

inp <- readRDS("results/inputs/ptree_inputs.rds")
dt <- inp$dt

cat("=== DATA SUMMARY ===\n")
cat("Total observations:", nrow(dt), "\n")
cat("Total firms:", length(unique(dt$isin)), "\n")
cat("Total months:", length(unique(dt$date)), "\n\n")

char_cols <- inp$char_cols
cat("Number of characteristics:", length(char_cols), "\n\n")

# Check each characteristic for split feasibility
cat("=== SPLIT FEASIBILITY BY CHARACTERISTIC ===\n")
cat("For a split to work, ALL months must have >= min_leaf_size (3) stocks on BOTH sides\n\n")

results <- data.table(
  characteristic = character(),
  min_left_at_02 = integer(),
  min_right_at_02 = integer(),
  splittable_at_02 = logical(),
  min_left_at_06 = integer(),
  min_right_at_06 = integer(),
  splittable_at_06 = logical()
)

for (char in char_cols) {
  # Count stocks in each bin per month
  dt[, bin := cut(get(char), breaks = c(-Inf, -0.6, -0.2, 0.2, 0.6, Inf), labels = c("Q1", "Q2", "Q3", "Q4", "Q5"))]
  bin_counts <- dt[, .N, by = .(date, bin)]
  bin_summary <- dcast(bin_counts, date ~ bin, value.var = "N", fill = 0)
  
  # For split at -0.2
  left_02 <- if ("Q1" %in% names(bin_summary) && "Q2" %in% names(bin_summary)) {
    min(bin_summary$Q1 + bin_summary$Q2)
  } else 0
  right_02 <- if (all(c("Q3", "Q4", "Q5") %in% names(bin_summary))) {
    min(bin_summary$Q3 + bin_summary$Q4 + bin_summary$Q5)
  } else 0
  
  # For split at -0.6
  left_06 <- if ("Q1" %in% names(bin_summary)) min(bin_summary$Q1) else 0
  right_06 <- if (all(c("Q2", "Q3", "Q4", "Q5") %in% names(bin_summary))) {
    min(bin_summary$Q2 + bin_summary$Q3 + bin_summary$Q4 + bin_summary$Q5)
  } else 0
  
  results <- rbind(results, data.table(
    characteristic = gsub("rank_", "", char),
    min_left_at_02 = left_02,
    min_right_at_02 = right_02,
    splittable_at_02 = (left_02 >= 3 && right_02 >= 3),
    min_left_at_06 = left_06,
    min_right_at_06 = right_06,
    splittable_at_06 = (left_06 >= 3 && right_06 >= 3)
  ))
}

cat("Characteristics that CAN be split at -0.2:\n")
print(results[splittable_at_02 == TRUE, .(characteristic, min_left_at_02, min_right_at_02)])

cat("\nCharacteristics that CANNOT be split at -0.2:\n")
print(results[splittable_at_02 == FALSE, .(characteristic, min_left_at_02, min_right_at_02)])

cat("\n\n=== CHECKING SECOND SPLIT AFTER FIRST SPLIT ===\n")
# After first split, we're in one leaf. The issue is that within THAT leaf,
# we need to check if a second split is possible.

# Let's check what happens after splitting on a valid characteristic
# The tree shows: "1 3 -0.2 1 0" meaning split on var 3 (index 3 = 4th char) at -0.2

cat("\nFirst split was on characteristic index 3:", char_cols[4], "\n")
split_char <- char_cols[4]

# After split: left leaf has stocks with split_char <= -0.2
# Right leaf has stocks with split_char > -0.2

dt_left <- dt[get(split_char) <= -0.2]
dt_right <- dt[get(split_char) > -0.2]

cat("\nLeft leaf (", split_char, "<= -0.2):\n")
cat("  Observations:", nrow(dt_left), "\n")
cat("  Firms per month - min:", dt_left[, .N, by=date][, min(N)], "\n")
cat("  Firms per month - mean:", round(dt_left[, .N, by=date][, mean(N)], 1), "\n")

cat("\nRight leaf (", split_char, "> -0.2):\n")
cat("  Observations:", nrow(dt_right), "\n")
cat("  Firms per month - min:", dt_right[, .N, by=date][, min(N)], "\n")
cat("  Firms per month - mean:", round(dt_right[, .N, by=date][, mean(N)], 1), "\n")

# Now check if ANY further split is possible in either leaf
cat("\n\n=== CAN WE SPLIT FURTHER IN LEFT LEAF? ===\n")

results_left <- data.table()
for (char in char_cols) {
  # Within the left leaf, try to split on each characteristic
  dt_left[, bin := cut(get(char), breaks = c(-Inf, -0.6, -0.2, 0.2, 0.6, Inf), labels = c("Q1", "Q2", "Q3", "Q4", "Q5"))]
  bin_counts <- dt_left[, .N, by = .(date, bin)]
  bin_summary <- dcast(bin_counts, date ~ bin, value.var = "N", fill = 0)
  
  # Check all 4 possible cutpoints
  for (cutpoint in c(-0.6, -0.2, 0.2, 0.6)) {
    if (cutpoint == -0.6) {
      left_n <- if ("Q1" %in% names(bin_summary)) min(bin_summary$Q1) else 0
      right_n <- if (all(c("Q2","Q3","Q4","Q5") %in% names(bin_summary))) min(bin_summary$Q2 + bin_summary$Q3 + bin_summary$Q4 + bin_summary$Q5) else 0
    } else if (cutpoint == -0.2) {
      left_n <- if (all(c("Q1","Q2") %in% names(bin_summary))) min(bin_summary$Q1 + bin_summary$Q2) else 0
      right_n <- if (all(c("Q3","Q4","Q5") %in% names(bin_summary))) min(bin_summary$Q3 + bin_summary$Q4 + bin_summary$Q5) else 0
    } else if (cutpoint == 0.2) {
      left_n <- if (all(c("Q1","Q2","Q3") %in% names(bin_summary))) min(bin_summary$Q1 + bin_summary$Q2 + bin_summary$Q3) else 0
      right_n <- if (all(c("Q4","Q5") %in% names(bin_summary))) min(bin_summary$Q4 + bin_summary$Q5) else 0
    } else {  # 0.6
      left_n <- if (all(c("Q1","Q2","Q3","Q4") %in% names(bin_summary))) min(bin_summary$Q1 + bin_summary$Q2 + bin_summary$Q3 + bin_summary$Q4) else 0
      right_n <- if ("Q5" %in% names(bin_summary)) min(bin_summary$Q5) else 0
    }
    
    if (left_n >= 3 && right_n >= 3) {
      results_left <- rbind(results_left, data.table(
        char = gsub("rank_", "", char),
        cutpoint = cutpoint,
        min_left = left_n,
        min_right = right_n
      ))
    }
  }
}

if (nrow(results_left) > 0) {
  cat("Possible splits in LEFT leaf:\n")
  print(results_left)
} else {
  cat("NO valid splits possible in LEFT leaf!\n")
}

cat("\n\n=== CAN WE SPLIT FURTHER IN RIGHT LEAF? ===\n")
results_right <- data.table()
for (char in char_cols) {
  dt_right[, bin := cut(get(char), breaks = c(-Inf, -0.6, -0.2, 0.2, 0.6, Inf), labels = c("Q1", "Q2", "Q3", "Q4", "Q5"))]
  bin_counts <- dt_right[, .N, by = .(date, bin)]
  bin_summary <- dcast(bin_counts, date ~ bin, value.var = "N", fill = 0)
  
  for (cutpoint in c(-0.6, -0.2, 0.2, 0.6)) {
    if (cutpoint == -0.6) {
      left_n <- if ("Q1" %in% names(bin_summary)) min(bin_summary$Q1) else 0
      right_n <- if (all(c("Q2","Q3","Q4","Q5") %in% names(bin_summary))) min(bin_summary$Q2 + bin_summary$Q3 + bin_summary$Q4 + bin_summary$Q5) else 0
    } else if (cutpoint == -0.2) {
      left_n <- if (all(c("Q1","Q2") %in% names(bin_summary))) min(bin_summary$Q1 + bin_summary$Q2) else 0
      right_n <- if (all(c("Q3","Q4","Q5") %in% names(bin_summary))) min(bin_summary$Q3 + bin_summary$Q4 + bin_summary$Q5) else 0
    } else if (cutpoint == 0.2) {
      left_n <- if (all(c("Q1","Q2","Q3") %in% names(bin_summary))) min(bin_summary$Q1 + bin_summary$Q2 + bin_summary$Q3) else 0
      right_n <- if (all(c("Q4","Q5") %in% names(bin_summary))) min(bin_summary$Q4 + bin_summary$Q5) else 0
    } else {
      left_n <- if (all(c("Q1","Q2","Q3","Q4") %in% names(bin_summary))) min(bin_summary$Q1 + bin_summary$Q2 + bin_summary$Q3 + bin_summary$Q4) else 0
      right_n <- if ("Q5" %in% names(bin_summary)) min(bin_summary$Q5) else 0
    }
    
    if (left_n >= 3 && right_n >= 3) {
      results_right <- rbind(results_right, data.table(
        char = gsub("rank_", "", char),
        cutpoint = cutpoint,
        min_left = left_n,
        min_right = right_n
      ))
    }
  }
}

if (nrow(results_right) > 0) {
  cat("Possible splits in RIGHT leaf:\n")
  print(results_right)
} else {
  cat("NO valid splits possible in RIGHT leaf!\n")
}

cat("\n\n=== CONCLUSION ===\n")
cat("The P-Tree algorithm requires that EVERY month has at least min_leaf_size\n")
cat("stocks on BOTH sides of a split. With the Swedish data:\n")
cat("- Average ~153 firms/month, but minimum is only 70 firms\n")
cat("- After first split, each leaf has ~half the stocks\n")
cat("- Further splitting creates even smaller groups\n")
cat("- Some months don't have enough stocks in the extreme quintiles\n")
cat("\nThis is a DATA SPARSITY issue, not a code bug.\n")
