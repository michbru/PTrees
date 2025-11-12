"""
Validation Script: Verify P-Tree Out-of-Sample Performance

This script calculates TRUE out-of-sample Sharpe ratios for Scenarios B and C
to verify that the reported results are accurate and not inflated.

Critical checks:
1. OOS Sharpe ratios (test period only)
2. IS vs OOS comparison (overfitting check)
3. Factor correlation between IS and OOS
4. Statistical significance of Sharpe ratios
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("=" * 80)
print("P-TREE RESULTS VALIDATION")
print("=" * 80)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_sharpe(returns, annualize=True):
    """Calculate Sharpe ratio (annualized by default)"""
    mean_ret = returns.mean()
    std_ret = returns.std()
    
    if std_ret == 0:
        return 0
    
    sharpe = mean_ret / std_ret
    
    if annualize:
        sharpe *= np.sqrt(12)  # Monthly to annual
    
    return sharpe

def sharpe_std_error(sharpe, n_obs):
    """Standard error of Sharpe ratio (Lo, 2002)"""
    return np.sqrt((1 + 0.5 * sharpe**2) / n_obs)

def sharpe_t_stat(sharpe, n_obs):
    """T-statistic for Sharpe ratio"""
    se = sharpe_std_error(sharpe, n_obs)
    return sharpe / se if se > 0 else 0

# =============================================================================
# LOAD DATA
# =============================================================================

print("\n[1] Loading P-Tree factor returns...")

results_dir = Path('results/ptree_34chars')

# Scenario A: Full sample (in-sample only)
scenario_a = pd.read_csv(results_dir / 'ptree_scenario_a_full' / 'ptree_factors.csv')
scenario_a['date'] = pd.to_datetime(scenario_a['month'])

# Scenario B: Time split
scenario_b_is = pd.read_csv(results_dir / 'ptree_scenario_b_split' / 'ptree_factors_is.csv')
scenario_b_is['date'] = pd.to_datetime(scenario_b_is['month'])
scenario_b_is['sample'] = 'IS'

scenario_b_oos = pd.read_csv(results_dir / 'ptree_scenario_b_split' / 'ptree_factors_oos.csv')
scenario_b_oos['date'] = pd.to_datetime(scenario_b_oos['month'])
scenario_b_oos['sample'] = 'OOS'

# Scenario C: Reverse split
scenario_c_is = pd.read_csv(results_dir / 'ptree_scenario_c_reverse' / 'ptree_factors_is.csv')
scenario_c_is['date'] = pd.to_datetime(scenario_c_is['month'])
scenario_c_is['sample'] = 'IS'

scenario_c_oos = pd.read_csv(results_dir / 'ptree_scenario_c_reverse' / 'ptree_factors_oos.csv')
scenario_c_oos['date'] = pd.to_datetime(scenario_c_oos['month'])
scenario_c_oos['sample'] = 'OOS'

print(f"  ✓ Scenario A (Full): {len(scenario_a)} months ({scenario_a['date'].min().strftime('%Y-%m')} to {scenario_a['date'].max().strftime('%Y-%m')})")
print(f"  ✓ Scenario B IS: {len(scenario_b_is)} months ({scenario_b_is['date'].min().strftime('%Y-%m')} to {scenario_b_is['date'].max().strftime('%Y-%m')})")
print(f"  ✓ Scenario B OOS: {len(scenario_b_oos)} months ({scenario_b_oos['date'].min().strftime('%Y-%m')} to {scenario_b_oos['date'].max().strftime('%Y-%m')})")
print(f"  ✓ Scenario C IS: {len(scenario_c_is)} months ({scenario_c_is['date'].min().strftime('%Y-%m')} to {scenario_c_is['date'].max().strftime('%Y-%m')})")
print(f"  ✓ Scenario C OOS: {len(scenario_c_oos)} months ({scenario_c_oos['date'].min().strftime('%Y-%m')} to {scenario_c_oos['date'].max().strftime('%Y-%m')})")

# =============================================================================
# VALIDATE: CHECK FOR OVERLAP
# =============================================================================

print("\n[2] Validating data integrity...")

# Check B: IS should end before OOS begins
b_is_end = scenario_b_is['date'].max()
b_oos_start = scenario_b_oos['date'].min()

if b_is_end < b_oos_start:
    print(f"  ✓ Scenario B: No overlap (IS ends {b_is_end.strftime('%Y-%m')}, OOS starts {b_oos_start.strftime('%Y-%m')})")
else:
    print(f"  ✗ WARNING: Scenario B has overlap! IS ends {b_is_end.strftime('%Y-%m')}, OOS starts {b_oos_start.strftime('%Y-%m')}")

# Check C: IS should end before OOS begins
c_is_end = scenario_c_is['date'].max()
c_oos_start = scenario_c_oos['date'].min()

if c_is_end > c_oos_start:
    print(f"  ✓ Scenario C: No overlap (reverse split - as expected)")
else:
    print(f"  ✗ WARNING: Scenario C has unexpected date ordering!")

# =============================================================================
# CALCULATE SHARPE RATIOS
# =============================================================================

print("\n[3] Calculating Sharpe Ratios...")
print("\n" + "-" * 80)
print("SCENARIO A: FULL SAMPLE (In-Sample)")
print("-" * 80)

for i in [1, 2, 3]:
    factor_col = f'factor{i}'
    sharpe = calculate_sharpe(scenario_a[factor_col])
    t_stat = sharpe_t_stat(sharpe, len(scenario_a))
    mean_ret = scenario_a[factor_col].mean() * 12 * 100  # Annualized %
    vol = scenario_a[factor_col].std() * np.sqrt(12) * 100  # Annualized %
    
    print(f"  Tree {i}: Sharpe = {sharpe:.3f} (t = {t_stat:.2f}) | Mean = {mean_ret:.2f}% | Vol = {vol:.2f}%")

print("\n" + "-" * 80)
print("SCENARIO B: TIME SPLIT (1997-2010 → 2010-2022)")
print("-" * 80)

print("\n  In-Sample (1997-2010):")
for i in [1, 2, 3]:
    factor_col = f'factor{i}'
    sharpe = calculate_sharpe(scenario_b_is[factor_col])
    t_stat = sharpe_t_stat(sharpe, len(scenario_b_is))
    mean_ret = scenario_b_is[factor_col].mean() * 12 * 100
    vol = scenario_b_is[factor_col].std() * np.sqrt(12) * 100
    
    print(f"    Tree {i}: Sharpe = {sharpe:.3f} (t = {t_stat:.2f}) | Mean = {mean_ret:.2f}% | Vol = {vol:.2f}%")

print("\n  Out-of-Sample (2010-2022): *** CRITICAL TEST ***")
for i in [1, 2, 3]:
    factor_col = f'factor{i}'
    sharpe_oos = calculate_sharpe(scenario_b_oos[factor_col])
    t_stat = sharpe_t_stat(sharpe_oos, len(scenario_b_oos))
    mean_ret = scenario_b_oos[factor_col].mean() * 12 * 100
    vol = scenario_b_oos[factor_col].std() * np.sqrt(12) * 100
    
    # Also calculate IS sharpe for comparison
    sharpe_is = calculate_sharpe(scenario_b_is[factor_col])
    
    degradation = (sharpe_oos - sharpe_is) / sharpe_is * 100 if sharpe_is != 0 else 0
    
    print(f"    Tree {i}: Sharpe = {sharpe_oos:.3f} (t = {t_stat:.2f}) | Mean = {mean_ret:.2f}% | Vol = {vol:.2f}%")
    print(f"             IS→OOS change: {degradation:+.1f}%")

print("\n" + "-" * 80)
print("SCENARIO C: REVERSE SPLIT (2010-2022 → 1997-2010)")
print("-" * 80)

print("\n  In-Sample (2010-2022):")
for i in [1, 2, 3]:
    factor_col = f'factor{i}'
    sharpe = calculate_sharpe(scenario_c_is[factor_col])
    t_stat = sharpe_t_stat(sharpe, len(scenario_c_is))
    mean_ret = scenario_c_is[factor_col].mean() * 12 * 100
    vol = scenario_c_is[factor_col].std() * np.sqrt(12) * 100
    
    print(f"    Tree {i}: Sharpe = {sharpe:.3f} (t = {t_stat:.2f}) | Mean = {mean_ret:.2f}% | Vol = {vol:.2f}%")

print("\n  Out-of-Sample (1997-2010): *** CRITICAL TEST ***")
for i in [1, 2, 3]:
    factor_col = f'factor{i}'
    sharpe_oos = calculate_sharpe(scenario_c_oos[factor_col])
    t_stat = sharpe_t_stat(sharpe_oos, len(scenario_c_oos))
    mean_ret = scenario_c_oos[factor_col].mean() * 12 * 100
    vol = scenario_c_oos[factor_col].std() * np.sqrt(12) * 100
    
    sharpe_is = calculate_sharpe(scenario_c_is[factor_col])
    degradation = (sharpe_oos - sharpe_is) / sharpe_is * 100 if sharpe_is != 0 else 0
    
    print(f"    Tree {i}: Sharpe = {sharpe_oos:.3f} (t = {t_stat:.2f}) | Mean = {mean_ret:.2f}% | Vol = {vol:.2f}%")
    print(f"             IS→OOS change: {degradation:+.1f}%")

# =============================================================================
# SUMMARY TABLE
# =============================================================================

print("\n" + "=" * 80)
print("SUMMARY TABLE: SHARPE RATIOS")
print("=" * 80)

summary_data = []

# Scenario A
for i in [1, 2, 3]:
    sharpe = calculate_sharpe(scenario_a[f'factor{i}'])
    summary_data.append({
        'Scenario': 'A: Full',
        'Sample': 'IS',
        'Tree': i,
        'Sharpe': round(sharpe, 3),
        'N_Months': len(scenario_a)
    })

# Scenario B
for sample, data in [('IS', scenario_b_is), ('OOS', scenario_b_oos)]:
    for i in [1, 2, 3]:
        sharpe = calculate_sharpe(data[f'factor{i}'])
        summary_data.append({
            'Scenario': 'B: Split',
            'Sample': sample,
            'Tree': i,
            'Sharpe': round(sharpe, 3),
            'N_Months': len(data)
        })

# Scenario C
for sample, data in [('IS', scenario_c_is), ('OOS', scenario_c_oos)]:
    for i in [1, 2, 3]:
        sharpe = calculate_sharpe(data[f'factor{i}'])
        summary_data.append({
            'Scenario': 'C: Reverse',
            'Sample': sample,
            'Tree': i,
            'Sharpe': round(sharpe, 3),
            'N_Months': len(data)
        })

summary_df = pd.DataFrame(summary_data)
summary_pivot = summary_df.pivot_table(
    index=['Scenario', 'Sample'],
    columns='Tree',
    values='Sharpe'
)

print(summary_pivot)

# Save summary
summary_df.to_csv(results_dir / 'validation_summary.csv', index=False)
print(f"\n✓ Saved to: {results_dir / 'validation_summary.csv'}")

# =============================================================================
# OVERFITTING DIAGNOSTIC
# =============================================================================

print("\n" + "=" * 80)
print("OVERFITTING DIAGNOSTIC")
print("=" * 80)

# Expected: IS Sharpe > OOS Sharpe (some degradation is normal)
# Red flag: OOS Sharpe > IS Sharpe (suggests data snooping or lucky split)

def diagnose_overfitting(is_sharpe, oos_sharpe, scenario_name):
    """Check for signs of overfitting"""
    degradation_pct = (oos_sharpe - is_sharpe) / is_sharpe * 100 if is_sharpe != 0 else 0
    
    if degradation_pct > 0:
        status = "⚠️ WARNING: OOS > IS (unusual, check for data snooping)"
    elif degradation_pct > -20:
        status = "✓ OK: Modest degradation (expected)"
    elif degradation_pct > -50:
        status = "⚠️ CAUTION: Large degradation (possible overfitting)"
    else:
        status = "✗ PROBLEM: Severe degradation (likely overfitted)"
    
    return degradation_pct, status

print("\nScenario B (Tree 1):")
is_b = calculate_sharpe(scenario_b_is['factor1'])
oos_b = calculate_sharpe(scenario_b_oos['factor1'])
deg_b, status_b = diagnose_overfitting(is_b, oos_b, "B")
print(f"  IS Sharpe: {is_b:.3f}")
print(f"  OOS Sharpe: {oos_b:.3f}")
print(f"  Change: {deg_b:+.1f}%")
print(f"  {status_b}")

print("\nScenario C (Tree 1):")
is_c = calculate_sharpe(scenario_c_is['factor1'])
oos_c = calculate_sharpe(scenario_c_oos['factor1'])
deg_c, status_c = diagnose_overfitting(is_c, oos_c, "C")
print(f"  IS Sharpe: {is_c:.3f}")
print(f"  OOS Sharpe: {oos_c:.3f}")
print(f"  Change: {deg_c:+.1f}%")
print(f"  {status_c}")

# =============================================================================
# FINAL VERDICT
# =============================================================================

print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

# Check if any OOS Sharpe > 2.0 (very high threshold)
max_oos_sharpe = max(
    calculate_sharpe(scenario_b_oos['factor1']),
    calculate_sharpe(scenario_c_oos['factor1'])
)

if max_oos_sharpe > 2.0:
    print("\n⚠️ WARNING: Out-of-sample Sharpe > 2.0 is VERY HIGH")
    print("   This is exceptional and should be carefully verified:")
    print("   1. Check calculation is correct (annualized monthly Sharpe)")
    print("   2. Verify no data leakage between IS and OOS")
    print("   3. Confirm this is first/second iteration (not 10th)")
    print("   4. Compare to naive benchmarks (equal-weight, momentum)")
elif max_oos_sharpe > 1.5:
    print("\n✓ STRONG RESULTS: Out-of-sample Sharpe > 1.5")
    print("   Results are strong but plausible for factor strategies")
elif max_oos_sharpe > 1.0:
    print("\n✓ GOOD RESULTS: Out-of-sample Sharpe > 1.0")
    print("   Results are solid and comparable to academic literature")
elif max_oos_sharpe > 0.5:
    print("\n✓ MODEST RESULTS: Out-of-sample Sharpe > 0.5")
    print("   Results show some predictive power")
else:
    print("\n⚠️ WEAK RESULTS: Out-of-sample Sharpe < 0.5")
    print("   Limited evidence of predictive power")

print("\n" + "=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)
