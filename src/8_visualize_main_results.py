"""
Visualize Main P-Tree Results

Creates publication-quality plots for:
1. Sharpe ratios across scenarios (3 scenarios, 3 trees each)
2. Alphas vs benchmarks (CAPM/FF3/FF4)
3. Transaction cost impact
4. Subperiod consistency
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

print("="*80)
print("MAIN RESULTS VISUALIZATION")
print("="*80)

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
colors = ['#2E86AB', '#A23B72', '#F18F01']  # Professional color scheme

# Create output directory
output_dir = Path('results/plots')
output_dir.mkdir(exist_ok=True, parents=True)

# ===== PLOT 1: SHARPE RATIOS ACROSS SCENARIOS =====
print("\nGenerating Sharpe ratio comparison...")

# Load summary data
summary_file = Path('results/ptree_all_scenarios_summary.csv')
if summary_file.exists():
    df_summary = pd.read_csv(summary_file)

    fig, ax = plt.subplots(figsize=(12, 6))

    scenarios = df_summary['Scenario'].values
    x_pos = np.arange(len(scenarios))
    width = 0.25

    # Plot bars for each tree
    bars1 = ax.bar(x_pos - width, df_summary['Tree1_Sharpe'], width,
                   label='Tree 1', color=colors[0], edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x_pos, df_summary['Tree2_Sharpe'], width,
                   label='Tree 2', color=colors[1], edgecolor='black', linewidth=1.5)
    bars3 = ax.bar(x_pos + width, df_summary['Tree3_Sharpe'], width,
                   label='Tree 3', color=colors[2], edgecolor='black', linewidth=1.5)

    # Add value labels on bars
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_xlabel('Scenario', fontsize=12, fontweight='bold')
    ax.set_ylabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax.set_title('P-Tree Performance Across Scenarios', fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(scenarios, fontsize=10)
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Sharpe = 1.0')

    plt.tight_layout()
    plt.savefig(output_dir / 'sharpe_ratios_by_scenario.png', dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_dir / 'sharpe_ratios_by_scenario.png'}")
    plt.close()
else:
    print("  [SKIP] Summary file not found")

# ===== PLOT 2: ALPHAS VS BENCHMARKS =====
print("\nGenerating alpha comparison...")

benchmark_results = []
scenarios_map = {
    'A_Full': ('Scenario A\n(Full Sample)', 'results/ptree_scenario_a_full'),
    'B_Split': ('Scenario B\n(Time Split OOS)', 'results/ptree_scenario_b_split'),
    'C_Reverse': ('Scenario C\n(Reverse Split OOS)', 'results/ptree_scenario_c_reverse')
}

for scenario_key, (label, folder) in scenarios_map.items():
    alpha_file = Path(folder) / 'benchmark_analysis' / 'table2_alphas.csv'
    if alpha_file.exists():
        df_alpha = pd.read_csv(alpha_file)
        # Get Factor 1 (most important)
        f1 = df_alpha[df_alpha['Factor'] == 'F1'].iloc[0]
        benchmark_results.append({
            'Scenario': label,
            'CAPM': f1['CAPM_alpha'],
            'FF3': f1['FF3_alpha'],
            'FF4': f1['FF4_alpha']
        })

if len(benchmark_results) > 0:
    df_benchmarks = pd.DataFrame(benchmark_results)

    fig, ax = plt.subplots(figsize=(12, 6))

    x_pos = np.arange(len(df_benchmarks))
    width = 0.25

    bars1 = ax.bar(x_pos - width, df_benchmarks['CAPM'], width,
                   label='CAPM Alpha', color='#1E88E5', edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x_pos, df_benchmarks['FF3'], width,
                   label='FF3 Alpha', color='#FFC107', edgecolor='black', linewidth=1.5)
    bars3 = ax.bar(x_pos + width, df_benchmarks['FF4'], width,
                   label='FF4 Alpha', color='#43A047', edgecolor='black', linewidth=1.5)

    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%',
                   ha='center', va='bottom' if height > 0 else 'top',
                   fontsize=9, fontweight='bold')

    ax.set_xlabel('Scenario', fontsize=12, fontweight='bold')
    ax.set_ylabel('Alpha (% per year)', fontsize=12, fontweight='bold')
    ax.set_title('P-Tree Factor 1 Alphas vs Benchmarks', fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(df_benchmarks['Scenario'], fontsize=10)
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)

    plt.tight_layout()
    plt.savefig(output_dir / 'alphas_vs_benchmarks.png', dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_dir / 'alphas_vs_benchmarks.png'}")
    plt.close()
else:
    print("  [SKIP] Benchmark data not found")

# ===== PLOT 3: TRANSACTION COST IMPACT =====
print("\nGenerating transaction cost impact...")

tc_file = Path('results/robustness_checks/transaction_cost_analysis.csv')
if tc_file.exists():
    df_tc = pd.read_csv(tc_file)

    # Focus on Scenario B (most realistic OOS)
    df_tc_b = df_tc[df_tc['Scenario'] == 'B: Time Split (OOS)']

    # Get medium turnover scenarios
    df_tc_medium = df_tc_b[df_tc_b['Turnover_Level'] == 'Medium']

    if len(df_tc_medium) > 0:
        fig, ax = plt.subplots(figsize=(10, 6))

        tc_levels = df_tc_medium['TC_Level'].values
        gross_returns = df_tc_medium['Gross_Return_pct'].values
        net_returns = df_tc_medium['Net_Return_pct'].values
        cost_drag = df_tc_medium['Cost_Drag_pct'].values

        x_pos = np.arange(len(tc_levels))
        width = 0.35

        bars1 = ax.bar(x_pos - width/2, gross_returns, width,
                       label='Gross Return', color='#4CAF50', edgecolor='black', linewidth=1.5)
        bars2 = ax.bar(x_pos + width/2, net_returns, width,
                       label='Net Return (After Costs)', color='#F44336', edgecolor='black', linewidth=1.5)

        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%',
                       ha='center', va='bottom', fontsize=10, fontweight='bold')

        # Add cost drag annotations
        for i, (x, drag) in enumerate(zip(x_pos, cost_drag)):
            ax.annotate(f'Cost: {drag:.1f}%', xy=(x, 0), xytext=(x, -5),
                       ha='center', fontsize=9, color='gray')

        ax.set_xlabel('Transaction Cost Level', fontsize=12, fontweight='bold')
        ax.set_ylabel('Annualized Return (%)', fontsize=12, fontweight='bold')
        ax.set_title('Impact of Transaction Costs (Scenario B, 100% Monthly Turnover)',
                     fontsize=13, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels([f'{tc}\nTC' for tc in tc_levels], fontsize=10)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1)

        plt.tight_layout()
        plt.savefig(output_dir / 'transaction_cost_impact.png', dpi=300, bbox_inches='tight')
        print(f"  Saved: {output_dir / 'transaction_cost_impact.png'}")
        plt.close()
    else:
        print("  [SKIP] No medium turnover data")
else:
    print("  [SKIP] Transaction cost file not found")

# ===== PLOT 4: SUBPERIOD CONSISTENCY =====
print("\nGenerating subperiod consistency...")

subperiod_file = Path('results/robustness_checks/subperiod_analysis.csv')
if subperiod_file.exists():
    df_subperiod = pd.read_csv(subperiod_file)

    # Focus on Scenario B OOS
    df_sub_b = df_subperiod[(df_subperiod['Scenario'] == 'B: Time Split (OOS)') &
                             (df_subperiod['Data_Type'] == 'OOS')]

    if len(df_sub_b) > 0:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Sharpe ratios by period
        periods = df_sub_b['Period'].values
        sharpe_values = df_sub_b['Sharpe_Ratio'].values

        bars = ax1.bar(range(len(periods)), sharpe_values,
                       color=['#4CAF50' if s > 0 else '#F44336' for s in sharpe_values],
                       edgecolor='black', linewidth=1.5)

        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, sharpe_values)):
            ax1.text(i, val, f'{val:.2f}',
                    ha='center', va='bottom' if val > 0 else 'top',
                    fontsize=9, fontweight='bold')

        ax1.set_xlabel('Time Period', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Sharpe Ratio', fontsize=11, fontweight='bold')
        ax1.set_title('Sharpe Ratio by Economic Period', fontsize=12, fontweight='bold')
        ax1.set_xticks(range(len(periods)))
        ax1.set_xticklabels(periods, rotation=45, ha='right', fontsize=9)
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax1.axhline(y=df_sub_b['Sharpe_Ratio'].mean(), color='blue',
                   linestyle='--', linewidth=2, alpha=0.7, label=f'Mean: {df_sub_b["Sharpe_Ratio"].mean():.2f}')
        ax1.legend(fontsize=9)

        # CAPM Alphas by period
        alpha_values = df_sub_b['CAPM_Alpha_pct'].values

        bars = ax2.bar(range(len(periods)), alpha_values,
                       color=['#1E88E5' if a > 0 else '#E53935' for a in alpha_values],
                       edgecolor='black', linewidth=1.5)

        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, alpha_values)):
            if not np.isnan(val):
                ax2.text(i, val, f'{val:.1f}%',
                        ha='center', va='bottom' if val > 0 else 'top',
                        fontsize=9, fontweight='bold')

        ax2.set_xlabel('Time Period', fontsize=11, fontweight='bold')
        ax2.set_ylabel('CAPM Alpha (% per year)', fontsize=11, fontweight='bold')
        ax2.set_title('CAPM Alpha by Economic Period', fontsize=12, fontweight='bold')
        ax2.set_xticks(range(len(periods)))
        ax2.set_xticklabels(periods, rotation=45, ha='right', fontsize=9)
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
        mean_alpha = df_sub_b['CAPM_Alpha_pct'].mean()
        if not np.isnan(mean_alpha):
            ax2.axhline(y=mean_alpha, color='blue',
                       linestyle='--', linewidth=2, alpha=0.7, label=f'Mean: {mean_alpha:.1f}%')
            ax2.legend(fontsize=9)

        plt.tight_layout()
        plt.savefig(output_dir / 'subperiod_consistency.png', dpi=300, bbox_inches='tight')
        print(f"  Saved: {output_dir / 'subperiod_consistency.png'}")
        plt.close()
    else:
        print("  [SKIP] No Scenario B OOS subperiod data")
else:
    print("  [SKIP] Subperiod file not found")

print("\n" + "="*80)
print("VISUALIZATION SUMMARY")
print("="*80)

# List all generated plots
plot_files = [
    'sharpe_ratios_by_scenario.png',
    'alphas_vs_benchmarks.png',
    'transaction_cost_impact.png',
    'subperiod_consistency.png'
]

print(f"\nGenerated plots in: {output_dir}/")
for plot_file in plot_files:
    plot_path = output_dir / plot_file
    if plot_path.exists():
        print(f"  [OK] {plot_file}")
    else:
        print(f"  [MISS] {plot_file}")

print("\n" + "="*80)
print("MAIN RESULTS VISUALIZATION COMPLETE")
print("="*80)
print(f"\nAll plots saved to: {output_dir}/")
print("\nUse these plots in your thesis to visualize:")
print("  1. Overall P-Tree performance (Sharpe ratios)")
print("  2. Alphas vs academic benchmarks (CAPM/FF3/FF4)")
print("  3. Real-world implementability (transaction costs)")
print("  4. Temporal stability (subperiod consistency)")
