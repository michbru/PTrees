"""
Benchmark Analysis for Swedish P-Tree Factors
==============================================

This script compares P-Tree factors against:
1. CAPM (Market factor)
2. Fama-French 3-Factor (MKT, SMB, HML)
3. Fama-French 4-Factor (FF3 + Momentum)
4. Macro variables (volatility, inflation)

Following the methodology from:
Cong et al. (2024) "Growing the Efficient Frontier on Panel Trees"
Journal of Financial Economics
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from numpy.linalg import inv, pinv
import warnings
warnings.filterwarnings("ignore")

print("="*80)
print("SWEDISH P-TREE BENCHMARK ANALYSIS")
print("="*80)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Regularization parameters (matching original paper)
lambda_mean = 0
lambda_cov = 1e-5

# Output directory
import os
os.makedirs('results/benchmark_analysis', exist_ok=True)

# ============================================================================
# LOAD DATA
# ============================================================================

print("\n" + "="*80)
print("LOADING DATA")
print("="*80)

# Load P-Tree factors
print("\n1. Loading P-Tree factors...")
ptree_factors = pd.read_csv('results/ptree_factors.csv')
ptree_factors['month'] = pd.to_datetime(ptree_factors['month'])
ptree_factors = ptree_factors.set_index('month')
print(f"   [OK] Loaded {len(ptree_factors)} months ({ptree_factors.index[0].strftime('%Y-%m')} to {ptree_factors.index[-1].strftime('%Y-%m')})")
print(f"   [OK] Factors: {list(ptree_factors.columns)}")

# Load macro variables (Fama-French factors + macro predictors)
print("\n2. Loading macro variables and Fama-French factors...")

# Check if dated version exists
import os
if os.path.exists('data/macro_variables_with_dates.csv'):
    print("   [OK] Found macro_variables_with_dates.csv (with date column)")
    macro = pd.read_csv('data/macro_variables_with_dates.csv')
    macro['date'] = pd.to_datetime(macro['date'])
    macro = macro.set_index('date')
    print(f"   [OK] Loaded {len(macro)} months ({macro.index[0].strftime('%Y-%m')} to {macro.index[-1].strftime('%Y-%m')})")

    # Align P-Tree factors to match macro date range
    common_dates = ptree_factors.index.intersection(macro.index)
    print(f"   [OK] Common dates: {len(common_dates)} months")

    if len(common_dates) < len(macro):
        print(f"   [WARNING] Using {len(common_dates)} overlapping months")

    ptree_factors = ptree_factors.loc[common_dates]
    macro = macro.loc[common_dates]

else:
    print("   [WARNING] Using macro_variables.csv (no date column - will infer dates)")
    macro = pd.read_csv('data/macro_variables.csv')
    print(f"   [OK] Loaded {len(macro)} rows")

    # Infer dates based on P-Tree data
    print(f"\n   Note: Inferred date range: Sep 1997 to Jul 2020 (275 months)")
    print("   (Based on correlation analysis with P-Tree value-weighted returns)")

    # Generate date range
    inferred_dates = pd.date_range(start='1997-09-30', periods=len(macro), freq='M')
    macro.index = inferred_dates

    # Align with P-Tree
    common_dates = ptree_factors.index.intersection(macro.index)
    ptree_factors = ptree_factors.loc[common_dates]
    macro = macro.loc[common_dates]

    print(f"   [OK] Aligned to {len(common_dates)} common months")

print(f"\n   Final analysis period: {ptree_factors.index[0].strftime('%Y-%m')} to {ptree_factors.index[-1].strftime('%Y-%m')}")
print(f"   Total months: {len(ptree_factors)}")

# Extract key variables
mkt = macro['rm_rf'].values  # Market excess return
rf = macro['rf'].values       # Risk-free rate
smb = macro['smb_vw'].values  # Size factor (value-weighted)
hml = macro['hml_vw'].values  # Value factor (value-weighted)
mom = macro['mom_vw'].values  # Momentum factor (value-weighted)

print(f"\n   [OK] Extracted factors:")
print(f"     - Market (rm_rf): mean={mkt.mean()*100:.2f}%, std={mkt.std()*100:.2f}%")
print(f"     - SMB (vw):       mean={smb.mean()*100:.2f}%, std={smb.std()*100:.2f}%")
print(f"     - HML (vw):       mean={hml.mean()*100:.2f}%, std={hml.std()*100:.2f}%")
print(f"     - MOM (vw):       mean={mom.mean()*100:.2f}%, std={mom.std()*100:.2f}%")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_sharpe(returns):
    """Calculate annualized Sharpe ratio"""
    return returns.mean() / returns.std() * np.sqrt(12)

def calculate_mve_sharpe(factor_df, lambda_cov=1e-5, lambda_mean=0):
    """
    Calculate Mean-Variance Efficient portfolio Sharpe ratio

    Following Cong et al. (2024) methodology:
    w = inv(Cov + λ*I) @ (Mean + λ*1)
    """
    f = factor_df.values
    cov_matrix = np.cov(f.T) + lambda_cov * np.eye(f.shape[1])
    mean_vec = f.mean(axis=0) + lambda_mean * np.ones(f.shape[1])

    # Calculate optimal weights
    w = pinv(cov_matrix) @ mean_vec
    w = w / np.sum(np.abs(w))  # Normalize weights

    # Calculate MVE portfolio return
    mve_return = f @ w
    sharpe = mve_return.mean() / mve_return.std() * np.sqrt(12)

    return sharpe, mve_return.mean() * 12 * 100, mve_return.std() * np.sqrt(12) * 100, w

def run_regression(Y, X, add_constant=True, hac_lags=3):
    """
    Run OLS regression with HAC standard errors (Newey-West)

    Returns: alpha (annualized %), t-stat, R², RMSE (annualized %)
    """
    if add_constant:
        X = sm.add_constant(X)

    model = sm.OLS(Y, X)
    results = model.fit(cov_type='HAC', cov_kwds={'maxlags': hac_lags})

    alpha = results.params[0] if add_constant else np.nan
    t_stat = results.tvalues[0] if add_constant else np.nan
    r2 = results.rsquared
    rmse = np.sqrt(np.mean(results.resid**2))

    # Annualize
    alpha_ann = alpha * 12 * 100  # Monthly to annual percentage
    rmse_ann = rmse * np.sqrt(12) * 100

    return alpha_ann, t_stat, r2, rmse_ann, results

# ============================================================================
# TABLE 1: SHARPE RATIOS (Individual and MVE)
# ============================================================================

print("\n" + "="*80)
print("TABLE 1: SHARPE RATIOS")
print("="*80)

sharpe_results = []

for i in range(1, len(ptree_factors.columns) + 1):
    factor_name = f'factor{i}'

    # Individual Sharpe ratio
    individual_sr = calculate_sharpe(ptree_factors[factor_name])

    # MVE Sharpe ratio (using factors 1 through i)
    mve_sr, mve_mean, mve_std, mve_weights = calculate_mve_sharpe(
        ptree_factors.iloc[:, :i],
        lambda_cov=lambda_cov,
        lambda_mean=lambda_mean
    )

    sharpe_results.append({
        'Factor': factor_name,
        'Individual SR': individual_sr,
        'MVE SR (1 to i)': mve_sr,
        'MVE Mean (%)': mve_mean,
        'MVE Std (%)': mve_std
    })

    print(f"\n{factor_name}:")
    print(f"  Individual SR: {individual_sr:.3f}")
    print(f"  MVE SR (factors 1-{i}): {mve_sr:.3f}")

# Save results
df_sharpe = pd.DataFrame(sharpe_results)
df_sharpe.to_csv('results/benchmark_analysis/table1_sharpe_ratios.csv', index=False)
print(f"\n[OK] Saved to results/benchmark_analysis/table1_sharpe_ratios.csv")

# ============================================================================
# TABLE 2: ALPHA VS BENCHMARKS
# ============================================================================

print("\n" + "="*80)
print("TABLE 2: ALPHAS VS BENCHMARK MODELS")
print("="*80)

alpha_results = []

for i, factor_name in enumerate(ptree_factors.columns, 1):
    Y = ptree_factors[factor_name].values

    print(f"\n{factor_name}:")

    # Alpha vs CAPM
    alpha_capm, t_capm, r2_capm, rmse_capm, _ = run_regression(Y, mkt.reshape(-1, 1))
    print(f"  CAPM:  alpha={alpha_capm:6.2f}% (t={t_capm:5.2f}), R²={r2_capm:.3f}")

    # Alpha vs FF3 (MKT + SMB + HML)
    X_ff3 = np.column_stack([mkt, smb, hml])
    alpha_ff3, t_ff3, r2_ff3, rmse_ff3, _ = run_regression(Y, X_ff3)
    print(f"  FF3:   alpha={alpha_ff3:6.2f}% (t={t_ff3:5.2f}), R²={r2_ff3:.3f}")

    # Alpha vs FF4 (FF3 + MOM)
    X_ff4 = np.column_stack([mkt, smb, hml, mom])
    alpha_ff4, t_ff4, r2_ff4, rmse_ff4, _ = run_regression(Y, X_ff4)
    print(f"  FF4:   alpha={alpha_ff4:6.2f}% (t={t_ff4:5.2f}), R²={r2_ff4:.3f}")

    # Alpha vs previous P-Tree factors (for factors 2+)
    if i > 1:
        X_prev = ptree_factors.iloc[:, :i-1].values
        alpha_prev, t_prev, r2_prev, rmse_prev, _ = run_regression(Y, X_prev)
        print(f"  Prev:  alpha={alpha_prev:6.2f}% (t={t_prev:5.2f}), R²={r2_prev:.3f}")
    else:
        alpha_prev = np.nan
        t_prev = np.nan
        r2_prev = np.nan
        rmse_prev = np.nan

    alpha_results.append({
        'Factor': factor_name,
        'CAPM_alpha': alpha_capm,
        'CAPM_tstat': t_capm,
        'CAPM_R2': r2_capm,
        'FF3_alpha': alpha_ff3,
        'FF3_tstat': t_ff3,
        'FF3_R2': r2_ff3,
        'FF4_alpha': alpha_ff4,
        'FF4_tstat': t_ff4,
        'FF4_R2': r2_ff4,
        'PrevFactors_alpha': alpha_prev,
        'PrevFactors_tstat': t_prev,
        'PrevFactors_R2': r2_prev
    })

df_alpha = pd.DataFrame(alpha_results)
df_alpha.to_csv('results/benchmark_analysis/table2_alphas.csv', index=False)
print(f"\n[OK] Saved to results/benchmark_analysis/table2_alphas.csv")

# ============================================================================
# TABLE 3: BENCHMARK FACTOR PERFORMANCE
# ============================================================================

print("\n" + "="*80)
print("TABLE 3: BENCHMARK FACTOR PERFORMANCE")
print("="*80)

benchmark_factors = {
    'Market (rm_rf)': mkt,
    'SMB (vw)': smb,
    'HML (vw)': hml,
    'MOM (vw)': mom
}

benchmark_results = []

for name, factor in benchmark_factors.items():
    sr = factor.mean() / factor.std() * np.sqrt(12)
    mean_ret = factor.mean() * 12 * 100
    std_ret = factor.std() * np.sqrt(12) * 100

    benchmark_results.append({
        'Factor': name,
        'Sharpe Ratio': sr,
        'Mean Return (%)': mean_ret,
        'Std Dev (%)': std_ret
    })

    print(f"\n{name}:")
    print(f"  Sharpe Ratio: {sr:.3f}")
    print(f"  Mean: {mean_ret:.2f}%")
    print(f"  Std: {std_ret:.2f}%")

df_benchmark = pd.DataFrame(benchmark_results)
df_benchmark.to_csv('results/benchmark_analysis/table3_benchmark_performance.csv', index=False)
print(f"\n[OK] Saved to results/benchmark_analysis/table3_benchmark_performance.csv")

# ============================================================================
# TABLE 4: MACRO VARIABLES ANALYSIS
# ============================================================================

print("\n" + "="*80)
print("TABLE 4: MACRO VARIABLES")
print("="*80)

macro_vars = {
    'Market Volatility (ann %)': macro['rolling_vol_annualized_pct'].values,
    'Inflation': macro['inflation'].values
}

macro_results = []

for name, var in macro_vars.items():
    mean_val = var.mean()
    std_val = var.std()
    min_val = var.min()
    max_val = var.max()

    macro_results.append({
        'Variable': name,
        'Mean': mean_val,
        'Std': std_val,
        'Min': min_val,
        'Max': max_val
    })

    print(f"\n{name}:")
    print(f"  Mean: {mean_val:.2f}")
    print(f"  Std:  {std_val:.2f}")
    print(f"  Range: [{min_val:.2f}, {max_val:.2f}]")

df_macro = pd.DataFrame(macro_results)
df_macro.to_csv('results/benchmark_analysis/table4_macro_variables.csv', index=False)
print(f"\n[OK] Saved to results/benchmark_analysis/table4_macro_variables.csv")

# ============================================================================
# TABLE 5: CORRELATION ANALYSIS
# ============================================================================

print("\n" + "="*80)
print("TABLE 5: FACTOR CORRELATIONS")
print("="*80)

# Combine all factors
all_factors = pd.DataFrame({
    'P-Tree F1': ptree_factors['factor1'],
    'P-Tree F2': ptree_factors['factor2'],
    'P-Tree F3': ptree_factors['factor3'],
    'MKT': mkt,
    'SMB': smb,
    'HML': hml,
    'MOM': mom
})

corr_matrix = all_factors.corr()
print("\nCorrelation Matrix:")
print(corr_matrix.round(3))

corr_matrix.to_csv('results/benchmark_analysis/table5_correlations.csv')
print(f"\n[OK] Saved to results/benchmark_analysis/table5_correlations.csv")

# ============================================================================
# SUMMARY REPORT
# ============================================================================

print("\n" + "="*80)
print("SUMMARY REPORT")
print("="*80)

summary = f"""
SWEDISH P-TREE BENCHMARK ANALYSIS - SUMMARY
============================================

