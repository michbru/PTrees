"""
P-TREE VISUALIZATION SCRIPT (Python)

Generates comprehensive visualizations of P-Tree results:
1. Cumulative returns time series
2. Return distribution histograms
3. Rolling window OOS Sharpe bar chart
4. IS vs OOS scatterplot
5. Scenario comparison charts
6. Summary statistics table
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

print("=" * 80)
print("P-TREE VISUALIZATION")
print("=" * 80)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 7)
plt.rcParams['font.size'] = 10

# Output directory
vis_dir = Path('../../results/ptree_34chars/visualizations')
vis_dir.mkdir(exist_ok=True, parents=True)

# =============================================================================
# 1. LOAD DATA
# =============================================================================

print("\n[1] Loading data...")

results_dir = Path('../../results/ptree_34chars')

# Load factor returns
scenarios = {
    'Scenario A: Full Sample': results_dir / 'scenario_a_full' / 'ptree_factors.csv',
    'Scenario B: Time Split (IS)': results_dir / 'scenario_b_split' / 'ptree_factors_is.csv',
    'Scenario B: Time Split (OOS)': results_dir / 'scenario_b_split' / 'ptree_factors_oos.csv',
    'Scenario C: Reverse Split (IS)': results_dir / 'scenario_c_reverse' / 'ptree_factors_is.csv',
    'Scenario C: Reverse Split (OOS)': results_dir / 'scenario_c_reverse' / 'ptree_factors_oos.csv'
}

all_factors = []

for name, path in scenarios.items():
    if path.exists():
        df = pd.read_csv(path)
        df['date'] = pd.to_datetime(df['month'])
        df['scenario'] = name
        df['type'] = 'OOS' if 'OOS' in name else 'IS'
        df['cumret'] = (1 + df['factor']).cumprod() - 1
        all_factors.append(df[['date', 'factor', 'scenario', 'type', 'cumret']])

all_factors_df = pd.concat(all_factors, ignore_index=True)
print(f"  Loaded {len(scenarios)} scenarios")

# Load rolling window results
rolling = pd.read_csv(results_dir / 'rolling_window' / 'rolling_window_results.csv')
print(f"  Loaded rolling window results ({len(rolling)} windows)")

# Load scenario comparison
comparison = pd.read_csv(results_dir / 'cross_scenario_comparison.csv')
print(f"  Loaded scenario comparison")

# =============================================================================
# 2. PLOT 1: CUMULATIVE RETURNS
# =============================================================================

print("\n[2] Creating cumulative returns plot...")

fig, ax = plt.subplots(figsize=(12, 7))

for scenario in all_factors_df['scenario'].unique():
    data = all_factors_df[all_factors_df['scenario'] == scenario]
    linestyle = '--' if 'IS' in scenario else '-'
    linewidth = 1.5 if 'OOS' in scenario else 1.0
    ax.plot(data['date'], data['cumret'] * 100,
            label=scenario, linestyle=linestyle, linewidth=linewidth)

ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Cumulative Return (%)', fontsize=12)
ax.set_title('P-Tree Factor: Cumulative Returns\n34-Characteristic Implementation on Swedish Market',
             fontsize=14, fontweight='bold')
ax.legend(loc='best', fontsize=9)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(vis_dir / 'cumulative_returns.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  Saved: cumulative_returns.png")

# =============================================================================
# 3. PLOT 2: RETURN DISTRIBUTION
# =============================================================================

print("\n[3] Creating return distribution plot...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for idx, sample_type in enumerate(['IS', 'OOS']):
    data = all_factors_df[all_factors_df['type'] == sample_type]['factor'] * 100

    axes[idx].hist(data, bins=30, alpha=0.7, color='steelblue' if sample_type == 'IS' else 'darkgreen',
                   edgecolor='black')
    axes[idx].axvline(x=data.mean(), color='red', linestyle='--', linewidth=2,
                      label=f'Mean = {data.mean():.2f}%')
    axes[idx].set_xlabel('Monthly Return (%)', fontsize=11)
    axes[idx].set_ylabel('Frequency', fontsize=11)
    axes[idx].set_title(f'{sample_type} Returns Distribution', fontsize=12, fontweight='bold')
    axes[idx].legend()
    axes[idx].grid(True, alpha=0.3)

fig.suptitle('P-Tree Factor: Monthly Return Distribution', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(vis_dir / 'return_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  Saved: return_distribution.png")

# =============================================================================
# 4. PLOT 3: ROLLING WINDOW SHARPE RATIOS
# =============================================================================

print("\n[4] Creating rolling window Sharpe plot...")

fig, ax = plt.subplots(figsize=(12, 7))

colors = ['darkgreen' if x > 0 else 'darkred' for x in rolling['oos_sharpe']]
bars = ax.bar(rolling['window'], rolling['oos_sharpe'], color=colors, alpha=0.8, edgecolor='black')

# Add mean line
mean_sharpe = rolling['oos_sharpe'].mean()
ax.axhline(y=mean_sharpe, color='blue', linestyle='-', linewidth=2,
           label=f'Mean = {mean_sharpe:.2f}')
ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

ax.set_xlabel('Window Number', fontsize=12)
ax.set_ylabel('Out-of-Sample Sharpe Ratio', fontsize=12)
ax.set_title('Rolling Window Validation: Out-of-Sample Sharpe Ratios\n' +
             '20 Independent Windows (5-year train, 1-year test)',
             fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(vis_dir / 'rolling_window_sharpe.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  Saved: rolling_window_sharpe.png")

# =============================================================================
# 5. PLOT 4: IS vs OOS SHARPE (DEGRADATION)
# =============================================================================

print("\n[5] Creating IS vs OOS scatterplot...")

fig, ax = plt.subplots(figsize=(10, 8))

scatter = ax.scatter(rolling['is_sharpe'], rolling['oos_sharpe'],
                     c=rolling['degradation_pct'], cmap='RdYlGn_r',
                     s=100, alpha=0.7, edgecolors='black', linewidth=0.5)

# Add diagonal line (no degradation)
max_val = max(rolling['is_sharpe'].max(), rolling['oos_sharpe'].max())
ax.plot([0, max_val], [0, max_val], 'k--', alpha=0.5, linewidth=1, label='No Degradation')

# Add trend line
z = np.polyfit(rolling['is_sharpe'], rolling['oos_sharpe'], 1)
p = np.poly1d(z)
x_line = np.linspace(rolling['is_sharpe'].min(), rolling['is_sharpe'].max(), 100)
ax.plot(x_line, p(x_line), 'b-', alpha=0.5, linewidth=2, label='Trend')

ax.set_xlabel('In-Sample Sharpe Ratio', fontsize=12)
ax.set_ylabel('Out-of-Sample Sharpe Ratio', fontsize=12)
ax.set_title('In-Sample vs Out-of-Sample Performance\nRolling Window Validation (n=20)',
             fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Degradation (%)', fontsize=11)

plt.tight_layout()
plt.savefig(vis_dir / 'is_vs_oos_sharpe.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  Saved: is_vs_oos_sharpe.png")

# =============================================================================
# 6. PLOT 5: SCENARIO COMPARISON (SHARPE RATIOS)
# =============================================================================

print("\n[6] Creating scenario comparison plot...")

fig, ax = plt.subplots(figsize=(10, 7))

# Prepare data
comparison['Scenario_Label'] = comparison['Scenario'].str.replace('Scenario ', '')
x = np.arange(len(comparison))
width = 0.35

# Separate IS and OOS
is_data = comparison[comparison['Data_Type'] == 'IS']
oos_data = comparison[comparison['Data_Type'] == 'OOS']

# Create bars
if len(is_data) > 0:
    bars1 = ax.bar(x[comparison['Data_Type'] == 'IS'] - width/2,
                   is_data['F1_Sharpe'], width,
                   label='In-Sample', color='steelblue', alpha=0.8, edgecolor='black')
if len(oos_data) > 0:
    bars2 = ax.bar(x[comparison['Data_Type'] == 'OOS'] + width/2,
                   oos_data['F1_Sharpe'], width,
                   label='Out-of-Sample', color='darkgreen', alpha=0.8, edgecolor='black')

# Add value labels
for i, row in comparison.iterrows():
    offset = -width/2 if row['Data_Type'] == 'IS' else width/2
    ax.text(i + offset, row['F1_Sharpe'] + 0.05, f"{row['F1_Sharpe']:.2f}",
            ha='center', va='bottom', fontsize=9, fontweight='bold')

ax.set_xlabel('Scenario', fontsize=12)
ax.set_ylabel('Sharpe Ratio', fontsize=12)
ax.set_title('P-Tree Performance: Three-Scenario Validation\nSharpe Ratios Across Different Train-Test Splits',
             fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(comparison['Scenario_Label'])
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(vis_dir / 'scenario_comparison_sharpe.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  Saved: scenario_comparison_sharpe.png")

# =============================================================================
# 7. PLOT 6: ALPHA COMPARISON
# =============================================================================

print("\n[7] Creating alpha comparison plot...")

fig, ax = plt.subplots(figsize=(12, 7))

# Prepare data for grouped bar chart
alpha_cols = ['F1_Alpha_CAPM', 'F1_Alpha_FF3', 'F1_Alpha_FF4']
x = np.arange(len(comparison))
width = 0.25

for i, col in enumerate(alpha_cols):
    model_name = col.replace('F1_Alpha_', '')
    offset = (i - 1) * width
    bars = ax.bar(x + offset, comparison[col], width,
                  label=model_name, alpha=0.8, edgecolor='black')

ax.set_xlabel('Scenario', fontsize=12)
ax.set_ylabel('Alpha (%)', fontsize=12)
ax.set_title('P-Tree Alphas: Factor Model Comparisons\nAnnualized Alpha (%) Relative to CAPM, FF3, FF4',
             fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([f"{row['Scenario_Label']}\n({row['Data_Type']})"
                     for _, row in comparison.iterrows()], fontsize=9)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(vis_dir / 'alpha_comparison.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  Saved: alpha_comparison.png")

# =============================================================================
# 8. SUMMARY STATISTICS TABLE
# =============================================================================

print("\n[8] Creating summary statistics table...")

summary_data = pd.DataFrame({
    'Metric': [
        'Scenarios Tested (Traditional)',
        'Rolling Windows (Anti-Overfitting)',
        'Average OOS Sharpe (Rolling)',
        'Median OOS Sharpe (Rolling)',
        'Std Dev OOS Sharpe (Rolling)',
        'Positive Windows',
        'Success Rate',
        'Scenario B OOS Sharpe',
        'Scenario C OOS Sharpe',
        'Characteristics Used',
        'Sample Period'
    ],
    'Value': [
        '3 (A, B, C)',
        '20',
        f"{rolling['oos_sharpe'].mean():.3f}",
        f"{rolling['oos_sharpe'].median():.3f}",
        f"{rolling['oos_sharpe'].std():.3f}",
        f"{(rolling['oos_sharpe'] > 0).sum()}/20",
        f"{(rolling['oos_sharpe'] > 0).sum() / len(rolling) * 100:.0f}%",
        f"{comparison[comparison['Scenario'] == 'Scenario B']['F1_Sharpe'].values[0]:.3f}" if len(comparison[comparison['Scenario'] == 'Scenario B']) > 0 else 'N/A',
        f"{comparison[comparison['Scenario'] == 'Scenario C']['F1_Sharpe'].values[0]:.3f}" if len(comparison[comparison['Scenario'] == 'Scenario C']) > 0 else 'N/A',
        '34',
        '1997-2022'
    ]
})

summary_data.to_csv(vis_dir / 'summary_statistics.csv', index=False)
print(f"  Saved: summary_statistics.csv")

# =============================================================================
# DONE
# =============================================================================

print("\n" + "=" * 80)
print("VISUALIZATION COMPLETE")
print("=" * 80)
print(f"\nAll visualizations saved to: {vis_dir.absolute()}")
print("\nGenerated files:")
print("  1. cumulative_returns.png        - Time series of cumulative factor returns")
print("  2. return_distribution.png       - Distribution of monthly returns (IS vs OOS)")
print("  3. rolling_window_sharpe.png     - Bar chart of rolling window OOS Sharpe ratios")
print("  4. is_vs_oos_sharpe.png          - Scatterplot of IS vs OOS performance")
print("  5. scenario_comparison_sharpe.png - Comparison of Scenarios A, B, C")
print("  6. alpha_comparison.png          - Alpha comparison across factor models")
print("  7. summary_statistics.csv        - Key metrics summary table")
print()
print("Note: To visualize P-Tree structure (splits), the R script must first save")
print("      the tree structure. Run 1_ptree_analysis.R to generate tree files.")
print()
