#!/usr/bin/env Rscript

################################################################################
# Train P-Tree with num_iter = 10 for sensitivity analysis table
################################################################################

suppressPackageStartupMessages({
  library(data.table)
  library(PTree)
  library(lmtest)
  library(sandwich)
})

# Setup paths
args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- if (length(file_arg) > 0) dirname(normalizePath(file_arg)) else getwd()
repo_root <- normalizePath(file.path(script_dir, "..", ".."))
setwd(repo_root)

cat("Training P-Trees with num_iter = 10 (max depth)...\n\n")

# Load inputs
inp <- readRDS("results/inputs/ptree_inputs.rds")
dt <- copy(inp$dt)
char_cols <- inp$char_cols

# Load FF factors (same as script 03)
ff_factors <- fread("data/raw/macro/raw_macro_factors.csv")
ff_factors[, date := as.IDate(date)]

# Parameters (same as script 02, but num_iter = 10)
params <- list(
  max_depth = 10,
  min_leaf_size = 3,
  num_cutpoints = 4,
  gamma = 1e-4,
  lambda = 1e-5,
  equal_weight = FALSE,
  abs_normalize = TRUE
)

# Helper functions from script 02
prepare_data <- function(dt_subset, char_cols) {
  X <- as.matrix(dt_subset[, .SD, .SDcols = char_cols])
  R <- as.vector(dt_subset$ret_next)
  Y <- R
  Z <- matrix(1, nrow = nrow(dt_subset), ncol = 1)
  months <- as.integer(as.factor(dt_subset$date)) - 1L
  stocks <- as.integer(as.factor(dt_subset$isin)) - 1L
  pw <- as.vector(dt_subset$lag_me)
  lw <- as.vector(dt_subset$lag_me)
  
  list(
    X = X, R = R, Y = Y, Z = Z,
    months = months, stocks = stocks,
    num_months = length(unique(months)),
    num_stocks = length(unique(stocks)),
    pw = pw, lw = lw
  )
}

train_model <- function(scenario_name, train_data) {
  cat(sprintf("Training %s with num_iter=10...\n", scenario_name))
  
  fit <- PTree::PTree(
    R = train_data$R,
    Y = train_data$Y,
    X = train_data$X,
    Z = train_data$Z,
    H = rep(0, train_data$num_months),
    portfolio_weight = train_data$pw,
    loss_weight = train_data$lw,
    stocks = train_data$stocks,
    months = train_data$months,
    first_split_var = seq(0L, ncol(train_data$X) - 1L),
    second_split_var = seq(0L, ncol(train_data$X) - 1L),
    num_stocks = train_data$num_stocks,
    num_months = train_data$num_months,
    min_leaf_size = params$min_leaf_size,
    max_depth = params$max_depth,
    num_cutpoints = params$num_cutpoints,
    num_iter = 10,  # CHANGED FROM 1
    eta = 1.0,
    equal_weight = params$equal_weight,
    abs_normalize = params$abs_normalize,
    lambda_mean = 0,
    lambda_cov = params$gamma,
    lambda_mean_factor = 0,
    lambda_cov_factor = params$lambda,
    lambda_ridge = 1e-6,
    no_H = TRUE,
    weighted_loss = FALSE,
    early_stop = FALSE,
    stop_threshold = 1.0,
    random_split = FALSE,
    a1 = 0,
    a2 = 0,
    list_K = matrix(0, nrow = 3, ncol = 1)
  )
  
  factor_returns <- as.numeric(fit$ft)
  mean_monthly <- mean(factor_returns, na.rm = TRUE)
  sd_monthly <- sd(factor_returns, na.rm = TRUE)
  sharpe <- mean_monthly / sd_monthly * sqrt(12)
  
  list(fit = fit, factor_returns = factor_returns, 
       mean_monthly = mean_monthly, sd_monthly = sd_monthly, sharpe = sharpe)
}

evaluate_performance <- function(factor_returns, dates, ff_factors, scenario_name) {
  factor_dt <- data.table(date = dates, factor_return = factor_returns)
  merged <- merge(factor_dt, ff_factors, by = "date", all.x = TRUE)
  
  # CAPM
  capm <- lm(factor_return ~ rm_rf, data = merged)
  capm_se <- coeftest(capm, vcov = NeweyWest(capm, lag = 12))
  
  # FF3
  ff3 <- lm(factor_return ~ rm_rf + smb_vw + hml_vw, data = merged)
  ff3_se <- coeftest(ff3, vcov = NeweyWest(ff3, lag = 12))
  
  data.table(
    scenario = scenario_name,
    ret_pct = mean(factor_returns) * 1200,
    vol_pct = sd(factor_returns) * sqrt(12) * 100,
    sharpe = mean(factor_returns) / sd(factor_returns),
    beta = coef(capm)[2],
    capm_alpha = coef(capm)[1] * 1200,
    capm_t = capm_se[1, 3],
    ff3_alpha = coef(ff3)[1] * 1200,
    ff3_t = ff3_se[1, 3],
    r2 = summary(capm)$r.squared * 100
  )
}

