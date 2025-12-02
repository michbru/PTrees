#!/usr/bin/env Rscript

# A4: Visualize Results (Consolidated)
# -------------------------------------
# Generates key tables and figures from Steps 2–3 for the thesis:
# - Tables: descriptive stats, coverage, factor stats, regression diagnostics
# - Figures: cumulative returns per scenario, variable importance, performance bars, correlations, split diagram

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(lmtest)
  library(sandwich)
  library(PTree)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- tryCatch(dirname(normalizePath(file_arg)), error = function(e) getwd())
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = FALSE)

# Paths
in_rds <- file.path(repo_root, "results", "inputs", "ptree_inputs.rds")
models_dir <- file.path(repo_root, "results", "models")
eval_dir <- file.path(repo_root, "results", "evaluation")
out_dir <- file.path(repo_root, "results", "thesis_visualisations")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# Ensure thesis visualisations folder has no stale tables
unlink(Sys.glob(file.path(out_dir, "*.csv")))
unlink(Sys.glob(file.path(out_dir, "*.tex")))

# Minimal LaTeX table writer (for benchmarking table only)
write_tex_table <- function(dt, file, caption = NULL, label = NULL, digits = 3) {
  if (!inherits(dt, "data.table")) dt <- as.data.table(dt)
  for (cn in names(dt)) if (is.numeric(dt[[cn]])) dt[[cn]] <- round(dt[[cn]], digits)
  cols <- names(dt)
  con <- file(file, open = "wt"); on.exit(close(con))
  writeLines("\\begin{table}[!ht]", con)
  writeLines("\\centering", con)
  if (!is.null(caption)) writeLines(paste0("\\caption{", caption, "}"), con)
  if (!is.null(label)) writeLines(paste0("\\label{", label, "}"), con)
  writeLines(paste0("\\begin{tabular}{", paste(rep("l", length(cols)), collapse = "|"), "}"), con)
  writeLines("\\hline", con)
  writeLines(paste(cols, collapse = " & "), con)
  writeLines("\\\\\\hline", con)
  apply(dt, 1, function(row) writeLines(paste(row, collapse = " & "), con))
  writeLines("\\\\\\hline", con)
  writeLines("\\end{tabular}", con)
  writeLines("\\end{table}", con)
}

cat("\n=== A4: VISUALIZE RESULTS (CONSOLIDATED) ===\n")
cat("Repo root:", repo_root, "\n\n")

if (!file.exists(in_rds)) stop("Inputs RDS not found. Run Step 1 first.")
inp <- readRDS(in_rds)
dt <- copy(inp$dt)

# Scenarios (files from Step 2)
scenarios <- list(
  list(name = "A: Full Sample (Single)",  file = file.path(models_dir, "scenario_a_single_factor.csv")),
  list(name = "A: Full Sample (Boosted)", file = file.path(models_dir, "scenario_a_boosted_factor.csv")),
  list(name = "B: Time-Split (Single)",   file = file.path(models_dir, "scenario_b_single_test_factor.csv")),
  list(name = "B: Time-Split (Boosted)",  file = file.path(models_dir, "scenario_b_boosted_test_factor.csv")),
  list(name = "C: Reverse Split (Single)",file = file.path(models_dir, "scenario_c_single_test_factor.csv")),
  list(name = "C: Reverse Split (Boosted)",file = file.path(models_dir, "scenario_c_boosted_test_factor.csv"))
)

## No table writers; visuals only

## No Table 1 output (LaTeX removed)

# ==============================================================================
# 2. FIGURE 1: CUMULATIVE RETURNS
# ==============================================================================
cat("Generating Cumulative Return Figures...\n")