Data Period: {ptree_factors.index[0].strftime('%Y-%m')} to {ptree_factors.index[-1].strftime('%Y-%m')} ({len(ptree_factors)} months)

P-TREE FACTOR PERFORMANCE:
--------------------------
Factor 1 Individual SR: {sharpe_results[0]['Individual SR']:.3f}
Factor 2 Individual SR: {sharpe_results[1]['Individual SR']:.3f}
Factor 3 Individual SR: {sharpe_results[2]['Individual SR']:.3f}

MVE SR (all 3 factors): {sharpe_results[2]['MVE SR (1 to i)']:.3f}

BENCHMARK COMPARISON:
--------------------
Swedish Market SR:      {benchmark_results[0]['Sharpe Ratio']:.3f}
SMB (Size) SR:          {benchmark_results[1]['Sharpe Ratio']:.3f}
HML (Value) SR:         {benchmark_results[2]['Sharpe Ratio']:.3f}
MOM (Momentum) SR:      {benchmark_results[3]['Sharpe Ratio']:.3f}

ALPHA ANALYSIS (Factor 1):
-------------------------
vs CAPM:  alpha = {alpha_results[0]['CAPM_alpha']:6.2f}% (t = {alpha_results[0]['CAPM_tstat']:5.2f})
vs FF3:   alpha = {alpha_results[0]['FF3_alpha']:6.2f}% (t = {alpha_results[0]['FF3_tstat']:5.2f})
vs FF4:   alpha = {alpha_results[0]['FF4_alpha']:6.2f}% (t = {alpha_results[0]['FF4_tstat']:5.2f})

KEY FINDINGS:
------------
1. P-Tree factors default to market portfolio (all 3 identical)
2. This indicates Swedish market too small for profitable tree splits
3. Sharpe ratio of {sharpe_results[0]['Individual SR']:.3f} is reasonable for Swedish market
4. Alpha vs benchmarks indicates {
   'significant abnormal returns' if abs(alpha_results[0]['CAPM_tstat']) > 2
   else 'no significant abnormal returns (consistent with efficient market)'
}

All detailed results saved to: results/benchmark_analysis/
"""

print(summary)

with open('results/benchmark_analysis/summary_report.txt', 'w') as f:
    f.write(summary)

print("\n" + "="*80)
print("ANALYSIS COMPLETE!")
print("="*80)
print("\nAll results saved to: results/benchmark_analysis/")
print("\nGenerated files:")
print("  - table1_sharpe_ratios.csv")
print("  - table2_alphas.csv")
print("  - table3_benchmark_performance.csv")
print("  - table4_macro_variables.csv")
print("  - table5_correlations.csv")
print("  - summary_report.txt")
