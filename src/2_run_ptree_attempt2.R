############################################################################
# PTree Analysis - Attempt 2 (Relaxed NA Requirements)
# Swedish Stock Market (1997-2022)
############################################################################

t = proc.time()

###### Parameters #####

case = 'swedish_attempt2_relaxed_na'

# Use entire Swedish data period
start = '1997-01-01'
split = '2022-12-31'
end = '2022-12-31'

# Tree parameters (adjusted for Swedish market size ~300 stocks/month vs US ~2000+)
min_leaf_size = 10  # Intermediate: allows splits but prevents overfitting
max_depth = 10
max_depth_boosting = 10

num_iter = 9
num_iterB = 9

num_cutpoints = 4   # Match original paper
equal_weight = FALSE  # Match original paper (value-weighted)

no_H1 = TRUE  # First tree: no benchmark
no_H = FALSE  # Subsequent trees: use previous as benchmark

abs_normalize = TRUE
weighted_loss = FALSE

early_stop = FALSE
stop_threshold = 1
lambda_ridge = 0

# Regularization parameters
lambda_mean = 0
lambda_cov = 1e-4

lambda_mean_factor = 0
lambda_cov_factor = 1e-5

# Extension parameters
eta = 1
a1 = 0.0
a2 = 0.0
list_K = matrix(rep(0,3), nrow = 3, ncol = 1)
random_split = FALSE

###### Load Libraries #####

library(PTree)

cat(paste(rep("=", 70), collapse=""), "\n")
cat("PTREE ANALYSIS - ATTEMPT 2\n")
cat(paste(rep("=", 70), collapse=""), "\n")

cat("\nLoading Swedish stock data (relaxed NA)...\n")

##### Load Swedish Data #####

# Load the prepared Swedish data (self-contained - relative path)
# Use relative path from project root
data_path = "results/ptree_ready_data_full.csv"
cat(sprintf("Reading from: %s\n", data_path))
cat(sprintf("File exists: %s\n", file.exists(data_path)))

data <- read.csv(data_path, stringsAsFactors = FALSE)
cat(sprintf("Raw loaded: %d rows\n", nrow(data)))

# Verify no NAs (data prep should have handled this)
rank_cols <- grep("^rank_", names(data), value = TRUE)
na_count <- sum(is.na(data[, rank_cols]))
if (na_count > 0) {
  cat(sprintf("WARNING: Found %d NAs in characteristics, removing...\n", na_count))
  data <- data[complete.cases(data[, rank_cols]), ]
}

cat(sprintf("\nFinal data: %d observations from %d stocks\n", nrow(data), length(unique(data$permno))))
cat(sprintf("Date range: %s to %s\n", min(data$date), max(data$date)))

# Check available characteristics
all_chars <- names(data)[grep("^rank_", names(data))]
cat(sprintf("Available characteristics: %d\n", length(all_chars)))

# Use all available characteristics
instruments = all_chars[1:min(5, length(all_chars))]
splitting_chars <- all_chars

first_split_var = seq(0, length(all_chars)-1)
second_split_var = seq(0, length(all_chars)-1)

##### Train-Test Split #####

data$date <- as.Date(data$date, format='%Y-%m-%d')
data1 <- data[(data$date >= start) & (data$date <= split), ]

cat(sprintf("\nTraining data: %d observations\n", nrow(data1)))
cat(sprintf("Date range: %s to %s\n", min(data1$date), max(data1$date)))

###### Prepare Training Data #####

X_train = data1[, splitting_chars]
R_train = data1[, "xret"]
months_train = as.numeric(as.factor(data1$date))
months_train = months_train - 1
stocks_train = as.numeric(as.factor(data1$permno)) - 1
Z_train = data1[, instruments]
Z_train = cbind(1, Z_train)

portfolio_weight_train = data1[, "lag_me"]
loss_weight_train = data1[, "lag_me"]
num_months = length(unique(months_train))
num_stocks = length(unique(stocks_train))

cat(sprintf("\nTraining setup:\n"))
cat(sprintf("  Months: %d\n", num_months))
cat(sprintf("  Stocks: %d\n", num_stocks))
cat(sprintf("  Characteristics: %d\n", ncol(X_train)))

# Check average stocks per month
stocks_per_month <- aggregate(stocks_train, by=list(months_train), FUN=function(x) length(unique(x)))
cat(sprintf("  Avg stocks per month: %.1f (min: %d, max: %d)\n",
            mean(stocks_per_month$x), min(stocks_per_month$x), max(stocks_per_month$x)))

# Check early period coverage
early_data <- data1[data1$date < as.Date('2000-01-01'), ]
if (nrow(early_data) > 0) {
  early_months <- length(unique(early_data$date))
  early_stocks <- length(unique(early_data$permno))
  cat(sprintf("\n  Early period (1997-1999): %d months, %d stocks\n", early_months, early_stocks))
} else {
  cat("\n  WARNING: No data before 2000!\n")
}

###### Train P-Tree 1 (No Benchmark) #####

cat("\n")
cat(paste(rep("=", 70), collapse=""), "\n")
cat("Training P-Tree 1 (No Benchmark)\n")
cat(paste(rep("=", 70), collapse=""), "\n")

Y_train1 = data1[, "xret"]
H_train1 = rep(0, nrow(data1))

t1 = proc.time()

fit1 = PTree(R_train, Y_train1, X_train, Z_train, H_train1, portfolio_weight_train,
loss_weight_train, stocks_train, months_train, first_split_var, second_split_var, num_stocks,
num_months, min_leaf_size, max_depth, num_iter, num_cutpoints, eta, equal_weight,
  no_H1,
abs_normalize, weighted_loss, lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
early_stop, stop_threshold, lambda_ridge, a1, a2, list_K, random_split)

