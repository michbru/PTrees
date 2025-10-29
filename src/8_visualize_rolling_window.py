"""
Visualize Rolling Window Results

Creates plots showing:
1. Time series of rolling window Sharpe ratios
2. Distribution of OOS returns
3. Cumulative performance over time
4. Comparison to benchmarks
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

print("="*80)
print("ROLLING WINDOW VISUALIZATION")
print("="*80)

# Set style
plt.style.use('seaborn-v0_8-darkgrid')

# Load results
results_dir = Path('results/robustness_checks')

# Check if results exist
rolling_file = results_dir / 'rolling_window_ptree_results.csv'
returns_file = results_dir / 'rolling_window_all_returns.csv'

if not rolling_file.exists():
    print("\nERROR: Rolling window results not found!")
    print(f"  Expected: {rolling_file}")
    print("\nRun: Rscript src/7_rolling_window_ptree.R")
    exit(1)

# Load data
print("\nLoading rolling window results...")
df_rolling = pd.read_csv(rolling_file)
df_returns = pd.read_csv(returns_file)

print(f"  Windows: {len(df_rolling)}")
print(f"  Total OOS months: {len(df_returns)}")
print(f"  Period: {df_rolling['Test_Start'].min()} to {df_rolling['Test_End'].max()}")

# Create output directory
output_dir = Path('results/robustness_checks/plots')
output_dir.mkdir(exist_ok=True, parents=True)

# Calculate aggregate statistics
all_returns = df_returns['Return'].values
aggregate_sharpe = all_returns.mean() / all_returns.std() * np.sqrt(12)
aggregate_return = all_returns.mean() * 12 * 100

print(f"\nAggregate OOS Performance:")
print(f"  Sharpe: {aggregate_sharpe:.3f}")
print(f"  Return: {aggregate_return:.2f}% per year")

# ===== PLOT 1: Sharpe Ratios Over Time =====
print("\nGenerating plots...")
fig, ax = plt.subplots(figsize=(14, 6))

df_rolling['Window_Label'] = df_rolling.apply(
    lambda x: f"{x['Test_Start'][:7]}", axis=1
)

ax.plot(range(len(df_rolling)), df_rolling['Sharpe_Ratio'],
        marker='o', linewidth=2, markersize=8, label='Rolling Window Sharpe')
ax.axhline(y=aggregate_sharpe, color='red', linestyle='--',
           linewidth=2, label=f'Average: {aggregate_sharpe:.3f}')
ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax.axhline(y=1.69, color='green', linestyle='--', linewidth=2,
           label='Single Split (Scenario B): 1.69', alpha=0.7)

ax.set_xlabel('Window Number', fontsize=12, fontweight='bold')
ax.set_ylabel('Sharpe Ratio (OOS)', fontsize=12, fontweight='bold')
ax.set_title('Rolling Window Sharpe Ratios - Out-of-Sample Performance',
             fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

# Add window labels on x-axis
ax.set_xticks(range(0, len(df_rolling), max(1, len(df_rolling)//10)))
ax.set_xticklabels([df_rolling.iloc[i]['Window_Label']
                     for i in range(0, len(df_rolling), max(1, len(df_rolling)//10))],
                    rotation=45, ha='right')

plt.tight_layout()
plt.savefig(output_dir / 'rolling_sharpe_ratios.png', dpi=300, bbox_inches='tight')
print(f"  Saved: {output_dir / 'rolling_sharpe_ratios.png'}")
plt.close()

# ===== PLOT 2: Return Distribution =====
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Histogram
ax1.hist(df_rolling['Mean_Return_pct'], bins=20, edgecolor='black', alpha=0.7)
ax1.axvline(x=aggregate_return, color='red', linestyle='--', linewidth=2,
            label=f'Mean: {aggregate_return:.2f}%')
ax1.set_xlabel('Annualized Return (%)', fontsize=11, fontweight='bold')
ax1.set_ylabel('Frequency', fontsize=11, fontweight='bold')
ax1.set_title('Distribution of Rolling Window Returns', fontsize=12, fontweight='bold')
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# Box plot
box_data = [df_rolling['Sharpe_Ratio'],
            df_rolling['Mean_Return_pct']]
ax2.boxplot(box_data, labels=['Sharpe Ratio', 'Return (%)'])
ax2.set_ylabel('Value', fontsize=11, fontweight='bold')
ax2.set_title('Performance Statistics Distribution', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(output_dir / 'rolling_distributions.png', dpi=300, bbox_inches='tight')
print(f"  Saved: {output_dir / 'rolling_distributions.png'}")
plt.close()

# ===== PLOT 3: Cumulative Returns =====
fig, ax = plt.subplots(figsize=(14, 6))

# Calculate cumulative wealth
monthly_returns = df_returns['Return'].values
cumulative_wealth = (1 + monthly_returns).cumprod()

months = range(len(monthly_returns))
ax.plot(months, cumulative_wealth, linewidth=2, label='P-Tree Strategy')
ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1, alpha=0.5)

ax.set_xlabel('Month (OOS)', fontsize=12, fontweight='bold')
ax.set_ylabel('Cumulative Wealth (Starting at $1)', fontsize=12, fontweight='bold')
ax.set_title('Cumulative Out-of-Sample Performance', fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

# Add shaded regions for positive/negative periods
for i in range(len(monthly_returns)):
    if monthly_returns[i] < 0:
        ax.axvspan(i-0.5, i+0.5, alpha=0.1, color='red')

plt.tight_layout()
plt.savefig(output_dir / 'cumulative_returns.png', dpi=300, bbox_inches='tight')
print(f"  Saved: {output_dir / 'cumulative_returns.png'}")
plt.close()

# ===== PLOT 4: Performance by Time Period =====
fig, ax = plt.subplots(figsize=(14, 6))

df_rolling['Test_Year'] = pd.to_datetime(df_rolling['Test_Start']).dt.year
yearly_sharpe = df_rolling.groupby('Test_Year')['Sharpe_Ratio'].mean()

ax.bar(yearly_sharpe.index, yearly_sharpe.values, alpha=0.7, edgecolor='black')
ax.axhline(y=aggregate_sharpe, color='red', linestyle='--', linewidth=2,
           label=f'Overall Average: {aggregate_sharpe:.3f}')
ax.axhline(y=0, color='black', linestyle='-', linewidth=1)

ax.set_xlabel('Year', fontsize=12, fontweight='bold')
ax.set_ylabel('Average Sharpe Ratio', fontsize=12, fontweight='bold')
ax.set_title('Average Out-of-Sample Sharpe Ratio by Year', fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(output_dir / 'sharpe_by_year.png', dpi=300, bbox_inches='tight')
print(f"  Saved: {output_dir / 'sharpe_by_year.png'}")
plt.close()

# ===== SUMMARY STATISTICS =====
print("\n" + "="*80)
print("ROLLING WINDOW STATISTICS SUMMARY")
print("="*80)

print("\nSharpe Ratio:")
print(f"  Mean:     {df_rolling['Sharpe_Ratio'].mean():7.3f}")
print(f"  Median:   {df_rolling['Sharpe_Ratio'].median():7.3f}")
print(f"  Std Dev:  {df_rolling['Sharpe_Ratio'].std():7.3f}")
print(f"  Min:      {df_rolling['Sharpe_Ratio'].min():7.3f}")
print(f"  Max:      {df_rolling['Sharpe_Ratio'].max():7.3f}")
print(f"  Positive: {(df_rolling['Sharpe_Ratio'] > 0).sum()}/{len(df_rolling)}")

print("\nAnnualized Returns:")
print(f"  Mean:     {df_rolling['Mean_Return_pct'].mean():7.2f}%")
print(f"  Median:   {df_rolling['Mean_Return_pct'].median():7.2f}%")
print(f"  Std Dev:  {df_rolling['Mean_Return_pct'].std():7.2f}%")
print(f"  Min:      {df_rolling['Mean_Return_pct'].min():7.2f}%")
print(f"  Max:      {df_rolling['Mean_Return_pct'].max():7.2f}%")
print(f"  Positive: {(df_rolling['Mean_Return_pct'] > 0).sum()}/{len(df_rolling)}")

print("\nTree Complexity:")
print(f"  Mean nodes: {df_rolling['N_Nodes'].mean():.1f}")
print(f"  Min nodes:  {df_rolling['N_Nodes'].min()}")
print(f"  Max nodes:  {df_rolling['N_Nodes'].max()}")

print("\n" + "="*80)
print("INTERPRETATION")
print("="*80)

# Consistency check
pct_positive = (df_rolling['Sharpe_Ratio'] > 0).sum() / len(df_rolling) * 100
sharpe_std = df_rolling['Sharpe_Ratio'].std()

print("\n1. PERFORMANCE CONSISTENCY:")
if pct_positive >= 80 and sharpe_std < 0.5:
    print("   ✓ EXCELLENT: High consistency (>80% positive, low variance)")
elif pct_positive >= 70 and sharpe_std < 1.0:
    print("   ✓ GOOD: Reasonable consistency (>70% positive, moderate variance)")
elif pct_positive >= 60:
    print("   ~ MODERATE: Some inconsistency")
else:
    print("   ✗ POOR: Highly inconsistent performance")

print(f"   - {pct_positive:.1f}% of windows have positive Sharpe")
print(f"   - Standard deviation: {sharpe_std:.3f}")

# Comparison to single split
print("\n2. COMPARISON TO SINGLE SPLIT (Scenario B):")
diff_pct = (aggregate_sharpe - 1.69) / 1.69 * 100
if abs(diff_pct) < 10:
    print(f"   ✓ CONSISTENT: Rolling avg ({aggregate_sharpe:.3f}) ≈ Single split (1.69)")
    print(f"     Difference: {diff_pct:+.1f}%")
elif aggregate_sharpe < 1.69:
    print(f"   ⚠ LOWER: Rolling avg ({aggregate_sharpe:.3f}) < Single split (1.69)")
    print(f"     Difference: {diff_pct:+.1f}% (more conservative)")
else:
    print(f"   ⚠ HIGHER: Rolling avg ({aggregate_sharpe:.3f}) > Single split (1.69)")
    print(f"     Difference: {diff_pct:+.1f}% (less conservative)")

# Economic significance
print("\n3. ECONOMIC SIGNIFICANCE:")
if aggregate_return > 10:
    print(f"   ✓ STRONG: {aggregate_return:.2f}% annual return (economically significant)")
elif aggregate_return > 5:
    print(f"   ~ MODERATE: {aggregate_return:.2f}% annual return")
else:
    print(f"   ✗ WEAK: {aggregate_return:.2f}% annual return (may not cover costs)")

# Transaction costs
annual_cost_medium = 9.0  # 9% annual drag from medium TC scenario
net_return = aggregate_return - annual_cost_medium

print("\n4. AFTER TRANSACTION COSTS:")
print(f"   Gross return: {aggregate_return:6.2f}%")
print(f"   TC drag:      -{annual_cost_medium:6.2f}%")
print(f"   Net return:   {net_return:6.2f}%")

if net_return > 5:
    print("   ✓ Still profitable after costs")
elif net_return > 0:
    print("   ~ Marginally profitable after costs")
else:
    print("   ✗ Unprofitable after costs")

print("\n" + "="*80)
print("ROLLING WINDOW VISUALIZATION COMPLETE")
print("="*80)
print(f"\nPlots saved to: {output_dir}/")