# Helper to compute cumulative plot for a factor vs simple EW market
plot_cumulative <- function(factor_file, title_suffix, out_name) {
  if (!file.exists(factor_file)) {
    cat("  Skipping (missing):", basename(factor_file), "\n")
    return(NULL)
  }
  f <- fread(factor_file)
  f[, date := as.IDate(date)]
  f[, Strategy := "P-Tree Factor"]
  f[, Return := factor]

  market <- dt[, .(Return = mean(ret_next * 100, na.rm=TRUE)), by=date]
  market[, Strategy := "Market (EW)"]

  combined <- rbind(f[, .(date, Strategy, Return)], market[, .(date, Strategy, Return)])
  setorder(combined, date)
  combined[, Cumulative := cumprod(1 + Return/100) - 1, by=Strategy]

  p <- ggplot(combined, aes(x=date, y=Cumulative*100, color=Strategy)) +
    geom_line(linewidth=1) +
    geom_hline(yintercept=0, linetype="dashed", color="gray50") +
    scale_color_manual(values=c("P-Tree Factor"="#2E86AB", "Market (EW)"="#A23B72")) +
    labs(title=paste0("Cumulative Returns: ", title_suffix), x="", y="Cumulative Return (%)") +
    theme_minimal(base_size=12) + theme(legend.position="bottom", plot.title=element_text(face="bold"))

  ggsave(file.path(out_dir, out_name), p, width=10, height=6, dpi=300)
  cat("  Saved:", out_name, "\n")
}

plot_cumulative(file.path(models_dir, "scenario_a_single_factor.csv"),  "A (Full Sample, Single)",  "figure_cum_A_single.png")
plot_cumulative(file.path(models_dir, "scenario_a_boosted_factor.csv"), "A (Full Sample, Boosted)", "figure_cum_A_boosted.png")
plot_cumulative(file.path(models_dir, "scenario_b_single_test_factor.csv"),  "B (OOS, Single)",  "figure_cum_B_single.png")
plot_cumulative(file.path(models_dir, "scenario_b_boosted_test_factor.csv"), "B (OOS, Boosted)", "figure_cum_B_boosted.png")
plot_cumulative(file.path(models_dir, "scenario_c_single_test_factor.csv"),  "C (OOS, Single)",  "figure_cum_C_single.png")
plot_cumulative(file.path(models_dir, "scenario_c_boosted_test_factor.csv"), "C (OOS, Boosted)", "figure_cum_C_boosted.png")

# ==============================================================================
# 3. FIGURE 2: TREE STRUCTURE (DECODED)
# ==============================================================================
cat("Generating Tree Structure Text (A scenarios)...\n")

# Characteristic mapping
char_map <- setNames(inp$char_cols, as.character(0:(length(inp$char_cols)-1)))

# Simple parser
parse_tree_text <- function(tree_file) {
  lines <- readLines(tree_file)
  if (length(lines) < 2) return("Single Node Tree")
  
  desc <- c("Root Node")
  for (i in 2:length(lines)) {
    parts <- as.numeric(strsplit(trimws(lines[i]), "\\s+")[[1]])
    if (length(parts) < 5 || parts[2] == 0) next
    
    var_name <- char_map[as.character(parts[2])]
    threshold <- parts[3]
    desc <- c(desc, sprintf("|-- Split on %s (Threshold: %.2f)", var_name, threshold))
  }
  paste(desc, collapse="\n")
}

tree_text_single <- parse_tree_text(file.path(models_dir, "scenario_a_single_tree.txt"))
writeLines(tree_text_single, file.path(out_dir, "tree_structure_A_single.txt"))
tree_text_boost  <- parse_tree_text(file.path(models_dir, "scenario_a_boosted_tree.txt"))
writeLines(tree_text_boost,  file.path(out_dir, "tree_structure_A_boosted.txt"))
cat("  Saved: tree_structure_A_single.txt, tree_structure_A_boosted.txt\n")

# ==============================================================================
# 4. FIGURE 3: VARIABLE IMPORTANCE
# ==============================================================================
cat("Generating Variable Importance (A scenarios)...\n")

