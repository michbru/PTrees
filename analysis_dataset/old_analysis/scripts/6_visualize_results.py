"""
PTree Results Visualization and Analysis
Creates comprehensive visualizations and summary statistics
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# Paths
results_dir = Path(__file__).parent.parent / "results"
output_dir = results_dir / "ptree_analysis"
output_dir.mkdir(exist_ok=True)

# Create subdirectories
(output_dir / "plots").mkdir(exist_ok=True)
(output_dir / "tables").mkdir(exist_ok=True)

print("="*60)
print("PTREE RESULTS VISUALIZATION")
print("="*60)

# Load factor returns
factors = pd.read_csv(results_dir / "ptree_outputs" / "ptree_factors.csv")
factors['month'] = pd.to_datetime(factors['month'])
factors = factors.set_index('month')

print(f"\nLoaded {len(factors)} months of factor returns")
print(f"Date range: {factors.index.min()} to {factors.index.max()}")

# ========== 1. CUMULATIVE RETURNS ==========
print("\n1. Creating cumulative return plots...")

fig, ax = plt.subplots(figsize=(14, 7))
for col in factors.columns:
    cumulative = (1 + factors[col]).cumprod()
    ax.plot(factors.index, cumulative, label=col.replace('factor', 'Factor '), linewidth=2)

ax.set_title('Cumulative Returns of PTree Factors (Swedish Market 1998-2022)', fontsize=14, fontweight='bold')
ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Cumulative Return (Initial Investment = 1)', fontsize=12)
ax.legend(loc='best', fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(output_dir / "plots" / "01_cumulative_returns.png", dpi=300, bbox_inches='tight')
print(f"   Saved: 01_cumulative_returns.png")
plt.close()

# ========== 2. ROLLING SHARPE RATIOS ==========
print("\n2. Creating rolling Sharpe ratio plots...")

fig, ax = plt.subplots(figsize=(14, 7))
window = 36  # 3-year rolling window

for col in factors.columns:
    rolling_mean = factors[col].rolling(window=window).mean()
    rolling_std = factors[col].rolling(window=window).std()
    rolling_sharpe = (rolling_mean / rolling_std) * np.sqrt(12)  # Annualized
    ax.plot(factors.index, rolling_sharpe, label=col.replace('factor', 'Factor '), linewidth=2)

ax.set_title(f'{window}-Month Rolling Sharpe Ratios (Annualized)', fontsize=14, fontweight='bold')
ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Sharpe Ratio', fontsize=12)
ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
ax.legend(loc='best', fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(output_dir / "plots" / "02_rolling_sharpe.png", dpi=300, bbox_inches='tight')
print(f"   OK Saved: 02_rolling_sharpe.png")
plt.close()

# ========== 3. MONTHLY RETURN DISTRIBUTIONS ==========
print("\n3. Creating return distribution plots...")

fig, axes = plt.subplots(2, 3, figsize=(16, 10))
axes = axes.flatten()

for idx, col in enumerate(factors.columns):
    ax = axes[idx]
    factors[col].hist(bins=30, ax=ax, edgecolor='black', alpha=0.7)
    ax.set_title(col.replace('factor', 'Factor '), fontsize=12, fontweight='bold')
    ax.set_xlabel('Monthly Return', fontsize=10)
    ax.set_ylabel('Frequency', fontsize=10)
    ax.axvline(x=factors[col].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {factors[col].mean():.4f}')
    ax.legend()
    ax.grid(True, alpha=0.3)

# Remove empty subplot
axes[-1].axis('off')

plt.suptitle('Distribution of Monthly Returns', fontsize=16, fontweight='bold', y=1.00)
plt.tight_layout()
plt.savefig(output_dir / "plots" / "03_return_distributions.png", dpi=300, bbox_inches='tight')
print(f"   OK Saved: 03_return_distributions.png")
plt.close()

# ========== 4. CORRELATION HEATMAP ==========
print("\n4. Creating correlation heatmap...")

fig, ax = plt.subplots(figsize=(10, 8))
corr = factors.corr()
sns.heatmap(corr, annot=True, fmt='.3f', cmap='coolwarm', center=0,
            square=True, linewidths=1, cbar_kws={"shrink": 0.8}, ax=ax)
ax.set_title('Correlation Matrix of PTree Factors', fontsize=14, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(output_dir / "plots" / "04_correlation_heatmap.png", dpi=300, bbox_inches='tight')
print(f"   OK Saved: 04_correlation_heatmap.png")
plt.close()

# ========== 5. DRAWDOWN ANALYSIS ==========
print("\n5. Creating drawdown plots...")

fig, ax = plt.subplots(figsize=(14, 7))

for col in factors.columns:
    cumulative = (1 + factors[col]).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    ax.plot(factors.index, drawdown * 100, label=col.replace('factor', 'Factor '), linewidth=2)

ax.set_title('Drawdown Analysis (% from Peak)', fontsize=14, fontweight='bold')
ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Drawdown (%)', fontsize=12)
ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
ax.legend(loc='best', fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(output_dir / "plots" / "05_drawdowns.png", dpi=300, bbox_inches='tight')
print(f"   OK Saved: 05_drawdowns.png")
plt.close()

# ========== 6. SUMMARY STATISTICS TABLE ==========
print("\n6. Creating summary statistics...")

stats = []
for col in factors.columns:
    returns = factors[col]
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max

    stats.append({
        'Factor': col.replace('factor', 'Factor '),
        'Mean Monthly Return': returns.mean(),
        'Annualized Return': (1 + returns.mean())**12 - 1,
        'Monthly Std Dev': returns.std(),
        'Annualized Std Dev': returns.std() * np.sqrt(12),
        'Sharpe Ratio (Annual)': (returns.mean() / returns.std()) * np.sqrt(12),
        'Cumulative Return': cumulative.iloc[-1] - 1,
        'Max Drawdown': drawdown.min(),
        'Skewness': returns.skew(),
        'Kurtosis': returns.kurtosis(),
        'Min Monthly Return': returns.min(),
        'Max Monthly Return': returns.max(),
        'Positive Months %': (returns > 0).sum() / len(returns) * 100
    })

stats_df = pd.DataFrame(stats)
stats_df.to_csv(output_dir / "tables" / "summary_statistics.csv", index=False)
print(f"   OK Saved: summary_statistics.csv")

# Create formatted version for display
stats_display = stats_df.copy()
for col in stats_display.columns:
    if col == 'Factor':
        continue
    if 'Return' in col or 'Drawdown' in col:
        stats_display[col] = stats_display[col].apply(lambda x: f"{x*100:.2f}%")
    elif 'Std Dev' in col:
        stats_display[col] = stats_display[col].apply(lambda x: f"{x*100:.2f}%")
    elif 'Sharpe' in col:
        stats_display[col] = stats_display[col].apply(lambda x: f"{x:.2f}")
    elif 'Positive' in col:
        stats_display[col] = stats_display[col].apply(lambda x: f"{x:.1f}%")
    else:
        stats_display[col] = stats_display[col].apply(lambda x: f"{x:.3f}")

stats_display.to_csv(output_dir / "tables" / "summary_statistics_formatted.csv", index=False)

# ========== 7. CREATE README ==========
print("\n7. Creating README...")

readme_content = f"""# PTree Analysis Results - Swedish Stock Market (1998-2022)

