############################################################################
# Debug Factor Output - Why do factors start in 2011?
############################################################################

library(PTree)

# Load data
data <- read.csv("/mnt/c/Users/micha/Desktop/Projekte/PTrees/analysis_dataset/ptree_attempt2/results/ptree_ready_data_full.csv", stringsAsFactors = FALSE)
data$date <- as.Date(data$date, format='%Y-%m-%d')

# Load saved models
load("/mnt/c/Users/micha/Desktop/Projekte/PTrees/analysis_dataset/ptree_attempt2/results/ptree_models.RData")

cat("Data info:\n")
cat(sprintf("  Date range: %s to %s\n", min(data$date), max(data$date)))
cat(sprintf("  Total observations: %d\n", nrow(data)))
cat(sprintf("  Unique dates: %d\n", length(unique(data$date))))

cat("\nFactor 1 info:\n")
cat(sprintf("  Length of fit1$ft: %d\n", length(fit1$ft)))
cat(sprintf("  Should match unique dates: %d\n", length(unique(data$date))))

# Check first few factor values
cat("\nFirst 10 factor values:\n")
print(head(fit1$ft, 10))

# Get unique dates
unique_dates <- sort(unique(data$date))
cat(sprintf("\nFirst date in data: %s\n", unique_dates[1]))
cat(sprintf("Last date in data: %s\n", unique_dates[length(unique_dates)]))

# Check if factor length matches
if (length(fit1$ft) < length(unique_dates)) {
  cat(sprintf("\nPROBLEM: Factor has %d values but data has %d unique dates\n",
              length(fit1$ft), length(unique_dates)))
  cat(sprintf("Missing %d months of data!\n", length(unique_dates) - length(fit1$ft)))

  # Try to find which dates are included
  if (length(fit1$ft) > 0) {
    start_idx = length(unique_dates) - length(fit1$ft) + 1
    cat(sprintf("\nFactor appears to start at date index %d: %s\n",
                start_idx, unique_dates[start_idx]))
  }
}

# Check training data preparation
start_date = '1997-01-01'
data1 <- data[(data$date >= start_date), ]

cat(sprintf("\nTraining data after filtering:\n"))
cat(sprintf("  Date range: %s to %s\n", min(data1$date), max(data1$date)))
cat(sprintf("  Total observations: %d\n", nrow(data1)))

# Prepare indices
months_train = as.numeric(as.factor(data1$date)) - 1
stocks_train = as.numeric(as.factor(data1$permno)) - 1
num_months = length(unique(months_train))

cat(sprintf("  Number of unique months: %d\n", num_months))
cat(sprintf("  Length of fit1$ft: %d\n", length(fit1$ft)))

# Check portfolio weights
cat(sprintf("\nPortfolio weight (lag_me) stats:\n"))
cat(sprintf("  Min: %.2f\n", min(data1$lag_me)))
cat(sprintf("  Max: %.2e\n", max(data1$lag_me)))
cat(sprintf("  Mean: %.2e\n", mean(data1$lag_me)))
cat(sprintf("  Any zeros: %s\n", any(data1$lag_me == 0)))
cat(sprintf("  Any NAs: %s\n", any(is.na(data1$lag_me))))
