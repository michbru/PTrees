"""
Subperiod Analysis - Robustness Check

Checks if P-Tree performance is consistent across different time periods
or driven by a few exceptional years.

Breaks the full period into subperiods and analyzes each separately.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

print("="*80)
print("SUBPERIOD ANALYSIS - ROBUSTNESS CHECK")
print("="*80)

def calculate_sharpe(returns):
    if len(returns) == 0 or returns.std() == 0:
        return 0
    return returns.mean() / returns.std() * np.sqrt(12)

def run_regression(Y, X, add_constant=True, hac_lags=3):
    """Run time-series regression with HAC standard errors"""
    if add_constant:
        X = sm.add_constant(X)
    try:
        model = sm.OLS(Y, X)
        results = model.fit(cov_type='HAC', cov_kwds={'maxlags': hac_lags})
        alpha = results.params[0] if add_constant else np.nan
        t_stat = results.tvalues[0] if add_constant else np.nan
        alpha_ann = alpha * 12 * 100
        return alpha_ann, t_stat
    except:
        return np.nan, np.nan

# Load macro data
print("\nLoading macro data...")
macro = pd.read_csv('data/macro_variables_with_dates.csv')
macro['date'] = pd.to_datetime(macro['date'])
macro = macro.set_index('date')

# Define subperiods
# Break 1997-2020 into meaningful economic periods
SUBPERIODS = [
    ('1997-2000', 'Dot-com Boom', pd.Timestamp('1997-01-01'), pd.Timestamp('2000-12-31')),
    ('2001-2003', 'Dot-com Bust', pd.Timestamp('2001-01-01'), pd.Timestamp('2003-12-31')),
    ('2004-2007', 'Pre-Crisis Expansion', pd.Timestamp('2004-01-01'), pd.Timestamp('2007-12-31')),
    ('2008-2009', 'Financial Crisis', pd.Timestamp('2008-01-01'), pd.Timestamp('2009-12-31')),
    ('2010-2014', 'Post-Crisis Recovery', pd.Timestamp('2010-01-01'), pd.Timestamp('2014-12-31')),
    ('2015-2020', 'Late Expansion', pd.Timestamp('2015-01-01'), pd.Timestamp('2020-12-31'))
]

print("\nSubperiods:")
for name, label, start, end in SUBPERIODS:
    print(f"  {name:10} | {label:25} | {start.strftime('%Y-%m')} to {end.strftime('%Y-%m')}")

# Analyze each scenario
scenarios_to_analyze = {
    'A: Full Sample': 'results/ptree_scenario_a_full',
    'B: Time Split (OOS)': 'results/ptree_scenario_b_split',
    'C: Reverse Split (OOS)': 'results/ptree_scenario_c_reverse'
}

all_subperiod_results = []

for scenario_name, folder in scenarios_to_analyze.items():
    print("\n" + "="*80)
    print(f"{scenario_name}")
    print("="*80)

    # Load P-Tree factors
    factor_files = [
        Path(folder) / 'ptree_factors_oos.csv',
        Path(folder) / 'ptree_factors.csv',
        Path(folder) / 'ptree_factors_is.csv'
    ]

    factor_file = None
    for f in factor_files:
        if f.exists():
            factor_file = f
            break

    if factor_file is None:
        print(f"  [SKIP] No factor file found")
        continue

    # Load factors
    factors = pd.read_csv(factor_file)
    factors['month'] = pd.to_datetime(factors['month'])
    factors = factors.set_index('month')

    is_oos = 'oos' in factor_file.name
    print(f"\nUsing: {factor_file.name} ({'OOS' if is_oos else 'IS'})")
    print(f"Full period: {factors.index[0].strftime('%Y-%m')} to {factors.index[-1].strftime('%Y-%m')}")

    # Analyze each subperiod
    print("\nSubperiod Performance:")
    print(f"  {'Period':10} {'Label':25} {'N':>4} {'Mean Ret':>10} {'Sharpe':>8} {'Alpha':>10} {'t-stat':>8}")

    for period_name, period_label, start_date, end_date in SUBPERIODS:
        # Filter to subperiod
        mask = (factors.index >= start_date) & (factors.index <= end_date)
        period_factors = factors[mask].copy()

        if len(period_factors) == 0:
            print(f"  {period_name:10} {period_label:25} {'N/A':>4} {'---':>10} {'---':>8} {'---':>10} {'---':>8}")
            continue

        # Get returns
        returns = period_factors['factor1'].values
        n_months = len(returns)

        # Calculate metrics
        mean_return = returns.mean() * 12 * 100  # Annualized %
        sharpe = calculate_sharpe(pd.Series(returns))

        # CAPM alpha
        period_macro = macro[(macro.index >= start_date) & (macro.index <= end_date)]
        common_dates = period_factors.index.intersection(period_macro.index)

        if len(common_dates) > 0:
            aligned_factors = period_factors.loc[common_dates]
            aligned_macro = period_macro.loc[common_dates]
            mkt = aligned_macro['rm_rf'].values
            alpha, t_stat = run_regression(aligned_factors['factor1'].values, mkt.reshape(-1, 1))
        else:
            alpha, t_stat = np.nan, np.nan

        print(f"  {period_name:10} {period_label:25} {n_months:4d} {mean_return:9.2f}%  {sharpe:7.2f}  {alpha:9.2f}%  {t_stat:7.2f}")

        all_subperiod_results.append({
            'Scenario': scenario_name,
            'Data_Type': 'OOS' if is_oos else 'IS',
            'Period': period_name,
            'Period_Label': period_label,
            'Start_Date': start_date.strftime('%Y-%m'),
            'End_Date': end_date.strftime('%Y-%m'),
            'N_Months': n_months,
            'Mean_Return_pct': mean_return,
            'Sharpe_Ratio': sharpe,
            'CAPM_Alpha_pct': alpha,
            'CAPM_tstat': t_stat
        })

# Save results
df_results = pd.DataFrame(all_subperiod_results)
output_dir = Path('results/robustness_checks')
output_dir.mkdir(exist_ok=True, parents=True)
df_results.to_csv(output_dir / 'subperiod_analysis.csv', index=False)

print("\n" + "="*80)
print("CROSS-PERIOD CONSISTENCY CHECK")
print("="*80)

for scenario_name in scenarios_to_analyze.keys():
    scenario_data = df_results[df_results['Scenario'] == scenario_name]
    if len(scenario_data) == 0:
        continue

    print(f"\n{scenario_name}:")

    sharpe_values = scenario_data['Sharpe_Ratio'].dropna()
    alpha_values = scenario_data['CAPM_Alpha_pct'].dropna()

    if len(sharpe_values) > 0:
        print(f"  Sharpe Ratio:")
        print(f"    Mean:   {sharpe_values.mean():7.3f}")
        print(f"    Median: {sharpe_values.median():7.3f}")
        print(f"    Std:    {sharpe_values.std():7.3f}")
        print(f"    Min:    {sharpe_values.min():7.3f} ({scenario_data.loc[sharpe_values.idxmin(), 'Period']})")
        print(f"    Max:    {sharpe_values.max():7.3f} ({scenario_data.loc[sharpe_values.idxmax(), 'Period']})")
        print(f"    Positive periods: {(sharpe_values > 0).sum()}/{len(sharpe_values)}")

    if len(alpha_values) > 0:
        print(f"  CAPM Alpha:")
        print(f"    Mean:   {alpha_values.mean():7.2f}%")
        print(f"    Median: {alpha_values.median():7.2f}%")
        print(f"    Std:    {alpha_values.std():7.2f}%")
        print(f"    Min:    {alpha_values.min():7.2f}% ({scenario_data.loc[alpha_values.idxmin(), 'Period']})")
        print(f"    Max:    {alpha_values.max():7.2f}% ({scenario_data.loc[alpha_values.idxmax(), 'Period']})")
        print(f"    Positive periods: {(alpha_values > 0).sum()}/{len(alpha_values)}")

print("\n" + "="*80)
print("KEY FINDINGS")
print("="*80)

print("\n1. CONSISTENCY:")
print("   - Check if performance is consistent across periods")
print("   - High std dev in Sharpe/Alpha suggests period-specific results")
print("   - Look for negative performance in some periods")

print("\n2. REGIME DEPENDENCE:")
print("   - Compare crisis (2008-2009) vs expansion periods")
print("   - Early period (1997-2003) vs late period (2015-2020)")

print("\n3. OVERFITTING RED FLAGS:")
print("   - If performance is strong in 1-2 periods but weak in others:")
print("     → Suggests model may be overfit to specific regimes")
print("   - If crisis period has best performance:")
print("     → Unusual and may indicate data issues")

print("\n4. SAMPLE SIZE:")
print("   - Short subperiods have fewer observations")
print("   - Statistical significance is lower")
print("   - Use as qualitative robustness check")

print(f"\nDetailed results saved to: {output_dir / 'subperiod_analysis.csv'}")

print("\n" + "="*80)
print("SUBPERIOD ANALYSIS COMPLETE")
print("="*80)
