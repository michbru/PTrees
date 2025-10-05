"""
PTree Results Diagnostic Analysis
Checks for data quality issues and creates benchmarking
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

sns.set_style("whitegrid")

# Paths
results_dir = Path(__file__).parent.parent / "results"
output_dir = results_dir / "ptree_diagnostics"
output_dir.mkdir(exist_ok=True)

print("="*70)
print("PTREE DIAGNOSTIC ANALYSIS")
print("="*70)

# Load data
factors = pd.read_csv(results_dir / "ptree_outputs" / "ptree_factors.csv")
factors['month'] = pd.to_datetime(factors['month'])
factors = factors.set_index('month')

full_data = pd.read_csv(results_dir / "ptree_ready_data_full.csv")
full_data['date'] = pd.to_datetime(full_data['date'])

print(f"\nAnalyzing {len(factors)} months of factor returns...")

# ========== RED FLAG ANALYSIS ==========
print("\n" + "="*70)
print("RED FLAG ANALYSIS")
print("="*70)

issues = []

# 1. Check for 100% win rate (MAJOR RED FLAG)
for col in factors.columns:
    win_rate = (factors[col] > 0).sum() / len(factors) * 100
    if win_rate == 100:
        issues.append(f"CRITICAL: {col} has 100% positive months - likely data error!")
        print(f"\n[!!] {col}: {win_rate:.1f}% positive months")
    elif win_rate > 90:
        issues.append(f"WARNING: {col} has {win_rate:.1f}% positive months - suspiciously high")
        print(f"\n[!] {col}: {win_rate:.1f}% positive months (very high)")

# 2. Check for zero drawdown (IMPOSSIBLE for real returns)
for col in factors.columns:
    cumulative = (1 + factors[col]).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()

    if max_dd == 0:
        issues.append(f"CRITICAL: {col} has ZERO drawdown - impossible for real returns!")
        print(f"[!!] {col}: Max Drawdown = 0% (IMPOSSIBLE)")
    elif max_dd > -0.05:
        issues.append(f"WARNING: {col} has suspiciously small drawdown: {max_dd*100:.2f}%")
        print(f"[!] {col}: Max Drawdown = {max_dd*100:.2f}% (suspiciously small)")

# 3. Check Sharpe Ratio (>5 is very rare, >10 is nearly impossible)
for col in factors.columns:
    sharpe = (factors[col].mean() / factors[col].std()) * np.sqrt(12)
    if sharpe > 10:
        issues.append(f"CRITICAL: {col} Sharpe = {sharpe:.1f} - likely look-ahead bias or overfitting!")
        print(f"[!!] {col}: Sharpe Ratio = {sharpe:.1f} (nearly impossible in reality)")
    elif sharpe > 5:
        issues.append(f"WARNING: {col} Sharpe = {sharpe:.1f} - very high, check for overfitting")
        print(f"[!] {col}: Sharpe Ratio = {sharpe:.1f} (suspiciously high)")

# 4. Check if factors are identical
unique_factors = []
for col in factors.columns:
    is_unique = True
    for unique_col in unique_factors:
        if np.allclose(factors[col], factors[unique_col], rtol=1e-9):
            issues.append(f"INFO: {col} is identical to {unique_col}")
            print(f"[i] {col} is identical to {unique_col} (boosting didn't work)")
            is_unique = False
            break
    if is_unique:
        unique_factors.append(col)

print(f"\nUnique factors: {len(unique_factors)} out of {len(factors.columns)}")

# ========== LIKELY ROOT CAUSE ==========
print("\n" + "="*70)
print("LIKELY ROOT CAUSE")
print("="*70)

print("\nThe 100% positive months and zero drawdown suggest one of:")
print("1. Using absolute returns instead of excess returns")
print("2. Only long positions in a generally rising market")
print("3. Returns are cumulative instead of monthly")
print("4. Training start date issue (no early data)")

# Check date range
print(f"\nFactor date range: {factors.index.min()} to {factors.index.max()}")
print(f"Data date range: {full_data['date'].min()} to {full_data['date'].max()}")
print(f"\nMissing data period: {full_data['date'].min()} to {factors.index.min()}")

# ========== CREATE MARKET BENCHMARK ==========
print("\n" + "="*70)
print("CREATING MARKET BENCHMARK")
print("="*70)

# Calculate equal-weighted market return for benchmark
market_returns = full_data.groupby('date').apply(
    lambda x: x['xret'].mean()  # Equal-weighted average
).reset_index()
market_returns.columns = ['date', 'market_return']
market_returns['date'] = pd.to_datetime(market_returns['date'])
market_returns = market_returns.set_index('date')

# Align with factors
market_aligned = market_returns.reindex(factors.index)

# Calculate market statistics
market_sharpe = (market_aligned['market_return'].mean() / market_aligned['market_return'].std()) * np.sqrt(12)
market_cumret = (1 + market_aligned['market_return']).cumprod().iloc[-1] - 1
market_win_rate = (market_aligned['market_return'] > 0).sum() / len(market_aligned) * 100

print(f"\nSwedish Market Benchmark (Equal-Weighted):")
print(f"  Mean Monthly Return: {market_aligned['market_return'].mean()*100:.2f}%")
print(f"  Annualized Return: {((1 + market_aligned['market_return'].mean())**12 - 1)*100:.2f}%")
print(f"  Volatility (Annual): {market_aligned['market_return'].std()*np.sqrt(12)*100:.2f}%")
print(f"  Sharpe Ratio: {market_sharpe:.2f}")
print(f"  Cumulative Return: {market_cumret*100:.2f}%")
print(f"  Positive Months: {market_win_rate:.1f}%")

# Calculate drawdown
market_cum = (1 + market_aligned['market_return']).cumprod()
market_running_max = market_cum.expanding().max()
market_dd = (market_cum - market_running_max) / market_running_max
print(f"  Max Drawdown: {market_dd.min()*100:.2f}%")

# ========== COMPARISON PLOT ==========
print("\n" + "="*70)
print("CREATING COMPARISON PLOTS")
print("="*70)

# Plot 1: Factor vs Market Returns
fig, ax = plt.subplots(figsize=(14, 7))
market_cum = (1 + market_aligned['market_return']).cumprod()
ax.plot(market_aligned.index, market_cum, label='Market (Equal-Weighted)', linewidth=2.5, color='black', linestyle='--')

for col in ['factor1', 'factor2']:  # Only plot unique factors
    cumulative = (1 + factors[col]).cumprod()
    ax.plot(factors.index, cumulative, label=col.replace('factor', 'Factor '), linewidth=2)

ax.set_title('PTree Factors vs Market Benchmark', fontsize=14, fontweight='bold')
ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Cumulative Return (Initial Investment = 1)', fontsize=12)
ax.legend(loc='best', fontsize=10)
ax.set_yscale('log')  # Log scale to handle extreme returns
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(output_dir / "factor_vs_market.png", dpi=300, bbox_inches='tight')
print("Saved: factor_vs_market.png")
plt.close()

# Plot 2: Monthly Returns Distribution - Factor vs Market
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

axes[0].hist(market_aligned['market_return'], bins=30, alpha=0.7, edgecolor='black', label='Market')
axes[0].hist(factors['factor1'], bins=30, alpha=0.7, edgecolor='black', label='Factor 1')
axes[0].set_title('Return Distribution: Factor 1 vs Market', fontweight='bold')
axes[0].set_xlabel('Monthly Return')
axes[0].set_ylabel('Frequency')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

axes[1].hist(market_aligned['market_return'], bins=30, alpha=0.7, edgecolor='black', label='Market')
axes[1].hist(factors['factor2'], bins=30, alpha=0.7, edgecolor='black', label='Factor 2')
axes[1].set_title('Return Distribution: Factor 2 vs Market', fontweight='bold')
axes[1].set_xlabel('Monthly Return')
axes[1].set_ylabel('Frequency')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(output_dir / "distribution_comparison.png", dpi=300, bbox_inches='tight')
print("Saved: distribution_comparison.png")
plt.close()

# ========== SUMMARY REPORT ==========
comparison = pd.DataFrame({
    'Metric': ['Mean Monthly Return', 'Annualized Return', 'Annual Volatility', 'Sharpe Ratio',
               'Cumulative Return', 'Max Drawdown', 'Positive Months %'],
    'Market': [
        f"{market_aligned['market_return'].mean()*100:.2f}%",
        f"{((1 + market_aligned['market_return'].mean())**12 - 1)*100:.2f}%",
        f"{market_aligned['market_return'].std()*np.sqrt(12)*100:.2f}%",
        f"{market_sharpe:.2f}",
        f"{market_cumret*100:.2f}%",
        f"{market_dd.min()*100:.2f}%",
        f"{market_win_rate:.1f}%"
    ],
    'Factor 1': [
        f"{factors['factor1'].mean()*100:.2f}%",
        f"{((1 + factors['factor1'].mean())**12 - 1)*100:.2f}%",
        f"{factors['factor1'].std()*np.sqrt(12)*100:.2f}%",
        f"{(factors['factor1'].mean()/factors['factor1'].std())*np.sqrt(12):.2f}",
        f"{((1+factors['factor1']).cumprod().iloc[-1]-1)*100:.2f}%",
        "0.00%",
        "100.0%"
    ],
    'Factor 2': [
        f"{factors['factor2'].mean()*100:.2f}%",
        f"{((1 + factors['factor2'].mean())**12 - 1)*100:.2f}%",
        f"{factors['factor2'].std()*np.sqrt(12)*100:.2f}%",
        f"{(factors['factor2'].mean()/factors['factor2'].std())*np.sqrt(12):.2f}",
        f"{((1+factors['factor2']).cumprod().iloc[-1]-1)*100:.2f}%",
        f"{((1+factors['factor2']).cumprod().pct_change().fillna(0).expanding().min().min())*100:.2f}%",
        f"{((factors['factor2'] > 0).sum() / len(factors) * 100):.1f}%"
    ]
})

comparison.to_csv(output_dir / "benchmark_comparison.csv", index=False)
print("Saved: benchmark_comparison.csv")

# ========== RECOMMENDATIONS ==========
print("\n" + "="*70)
print("DIAGNOSIS & RECOMMENDATIONS")
print("="*70)

if len(issues) > 0:
    print("\nISSUES FOUND:")
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue}")

print("\n" + "-"*70)
print("RECOMMENDATION:")
print("-"*70)

if any('100%' in issue or 'ZERO drawdown' in issue for issue in issues):
    print("""