# Count splits in Scenario A tree
plot_importance <- function(tree_file, title_suffix, out_name) {
  if (!file.exists(tree_file)) {
    cat("  Skipping (missing):", basename(tree_file), "\n")
    return(NULL)
  }
  tree_lines <- readLines(tree_file)
  counts <- table(sapply(tree_lines[-1], function(x) {
    parts <- as.numeric(strsplit(trimws(x), "\\s+")[[1]])
    if (length(parts) >= 5 && parts[2] != 0) char_map[as.character(parts[2])] else NA
  }))
  importance <- data.table(Characteristic = names(counts), Count = as.numeric(counts))
  importance <- importance[!is.na(Characteristic)]
  setorder(importance, -Count)
  if (nrow(importance) == 0) { cat("  No splits found for", basename(tree_file), "\n"); return(NULL) }
  p <- ggplot(importance, aes(x=reorder(Characteristic, Count), y=Count)) +
    geom_bar(stat="identity", fill="#2E86AB", width=0.6) +
    coord_flip() +
    labs(title=paste0("Variable Importance: ", title_suffix), x="", y="Split Count") +
    theme_minimal(base_size=12) + theme(plot.title=element_text(face="bold"))
  ggsave(file.path(out_dir, out_name), p, width=8, height=6, dpi=300)
  cat("  Saved:", out_name, "\n")
}

plot_importance(file.path(models_dir, "scenario_a_single_tree.txt"),  "A (Single)",  "figure_importance_A_single.png")
plot_importance(file.path(models_dir, "scenario_a_boosted_tree.txt"), "A (Boosted)", "figure_importance_A_boosted.png")

# ==============================================================================
# 5. FIGURE 4: PERFORMANCE COMPARISON
# ==============================================================================
cat("Generating Performance Comparison (Sharpe ratios)...\n")

summary_all <- fread(file.path(models_dir, "all_scenarios_summary.csv"))
summary_all[, Type := ifelse(grepl("Test", period), "Out-of-Sample", "In-Sample")]

p_sharpe <- ggplot(summary_all, aes(x=scenario, y=sharpe, fill=Type)) +
  geom_bar(stat="identity", width=0.6) +
  geom_hline(yintercept=0, color="black") +
  scale_fill_manual(values=c("In-Sample"="#2E86AB", "Out-of-Sample"="#A23B72")) +
  labs(title="Model Performance Across Scenarios", x="", y="Sharpe Ratio") +
  theme_minimal(base_size=12) + theme(legend.position="bottom", plot.title=element_text(face="bold")) +
  coord_flip()

ggsave(file.path(out_dir, "figure_performance_sharpe.png"), p_sharpe, width=10, height=6, dpi=300)
cat("  Saved: figure_performance_sharpe.png\n")

# Mean-Std scatter (akin to the paper's mean-std exhibits)
cat("Generating mean-std scatter...\n")
ms_rows <- list()
for (sc in scenarios) {
  if (!file.exists(sc$file)) next
  f <- fread(sc$file)
  x <- as.numeric(f$factor)
  ms_rows[[length(ms_rows)+1]] <- data.table(scenario = sc$name,
                                             mean = mean(x, na.rm=TRUE),
                                             sd = sd(x, na.rm=TRUE))
}
ms <- rbindlist(ms_rows, fill = TRUE)
if (nrow(ms)) {
  if (!requireNamespace("ggrepel", quietly = TRUE)) {
    warning("ggrepel not installed; labels may overlap in mean-std figure")
    p_ms <- ggplot(ms, aes(x=sd, y=mean)) +
      geom_point(color="#2E86AB", size=3) +
      geom_text(aes(label=scenario), hjust=0, vjust=1, size=3) +
      labs(title="Mean vs. Std of Monthly P-Tree Factor Returns", x="Std (pct)", y="Mean (pct)") +
      theme_minimal(base_size=12)
  } else {
    p_ms <- ggplot(ms, aes(x=sd, y=mean, label=scenario)) +
      geom_point(color="#2E86AB", size=3) +
      ggrepel::geom_text_repel(size=3, max.overlaps=20) +
      labs(title="Mean vs. Std of Monthly P-Tree Factor Returns", x="Std (pct)", y="Mean (pct)") +
      theme_minimal(base_size=12)
  }
  ggsave(file.path(out_dir, "figure_mean_std.png"), p_ms, width=9, height=6, dpi=300)
  cat("  Saved: figure_mean_std.png\n")
}

