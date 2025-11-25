###################################################################################
# SCENARIO RUNNER - Execute three-scenario validation
###################################################################################

run_three_scenarios <- function(data, all_chars, instruments, params, scenarios, output_dir) {
  cat("\n")
  cat("================================================================================\n")
  cat("PART 1: THREE-SCENARIO VALIDATION\n")
  cat("================================================================================\n\n")
  
  results <- list()
  
  for(scenario_key in names(scenarios)) {
    scenario <- scenarios[[scenario_key]]
    
    cat(scenario$name, "\n")
    cat("--------------------------------------------------------------------------------\n")
    
    if(is.null(scenario$split_date)) {
      # Full sample
      train_data <- data
      test_data <- NULL
      
      fit <- train_ptree(train_data, all_chars, instruments, params, "Full Sample")
      
      output_path <- file.path(output_dir, paste0("scenario_", scenario_key))
      dir.create(output_path, showWarnings = FALSE, recursive = TRUE)
      
      if(!is.null(fit)) {
        factors <- data.frame(
          month = sort(unique(train_data$date)),
          factor = fit$ft
        )
        write.csv(factors, file.path(output_path, "ptree_factors.csv"), row.names = FALSE)
        writeLines(fit$tree, file.path(output_path, "ptree_structure.txt"))
        
        results[[scenario_key]] <- list(fit = fit, factors_is = factors, factors_oos = NULL)
        cat("  [SAVED]", output_path, "\n")
      }
      
    } else {
      # Split scenario
      split_date <- scenario$split_date
      train_data <- data[scenario$train_filter(data$date, split_date), ]
      test_data <- data[scenario$test_filter(data$date, split_date), ]
      
      cat("  Train:", nrow(train_data), "obs |")
      cat("  Test:", nrow(test_data), "obs\n")
      
      fit <- train_ptree(train_data, all_chars, instruments, params,
                         paste(scenario$name, "(IS)"))
      
      output_path <- file.path(output_dir, paste0("scenario_", scenario_key))
      dir.create(output_path, showWarnings = FALSE, recursive = TRUE)
      
      if(!is.null(fit)) {
        # Save IS factors
        factors_is <- data.frame(
          month = sort(unique(train_data$date)),
          factor = fit$ft
        )
        write.csv(factors_is, file.path(output_path, "ptree_factors_is.csv"), row.names = FALSE)
        writeLines(fit$tree, file.path(output_path, "ptree_structure.txt"))
        
        # Predict OOS
        factors_oos_vec <- predict_ptree(fit, test_data, all_chars,
                                         paste(scenario$name, "(OOS)"))
        
        factors_oos <- NULL
        if(!is.null(factors_oos_vec)) {
          factors_oos <- data.frame(
            month = sort(unique(test_data$date)),
            factor = factors_oos_vec
          )
          write.csv(factors_oos, file.path(output_path, "ptree_factors_oos.csv"), row.names = FALSE)
        }
        
        results[[scenario_key]] <- list(fit = fit, factors_is = factors_is, factors_oos = factors_oos)
        cat("  [SAVED]", output_path, "\n")
      }
    }
    
    cat("\n")
  }
  
  return(results)
}