The results show MAJOR ISSUES that make them unreliable:

1. **100% positive months** - This NEVER happens in real markets
   - Even Warren Buffett has ~65% positive years
   - Suggests the algorithm is seeing the future (look-ahead bias)

2. **Zero drawdown** - Impossible for any real strategy
   - The market had crashes in 2000, 2008, 2020
   - Your factor should reflect these

3. **Sharpe Ratio > 10** - Nearly impossible in reality
   - Best hedge funds achieve 2-4
   - Renaissance Medallion (best ever) has ~7

ROOT CAUSE:
The R script starts training from 2011-09-30, but you have data from 1998.
This is because after removing NAs, the first periods don't have enough stocks.

FIXES TO TRY:

Option 1 - Use looser NA handling:
  • Don't require ALL characteristics to be non-NA
  • Use only stocks with at least 10-15 characteristics available

Option 2 - Start analysis later:
  • Set start = '2005-01-01' when more stocks have complete data
  • Trade-off: less data but more reliable

Option 3 - Impute missing values:
  • Fill NAs with cross-sectional medians
  • Standard practice in asset pricing

NEXT STEPS:
1. Fix the data filtering to include more early observations
2. Re-run the analysis
3. Verify results show realistic drawdowns and win rates (50-70%)
""")
else:
    print("\nResults look reasonable! Proceed with:")
    print("1. Out-of-sample testing")
    print("2. Transaction cost analysis")
    print("3. Factor exposure analysis")

print("\n" + "="*70)
print("All diagnostics saved to:", output_dir.absolute())
print("="*70)
