"""
Comprehensive Benchmark Comparison

Compares P-Tree factor performance against simple benchmark strategies:
1. Equal-Weighted Portfolio (EW)
2. Value-Weighted Portfolio (VW)
3. Simple Momentum (6-2-1: skip most recent month, use 6-month returns)
4. Book-to-Market Long-Short

This validates that P-Tree adds value beyond naive strategies.
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("BENCHMARK COMPARISON ANALYSIS")
print("="*80)
print()

def calculate_performance(returns):
    """Calculate comprehensive performance statistics"""
    returns_monthly = np.array(returns)

    # Annualized statistics
    mean_annual = np.mean(returns_monthly) * 12 * 100
    vol_annual = np.std(returns_monthly) * np.sqrt(12) * 100
    sharpe = (np.mean(returns_monthly) / np.std(returns_monthly)) * np.sqrt(12)

    # t-statistic
    t_stat = (np.mean(returns_monthly) / (np.std(returns_monthly) / np.sqrt(len(returns_monthly)))) * np.sqrt(12)

    # Cumulative return
    cum_return = np.prod(1 + returns_monthly) - 1

    return {
        'Mean (%)': mean_annual,
        'Vol (%)': vol_annual,
        'Sharpe': sharpe,
        't-stat': t_stat,
        'Cum Return (%)': cum_return * 100
    }

###### Load Data #####

print("Loading data...\n")

# Load prepared data
data = pd.read_csv('../../results/ptree_34chars/ptree_ready_data_34chars.csv')
data['date'] = pd.to_datetime(data['date'])

print(f"Loaded {len(data):,} observations")
print(f"Period: {data['date'].min().strftime('%Y-%m')} to {data['date'].max().strftime('%Y-%m')}")
print(f"Stocks: {data['permno'].nunique()}")
print()

###### Create Benchmark Portfolios #####

print("Creating benchmark portfolios...\n")

# Sort data
data = data.sort_values(['date', 'permno'])

# 1. Equal-Weighted Portfolio
print("1. Equal-Weighted Portfolio")
ew_returns = data.groupby('date')['xret'].mean().reset_index()
ew_returns.columns = ['date', 'ew_return']
print(f"   Created EW returns for {len(ew_returns)} months\n")

# 2. Value-Weighted Portfolio (weighted by lagged market cap)
print("2. Value-Weighted Portfolio")
vw_returns = data.groupby('date').apply(
    lambda x: np.average(x['xret'], weights=x['lag_me'])
).reset_index()
vw_returns.columns = ['date', 'vw_return']
print(f"   Created VW returns for {len(vw_returns)} months\n")

# 3. Simple Momentum (6-2-1)
print("3. Simple Momentum Portfolio (6-2-1)")

# Calculate 6-month lagged momentum (skip most recent month)
data = data.sort_values(['permno', 'date'])
data['momentum_6_2'] = data.groupby('permno')['current_return'].apply(
    lambda x: x.shift(2).rolling(window=6, min_periods=3).mean()
)

# Create momentum portfolio: Long high momentum, short low momentum
momentum_returns = []
for date in sorted(data['date'].unique()):
    month_data = data[data['date'] == date].copy()

    # Skip if insufficient data
    if month_data['momentum_6_2'].notna().sum() < 10:
        continue

    # Rank by momentum
    month_data['mom_rank'] = month_data['momentum_6_2'].rank(pct=True)

    # Long top 30%, short bottom 30%
    long_mask = month_data['mom_rank'] >= 0.7
    short_mask = month_data['mom_rank'] <= 0.3

    if long_mask.sum() > 0 and short_mask.sum() > 0:
        long_return = np.average(
            month_data.loc[long_mask, 'xret'],
            weights=month_data.loc[long_mask, 'lag_me']
        )
        short_return = np.average(
            month_data.loc[short_mask, 'xret'],
            weights=month_data.loc[short_mask, 'lag_me']
        )
        mom_return = long_return - short_return
        momentum_returns.append({'date': date, 'mom_return': mom_return})

momentum_df = pd.DataFrame(momentum_returns)
print(f"   Created momentum returns for {len(momentum_df)} months\n")

# 4. Book-to-Market Long-Short
print("4. Book-to-Market Long-Short Portfolio")

bm_returns = []
for date in sorted(data['date'].unique()):
    month_data = data[data['date'] == date].copy()

    # Skip if insufficient data
    if 'book_to_market' not in month_data.columns or month_data['book_to_market'].notna().sum() < 10:
        continue

    # Rank by B/M
    month_data['bm_rank'] = month_data['book_to_market'].rank(pct=True)

    # Long top 30% (value), short bottom 30% (growth)
    long_mask = month_data['bm_rank'] >= 0.7
    short_mask = month_data['bm_rank'] <= 0.3

    if long_mask.sum() > 0 and short_mask.sum() > 0:
        long_return = np.average(
            month_data.loc[long_mask, 'xret'],
            weights=month_data.loc[long_mask, 'lag_me']
        )
        short_return = np.average(
            month_data.loc[short_mask, 'xret'],
            weights=month_data.loc[short_mask, 'lag_me']
        )
        bm_return = long_return - short_return
        bm_returns.append({'date': date, 'bm_return': bm_return})

bm_df = pd.DataFrame(bm_returns)
print(f"   Created B/M returns for {len(bm_df)} months\n")

###### Compare with P-Tree #####

print("="*80)
print("PERFORMANCE COMPARISON")
print("="*80)
print()

# Define scenarios to analyze
scenarios = [
    {
        'name': 'Scenario A: Full Sample (1997-2022)',
        'ptree_file': '../../results/ptree_34chars/scenario_a_full/ptree_factors.csv',
        'is_oos': 'Full Sample'
    },
    {
        'name': 'Scenario B: OOS (2010-2022)',
        'ptree_file': '../../results/ptree_34chars/scenario_b_split/ptree_factors_oos.csv',
        'is_oos': 'OOS'
    },
    {
        'name': 'Scenario C: OOS (1997-2010)',
        'ptree_file': '../../results/ptree_34chars/scenario_c_reverse/ptree_factors_oos.csv',
        'is_oos': 'OOS'
    }
]

all_results = []

for scenario in scenarios:
    print(f"\n{'-'*80}")
    print(scenario['name'])
    print(f"{'-'*80}\n")

    ptree_file = Path(scenario['ptree_file'])

    if not ptree_file.exists():
        print(f"WARNING: P-Tree file not found: {ptree_file}\n")
        continue

    # Load P-Tree factors
    ptree = pd.read_csv(ptree_file)
    ptree['month'] = pd.to_datetime(ptree['month'])

    # Merge with benchmarks
    combined = ptree.copy()
    combined = combined.merge(ew_returns, left_on='month', right_on='date', how='left')
    combined = combined.merge(vw_returns, left_on='month', right_on='date', how='left')
    combined = combined.merge(momentum_df, left_on='month', right_on='date', how='left')
    combined = combined.merge(bm_df, left_on='month', right_on='date', how='left')

    # Calculate performance for each strategy
    results = {}

    # P-Tree Tree 1
    if 'factor1' in combined.columns and combined['factor1'].notna().sum() > 0:
        results['P-Tree (Tree 1)'] = calculate_performance(combined['factor1'].dropna())

    # Benchmarks
    if 'ew_return' in combined.columns and combined['ew_return'].notna().sum() > 0:
        results['Equal-Weighted'] = calculate_performance(combined['ew_return'].dropna())

    if 'vw_return' in combined.columns and combined['vw_return'].notna().sum() > 0:
        results['Value-Weighted'] = calculate_performance(combined['vw_return'].dropna())

    if 'mom_return' in combined.columns and combined['mom_return'].notna().sum() > 0:
        results['Momentum (6-2-1)'] = calculate_performance(combined['mom_return'].dropna())

    if 'bm_return' in combined.columns and combined['bm_return'].notna().sum() > 0:
        results['B/M Long-Short'] = calculate_performance(combined['bm_return'].dropna())

    # Create results table
    results_df = pd.DataFrame(results).T
    results_df = results_df.round(2)
    print(results_df.to_string())

    # Save results
    output_dir = Path('../../results/ptree_34chars/benchmark_comparison')
    output_dir.mkdir(exist_ok=True, parents=True)

    scenario_suffix = scenario['name'].split(':')[0].replace(' ', '_').lower()
    results_df.to_csv(output_dir / f'benchmark_comparison_{scenario_suffix}.csv')

    # Store for summary
    results_df['Scenario'] = scenario['name']
    results_df['Type'] = scenario['is_oos']
    all_results.append(results_df.reset_index().rename(columns={'index': 'Strategy'}))

    # Highlight best strategy
    best_sharpe_idx = results_df['Sharpe'].idxmax()
    print(f"\n✅ Best Sharpe Ratio: {best_sharpe_idx} ({results_df.loc[best_sharpe_idx, 'Sharpe']:.2f})")

###### Overall Summary #####

if len(all_results) > 0:
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}\n")

    all_results_df = pd.concat(all_results, ignore_index=True)

    # Save comprehensive results
    output_dir = Path('../../results/ptree_34chars/benchmark_comparison')
    all_results_df.to_csv(output_dir / 'all_scenarios_benchmark_comparison.csv', index=False)

    # Calculate average performance by strategy across OOS scenarios
    oos_results = all_results_df[all_results_df['Type'] == 'OOS']

    if len(oos_results) > 0:
        avg_performance = oos_results.groupby('Strategy')[['Mean (%)', 'Vol (%)', 'Sharpe', 't-stat']].mean()
        avg_performance = avg_performance.round(2)

        print("Average OOS Performance Across Scenarios B & C:\n")
        print(avg_performance.to_string())

        print("\n✅ Interpretation:")
        print("If P-Tree Sharpe > all benchmarks: P-Tree adds unique value")
        print("If P-Tree Sharpe < simple strategies: Overfitting or data mining concerns")

    print(f"\nResults saved to: {output_dir}")

print(f"\n{'='*80}")
print("BENCHMARK COMPARISON COMPLETE")
print(f"{'='*80}\n")