# ==============================================================================
# 6. FIGURE 5: CHARACTERISTIC CORRELATION HEATMAP
# ==============================================================================
cat("Generating Characteristic Correlation Heatmap...\n")

# Select numeric columns starting with "rank_"
char_cols <- grep("^rank_", names(dt), value=TRUE)
# Filter to a curated set to avoid overcrowding
base_keys <- c("rank_mom12m", "rank_bm", "rank_me", "rank_roa",
               "rank_op", "rank_inv", "rank_lev", "rank_mom1m", "rank_mom36m")
key_chars_ext <- intersect(base_keys, char_cols)

dt_corr <- dt[, ..key_chars_ext]
dt_corr <- dt_corr[complete.cases(dt_corr)]

if (nrow(dt_corr) > 0) {
  cor_matrix <- cor(dt_corr)
  cor_dt <- as.data.table(cor_matrix, keep.rownames = TRUE)
  cor_melt <- melt(cor_dt, id.vars = "rn", variable.name = "Var2", value.name = "value")
  setnames(cor_melt, "rn", "Var1")
  
  p5 <- ggplot(cor_melt, aes(Var1, Var2, fill=value)) +
    geom_tile() +
    scale_fill_gradient2(low="#A23B72", mid="white", high="#2E86AB", midpoint=0, limit=c(-1,1)) +
    theme_minimal(base_size=10) +
    theme(axis.text.x = element_text(angle=45, vjust=1, hjust=1),
          axis.title = element_blank(),
          plot.title = element_text(face="bold")) +
    labs(title="Characteristic Correlation Matrix")
  
  ggsave(file.path(out_dir, "figure_correlation_heatmap.png"), p5, width=10, height=8, dpi=300)
  cat("  Saved: figure_correlation_heatmap.png\n")
}

## No Table 2 output (LaTeX removed)

# ==============================================================================
# 8. FIGURE 6: TIME PERIOD SPLIT DIAGRAM
# ==============================================================================
cat("Generating Time Period Split Diagram...\n")

# Define periods
periods <- data.table(
  Scenario = c("A: Full Sample", "A: Full Sample", 
               "B: Time-Split", "B: Time-Split", 
               "C: Reverse Split", "C: Reverse Split"),
  Type = c("Train", "Test (In-Sample)", 
           "Train", "Test (Out-of-Sample)", 
           "Test (Out-of-Sample)", "Train"),
  Start = as.Date(c("1999-06-01", "1999-06-01", 
                    "1999-06-01", "2010-01-01", 
                    "1999-06-01", "2010-01-01")),
  End = as.Date(c("2019-12-31", "2019-12-31", 
                  "2009-12-31", "2019-12-31", 
                  "2009-12-31", "2019-12-31"))
)

# Order scenarios for plotting
periods[, Scenario := factor(Scenario, levels=c("C: Reverse Split", "B: Time-Split", "A: Full Sample"))]

p6 <- ggplot(periods, aes(y=Scenario, x=Start, xend=End, color=Type)) +
  geom_segment(linewidth=6) +
  scale_color_manual(values=c("Train"="#2E86AB", "Test (Out-of-Sample)"="#A23B72", "Test (In-Sample)"="#6D9DC5")) +
  scale_x_date(date_breaks="2 years", date_labels="%Y") +
  labs(
    title="Data Splitting Scenarios",
    subtitle="Training and Testing Periods",
    x="", y=""
  ) +
  theme_minimal(base_size=12) +
  theme(legend.position="bottom", plot.title=element_text(face="bold"))

ggsave(file.path(out_dir, "figure_time_splits.png"), p6, width=10, height=5, dpi=300)
cat("  Saved: figure_time_splits.png\n")

