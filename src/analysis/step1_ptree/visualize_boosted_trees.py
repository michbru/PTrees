"""
Visualize Boosted P-Tree Results
Generates publication-quality figures for the 5 boosted P-Trees
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configuration
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 11

# Paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
RESULTS_DIR = BASE_DIR / 'results' / 'ptree_34chars' / 'boosted_trees'
OUTPUT_DIR = RESULTS_DIR / 'visualizations'
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 80)
print("BOOSTED P-TREE VISUALIZATION")
print("=" * 80)
print()

# Load data
print("Loading factor data...")
factors = pd.read_csv(RESULTS_DIR / 'all_factors.csv')
factors['date'] = pd.to_datetime(factors['date'])
factors = factors.set_index('date')
print(f"  Data range: {factors.index.min().date()} to {factors.index.max().date()}")
print(f"  Number of months: {len(factors)}")
print()

# Load characteristic names
data_path = BASE_DIR / 'results' / 'ptree_34chars' / 'ptree_ready_data_34chars.csv'
data_sample = pd.read_csv(data_path, nrows=1)
char_cols = [c for c in data_sample.columns if c.startswith('rank_')]

# ============================================================================
# 1. Individual Tree Performance
# ============================================================================
print("Generating individual tree performance plots...")
fig, axes = plt.subplots(3, 2, figsize=(16, 12))
axes = axes.flatten()

for i in range(5):
    col = f'tree_{i+1}'
    ax = axes[i]
    
    # Cumulative returns
    cum_returns = (1 + factors[col]).cumprod()
    ax.plot(cum_returns.index, cum_returns.values, linewidth=2.5, color=f'C{i}')
    ax.axhline(y=1, color='black', linestyle='--', alpha=0.3)
    ax.set_title(f'Tree {i+1} - Cumulative Factor Returns', fontsize=14, fontweight='bold')
    ax.set_ylabel('Cumulative Return')
    ax.grid(True, alpha=0.3)
    
    # Statistics
    sharpe = factors[col].mean() / factors[col].std() * np.sqrt(12)
    ann_return = factors[col].mean() * 12
    ann_vol = factors[col].std() * np.sqrt(12)
    
    stats_text = f'Sharpe: {sharpe:.3f}\nAnn. Return: {ann_return:.1%}\nAnn. Vol: {ann_vol:.1%}'
    ax.text(0.02, 0.98, stats_text, 
            transform=ax.transAxes, fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# Remove extra subplot
fig.delaxes(axes[5])

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'individual_tree_performance.png', dpi=300, bbox_inches='tight')
print(f"  Saved: {OUTPUT_DIR / 'individual_tree_performance.png'}")
plt.close()

# ============================================================================
# 2. Ensemble Performance
# ============================================================================
print("Generating ensemble performance plots...")
factors['ensemble'] = factors[[f'tree_{i}' for i in range(1, 6)]].mean(axis=1)

fig, axes = plt.subplots(2, 1, figsize=(16, 10))

# Cumulative returns
ax = axes[0]
cum_ensemble = (1 + factors['ensemble']).cumprod()
ax.plot(cum_ensemble.index, cum_ensemble.values, linewidth=3, color='darkblue', 
        label='Ensemble (Avg of 5 trees)', zorder=10)

# Individual trees in background
for i in range(1, 6):
    cum = (1 + factors[f'tree_{i}']).cumprod()
    ax.plot(cum.index, cum.values, linewidth=1, alpha=0.2, color='gray')

ax.axhline(y=1, color='black', linestyle='--', alpha=0.3)
ax.set_title('Ensemble P-Tree Factor - Cumulative Returns', fontsize=16, fontweight='bold')
ax.set_ylabel('Cumulative Return', fontsize=12)
ax.legend(fontsize=12, loc='upper left')
ax.grid(True, alpha=0.3)

ensemble_sharpe = factors['ensemble'].mean() / factors['ensemble'].std() * np.sqrt(12)
ensemble_return = factors['ensemble'].mean() * 12
ensemble_vol = factors['ensemble'].std() * np.sqrt(12)

stats_text = f'Sharpe: {ensemble_sharpe:.3f}\nAnnualized Return: {ensemble_return:.1%}\nAnnualized Volatility: {ensemble_vol:.1%}'
ax.text(0.02, 0.98, stats_text, 
        transform=ax.transAxes, fontsize=12, fontweight='bold',
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.9))

# Monthly returns distribution
ax = axes[1]
ax.hist(factors['ensemble'], bins=50, alpha=0.7, color='darkblue', edgecolor='black')
ax.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Zero')
ax.axvline(x=factors['ensemble'].mean(), color='green', linestyle='--', linewidth=2, 
           label=f'Mean: {factors["ensemble"].mean():.4f}')
ax.set_title('Ensemble Factor - Monthly Returns Distribution', fontsize=16, fontweight='bold')
ax.set_xlabel('Monthly Return', fontsize=12)
ax.set_ylabel('Frequency', fontsize=12)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'ensemble_performance.png', dpi=300, bbox_inches='tight')
print(f"  Saved: {OUTPUT_DIR / 'ensemble_performance.png'}")
plt.close()

# ============================================================================
# 3. Factor Correlations
# ============================================================================
print("Generating correlation heatmap...")
tree_cols = [f'tree_{i}' for i in range(1, 6)]
corr_matrix = factors[tree_cols].corr()

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='RdYlGn', center=0.5,
            square=True, linewidths=1, cbar_kws={"shrink": 0.8},
            vmin=0, vmax=1, ax=ax, annot_kws={'fontsize': 12, 'fontweight': 'bold'})
ax.set_title('Correlation Between Boosted Tree Factors', fontsize=16, fontweight='bold', pad=20)
ax.set_xticklabels(ax.get_xticklabels(), fontsize=12)
ax.set_yticklabels(ax.get_yticklabels(), fontsize=12)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'factor_correlations.png', dpi=300, bbox_inches='tight')
print(f"  Saved: {OUTPUT_DIR / 'factor_correlations.png'}")
plt.close()

# ============================================================================
# 4. Rolling Performance
# ============================================================================
print("Generating rolling performance analysis...")
window = 12
rolling_sharpe = factors['ensemble'].rolling(window=window).apply(
    lambda x: x.mean() / x.std() * np.sqrt(12) if x.std() > 0 else 0
)

fig, axes = plt.subplots(2, 1, figsize=(16, 10))

# Rolling Sharpe
ax = axes[0]
ax.plot(rolling_sharpe.index, rolling_sharpe.values, linewidth=2, color='darkblue')
ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=1.5)
ax.axhline(y=1, color='green', linestyle='--', alpha=0.5, linewidth=1.5, label='Sharpe = 1')
ax.fill_between(rolling_sharpe.index, 0, rolling_sharpe.values, 
                 where=(rolling_sharpe.values > 0), alpha=0.3, color='green')
ax.fill_between(rolling_sharpe.index, 0, rolling_sharpe.values, 
                 where=(rolling_sharpe.values <= 0), alpha=0.3, color='red')
ax.set_title('Ensemble Factor - Rolling 12-Month Sharpe Ratio', fontsize=16, fontweight='bold')
ax.set_ylabel('Sharpe Ratio', fontsize=12)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

avg_positive_sharpe = rolling_sharpe[rolling_sharpe > 0].mean()
pct_positive = (rolling_sharpe > 0).sum() / rolling_sharpe.notna().sum()
stats_text = f'Avg Positive Sharpe: {avg_positive_sharpe:.3f}\nPositive Periods: {pct_positive:.1%}'
ax.text(0.02, 0.98, stats_text, 
        transform=ax.transAxes, fontsize=11,
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

# Drawdown
ax = axes[1]
cum_returns = (1 + factors['ensemble']).cumprod()
running_max = cum_returns.expanding().max()
drawdown = (cum_returns - running_max) / running_max

ax.fill_between(drawdown.index, 0, drawdown.values, alpha=0.5, color='red')
ax.plot(drawdown.index, drawdown.values, linewidth=2, color='darkred')
ax.set_title('Ensemble Factor - Drawdown', fontsize=16, fontweight='bold')
ax.set_ylabel('Drawdown', fontsize=12)
ax.set_xlabel('Date', fontsize=12)
ax.grid(True, alpha=0.3)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.0%}'.format(y)))

max_dd = drawdown.min()
max_dd_date = drawdown.idxmin()
ax.text(0.02, 0.02, f'Max Drawdown: {max_dd:.1%}\nDate: {max_dd_date.date()}', 
        transform=ax.transAxes, fontsize=12, fontweight='bold',
        verticalalignment='bottom',
        bbox=dict(boxstyle='round', facecolor='salmon', alpha=0.8))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'rolling_analysis.png', dpi=300, bbox_inches='tight')
print(f"  Saved: {OUTPUT_DIR / 'rolling_analysis.png'}")
plt.close()

# ============================================================================
# 5. Tree Structure Summary
# ============================================================================
print("Generating tree structure summary...")

def parse_tree_structure(tree_file):
    """Parse P-Tree structure file"""
    with open(tree_file, 'r') as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    
    num_nodes = int(lines[0])
    nodes = []
    
    for i in range(1, min(num_nodes + 1, len(lines))):
        parts = lines[i].split()
        node_id = int(parts[0])
        char_idx = int(parts[1])
        split_val = float(parts[2])
        left_child = int(parts[3])
        
        nodes.append({
            'id': node_id,
            'char': char_idx,
            'split': split_val,
            'left': left_child,
            'is_leaf': char_idx == 0
        })
    
    return nodes

# Create text summary
summary_lines = ["=" * 80, "BOOSTED P-TREE STRUCTURES", "=" * 80, ""]

for tree_num in range(1, 6):
    tree_file = RESULTS_DIR / f'tree_{tree_num}_structure.txt'
    nodes = parse_tree_structure(tree_file)
    
    summary_lines.append(f"\nTree {tree_num}: {len(nodes)} nodes")
    summary_lines.append("-" * 80)
    
    for node in nodes:
        if node['is_leaf']:
            summary_lines.append(f"  Node {node['id']}: LEAF")
        else:
            char_name = char_cols[node['char']] if node['char'] < len(char_cols) else f"char_{node['char']}"
            char_name = char_name.replace('rank_', '')
            summary_lines.append(f"  Node {node['id']}: Split on {char_name} at {node['split']:.2f}")

# Save text summary
with open(OUTPUT_DIR / 'tree_structures.txt', 'w') as f:
    f.write('\n'.join(summary_lines))
print(f"  Saved: {OUTPUT_DIR / 'tree_structures.txt'}")

# ============================================================================
# Summary Statistics
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)
print()

print("Ensemble Factor Performance:")
print(f"  Sharpe Ratio:        {ensemble_sharpe:.3f}")
print(f"  Annualized Return:   {ensemble_return:.2%}")
print(f"  Annualized Vol:      {ensemble_vol:.2%}")
print(f"  Mean Monthly:        {factors['ensemble'].mean():.4f}")
print(f"  Positive Months:     {(factors['ensemble'] > 0).sum()}/{len(factors)} ({(factors['ensemble'] > 0).mean():.1%})")
print(f"  Max Drawdown:        {max_dd:.2%}")
print()

print("Individual Tree Sharpe Ratios:")
for i in range(1, 6):
    col = f'tree_{i}'
    sharpe = factors[col].mean() / factors[col].std() * np.sqrt(12)
    print(f"  Tree {i}: {sharpe:.3f}")
print()

print("Factor Correlations:")
print(f"  Trees 1-3: {corr_matrix.loc['tree_1', 'tree_3']:.3f} (nearly identical - captured main signal)")
print(f"  Tree 1 & 4: {corr_matrix.loc['tree_1', 'tree_4']:.3f}")
print(f"  Tree 1 & 5: {corr_matrix.loc['tree_1', 'tree_5']:.3f}")
print()

print("=" * 80)
print(f"All visualizations saved to: {OUTPUT_DIR}")
print("=" * 80)