t1 = proc.time() - t1
cat(sprintf("P-Tree 1 completed in %.2f seconds\n", t1[3]))

###### Train P-Tree 2 (Boosting) #####

cat("\n")
cat(paste(rep("=", 70), collapse=""), "\n")
cat("Training P-Tree 2 (Boosting on P-Tree 1)\n")
cat(paste(rep("=", 70), collapse=""), "\n")

Y_train2 = data1[, "xret"]
H_train2 = fit1$ft

t2 = proc.time()

fit2 = PTree(R_train, Y_train2, X_train, Z_train, H_train2, portfolio_weight_train,
loss_weight_train, stocks_train, months_train, first_split_var, second_split_var,
  num_stocks, num_months, min_leaf_size, max_depth_boosting, num_iterB, num_cutpoints, eta, equal_weight,
  no_H,
abs_normalize, weighted_loss, lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
early_stop, stop_threshold, lambda_ridge, a1, a2, list_K, random_split)

t2 = proc.time() - t2
cat(sprintf("P-Tree 2 completed in %.2f seconds\n", t2[3]))

###### Train P-Tree 3 (Boosting) #####

cat("\n")
cat(paste(rep("=", 70), collapse=""), "\n")
cat("Training P-Tree 3 (Boosting on P-Trees 1-2)\n")
cat(paste(rep("=", 70), collapse=""), "\n")

Y_train3 = data1[, "xret"]
H_train3 = cbind(fit1$ft, fit2$ft)

t3 = proc.time()

fit3 = PTree(R_train, Y_train3, X_train, Z_train, H_train3, portfolio_weight_train,
loss_weight_train, stocks_train, months_train, first_split_var, second_split_var,
num_stocks, num_months, min_leaf_size, max_depth_boosting, num_iterB, num_cutpoints, eta, equal_weight,
no_H,
abs_normalize, weighted_loss, lambda_mean, lambda_cov, lambda_mean_factor, lambda_cov_factor,
early_stop, stop_threshold, lambda_ridge, a1, a2, list_K, random_split)

t3 = proc.time() - t3
cat(sprintf("P-Tree 3 completed in %.2f seconds\n", t3[3]))

###### Save Results #####

cat("\n")
cat(paste(rep("=", 70), collapse=""), "\n")
cat("Saving Results\n")
cat(paste(rep("=", 70), collapse=""), "\n")

output_dir = "results"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# Save fitted models
save(fit1, fit2, fit3, file = file.path(output_dir, "ptree_models.RData"))
cat(sprintf("Saved models to %s/ptree_models.RData\n", output_dir))

# Save factor time series
# IMPORTANT: Sort dates chronologically!
all_dates <- sort(unique(data1$date))
factors_df = data.frame(
  month = all_dates,
  factor1 = fit1$ft,
  factor2 = fit2$ft,
  factor3 = fit3$ft
)

write.csv(factors_df, file.path(output_dir, "ptree_factors.csv"), row.names = FALSE)
cat(sprintf("Saved factors to %s/ptree_factors.csv\n", output_dir))

###### Calculate Performance Statistics #####

cat("\n")
cat(paste(rep("=", 70), collapse=""), "\n")
cat("Performance Summary\n")
cat(paste(rep("=", 70), collapse=""), "\n")

calculate_sharpe = function(returns) {
  mean_ret = mean(returns, na.rm = TRUE)
  sd_ret = sd(returns, na.rm = TRUE)
  sharpe = mean_ret / sd_ret * sqrt(12)  # Annualized
  return(sharpe)
}

calculate_win_rate = function(returns) {
  return(sum(returns > 0, na.rm = TRUE) / length(returns) * 100)
}

calculate_drawdown = function(returns) {
  cumulative = cumprod(1 + returns)
  running_max = cummax(cumulative)
  drawdown = (cumulative - running_max) / running_max
  return(min(drawdown))
}

cat(sprintf("\nFactor 1:\n"))
cat(sprintf("  Sharpe Ratio: %.3f\n", calculate_sharpe(fit1$ft)))
cat(sprintf("  Win Rate: %.1f%%\n", calculate_win_rate(fit1$ft)))
cat(sprintf("  Max Drawdown: %.2f%%\n", calculate_drawdown(fit1$ft) * 100))

cat(sprintf("\nFactor 2:\n"))
cat(sprintf("  Sharpe Ratio: %.3f\n", calculate_sharpe(fit2$ft)))
cat(sprintf("  Win Rate: %.1f%%\n", calculate_win_rate(fit2$ft)))
cat(sprintf("  Max Drawdown: %.2f%%\n", calculate_drawdown(fit2$ft) * 100))

cat(sprintf("\nFactor 3:\n"))
cat(sprintf("  Sharpe Ratio: %.3f\n", calculate_sharpe(fit3$ft)))
cat(sprintf("  Win Rate: %.1f%%\n", calculate_win_rate(fit3$ft)))
cat(sprintf("  Max Drawdown: %.2f%%\n", calculate_drawdown(fit3$ft) * 100))

###### Total Time #####

t_total = proc.time() - t
cat(sprintf("\n"))
cat(paste(rep("=", 70), collapse=""), "\n")
cat(sprintf("Total Runtime: %.2f minutes\n", t_total[3]/60))
cat(paste(rep("=", 70), collapse=""), "\n")

cat("\nSUCCESS: P-Tree Attempt 2 Complete!\n")
cat(sprintf("Results saved to: %s\n", output_dir))