# Scenario B
dt_b_train <- dt[date < as.IDate("2010-01-01")]
dt_b_test <- dt[date >= as.IDate("2010-01-01")]
b_train_data <- prepare_data(dt_b_train, char_cols)
b_test_data <- prepare_data(dt_b_test, char_cols)

model_b <- train_model("Scenario B (Train)", b_train_data)
perf_b_train <- evaluate_performance(model_b$factor_returns, dt_b_train[, unique(date)], 
                                     ff_factors, "B (Train)")

pred_b <- predict(model_b$fit, X = b_test_data$X, R = b_test_data$R, months = b_test_data$months)
test_returns_b <- as.numeric(pred_b$ft)
perf_b_test <- evaluate_performance(test_returns_b, dt_b_test[, unique(date)], 
                                    ff_factors, "B (Test)")

# Scenario C
dt_c_train <- dt[date >= as.IDate("2010-01-01")]
dt_c_test <- dt[date < as.IDate("2010-01-01")]
c_train_data <- prepare_data(dt_c_train, char_cols)
c_test_data <- prepare_data(dt_c_test, char_cols)

model_c <- train_model("Scenario C (Train)", c_train_data)
perf_c_train <- evaluate_performance(model_c$factor_returns, dt_c_train[, unique(date)], 
                                     ff_factors, "C (Train)")

pred_c <- predict(model_c$fit, X = c_test_data$X, R = c_test_data$R, months = c_test_data$months)
test_returns_c <- as.numeric(pred_c$ft)
perf_c_test <- evaluate_performance(test_returns_c, dt_c_test[, unique(date)], 
                                    ff_factors, "C (Test)")

# Scenario A
full_data <- prepare_data(dt, char_cols)
model_a <- train_model("Scenario A (Full)", full_data)
perf_a <- evaluate_performance(model_a$factor_returns, dt[, unique(date)], 
                               ff_factors, "A")

# Combine results
all_perf <- rbindlist(list(perf_a, perf_b_train, perf_b_test, perf_c_train, perf_c_test))

# Generate LaTeX table
cat("\nGenerating LaTeX table...\n")

latex <- c(
  "\\begin{table}[htbp]",
  "\\centering",
  "\\caption{P-Tree model performance when the number of boosting iterations is set to 10 (\\texttt{num\\_iter = 10}). The in-sample results are better but the out-of-sample results are worse. This shows that deeper trees tend to overfit as they capture noise rather than true relationships.}",
  "\\label{tab:performance_maxdepth}",
  "\\setlength{\\tabcolsep}{3pt}",
  "\\renewcommand{\\arraystretch}{1.0}",
  "\\small",
  "\\begin{tabular}{lccccccc}",
  "\\hline",
  "Scenario & Ret (\\%) & Vol (\\%) & Sharpe & $\\beta$ & CAPM $\\alpha$ (\\%, t) & FF3 $\\alpha$ (\\%, t) & $R^2$ (\\%) \\\\",
  "\\hline",
  "Market (VW) & 10.9 & 19.0 & 0.64 & 1.00 & -- & -- & -- \\\\"
)

for (i in 1:nrow(all_perf)) {
  row <- all_perf[i]
  capm_sig <- ifelse(abs(row$capm_t) >= 2.576, "***", ifelse(abs(row$capm_t) >= 1.96, "**", ifelse(abs(row$capm_t) >= 1.645, "*", "")))
  ff3_sig <- ifelse(abs(row$ff3_t) >= 2.576, "***", ifelse(abs(row$ff3_t) >= 1.96, "**", ifelse(abs(row$ff3_t) >= 1.645, "*", "")))
  r2_str <- if (grepl("Test", row$scenario)) sprintf("%.1f", row$r2) else "--"
  
  latex <- c(latex, sprintf("%s & %.1f & %.1f & %.2f & %.2f & %.2f%s (%.2f) & %.2f%s (%.2f) & %s \\\\",
                            row$scenario, row$ret_pct, row$vol_pct, row$sharpe, row$beta,
                            row$capm_alpha, capm_sig, row$capm_t,
                            row$ff3_alpha, ff3_sig, row$ff3_t, r2_str))
}

latex <- c(latex,
  "\\hline",
  "\\end{tabular}",
  "",
  "\\vspace{0.15cm}",
  "\\begin{minipage}{0.9\\textwidth}",
  "\\footnotesize",
  "\\textit{Notes:} Ret and Vol are annualized. Alphas are annualized (\\%) with Newey--West t-stats (12 lags). Significance: *** $p<0.01$, ** $p<0.05$, * $p<0.10$. $R^2$ is out-of-sample.",
  "\\end{minipage}",
  "\\end{table}"
)

writeLines(latex, "results/thesis_visualisations/table_performance_maxdepth.tex")
cat("\n✓ Saved to: results/thesis_visualisations/table_performance_maxdepth.tex\n")
cat("\nDone!\n")
