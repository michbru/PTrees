"""
Bootstrap Validation for P-Tree OOS Performance

Generates 100 bootstrap samples to assess the distribution of OOS Sharpe ratios.
This helps determine if the observed OOS performance is robust or due to luck.

Method:
1. Load OOS factor returns from Scenarios B and C
2. Bootstrap resample the OOS returns 100 times (with replacement)
3. Calculate Sharpe ratio for each bootstrap sample
4. Report: Mean ± Std. Dev. and 95% confidence interval
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

print("="*80)
print("BOOTSTRAP VALIDATION FOR P-TREE OOS PERFORMANCE")
print("="*80)
print()

def calculate_sharpe(returns):
    """Calculate annualized Sharpe ratio"""
    return np.mean(returns) / np.std(returns) * np.sqrt(12)

def bootstrap_sharpe(returns, n_bootstrap=100, random_state=42):
    """
    Bootstrap resample returns and calculate Sharpe ratios

    Args:
        returns: Array of monthly returns
        n_bootstrap: Number of bootstrap samples
        random_state: Random seed for reproducibility

    Returns:
        Array of bootstrap Sharpe ratios
    """
    np.random.seed(random_state)
    n_months = len(returns)
    bootstrap_sharpes = []

    for i in range(n_bootstrap):
        # Resample with replacement
        sample_indices = np.random.choice(n_months, size=n_months, replace=True)
        sample_returns = returns[sample_indices]

        # Calculate Sharpe
        sharpe = calculate_sharpe(sample_returns)
        bootstrap_sharpes.append(sharpe)

    return np.array(bootstrap_sharpes)

def analyze_scenario(scenario_name, oos_file, tree_num=1):
    """Analyze a single scenario with bootstrap"""
    print(f"\n{'='*80}")
    print(f"{scenario_name}")
    print(f"{'='*80}\n")

    if not oos_file.exists():
        print(f"WARNING: File not found: {oos_file}")
        print("Run P-Tree analysis first to generate OOS predictions\n")
        return None

    # Load OOS factors
    factors = pd.read_csv(oos_file)
    factor_col = f'factor{tree_num}'

    if factor_col not in factors.columns:
        print(f"WARNING: Column '{factor_col}' not found in {oos_file}")
        return None

    returns = factors[factor_col].values

    # Original Sharpe
    original_sharpe = calculate_sharpe(returns)
    print(f"Original OOS Sharpe (Tree {tree_num}): {original_sharpe:.3f}")
    print(f"OOS months: {len(returns)}")

    # Bootstrap
    print("\nBootstrapping (100 samples)...")
    bootstrap_sharpes = bootstrap_sharpe(returns, n_bootstrap=100)

    # Statistics
    mean_sharpe = np.mean(bootstrap_sharpes)
    std_sharpe = np.std(bootstrap_sharpes)
    ci_lower = np.percentile(bootstrap_sharpes, 2.5)
    ci_upper = np.percentile(bootstrap_sharpes, 97.5)

    print(f"Bootstrap Mean Sharpe: {mean_sharpe:.3f}")
    print(f"Bootstrap Std Dev: {std_sharpe:.3f}")
    print(f"95% CI: [{ci_lower:.3f}, {ci_upper:.3f}]")
    print(f"Positive Sharpe: {np.sum(bootstrap_sharpes > 0)}/100 samples ({np.sum(bootstrap_sharpes > 0)}%)")
    print(f"Sharpe > 1.0: {np.sum(bootstrap_sharpes > 1.0)}/100 samples ({np.sum(bootstrap_sharpes > 1.0)}%)")

    # Statistical significance (t-test)
    t_stat = np.mean(returns) / (np.std(returns) / np.sqrt(len(returns))) * np.sqrt(12)
    print(f"t-statistic: {t_stat:.2f}")

    return {
        'scenario': scenario_name,
        'tree': tree_num,
        'original_sharpe': original_sharpe,
        'bootstrap_mean': mean_sharpe,
        'bootstrap_std': std_sharpe,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'pct_positive': np.sum(bootstrap_sharpes > 0),
        'pct_above_1': np.sum(bootstrap_sharpes > 1.0),
        't_stat': t_stat,
        'bootstrap_sharpes': bootstrap_sharpes
    }

###### Analyze Scenarios B and C #####

results_dir = Path('../../results/ptree_34chars')

# Scenario B: Train 1997-2010, Test 2010-2022
scenario_b_file = results_dir / 'scenario_b_split' / 'ptree_factors_oos.csv'
results_b = analyze_scenario(
    "SCENARIO B: Time Split (Train 1997-2010, Test 2010-2022)",
    scenario_b_file,
    tree_num=1
)

# Scenario C: Train 2010-2022, Test 1997-2010
scenario_c_file = results_dir / 'scenario_c_reverse' / 'ptree_factors_oos.csv'
results_c = analyze_scenario(
    "SCENARIO C: Reverse Split (Train 2010-2022, Test 1997-2010)",
    scenario_c_file,
    tree_num=1
)

###### Summary and Visualization #####

if results_b is not None and results_c is not None:
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}\n")

    summary_df = pd.DataFrame([
        {
            'Scenario': results_b['scenario'].split(':')[0],
            'Original_Sharpe': f"{results_b['original_sharpe']:.3f}",
            'Bootstrap_Mean': f"{results_b['bootstrap_mean']:.3f}",
            'Bootstrap_StdDev': f"{results_b['bootstrap_std']:.3f}",
            '95%_CI': f"[{results_b['ci_lower']:.3f}, {results_b['ci_upper']:.3f}]",
            't_stat': f"{results_b['t_stat']:.2f}"
        },
        {
            'Scenario': results_c['scenario'].split(':')[0],
            'Original_Sharpe': f"{results_c['original_sharpe']:.3f}",
            'Bootstrap_Mean': f"{results_c['bootstrap_mean']:.3f}",
            'Bootstrap_StdDev': f"{results_c['bootstrap_std']:.3f}",
            '95%_CI': f"[{results_c['ci_lower']:.3f}, {results_c['ci_upper']:.3f}]",
            't_stat': f"{results_c['t_stat']:.2f}"
        }
    ])

    print(summary_df.to_string(index=False))

    # Save summary
    output_dir = results_dir / 'bootstrap_validation'
    output_dir.mkdir(exist_ok=True)
    summary_df.to_csv(output_dir / 'bootstrap_summary.csv', index=False)

    # Create histogram plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Scenario B histogram
    axes[0].hist(results_b['bootstrap_sharpes'], bins=20, alpha=0.7, edgecolor='black')
    axes[0].axvline(results_b['original_sharpe'], color='red', linestyle='--',
                   linewidth=2, label=f"Original: {results_b['original_sharpe']:.2f}")
    axes[0].axvline(results_b['bootstrap_mean'], color='blue', linestyle='--',
                   linewidth=2, label=f"Mean: {results_b['bootstrap_mean']:.2f}")
    axes[0].set_xlabel('OOS Sharpe Ratio')
    axes[0].set_ylabel('Frequency')
    axes[0].set_title('Scenario B: Bootstrap Distribution\n(Train 1997-2010, Test 2010-2022)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Scenario C histogram
    axes[1].hist(results_c['bootstrap_sharpes'], bins=20, alpha=0.7, edgecolor='black', color='orange')
    axes[1].axvline(results_c['original_sharpe'], color='red', linestyle='--',
                   linewidth=2, label=f"Original: {results_c['original_sharpe']:.2f}")
    axes[1].axvline(results_c['bootstrap_mean'], color='blue', linestyle='--',
                   linewidth=2, label=f"Mean: {results_c['bootstrap_mean']:.2f}")
    axes[1].set_xlabel('OOS Sharpe Ratio')
    axes[1].set_ylabel('Frequency')
    axes[1].set_title('Scenario C: Bootstrap Distribution\n(Train 2010-2022, Test 1997-2010)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'bootstrap_distributions.png', dpi=300, bbox_inches='tight')
    print(f"\nSaved visualization: {output_dir / 'bootstrap_distributions.png'}")

    print(f"\n{'='*80}")
    print("INTERPRETATION")
    print(f"{'='*80}\n")

    print("The bootstrap analysis helps assess robustness of OOS performance:")
    print("1. Bootstrap Mean ≈ Original Sharpe → Results are stable")
    print("2. Narrow confidence interval → Consistent performance")
    print("3. >95% positive Sharpe samples → Statistically robust")
    print("4. High t-statistic (>2.0) → Statistically significant\n")

    if results_b['pct_positive'] >= 95 and results_c['pct_positive'] >= 95:
        print("✅ VERDICT: Both scenarios show robust positive performance")
    elif results_b['pct_positive'] >= 95:
        print("⚠️ VERDICT: Scenario B is robust, but Scenario C shows weaker performance")
    else:
        print("⚠️ VERDICT: Results show high variability - interpret with caution")

print(f"\n{'='*80}")
print("BOOTSTRAP VALIDATION COMPLETE")
print(f"{'='*80}\n")
