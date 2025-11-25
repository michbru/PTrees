###################################################################################
# P-TREE TRAINER - Core training and prediction functions
###################################################################################

calculate_sharpe <- function(returns) {
  if(length(returns) < 2 || all(is.na(returns))) return(NA)
  
  mean_ret <- mean(returns, na.rm = TRUE)
  sd_ret <- sd(returns, na.rm = TRUE)
  
  if(sd_ret == 0) return(0)
  
  return(mean_ret / sd_ret * sqrt(12))  # Annualize
}

train_ptree <- function(train_data, all_chars, instruments, params, H_benchmark = NULL, desc = "") {
  # Prepare inputs
  X_train <- as.matrix(train_data[, all_chars])  # MUST be matrix
  R_train <- as.matrix(train_data[, "xret"])    # MUST be matrix
  Y_train <- as.matrix(train_data[, "xret"])    # Target = returns
  
  # Handle benchmark factor for boosting
  if(is.null(H_benchmark)) {
    # First tree: no benchmark
    H_train <- as.matrix(rep(0, nrow(train_data)))
    no_H_flag <- TRUE
  } else {
    # Subsequent trees: use previous factors as benchmark
    H_train <- as.matrix(H_benchmark)
    no_H_flag <- FALSE
  }
  
  # Panel structure (0-indexed for C++ backend)
  months_train <- as.numeric(as.factor(train_data$date)) - 1
  stocks_train <- as.numeric(as.factor(train_data$permno)) - 1
  
  # Instrument matrix: intercept + top 5 characteristics
  # Used in split criterion: Y ~ Z * F
  Z_train <- as.matrix(cbind(1, train_data[, instruments]))
  
  # Weights (MUST be non-negative, non-zero)
  portfolio_weight <- as.numeric(train_data[, "lag_me"])
  loss_weight <- as.numeric(train_data[, "lag_me"])
  
  # Verify no zero/negative weights
  if(any(portfolio_weight <= 0)) {
    portfolio_weight[portfolio_weight <= 0] <- 1e-6
    warning("Found zero/negative portfolio weights, replacing with 1e-6")
  }
  
  num_months_train <- length(unique(months_train))
  num_stocks_train <- length(unique(stocks_train))
  
  # Split variable indices (0-indexed for C++)
  # Allow ALL characteristics for root split
  first_split_var <- as.numeric(seq(0, length(all_chars) - 1))
  # Allow ALL characteristics for subsequent splits  
  second_split_var <- as.numeric(seq(0, length(all_chars) - 1))
  
  if(desc != "") cat("  Training P-Tree for", desc, "...\n")
  
  t_start <- proc.time()
  
  fit <- tryCatch({
    PTree(
      R_train,              # Returns to explain
      Y_train,              # Target for split (= R for single-tree)
      X_train,              # Characteristics matrix
      Z_train,              # Instruments (intercept + top 5)
      H_train,              # Benchmark (ignored when no_H=TRUE)
      portfolio_weight,     # Weights for leaf portfolios (market cap)
      loss_weight,          # Weights for loss function (market cap)
      stocks_train,         # Stock indices (0-indexed)
      months_train,         # Time indices (0-indexed)
      first_split_var,      # Vars allowed for root split
      second_split_var,     # Vars allowed for subsequent splits
      num_stocks_train,     # Number of unique stocks
      num_months_train,     # Number of unique months
      
      # Tree structure
      params$min_leaf_size, # Min stocks per leaf (10)
      params$max_depth,     # Max tree depth (5)
      params$num_iter,      # Tree-building iterations (1 for single-tree)
      params$num_cutpoints, # Split candidates per char (3)
      
      # Weighting
      eta = 1,              # No equal-weight regularization (pure optimization)
      equal_weight = params$equal_weight,  # FALSE = value-weighted
      
      # Boosting mode
      no_H = no_H_flag,     # TRUE for first tree, FALSE for subsequent trees
      
      # SDF construction  
      abs_normalize = TRUE,   # Normalize by sum(abs(w))
      weighted_loss = FALSE,  # Don't weight loss function
      
      # Regularization: (mu + lambda_mean) * (Sigma + lambda_cov)^-1
      0,                      # lambda_mean (no mean regularization)
      params$lambda_cov,      # lambda_cov (1e-3, strong regularization)
      0,                      # lambda_mean_factor (no mean reg for factors)
      params$lambda_cov_factor, # lambda_cov_factor (1e-4)
      
      # Early stopping (disabled)
      early_stop = FALSE,
      stop_threshold = 1,     # Not used when early_stop=FALSE
      
      # Ridge penalty (disabled)
      lambda_ridge = 0,
      
      # Tree regularization (disabled - redundant per paper)
      a1 = 0,
      a2 = 0,
      list_K = matrix(rep(0, 3), nrow = 3, ncol = 1),
      
      # Split criterion
      random_split = FALSE    # Use Sharpe ratio (not random)
    )
  }, error = function(e) {
    cat("    ERROR:", e$message, "\n")
    return(NULL)
  })
  
  t_elapsed <- (proc.time() - t_start)[3]
  
  if(!is.null(fit)) {
    sharpe_is <- calculate_sharpe(fit$ft)
    nodes <- as.numeric(strsplit(fit$tree, "\n")[[1]][1])
    
    cat("    [OK] Nodes:", nodes,
        "| IS Sharpe:", round(sharpe_is, 3),
        "| Time:", round(t_elapsed, 1), "s\n")
  }
  
  return(fit)
}

predict_ptree <- function(fit, test_data, all_chars, desc = "") {
  if(is.null(fit)) return(NULL)
  
  if(desc != "") cat("  Predicting OOS for", desc, "...\n")
  
  # Prepare test data (same format as training)
  X_test <- as.matrix(test_data[, all_chars])
  R_test <- as.matrix(test_data[, "xret"])
  months_test <- as.numeric(as.factor(test_data$date)) - 1
  weight_test <- as.numeric(test_data[, "lag_me"])
  
  # Verify weights
  if(any(weight_test <= 0)) {
    weight_test[weight_test <= 0] <- 1e-6
  }
  
  pred <- tryCatch({
    predict(fit, X_test, R_test, months_test, weight_test)
  }, error = function(e) {
    cat("    ERROR:", e$message, "\n")
    return(NULL)
  })
  
  if(!is.null(pred)) {
    sharpe_oos <- calculate_sharpe(pred$ft)
    cat("    [OK] OOS Sharpe:", round(sharpe_oos, 3), "\n")
    return(pred$ft)
  }
  
  return(NULL)
}