# ==============================================================================
# 9. FACTOR DESCRIPTIVES (all scenarios)
# ==============================================================================
## No factor descriptive tables (LaTeX removed)

# ==============================================================================
# 10. REGRESSION DIAGNOSTICS (CAPM and FF3)
# ==============================================================================
## No regression diagnostics table (LaTeX removed)

# ==============================================================================
# 11. PERFORMANCE + ALPHA SUMMARY (from Step 3)
# ==============================================================================
## No performance+alpha LaTeX table

# ==============================================================================
# 12. ALPHA–BETA SCATTER (CAPM, NW robust)
# ==============================================================================
cat("Generating alpha–beta scatter (CAPM, NW robust)...\n")

# Load factors only for this figure
ff_path <- Sys.getenv("PTREE_FF_CSV")
if (!nzchar(ff_path)) {
  shof_default <- file.path(repo_root, "data", "raw", "macro", "raw_macro_factors.csv")
  if (file.exists(shof_default)) {
    ff_path <- shof_default
  } else {
    ff_path <- file.path(repo_root, "data", "raw", "FamaFrench2020", "FF4F_monthly.csv")
  }
}
ff <- fread(ff_path)
if (!"ym" %in% names(ff)) {
  if ("date" %in% names(ff)) ff[, ym := format(as.IDate(date), "%Y-%m")] else stop("Macro factors need ym or date column")
}
if ("rm_rf" %in% names(ff) && !"mkt_rf" %in% names(ff)) ff[, mkt_rf := rm_rf]
if ("smb_ew" %in% names(ff) && !"smb" %in% names(ff)) ff[, smb := smb_ew]
if ("hml_ew" %in% names(ff) && !"hml" %in% names(ff)) ff[, hml := hml_ew]
for (col in c("mkt_rf","smb","hml")) if (col %in% names(ff) && max(abs(ff[[col]]), na.rm=TRUE) < 10) ff[[col]] <- ff[[col]] * 100

ab_rows <- list()
for (sc in scenarios) {
  if (!file.exists(sc$file)) next
  f <- fread(sc$file)
  f[, ym := format(as.IDate(date), "%Y-%m")]
  d <- merge(f, ff, by="ym", all.x=TRUE)
  # normalize columns as done above
  if (!"mkt_rf" %in% names(d) && "rm_rf" %in% names(d)) d[, mkt_rf := rm_rf]
  for (col in c("mkt_rf")) if (col %in% names(d) && max(abs(d[[col]]), na.rm=TRUE) < 10) d[[col]] <- d[[col]] * 100
  d <- d[complete.cases(d[, .(factor, mkt_rf)])]
  if (nrow(d) < 24) next
  m <- lm(factor ~ mkt_rf, data = d)
  vc <- NeweyWest(m, lag = 12)
  ct <- coeftest(m, vcov = vc)
  alpha_m <- as.numeric(coef(m)["(Intercept)"])
  beta <- as.numeric(coef(m)["mkt_rf"])
  t_alpha <- as.numeric(ct["(Intercept)", "t value"])
  t_beta  <- as.numeric(ct["mkt_rf", "t value"])
  ab_rows[[length(ab_rows)+1]] <- data.table(
    scenario = sc$name,
    alpha_ann = alpha_m * 12,
    t_alpha = t_alpha,
    beta = beta,
    t_beta = t_beta
  )
}
ab <- rbindlist(ab_rows, fill = TRUE)
if (nrow(ab)) {
  p_ab <- ggplot(ab, aes(x=beta, y=alpha_ann, label=scenario)) +
    geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
    geom_vline(xintercept = 1, linetype = "dotted", color = "gray70") +
    geom_point(color="#2E86AB", size=3) +
    {if (requireNamespace("ggrepel", quietly = TRUE)) ggrepel::geom_text_repel(size=3) else geom_text(hjust=0, vjust=1, size=3)} +
    labs(title = "Alpha–Beta (CAPM) across scenarios", x = "Beta (MKT)", y = "Annualized Alpha (%)") +
    theme_minimal(base_size=12)
  ggsave(file.path(out_dir, "figure_alpha_beta.png"), p_ab, width=9, height=6, dpi=300)
  cat("  Saved: figure_alpha_beta.png\n")
}

