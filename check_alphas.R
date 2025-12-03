library(data.table)

# Load factor returns
factor_a <- fread('results/models/scenario_a_1_factor.csv')

cat("=== SCENARIO A FACTOR DIAGNOSTICS ===\n\n")
cat("Sample period:", min(factor_a$date), "to", max(factor_a$date), "\n")
cat("Number of months:", nrow(factor_a), "\n\n")

cat("Factor return statistics:\n")
cat("  Mean: ", sprintf("%.4f", mean(factor_a$factor_return)), " (", sprintf("%.2f%%", mean(factor_a$factor_return)*100), " per month)\n", sep="")
cat("  SD:   ", sprintf("%.4f", sd(factor_a$factor_return)), " (", sprintf("%.2f%%", sd(factor_a$factor_return)*100), " per month)\n", sep="")
cat("  Min:  ", sprintf("%.4f", min(factor_a$factor_return)), " (", sprintf("%.2f%%", min(factor_a$factor_return)*100), ")\n", sep="")
cat("  Max:  ", sprintf("%.4f", max(factor_a$factor_return)), " (", sprintf("%.2f%%", max(factor_a$factor_return)*100), ")\n", sep="")
cat("  Negative months:", sum(factor_a$factor_return < 0), "/", nrow(factor_a), 
    sprintf("(%.1f%%)", sum(factor_a$factor_return < 0)/nrow(factor_a)*100), "\n\n")

cat("Annualized metrics:\n")
cat("  Mean return:", sprintf("%.2f%%", mean(factor_a$factor_return)*12*100), "\n")
cat("  Volatility: ", sprintf("%.2f%%", sd(factor_a$factor_return)*sqrt(12)*100), "\n")
cat("  Sharpe:     ", sprintf("%.3f", mean(factor_a$factor_return)/sd(factor_a$factor_return)*sqrt(12)), "\n\n")

# Check for outliers
cat("Extreme months (|ret| > 10%):\n")
extreme <- factor_a[abs(factor_return) > 0.10]
if (nrow(extreme) > 0) {
  print(extreme)
} else {
  cat("  None\n")
}

cat("\n=== REASONABLENESS CHECK ===\n\n")

# Load FF factors for comparison
ff <- fread('data/raw/FamaFrench2020/FF4F_monthly.csv')
ff[, date := as.IDate(date)]
ff <- ff[date >= min(factor_a$date) & date <= max(factor_a$date)]

cat("Market benchmark (same period):\n")
cat("  Mean market return:", sprintf("%.2f%%", mean(ff$mkt_rf, na.rm=TRUE)*100), "per month\n")
cat("  Market Sharpe:     ", sprintf("%.3f", mean(ff$mkt_rf, na.rm=TRUE)/sd(ff$mkt_rf, na.rm=TRUE)*sqrt(12)), "\n\n")

cat("P-Tree vs Market:\n")
cat("  P-Tree mean / Market mean:", sprintf("%.2fx", mean(factor_a$factor_return)/mean(ff$mkt_rf, na.rm=TRUE)), "\n")
cat("  P-Tree Sharpe / Market Sharpe:", sprintf("%.2fx", 
    (mean(factor_a$factor_return)/sd(factor_a$factor_return)) / (mean(ff$mkt_rf, na.rm=TRUE)/sd(ff$mkt_rf, na.rm=TRUE))), "\n\n")

cat("CONCLUSION:\n")
if (mean(factor_a$factor_return) > 0.02) {
  cat("  ⚠ WARNING: Mean return > 2%/month seems very high\n")
} else if (mean(factor_a$factor_return) > 0.015) {
  cat("  ⚠ CAUTION: Mean return > 1.5%/month is unusual but possible\n")
} else {
  cat("  ✓ Mean return looks reasonable for a factor strategy\n")
}

if (mean(factor_a$factor_return)/mean(ff$mkt_rf, na.rm=TRUE) > 3) {
  cat("  ⚠ WARNING: Factor return > 3x market return is suspicious\n")
} else {
  cat("  ✓ Factor return relative to market looks reasonable\n")
}
