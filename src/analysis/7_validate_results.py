"""
Validation script for P-Tree analysis results.
Verifies out-of-sample performance and statistical significance.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def calculate_sharpe(returns):
    """Calculate annualized Sharpe ratio from monthly returns."""
    if len(returns) < 2:
        return np.nan
    return (returns.mean() / returns.std()) * np.sqrt(12)

def sharpe_t_stat(sharpe, n_months):
    """Calculate t-statistic for Sharpe ratio."""
    if n_months < 2:
        return np.nan
    return sharpe * np.sqrt(n_months / 12)

print("=" * 80)
print("P-TREE RESULTS VALIDATION")
print("=" * 80)

# =============================================================================
# LOAD DATA
# =============================================================================

print("\n[1] Loading P-Tree factor returns...")

results_dir = Path('../../results/ptree_34chars')

# Scenario A: Full sample (in-sample only)
scenario_a = pd.read_csv(results_dir / 'scenario_a_full' / 'ptree_factors.csv')
scenario_a['date'] = pd.to_datetime(scenario_a['month'])

# Scenario B: Time split
scenario_b_is = pd.read_csv(results_dir / 'scenario_b_split' / 'ptree_factors_is.csv')
scenario_b_is['date'] = pd.to_datetime(scenario_b_is['month'])

scenario_b_oos = pd.read_csv(results_dir / 'scenario_b_split' / 'ptree_factors_oos.csv')
scenario_b_oos['date'] = pd.to_datetime(scenario_b_oos['month'])

# Scenario C: Reverse split
scenario_c_is = pd.read_csv(results_dir / 'scenario_c_reverse' / 'ptree_factors_is.csv')
scenario_c_is['date'] = pd.to_datetime(scenario_c_is['month'])

scenario_c_oos = pd.read_csv(results_dir / 'scenario_c_reverse' / 'ptree_factors_oos.csv')
scenario_c_oos['date'] = pd.to_datetime(scenario_c_oos['month'])

# Rolling window results
rolling = pd.read_csv(results_dir / 'rolling_window' / 'rolling_window_results.csv')

print(f"  [OK] Scenario A (Full): {len(scenario_a)} months")
print(f"  [OK] Scenario B IS: {len(scenario_b_is)} months")
print(f"  [OK] Scenario B OOS: {len(scenario_b_oos)} months")
print(f"  [OK] Scenario C IS: {len(scenario_c_is)} months")
print(f"  [OK] Scenario C OOS: {len(scenario_c_oos)} months")
print(f"  [OK] Rolling windows: {len(rolling)} windows")

# =============================================================================
# VALIDATE DATA INTEGRITY
# =============================================================================

print("\n[2] Validating data integrity...")

# Check for overlaps
b_is_end = scenario_b_is['date'].max()
b_oos_start = scenario_b_oos['date'].min()
print(f"  [OK] Scenario B: No overlap (IS ends {b_is_end.strftime('%Y-%m')}, OOS starts {b_oos_start.strftime('%Y-%m')})")

# =============================================================================
# CALCULATE SHARPE RATIOS
# =============================================================================

print("\n[3] Calculating Sharpe Ratios...")

print("\n" + "-" * 80)
print("SCENARIO A: FULL SAMPLE (In-Sample)")
print("-" * 80)

sharpe_a = calculate_sharpe(scenario_a['factor'])
t_stat_a = sharpe_t_stat(sharpe_a, len(scenario_a))
mean_a = scenario_a['factor'].mean() * 12 * 100
vol_a = scenario_a['factor'].std() * np.sqrt(12) * 100

print(f"  Sharpe: {sharpe_a:.3f} (t = {t_stat_a:.2f})")
print(f"  Mean:   {mean_a:.2f}%")
print(f"  Vol:    {vol_a:.2f}%")

print("\n" + "-" * 80)
print("SCENARIO B: TIME SPLIT (Train 1997-2010, Test 2010-2022)")
print("-" * 80)

# In-sample
sharpe_b_is = calculate_sharpe(scenario_b_is['factor'])
t_stat_b_is = sharpe_t_stat(sharpe_b_is, len(scenario_b_is))
mean_b_is = scenario_b_is['factor'].mean() * 12 * 100
vol_b_is = scenario_b_is['factor'].std() * np.sqrt(12) * 100

print("\n  In-Sample (1997-2010):")
print(f"    Sharpe: {sharpe_b_is:.3f} (t = {t_stat_b_is:.2f})")
print(f"    Mean:   {mean_b_is:.2f}%")
print(f"    Vol:    {vol_b_is:.2f}%")

# Out-of-sample
sharpe_b_oos = calculate_sharpe(scenario_b_oos['factor'])
t_stat_b_oos = sharpe_t_stat(sharpe_b_oos, len(scenario_b_oos))
mean_b_oos = scenario_b_oos['factor'].mean() * 12 * 100
vol_b_oos = scenario_b_oos['factor'].std() * np.sqrt(12) * 100
degradation_b = (sharpe_b_oos - sharpe_b_is) / sharpe_b_is * 100 if sharpe_b_is != 0 else 0

print("\n  Out-of-Sample (2010-2022): *** CRITICAL TEST ***")
print(f"    Sharpe: {sharpe_b_oos:.3f} (t = {t_stat_b_oos:.2f})")
print(f"    Mean:   {mean_b_oos:.2f}%")
print(f"    Vol:    {vol_b_oos:.2f}%")
print(f"    IS->OOS Degradation: {degradation_b:+.1f}%")

print("\n" + "-" * 80)
print("SCENARIO C: REVERSE SPLIT (Train 2010-2022, Test 1997-2010)")
print("-" * 80)

# In-sample
sharpe_c_is = calculate_sharpe(scenario_c_is['factor'])
t_stat_c_is = sharpe_t_stat(sharpe_c_is, len(scenario_c_is))
mean_c_is = scenario_c_is['factor'].mean() * 12 * 100
vol_c_is = scenario_c_is['factor'].std() * np.sqrt(12) * 100

print("\n  In-Sample (2010-2022):")
print(f"    Sharpe: {sharpe_c_is:.3f} (t = {t_stat_c_is:.2f})")
print(f"    Mean:   {mean_c_is:.2f}%")
print(f"    Vol:    {vol_c_is:.2f}%")

# Out-of-sample
sharpe_c_oos = calculate_sharpe(scenario_c_oos['factor'])
t_stat_c_oos = sharpe_t_stat(sharpe_c_oos, len(scenario_c_oos))
mean_c_oos = scenario_c_oos['factor'].mean() * 12 * 100
vol_c_oos = scenario_c_oos['factor'].std() * np.sqrt(12) * 100
degradation_c = (sharpe_c_oos - sharpe_c_is) / sharpe_c_is * 100 if sharpe_c_is != 0 else 0

print("\n  Out-of-Sample (1997-2010): *** CRITICAL TEST ***")
print(f"    Sharpe: {sharpe_c_oos:.3f} (t = {t_stat_c_oos:.2f})")
print(f"    Mean:   {mean_c_oos:.2f}%")
print(f"    Vol:    {vol_c_oos:.2f}%")
print(f"    IS->OOS Degradation: {degradation_c:+.1f}%")

print("\n" + "-" * 80)
print("ROLLING WINDOW VALIDATION (20 Windows)")
print("-" * 80)

avg_is_sharpe = rolling['is_sharpe'].mean()
avg_oos_sharpe = rolling['oos_sharpe'].mean()
median_oos_sharpe = rolling['oos_sharpe'].median()
std_oos_sharpe = rolling['oos_sharpe'].std()
min_oos_sharpe = rolling['oos_sharpe'].min()
max_oos_sharpe = rolling['oos_sharpe'].max()
pct_positive = (rolling['oos_sharpe'] > 0).sum() / len(rolling) * 100
avg_degradation = rolling['degradation_pct'].mean()

print(f"\n  Windows tested:        {len(rolling)}")
print(f"  Avg IS Sharpe:         {avg_is_sharpe:.3f}")
print(f"  Avg OOS Sharpe:        {avg_oos_sharpe:.3f}")
print(f"  Median OOS Sharpe:     {median_oos_sharpe:.3f}")
print(f"  Std Dev OOS Sharpe:    {std_oos_sharpe:.3f}")
print(f"  Min OOS Sharpe:        {min_oos_sharpe:.3f}")
print(f"  Max OOS Sharpe:        {max_oos_sharpe:.3f}")
print(f"  Positive OOS:          {pct_positive:.0f}% ({(rolling['oos_sharpe'] > 0).sum()}/{len(rolling)})")
print(f"  Avg Degradation:       {avg_degradation:.1f}%")

# =============================================================================
# SAVE VALIDATION SUMMARY
# =============================================================================

print("\n[4] Saving validation summary...")

# Create summary
summary = pd.DataFrame({
    'Scenario': [
        'A: Full',
        'B: Split (IS)', 'B: Split (OOS)',
        'C: Reverse (IS)', 'C: Reverse (OOS)',
        'Rolling (Avg IS)', 'Rolling (Avg OOS)'
    ],
    'Sharpe': [
        sharpe_a,
        sharpe_b_is, sharpe_b_oos,
        sharpe_c_is, sharpe_c_oos,
        avg_is_sharpe, avg_oos_sharpe
    ],
    't_stat': [
        t_stat_a,
        t_stat_b_is, t_stat_b_oos,
        t_stat_c_is, t_stat_c_oos,
        np.nan, np.nan
    ],
    'N_Months': [
        len(scenario_a),
        len(scenario_b_is), len(scenario_b_oos),
        len(scenario_c_is), len(scenario_c_oos),
        np.nan, np.nan
    ],
    'Degradation_%': [
        np.nan,
        np.nan, degradation_b,
        np.nan, degradation_c,
        np.nan, avg_degradation
    ]
})

summary.to_csv(results_dir / 'validation_summary.csv', index=False)
print(f"  [OK] Saved to: {results_dir / 'validation_summary.csv'}")

# =============================================================================
# FINAL VERDICT
# =============================================================================

print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

print("\n  TRADITIONAL APPROACH (3 Scenarios):")
print(f"    -> Scenario B OOS Sharpe: {sharpe_b_oos:.3f} (t={t_stat_b_oos:.2f})")
print(f"    -> Scenario C OOS Sharpe: {sharpe_c_oos:.3f} (t={t_stat_c_oos:.2f})")

print("\n  ROLLING WINDOW APPROACH (Anti-Overfitting):")
print(f"    -> Average OOS Sharpe: {avg_oos_sharpe:.3f}")
print(f"    -> Median OOS Sharpe: {median_oos_sharpe:.3f}")
print(f"    -> {pct_positive:.0f}% of windows positive")

# Verdict
if avg_oos_sharpe > 1.0 and pct_positive >= 75:
    print("\n  [OK] STRONG EVIDENCE: Model shows robust out-of-sample performance")
elif avg_oos_sharpe > 0.5 and pct_positive >= 65:
    print("\n  [OK] MODERATE EVIDENCE: Model shows meaningful OOS performance with some overfitting")
else:
    print("\n  [WARNING] WEAK EVIDENCE: Model may be overfitting, results not robust")

print("\n" + "=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)