# ==============================================================================
# 13. LEAF BASIS PORTFOLIO EVALUATION (Scenario A, Single+Boosted)
# ==============================================================================
cat("Evaluating leaf basis portfolios for Scenario A...\n")

build_data <- function(dt_sub) {
  Xdt <- dt_sub[, ..inp$char_cols]
  # Ensure numeric matrix
  for (cn in names(Xdt)) if (!is.numeric(Xdt[[cn]])) Xdt[[cn]] <- as.numeric(Xdt[[cn]])
  X <- as.matrix(Xdt)
  R <- as.numeric(dt_sub$ret_next) * 100
  months <- as.integer(as.factor(dt_sub$date)) - 1L
  weight <- as.numeric(dt_sub$lag_me)
  list(X=X, R=R, months=months, weight=weight, dates=sort(unique(dt_sub$date)))
}

eval_leaf_model <- function(model_path, dt_sub) {
  if (!file.exists(model_path)) return(NULL)
  # Try prediction; if not available, try loading from saved CSVs (Scenario A only)
  try_pred <- try({
    mdl <- readRDS(model_path)
    d <- build_data(dt_sub)
    pred <- predict(mdl, d$X, d$R, d$months, d$weight)
    leaf_mat <- as.matrix(pred$portfolio) # rows=months, cols=leaves
    list(returns=leaf_mat, dates=d$dates)
  }, silent = TRUE)
  if (!inherits(try_pred, "try-error")) return(try_pred)
  # Fallback: if Scenario A, load from files saved by Step 2
  if (grepl("scenario_a_", basename(model_path))) {
    tag <- if (grepl("single", basename(model_path))) "scenario_a_single" else "scenario_a_boosted"
    leaf_file <- file.path(models_dir, sprintf("%s_leaf_portfolios.csv", tag))
    fact_file <- file.path(models_dir, sprintf("%s_factor.csv", tag))
    if (file.exists(leaf_file) && file.exists(fact_file)) {
      lf <- fread(leaf_file)
      ff <- fread(fact_file)
      ff[, date := as.IDate(date)]
      return(list(returns=as.matrix(lf), dates=sort(unique(ff$date))))
    }
  }
  NULL
}

# Scenario A uses full sample
dt_full <- copy(dt)
leaf_a_single <- eval_leaf_model(file.path(models_dir, "scenario_a_single_model.rds"), dt_full)
leaf_a_boost  <- eval_leaf_model(file.path(models_dir, "scenario_a_boosted_model.rds"), dt_full)

leaf_stats <- function(leaf_obj, tag) {
  if (is.null(leaf_obj)) return(NULL)
  m <- leaf_obj$returns
  cols <- ncol(m)
  rows <- list()
  for (j in seq_len(cols)) {
    x <- as.numeric(m[, j])
    rows[[length(rows)+1]] <- data.table(
      scenario = tag,
      leaf = j,
      n = sum(is.finite(x)),
      mean_monthly = mean(x, na.rm=TRUE),
      sd_monthly = sd(x, na.rm=TRUE),
      sharpe = ifelse(sd(x, na.rm=TRUE)>0, mean(x, na.rm=TRUE)/sd(x, na.rm=TRUE)*sqrt(12), NA_real_),
      min = min(x, na.rm=TRUE), p05 = quantile(x, 0.05, na.rm=TRUE), median = median(x, na.rm=TRUE),
      p95 = quantile(x, 0.95, na.rm=TRUE), max = max(x, na.rm=TRUE)
    )
  }
  rbindlist(rows)
}