## Overview
This folder contains the complete analysis of PTree factors generated from the Swedish stock market.

**Date Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
**Analysis Period:** {factors.index.min().strftime('%Y-%m-%d')} to {factors.index.max().strftime('%Y-%m-%d')}
**Number of Months:** {len(factors)}

## Folder Structure

```
ptree_analysis/
├── plots/                          # Visualizations
│   ├── 01_cumulative_returns.png   # Cumulative return plot
│   ├── 02_rolling_sharpe.png       # Rolling Sharpe ratios
│   ├── 03_return_distributions.png # Histogram of returns
│   ├── 04_correlation_heatmap.png  # Factor correlations
│   └── 05_drawdowns.png            # Drawdown analysis
├── tables/                         # Summary statistics
│   ├── summary_statistics.csv      # Raw statistics
│   └── summary_statistics_formatted.csv  # Formatted for display
└── README.md                       # This file
```

## Key Findings

### Factor Performance Summary

{stats_display.to_markdown(index=False)}

## Plots Description

1. **Cumulative Returns**: Shows how $1 invested in each factor grows over time
2. **Rolling Sharpe Ratios**: 36-month rolling Sharpe ratios to show time-varying performance
3. **Return Distributions**: Histograms showing the distribution of monthly returns
4. **Correlation Heatmap**: Shows how correlated the factors are with each other
5. **Drawdowns**: Maximum decline from peak for each factor

## Factor Interpretation

- **Factor 1**: Primary PTree factor (base tree, no benchmark)
- **Factor 2**: First boosted factor (orthogonal to Factor 1)
- **Factors 3-5**: Additional boosted factors

### Split Information
The algorithm found splits primarily on:
- **rank_sp** (Sales-to-Price ratio) at threshold 0.636

## Notes

- All Sharpe ratios are annualized
- Annualized returns assume monthly compounding
- Equal-weighted portfolios were used
- Data cleaned to remove observations with missing characteristics

## Next Steps

1. Compare these factors with traditional Swedish market factors (size, value, momentum)
2. Test out-of-sample performance
3. Construct efficient frontier using these factors
4. Analyze factor exposures of individual stocks

## Data Source

Swedish stock market data (1997-2022) from FinBas and LSEG
"""

with open(output_dir / "README.md", "w", encoding='utf-8') as f:
    f.write(readme_content)

print(f"   OK Saved: README.md")

# ========== FINAL SUMMARY ==========
print("\n" + "="*60)
print("OK ANALYSIS COMPLETE!")
print("="*60)
print(f"\nAll results saved to:")
print(f"  {output_dir.absolute()}")
print(f"\nGenerated files:")
print(f"  - 5 visualization plots")
print(f"  - 2 summary statistics tables")
print(f"  - 1 README file")
print("\nOpen the folder to view your results!")
print("="*60)
