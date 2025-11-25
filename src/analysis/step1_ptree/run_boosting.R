###################################################################################
# BOOSTING - Fit multiple P-Trees sequentially
# Each tree fits residuals from previous trees
###################################################################################

run_boosting <- function() {
  cat("================================================================================\n")
  cat("BOOSTED P-TREE TRAINING\n")
  cat("================================================================================\n\n")
  
  # Load data
  data_obj <- load_ptree_data(DATA_PATH)
  data <- data_obj$data
  all_chars <- data_obj$all_chars
  instruments <- data_obj$instruments
  
  # Prepare parameters
  params <- list(
    min_leaf_size = MIN_LEAF_SIZE,
    max_depth = MAX_DEPTH,
    num_iter = NUM_ITER,
    num_cutpoints = NUM_CUTPOINTS,
    equal_weight = EQUAL_WEIGHT,
    lambda_cov = LAMBDA_COV,
    lambda_cov_factor = LAMBDA_COV_FACTOR
  )
  
  # Storage for all trees
  all_fits <- list()
  all_factors <- list()
  
  cat(sprintf("Training %d boosted trees...\n\n", NUM_TREES))
  
  for(tree_num in 1:NUM_TREES) {
    tree_start <- Sys.time()
    
    cat(sprintf("Tree %d/%d ", tree_num, NUM_TREES))
    cat("--------------------------------------------------------------------------------\n")
    
    # Prepare benchmark (previous factors)
    if(tree_num == 1) {
      H_benchmark <- NULL
      desc <- sprintf("Tree %d (no benchmark)", tree_num)
    } else {
      # Combine all previous factors as benchmark
      H_benchmark <- do.call(cbind, all_factors)
      desc <- sprintf("Tree %d (benchmark: trees 1-%d)", tree_num, tree_num-1)
    }
    
    # Train tree
    fit <- train_ptree(data, all_chars, instruments, params, H_benchmark, desc)
    
    if(!is.null(fit)) {
      # Store fit and factor
      all_fits[[tree_num]] <- fit
      all_factors[[tree_num]] <- fit$ft
      
      # Calculate cumulative performance
      cum_factors <- do.call(cbind, all_factors)
      cum_sharpe <- calculate_sharpe(rowMeans(cum_factors, na.rm = TRUE))
      
      elapsed <- as.numeric(difftime(Sys.time(), tree_start, units = "secs"))
      cat(sprintf("    [OK] Nodes: %d | Cumulative Sharpe: %.3f | Time: %.1f s\n\n", 
                  fit$num_leaves, cum_sharpe, elapsed))
    } else {
      cat("    [FAILED] Could not fit tree\n\n")
      break
    }
  }
  
  # Save all factors
  output_dir <- paste0(OUTPUT_DIR, "/boosted_trees")
  dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)
  
  cat("Saving results...\n")
  
  # Save individual tree structures
  for(i in 1:length(all_fits)) {
    if(!is.null(all_fits[[i]])) {
      write(all_fits[[i]]$tree, file.path(output_dir, sprintf("tree_%d_structure.txt", i)))
    }
  }
  
  # Save all factors as CSV
  if(length(all_factors) > 0) {
    factors_matrix <- do.call(cbind, all_factors)
    colnames(factors_matrix) <- paste0("tree_", 1:ncol(factors_matrix))
    
    # Add date info
    unique_dates <- unique(data$date)
    if(nrow(factors_matrix) == length(unique_dates)) {
      factors_df <- data.frame(date = unique_dates, factors_matrix)
    } else {
      factors_df <- data.frame(factors_matrix)
    }
    
    write.csv(factors_df, file.path(output_dir, "all_factors.csv"), row.names = FALSE)
  }
  
  # Save model objects
  save(all_fits, all_factors, file = file.path(output_dir, "boosted_models.RData"))
  
  cat(sprintf("  [SAVED] %s\n\n", output_dir))
  
  # Summary statistics
  cat("================================================================================\n")
  cat("BOOSTING SUMMARY\n")
  cat("================================================================================\n\n")
  
  cat(sprintf("Trees fitted:        %d/%d\n", length(all_fits), NUM_TREES))
  
  for(i in 1:length(all_fits)) {
    if(!is.null(all_fits[[i]])) {
      cat(sprintf("  Tree %d:            %d nodes\n", i, all_fits[[i]]$num_leaves))
    }
  }
  
  if(length(all_factors) > 0) {
    cum_factors <- do.call(cbind, all_factors)
    avg_factor <- rowMeans(cum_factors, na.rm = TRUE)
    final_sharpe <- calculate_sharpe(avg_factor)
    cat(sprintf("\nCumulative Sharpe:   %.3f\n", final_sharpe))
  }
  
  cat("\n")
  
  return(list(fits = all_fits, factors = all_factors))
}