ls_single <- leaf_stats(leaf_a_single, "A (Single)")
ls_boost  <- leaf_stats(leaf_a_boost,  "A (Boosted)")
leaf_eval <- rbindlist(list(ls_single, ls_boost), fill = TRUE)
## No leaf basis LaTeX table; stats computed if needed downstream

# ==============================================================================
# 14. EFFICIENT FRONTIER (Scenario A Boosted leaves + Market)
# ==============================================================================
cat("Generating efficient frontier (Scenario A Boosted leaves + Market)...\n")

compute_frontier <- function(Rmat) {
  # Rmat: T x N returns in percent
  mu <- colMeans(Rmat, na.rm=TRUE)
  S <- cov(Rmat, use = "pairwise.complete.obs")
  # Regularize covariance if needed
  eps <- 1e-6
  S <- S + diag(eps, ncol(S))
  Sinv <- tryCatch(solve(S), error=function(e) MASS::ginv(S))
  one <- rep(1, length(mu))
  A <- as.numeric(t(one) %*% Sinv %*% one)
  B <- as.numeric(t(one) %*% Sinv %*% mu)
  C <- as.numeric(t(mu)  %*% Sinv %*% mu)
  D <- A*C - B^2
  mseq <- seq(min(mu), max(mu), length.out = 100)
  vars <- (A * mseq^2 - 2 * B * mseq + C) / D
  data.table(mean = mseq, sd = sqrt(pmax(vars, 0)))
}

if (!is.null(leaf_a_boost)) {
  # Build returns: leaf columns + market EW
  m <- leaf_a_boost$returns
  keep <- which(colSums(abs(m)) > 0)
  m <- m[, keep, drop=FALSE]
  # market EW from dt
  market <- dt_full[, .(date, ret = mean(ret_next * 100, na.rm=TRUE))]
  market <- market[date %in% leaf_a_boost$dates]
  market <- market[match(leaf_a_boost$dates, market$date)]
  Rmat <- cbind(m, market$ret)
  ef <- compute_frontier(Rmat)
  pts <- data.table(asset = c(paste0("Leaf", seq_len(ncol(m))), "Market"),
                    mean = colMeans(Rmat, na.rm=TRUE),
                    sd = apply(Rmat, 2, sd, na.rm=TRUE))
  p_ef <- ggplot() +
    geom_path(data = ef, aes(x=sd, y=mean), color="#2E86AB", linewidth=1) +
    geom_point(data = pts, aes(x=sd, y=mean), color="#A23B72") +
    labs(title = "Efficient Frontier (Scenario A Boosted Leaves + Market)", x = "Std (pct)", y = "Mean (pct)") +
    theme_minimal(base_size=12)
  ggsave(file.path(out_dir, "figure_efficient_frontier_A_boosted.png"), p_ef, width=9, height=6, dpi=300)
  cat("  Saved: figure_efficient_frontier_A_boosted.png\n")
}

# ==============================================================================
# 15. BENCHMARKING TABLE (from Step 3, LaTeX)
# ==============================================================================
bench_csv <- file.path(eval_dir, "final_results_table.csv")
if (file.exists(bench_csv)) {
  cat("Generating benchmarking table (LaTeX)...\n")
  bench <- fread(bench_csv)
  setnames(bench, old = c("return_pct"), new = c("ann_return"), skip_absent = TRUE)
  keep <- c("scenario","n_months","sharpe","ann_return","capm_alpha","capm_tstat","ff3_alpha","ff3_tstat","leaves")
  bench_out <- bench[, intersect(keep, names(bench)), with=FALSE]
  write_tex_table(bench_out, file.path(out_dir, "table_benchmarking.tex"),
                  caption = "Benchmarking P-Tree factors against CAPM and FF3 (Newey–West)",
                  label = "tab:benchmarking")
  cat("  Saved: table_benchmarking.tex\n")
} else {
  cat("Warning: final_results_table.csv not found; skip benchmarking LaTeX table\n")
}

cat("\nAll visualisations saved to:", out_dir, "\n")
