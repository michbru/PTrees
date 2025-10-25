"""
Comprehensive Benchmark Analysis for All P-Tree Scenarios

Compares P-Tree factors against:
1. CAPM (Market factor)
2. Fama-French 3-Factor
3. Fama-French 4-Factor (FF3 + Momentum)

For scenarios A, B, and C
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from numpy.linalg import pinv
import warnings
import os
warnings.filterwarnings("ignore")

print("="*80)
print("COMPREHENSIVE BENCHMARK ANALYSIS - ALL P-TREE SCENARIOS")
print("="*80)

# Configuration
lambda_cov = 1e-5
lambda_mean = 0

# Scenarios to analyze
scenarios = {
    'A_Full': {
        'name': 'Scenario A: Full Sample (1997-2022)',
        'folder': 'results/ptree_scenario_a_full',
        'period': '1997-02 to 2022-12'
    },
    'B_Split': {
        'name': 'Scenario B: Time Split (Train 1997-2010)',
        'folder': 'results/ptree_scenario_b_split',
        'period': '1997-02 to 2009-12'
    },
    'C_Reverse': {
        'name': 'Scenario C: Reverse Split (Train 2010-2020)',
        'folder': 'results/ptree_scenario_c_reverse',
        'period': '2010-01 to 2022-12'
    }
}

# Load macro variables with dates
print("\nLoading benchmark factor data...")
macro = pd.read_csv('data/macro_variables_with_dates.csv')
macro['date'] = pd.to_datetime(macro['date'])
macro = macro.set_index('date')
print(f"  Macro data: {len(macro)} months ({macro.index[0].strftime('%Y-%m')} to {macro.index[-1].strftime('%Y-%m')})")

# Helper functions
def calculate_sharpe(returns):
    return returns.mean() / returns.std() * np.sqrt(12)

def calculate_mve_sharpe(factor_df, lambda_cov=1e-5, lambda_mean=0):
    f = factor_df.values
    cov_matrix = np.cov(f.T) + lambda_cov * np.eye(f.shape[1])
    mean_vec = f.mean(axis=0) + lambda_mean * np.ones(f.shape[1])
    w = pinv(cov_matrix) @ mean_vec
    w = w / np.sum(np.abs(w))
    mve_return = f @ w
    sharpe = mve_return.mean() / mve_return.std() * np.sqrt(12)
    return sharpe, mve_return.mean() * 12 * 100, mve_return.std() * np.sqrt(12) * 100

def run_regression(Y, X, add_constant=True, hac_lags=3):
    if add_constant:
        X = sm.add_constant(X)
    model = sm.OLS(Y, X)
    results = model.fit(cov_type='HAC', cov_kwds={'maxlags': hac_lags})
    alpha = results.params[0] if add_constant else np.nan
    t_stat = results.tvalues[0] if add_constant else np.nan
    r2 = results.rsquared
    alpha_ann = alpha * 12 * 100
    return alpha_ann, t_stat, r2, results

# Store all results
all_scenario_results = {}

# Analyze each scenario
for scenario_key, scenario_info in scenarios.items():
    print("\n" + "="*80)
    print(f"{scenario_info['name']}")
    print("="*80)

    # Load P-Tree factors for this scenario
    ptree_path = os.path.join(scenario_info['folder'], 'ptree_factors.csv')

    if not os.path.exists(ptree_path):
        print(f"  [SKIP] File not found: {ptree_path}")
        continue

    ptree = pd.read_csv(ptree_path)
    ptree['month'] = pd.to_datetime(ptree['month'])
    ptree = ptree.set_index('month')

    print(f"\n  P-Tree factors: {len(ptree)} months")
    print(f"  Period: {ptree.index[0].strftime('%Y-%m')} to {ptree.index[-1].strftime('%Y-%m')}")

    # Align with macro data
    common_dates = ptree.index.intersection(macro.index)

    if len(common_dates) == 0:
        print(f"  [ERROR] No overlapping dates with macro data!")
        continue

    ptree_aligned = ptree.loc[common_dates]
    macro_aligned = macro.loc[common_dates]

    print(f"  Aligned: {len(common_dates)} months")

    # Extract benchmark factors
    mkt = macro_aligned['rm_rf'].values
    smb = macro_aligned['smb_vw'].values
    hml = macro_aligned['hml_vw'].values
    mom = macro_aligned['mom_vw'].values

    # Results storage for this scenario
    scenario_results = {
        'sharpe': [],
        'alphas': [],
        'correlations': {}
    }

    # ----- TABLE 1: SHARPE RATIOS -----
    print("\n" + "-"*80)
    print("  TABLE 1: SHARPE RATIOS")
    print("-"*80)

    for i, factor_name in enumerate(['factor1', 'factor2', 'factor3'], 1):
        individual_sr = calculate_sharpe(ptree_aligned[factor_name])
        mve_sr, mve_mean, mve_std = calculate_mve_sharpe(
            ptree_aligned.iloc[:, :i],
            lambda_cov=lambda_cov,
            lambda_mean=lambda_mean
        )

        scenario_results['sharpe'].append({
            'Factor': f'F{i}',
            'Individual_SR': individual_sr,
            'MVE_SR': mve_sr,
            'MVE_Mean_pct': mve_mean,
            'MVE_Std_pct': mve_std
        })

        print(f"  Factor {i}: SR={individual_sr:.3f} | MVE SR(1-{i})={mve_sr:.3f}")

    # ----- TABLE 2: ALPHAS VS BENCHMARKS -----
    print("\n" + "-"*80)
    print("  TABLE 2: ALPHAS VS BENCHMARKS")
    print("-"*80)

    for i, factor_name in enumerate(['factor1', 'factor2', 'factor3'], 1):
        Y = ptree_aligned[factor_name].values

        # CAPM
        alpha_capm, t_capm, r2_capm, _ = run_regression(Y, mkt.reshape(-1, 1))

        # FF3
        X_ff3 = np.column_stack([mkt, smb, hml])
        alpha_ff3, t_ff3, r2_ff3, _ = run_regression(Y, X_ff3)

        # FF4
        X_ff4 = np.column_stack([mkt, smb, hml, mom])
        alpha_ff4, t_ff4, r2_ff4, _ = run_regression(Y, X_ff4)

        scenario_results['alphas'].append({
            'Factor': f'F{i}',
            'CAPM_alpha': alpha_capm,
            'CAPM_tstat': t_capm,
            'CAPM_R2': r2_capm,
            'FF3_alpha': alpha_ff3,
            'FF3_tstat': t_ff3,
            'FF3_R2': r2_ff3,
            'FF4_alpha': alpha_ff4,
            'FF4_tstat': t_ff4,
            'FF4_R2': r2_ff4
        })

        print(f"\n  Factor {i}:")
        print(f"    CAPM:  alpha={alpha_capm:6.2f}% (t={t_capm:5.2f}), R2={r2_capm:.3f}")
        print(f"    FF3:   alpha={alpha_ff3:6.2f}% (t={t_ff3:5.2f}), R2={r2_ff3:.3f}")
        print(f"    FF4:   alpha={alpha_ff4:6.2f}% (t={t_ff4:5.2f}), R2={r2_ff4:.3f}")

    # ----- TABLE 3: CORRELATIONS -----
    print("\n" + "-"*80)
    print("  TABLE 3: FACTOR CORRELATIONS")
    print("-"*80)

    all_factors = pd.DataFrame({
        'P-Tree F1': ptree_aligned['factor1'],
        'P-Tree F2': ptree_aligned['factor2'],
        'P-Tree F3': ptree_aligned['factor3'],
        'MKT': mkt,
        'SMB': smb,
        'HML': hml,
        'MOM': mom
    })

    corr_matrix = all_factors.corr()
    print(corr_matrix.round(3))

    scenario_results['correlations'] = corr_matrix

    # Save scenario results
    output_dir = os.path.join(scenario_info['folder'], 'benchmark_analysis')
    os.makedirs(output_dir, exist_ok=True)

    # Save tables
    df_sharpe = pd.DataFrame(scenario_results['sharpe'])
    df_sharpe.to_csv(os.path.join(output_dir, 'table1_sharpe_ratios.csv'), index=False)

    df_alphas = pd.DataFrame(scenario_results['alphas'])
    df_alphas.to_csv(os.path.join(output_dir, 'table2_alphas.csv'), index=False)

    corr_matrix.to_csv(os.path.join(output_dir, 'table3_correlations.csv'))

    print(f"\n  Results saved to: {output_dir}")

    # Store for cross-scenario comparison
    all_scenario_results[scenario_key] = scenario_results

# ----- CROSS-SCENARIO COMPARISON -----
print("\n" + "="*80)
print("CROSS-SCENARIO COMPARISON")
print("="*80)

comparison_data = []
for scenario_key, scenario_info in scenarios.items():
    if scenario_key not in all_scenario_results:
        continue

    results = all_scenario_results[scenario_key]

    # Get Factor 1 performance (most important)
    f1_sharpe = results['sharpe'][0]
    f1_alpha = results['alphas'][0]

    comparison_data.append({
        'Scenario': scenario_info['name'].split(':')[0],
        'Period': scenario_info['period'],
        'F1_Sharpe': f1_sharpe['Individual_SR'],
        'F1_Alpha_CAPM': f1_alpha['CAPM_alpha'],
        'F1_tstat_CAPM': f1_alpha['CAPM_tstat'],
        'F1_Alpha_FF3': f1_alpha['FF3_alpha'],
        'F1_tstat_FF3': f1_alpha['FF3_tstat'],
        'F1_Alpha_FF4': f1_alpha['FF4_alpha'],
        'F1_tstat_FF4': f1_alpha['FF4_tstat']
    })

df_comparison = pd.DataFrame(comparison_data)
print("\nFactor 1 Performance Across Scenarios:")
print(df_comparison.to_string(index=False))

df_comparison.to_csv('results/cross_scenario_comparison.csv', index=False)
print("\nSaved to: results/cross_scenario_comparison.csv")

print("\n" + "="*80)
print("BENCHMARK ANALYSIS COMPLETE")
print("="*80)
print("\nAll results saved to respective scenario folders under /benchmark_analysis/")
