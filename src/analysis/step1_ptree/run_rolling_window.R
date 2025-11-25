###################################################################################
# ROLLING WINDOW RUNNER - Execute rolling window validation
###################################################################################

run_rolling_window <- function(data, all_chars, instruments, params, rolling_params, output_dir) {
  cat("\n")
  cat("================================================================================\n")
  cat("PART 2: ROLLING WINDOW VALIDATION (ANTI-OVERFITTING)\n")
  cat("================================================================================\n\n")
  
  all_dates <- sort(unique(data$date))
  n_months <- length(all_dates)
  
  train_window <- rolling_params$train_months
  test_window <- rolling_params$test_months
  roll_step <- rolling_params$step_months
  
  max_start <- n_months - train_window - test_window
  n_windows <- floor(max_start / roll_step) + 1
  
  cat("CONFIGURATION:\n")
  cat("  Total months:     ", n_months, "\n")
  cat("  Training window:  ", train_window, "months (5 years)\n")
  cat("  Test window:      ", test_window, "months (1 year)\n")
  cat("  Roll step:        ", roll_step, "months (1 year)\n")
  cat("  Number of windows:", n_windows, "\n\n")
  
  results_list <- list()
  
  for(w in 1:n_windows) {
    train_start_idx <- (w - 1) * roll_step + 1
    train_end_idx <- train_start_idx + train_window - 1
    test_start_idx <- train_end_idx + 1
    test_end_idx <- test_start_idx + test_window - 1
    
    if(test_end_idx > n_months) {
      cat("Window", w, ": Insufficient data, skipping\n")
      break
    }
    
    train_dates <- all_dates[train_start_idx:train_end_idx]
    test_dates <- all_dates[test_start_idx:test_end_idx]
    train_data <- data[data$date %in% train_dates, ]
    test_data <- data[data$date %in% test_dates, ]
    
    cat(sprintf("Window %d/%d: Train %s to %s | Test %s to %s\n",
                w, n_windows,
                as.character(min(train_dates)), as.character(max(train_dates)),
                as.character(min(test_dates)), as.character(max(test_dates))))
    
    fit <- train_ptree(train_data, all_chars, instruments, params,
                      sprintf("Window %d", w))
    
    if(is.null(fit)) {
      cat("  [FAILED]\n\n")
      next
    }
    
    is_sharpe <- calculate_sharpe(fit$ft)
    oos_factors <- predict_ptree(fit, test_data, all_chars, sprintf("Window %d", w))
    
    if(is.null(oos_factors)) {
      cat("  [FAILED OOS]\n\n")
      next
    }
    
    oos_sharpe <- calculate_sharpe(oos_factors)
    degradation <- if(is_sharpe != 0) (oos_sharpe - is_sharpe) / is_sharpe * 100 else NA
    
    results_list[[w]] <- data.frame(
      window = w,
      train_start = as.character(min(train_dates)),
      train_end = as.character(max(train_dates)),
      test_start = as.character(min(test_dates)),
      test_end = as.character(max(test_dates)),
      is_sharpe = is_sharpe,
      oos_sharpe = oos_sharpe,
      degradation_pct = degradation,
      stringsAsFactors = FALSE
    )
    
    cat("\n")
  }
  
  results_df <- do.call(rbind, results_list)
  
  cat("================================================================================\n")
  cat("ROLLING WINDOW SUMMARY\n")
  cat("================================================================================\n\n")
  cat(sprintf("Windows tested:        %d\n", nrow(results_df)))
  cat(sprintf("Avg IS Sharpe:         %.3f\n", mean(results_df$is_sharpe, na.rm = TRUE)))
  cat(sprintf("Avg OOS Sharpe:        %.3f\n", mean(results_df$oos_sharpe, na.rm = TRUE)))
  cat(sprintf("Median OOS Sharpe:     %.3f\n", median(results_df$oos_sharpe, na.rm = TRUE)))
  cat(sprintf("Std Dev OOS Sharpe:    %.3f\n", sd(results_df$oos_sharpe, na.rm = TRUE)))
  cat(sprintf("Avg Degradation:       %.1f%%\n", mean(results_df$degradation_pct, na.rm = TRUE)))
  cat(sprintf("Positive OOS:          %.0f%% (%d/%d)\n",
              sum(results_df$oos_sharpe > 0, na.rm = TRUE) / nrow(results_df) * 100,
              sum(results_df$oos_sharpe > 0, na.rm = TRUE),
              nrow(results_df)))
  
  output_path <- file.path(output_dir, "rolling_window")
  dir.create(output_path, showWarnings = FALSE, recursive = TRUE)
  write.csv(results_df, file.path(output_path, "rolling_window_results.csv"), row.names = FALSE)
  cat(sprintf("\n[SAVED] %s\n", output_path))
  
  return(results_df)
}
