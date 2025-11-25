###################################################################################
# CONFIGURATION - P-TREE ANALYSIS FOR SWEDISH MARKET
# Single-tree approach with conservative parameters
###################################################################################

# --- TREE PARAMETERS ---
# Following original paper but adapted for Swedish market

MIN_LEAF_SIZE <- 5           # Minimum stocks per leaf (5 for Swedish vs paper's 20)
MAX_DEPTH <- 8               # Maximum tree depth (8 vs paper's 10)
NUM_ITER <- 5                # Tree-building iterations (5 vs paper's 9)
NUM_CUTPOINTS <- 4           # Split point candidates (same as paper)
EQUAL_WEIGHT <- FALSE        # Value-weighted portfolios

# --- BOOSTING PARAMETERS ---
NUM_TREES <- 5               # Number of boosted trees (5 for Swedish market vs 20 for US)

# --- REGULARIZATION PARAMETERS ---
# Stronger regularization than paper (Swedish market is smaller)

LAMBDA_COV <- 1e-3           # Covariance regularization (10x paper's 1e-4)
LAMBDA_COV_FACTOR <- 1e-4    # Factor covariance regularization (10x paper's 1e-5)

# --- DATA PATHS ---
# Relative to src/analysis/step1_ptree/ when running main.R
DATA_PATH <- "../../../results/ptree_34chars/ptree_ready_data_34chars.csv"
OUTPUT_DIR <- "../../../results/ptree_34chars"

# --- SCENARIO CONFIGURATIONS ---

SCENARIOS <- list(
  full_sample = list(
    name = "Scenario A: Full Sample",
    split_date = NULL,
    train_filter = function(date) TRUE,
    test_filter = NULL
  ),
  
  time_split = list(
    name = "Scenario B: Time Split",
    split_date = as.Date('2010-01-01'),
    train_filter = function(date, split) date < split,
    test_filter = function(date, split) date >= split
  ),
  
  reverse_split = list(
    name = "Scenario C: Reverse Split",
    split_date = as.Date('2010-01-01'),
    train_filter = function(date, split) date >= split,
    test_filter = function(date, split) date < split
  )
)

# --- ROLLING WINDOW PARAMETERS ---

ROLLING_TRAIN_MONTHS <- 60   # 5 years training window
ROLLING_TEST_MONTHS <- 12    # 1 year test window
ROLLING_STEP_MONTHS <- 12    # 1 year roll step (non-overlapping)

# --- DISPLAY CONFIGURATION ---

cat("================================================================================\n")
cat("P-TREE ANALYSIS CONFIGURATION\n")
cat("================================================================================\n\n")
cat("BOOSTED P-TREE PARAMETERS (ADAPTED FOR SWEDISH MARKET):\\n")
cat("  min_leaf_size     =", MIN_LEAF_SIZE, "(halved for Swedish market)\\n")
cat("  max_depth         =", MAX_DEPTH, "(reduced for Swedish market)\\n")
cat("  num_iter          =", NUM_ITER, "(reduced for Swedish market)\\n")
cat("  num_cutpoints     =", NUM_CUTPOINTS, "(same as paper)\n")
cat("  num_trees         =", NUM_TREES, "(boosted trees: 5 vs paper's 20)\n")
cat("  lambda_cov        =", LAMBDA_COV, "(10x paper for Swedish market)\n")
cat("  lambda_cov_factor =", LAMBDA_COV_FACTOR, "(10x paper for Swedish market)\n")
cat("  equal_weight      = FALSE (value-weighted portfolios)\n")
cat("  Rationale: Smaller Swedish market (~300 stocks vs ~2,500 US)\n")
cat("             uses fewer boosted trees (5 vs 20) with stronger regularization\n\n")
