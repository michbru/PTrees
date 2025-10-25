############################################################################
# Diagnose Why P-Trees Don't Split
############################################################################

library(PTree)

cat("LOADING DATA...\n")
data_path = "results/ptree_ready_data_full.csv"
data <- read.csv(data_path, stringsAsFactors = FALSE)

# Prepare data
all_chars <- names(data)[grep("^rank_", names(data))]
instruments = all_chars[1:min(5, length(all_chars))]
splitting_chars <- all_chars

cat("\nDATA STATISTICS:\n")
cat("================\n")
cat("Total observations:", nrow(data), "\n")
cat("Unique dates:", length(unique(data$date)), "\n")
cat("Unique stocks:", length(unique(data$permno)), "\n")
cat("Characteristics:", length(all_chars), "\n\n")

# Check monthly coverage
data$date <- as.Date(data$date, format='%Y-%m-%d')
stocks_per_month <- aggregate(data$permno, by=list(data$date), FUN=function(x) length(unique(x)))
names(stocks_per_month) <- c("date", "n_stocks")

cat("Stocks per month:\n")
cat("  Mean:", round(mean(stocks_per_month$n_stocks), 1), "\n")
cat("  Min:", min(stocks_per_month$n_stocks), "\n")
cat("  Max:", max(stocks_per_month$n_stocks), "\n")
cat("  Median:", median(stocks_per_month$n_stocks), "\n\n")

# Check if we have enough data for splits with min_leaf_size=10
min_leaf_size <- 10
cat("SPLIT FEASIBILITY (min_leaf_size =", min_leaf_size, "):\n")
cat("==================================================\n")
cat("To split, need at least 2 *", min_leaf_size, "=", 2*min_leaf_size, "stocks per month\n")
cat("Months with >= ", 2*min_leaf_size, "stocks:",
    sum(stocks_per_month$n_stocks >= 2*min_leaf_size), "/", nrow(stocks_per_month), "\n\n")

# Check months with insufficient stocks
insufficient <- stocks_per_month[stocks_per_month$n_stocks < 2*min_leaf_size, ]
if (nrow(insufficient) > 0) {
  cat("PROBLEM MONTHS (< ", 2*min_leaf_size, " stocks):\n")
  print(head(insufficient, 20))
  cat("\n")
}

# Test with smaller min_leaf_size
cat("\nTESTING SMALLER min_leaf_size:\n")
cat("================================\n")
for (mls in c(5, 3, 2, 1)) {
  feasible <- sum(stocks_per_month$n_stocks >= 2*mls)
  cat("min_leaf_size =", mls, ": Feasible in", feasible, "/", nrow(stocks_per_month), "months\n")
}

# Check characteristic variation
cat("\nCHARACTERISTIC VARIATION:\n")
cat("==========================\n")
first_month <- data[data$date == min(data$date), ]
cat("In first month (", as.character(min(data$date)), "):\n")
cat("  Stocks:", nrow(first_month), "\n")
for (char in all_chars[1:5]) {
  char_sd <- sd(first_month[[char]], na.rm=TRUE)
  char_range <- diff(range(first_month[[char]], na.rm=TRUE))
  cat("  ", char, "- SD:", round(char_sd, 4), "Range:", round(char_range, 4), "\n")
}

# Check return variation
cat("\nRETURN VARIATION:\n")
cat("==================\n")
cat("Overall xret SD:", round(sd(data$xret, na.rm=TRUE), 4), "\n")
cat("Cross-sectional xret SD (first month):", round(sd(first_month$xret, na.rm=TRUE), 4), "\n")

# Key diagnostic: Check if there's signal in characteristics
cat("\nSIGNAL CHECK (Simple univariate test):\n")
cat("=======================================\n")
cat("Correlation of characteristics with next-month return:\n")
for (char in all_chars[1:5]) {
  cor_val <- cor(data[[char]], data$xret, use="complete.obs")
  cat("  ", char, ":", round(cor_val, 4), "\n")
}

cat("\nCONCLUSION:\n")
cat("============\n")
if (mean(stocks_per_month$n_stocks) < 2*min_leaf_size) {
  cat("ISSUE: Average stocks per month too low for splits with min_leaf_size=10\n")
  cat("SOLUTION: Try min_leaf_size = 2 or 3\n")
} else {
  cat("Stock count seems adequate\n")
  cat("Issue might be: lack of predictive signal in characteristics\n")
}
