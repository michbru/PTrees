###################################################################################
# DATA LOADER - Load and prepare P-Tree ready dataset
###################################################################################

load_ptree_data <- function(data_path) {
  cat("Loading P-Tree ready data...\n")
  
  data <- read.csv(data_path, stringsAsFactors = FALSE)
  data$date <- as.Date(data$date, format='%Y-%m-%d')
  data <- data[order(data$date), ]
  
  # Extract characteristics
  all_chars <- names(data)[grep("^rank_", names(data))]
  instruments <- all_chars[1:min(5, length(all_chars))]
  
  cat("  Total observations:", nrow(data), "\n")
  cat("  Date range:", as.character(min(data$date)), "to", as.character(max(data$date)), "\n")
  cat("  Unique stocks:", length(unique(data$permno)), "\n")
  cat("  Characteristics:", length(all_chars), "\n")
  cat("  Instruments (Z):", length(instruments), "\n\n")
  
  return(list(
    data = data,
    all_chars = all_chars,
    instruments = instruments
  ))
}
