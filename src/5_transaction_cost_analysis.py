"""
Transaction Cost Analysis - Robustness Check

Adjusts P-Tree performance for realistic transaction costs:
- Bid-ask spreads: 30-50 bps for Swedish stocks
- Commissions: 10-20 bps
- Market impact: 10-30 bps for larger trades
- Total estimated: 50-100 bps per round-trip

Assumption: Monthly rebalancing
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("TRANSACTION COST ANALYSIS - ROBUSTNESS CHECK")
print("="*80)

# Transaction cost assumptions (basis points per trade)
SCENARIOS = {
    'Low': {
        'bid_ask_spread': 30,
        'commission': 10,
        'market_impact': 10,
        'total_bps': 50
    },
    'Medium': {
        'bid_ask_spread': 40,
        'commission': 15,
        'market_impact': 20,
        'total_bps': 75
    },
    'High': {
        'bid_ask_spread': 50,
        'commission': 20,
        'market_impact': 30,
        'total_bps': 100
    }
}

# Turnover assumptions
# P-Tree rebalances monthly based on tree structure
# Estimated turnover: 50-150% per month
TURNOVER_SCENARIOS = {
    'Low': 0.50,    # 50% monthly turnover
    'Medium': 1.00,  # 100% monthly turnover
    'High': 1.50    # 150% monthly turnover
}

print("\nTransaction Cost Assumptions:")
print("-" * 80)
for scenario, costs in SCENARIOS.items():
    print(f"{scenario:8} | Bid-Ask: {costs['bid_ask_spread']:2d} bps | "
          f"Commission: {costs['commission']:2d} bps | Impact: {costs['market_impact']:2d} bps | "
          f"Total: {costs['total_bps']:3d} bps")

print("\nTurnover Assumptions:")
print("-" * 80)
for scenario, turnover in TURNOVER_SCENARIOS.items():
    print(f"{scenario:8} | Monthly turnover: {turnover:5.1%}")

# Load P-Tree results
print("\n" + "="*80)
print("ANALYZING P-TREE SCENARIOS")
print("="*80)

scenarios_to_analyze = {
    'A: Full Sample': 'results/ptree_scenario_a_full',
    'B: Time Split (OOS)': 'results/ptree_scenario_b_split',
    'C: Reverse Split (OOS)': 'results/ptree_scenario_c_reverse'
}

all_results = []

for scenario_name, folder in scenarios_to_analyze.items():
    print(f"\n{scenario_name}")
    print("-" * 80)

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

    is_oos = 'oos' in factor_file.name
    print(f"  Using: {factor_file.name} ({'OOS' if is_oos else 'IS'})")
    print(f"  Period: {factors['month'].min().strftime('%Y-%m')} to {factors['month'].max().strftime('%Y-%m')}")
    print(f"  Months: {len(factors)}")

    # Calculate gross performance (before costs)
    factor1_returns = factors['factor1'].values
    gross_mean = factor1_returns.mean() * 12 * 100  # Annualized %
    gross_std = factor1_returns.std() * np.sqrt(12) * 100
    gross_sharpe = factor1_returns.mean() / factor1_returns.std() * np.sqrt(12)

    print(f"\n  Gross Performance (Before Costs):")
    print(f"    Mean Return: {gross_mean:6.2f}%")
    print(f"    Volatility:  {gross_std:6.2f}%")
    print(f"    Sharpe:      {gross_sharpe:6.3f}")

    # Calculate net performance for different scenarios
    print(f"\n  Net Performance (After Transaction Costs):")
    print(f"    {'':20} {'Mean Ret':>10} {'Vol':>8} {'Sharpe':>8} {'Cost Drag':>10}")

    for tc_scenario in ['Low', 'Medium', 'High']:
        for turn_scenario in ['Low', 'Medium', 'High']:
            tc_bps = SCENARIOS[tc_scenario]['total_bps']
            turnover = TURNOVER_SCENARIOS[turn_scenario]

            # Monthly cost = turnover * transaction_cost
            # (turnover is one-way, so we pay cost on that fraction of portfolio)
            monthly_cost_pct = (turnover * tc_bps / 10000)  # Convert bps to decimal
            annual_cost_pct = monthly_cost_pct * 12 * 100

            # Net return
            net_mean = gross_mean - annual_cost_pct
            net_sharpe = net_mean / gross_std

            scenario_label = f"{tc_scenario} TC / {turn_scenario} Turn"

            if turn_scenario == 'Medium':  # Show medium turnover scenarios
                print(f"    {scenario_label:20} {net_mean:9.2f}%  {gross_std:7.2f}%  {net_sharpe:7.3f}   {annual_cost_pct:9.2f}%")

            # Store result
            all_results.append({
                'Scenario': scenario_name,
                'Data_Type': 'OOS' if is_oos else 'IS',
                'TC_Level': tc_scenario,
                'Turnover_Level': turn_scenario,
                'TC_bps': tc_bps,
                'Turnover_pct': turnover * 100,
                'Gross_Return_pct': gross_mean,
                'Cost_Drag_pct': annual_cost_pct,
                'Net_Return_pct': net_mean,
                'Volatility_pct': gross_std,
                'Net_Sharpe': net_sharpe
            })

# Create results dataframe
df_results = pd.DataFrame(all_results)

# Save detailed results
output_dir = Path('results/robustness_checks')
output_dir.mkdir(exist_ok=True, parents=True)

df_results.to_csv(output_dir / 'transaction_cost_analysis.csv', index=False)

# Create summary for medium turnover (most realistic)
df_summary = df_results[df_results['Turnover_Level'] == 'Medium'].copy()

print("\n" + "="*80)
print("SUMMARY - MEDIUM TURNOVER (100% monthly)")
print("="*80)

for scenario in scenarios_to_analyze.keys():
    scenario_data = df_summary[df_summary['Scenario'] == scenario]
    if len(scenario_data) == 0:
        continue

    print(f"\n{scenario}:")
    print(f"  {'':15} {'Net Return':>12} {'Net Sharpe':>12} {'Cost Drag':>12}")

    for _, row in scenario_data.iterrows():
        print(f"  {row['TC_Level'] + ' TC':15} {row['Net_Return_pct']:11.2f}%  {row['Net_Sharpe']:11.3f}  {row['Cost_Drag_pct']:11.2f}%")

print("\n" + "="*80)
print("KEY FINDINGS")
print("="*80)

print("\n1. BASELINE SCENARIO (Medium TC, Medium Turnover):")
print("   - Transaction cost: 75 bps per trade")
print("   - Monthly turnover: 100%")
print("   - Annual cost drag: ~9% (0.75% × 100% × 12)")

print("\n2. COST IMPACT:")
print("   - Low scenario (50 bps, 50% turn): ~3% annual drag")
print("   - Medium scenario (75 bps, 100% turn): ~9% annual drag")
print("   - High scenario (100 bps, 150% turn): ~18% annual drag")

print("\n3. INTERPRETATION:")
print("   - If gross alpha is 21%, net alpha (medium scenario) approx 12%")
print("   - If gross alpha is 27%, net alpha (medium scenario) approx 18%")
print("   - Still economically significant, but MUCH lower than gross")

print("\n4. CAVEATS:")
print("   - Actual turnover depends on tree stability")
print("   - Swedish market may have higher costs than assumed")
print("   - Does not account for market impact on large positions")
print("   - Does not account for financing costs for short positions")

print(f"\nDetailed results saved to: {output_dir / 'transaction_cost_analysis.csv'}")

print("\n" + "="*80)
print("TRANSACTION COST ANALYSIS COMPLETE")
print("="*80)
