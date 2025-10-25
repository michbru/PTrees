"""
Data Preparation for P-Tree Analysis

Prepares Swedish stock market data for P-Tree analysis:
1. Loads raw data
2. Merges with macro variables (risk-free rate)
3. Creates required P-Tree columns (xret, permno, lag_me)
4. Creates cross-sectional ranked characteristics
5. Saves prepared dataset

Input: data/ptrees_final_dataset.csv, data/macro_variables_with_dates.csv
Output: results/ptree_ready_data_full.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("DATA PREPARATION FOR P-TREE ANALYSIS")
print("="*80)

# Load data
print("\nLoading raw data...")
data = pd.read_csv('data/ptrees_final_dataset.csv')
print(f"  Loaded {len(data):,} observations")
print(f"  Period: {data['date'].min()} to {data['date'].max()}")

# Convert date
data['date'] = pd.to_datetime(data['date'])

# Load macro variables (for risk-free rate)
print("\nLoading macro variables...")
macro = pd.read_csv('data/macro_variables_with_dates.csv')
macro['date'] = pd.to_datetime(macro['date'])
print(f"  Loaded {len(macro)} months of macro data")

# Merge with macro to get risk-free rate
print("\nMerging with macro variables...")
data = data.merge(macro[['date', 'rf', 'rm_rf']], on='date', how='left')
print(f"  Merged: {data['rf'].notna().sum():,} observations have risk-free rate")

# Create excess returns (xret = current_return - rf)
print("\nCreating excess returns...")
data['xret'] = data['current_return'] - data['rf'].fillna(0)
print(f"  Created xret (excess returns)")

# Create stock identifier (permno)
print("\nCreating stock identifier...")
data['permno'] = data.groupby('id').ngroup()
print(f"  Created permno: {data['permno'].nunique()} unique stocks")

# Create lagged market cap (lag_me) - critical for avoiding look-ahead bias
print("\nCreating lagged market cap...")
data = data.sort_values(['permno', 'date'])
data['lag_me'] = data.groupby('permno')['market_cap'].shift(1)
# Fill first observation per stock with current market cap (can't look ahead)
data['lag_me'] = data['lag_me'].fillna(data['market_cap'])
print(f"  Created lag_me (lagged market cap for value-weighting)")

# Remove observations without excess returns
data = data[data['xret'].notna()].copy()
print(f"\nAfter removing missing xret: {len(data):,} observations")

# Characteristics to rank
characteristics = [
    'market_cap', 'book_to_market', 'ep_ratio', 'cfp_ratio', 'sp_ratio',
    'price_to_assets', 'momentum_12m', 'return_1m', 'volatility_12m',
    'roa', 'gross_profitability', 'cfo_to_assets', 'sales_growth',
    'asset_growth', 'capex_to_assets', 'asset_turnover', 'debt_to_equity',
    'asset_quality', 'turnover'
]

print(f"\nCreating ranked characteristics...")
print(f"  Processing {len(characteristics)} characteristics")

# Cross-sectional ranking by month
for char in characteristics:
    if char in data.columns:
        data[f'rank_{char}'] = data.groupby('date')[char].rank(pct=True)
        print(f"  [OK] rank_{char}")

# Handle missing values in ranked characteristics
print("\nHandling missing values in ranked characteristics...")
ranked_cols = [c for c in data.columns if c.startswith('rank_')]
nan_before = data[ranked_cols].isna().sum().sum()

# Fill NaN ranks with 0.5 (median/neutral rank)
# This is standard practice when characteristics are missing
for col in ranked_cols:
    data[col] = data[col].fillna(0.5)

nan_after = data[ranked_cols].isna().sum().sum()
print(f"  Filled {nan_before:,} NaN values with 0.5 (median rank)")
print(f"  Remaining NaN values: {nan_after}")

# Create output directory
output_dir = Path('results')
output_dir.mkdir(exist_ok=True)

# Save prepared data
output_file = output_dir / 'ptree_ready_data_full.csv'
data.to_csv(output_file, index=False)

print(f"\n[SUCCESS] Data preparation complete")
print(f"  Saved to: {output_file}")
print(f"  Final observations: {len(data):,}")
print(f"  P-Tree required columns: xret, permno, lag_me (all non-null)")
print(f"  Ranked characteristics: {len([c for c in data.columns if c.startswith('rank_')])} (NaN filled with 0.5)")

# Final verification - check only P-Tree required columns
print("\nFinal data verification:")
ptree_required_cols = ['xret', 'permno', 'lag_me'] + ranked_cols
nan_in_required = data[ptree_required_cols].isna().sum().sum()
print(f"  NaN in P-Tree required columns: {nan_in_required}")
print(f"  Ready for P-Tree analysis: {'YES' if nan_in_required == 0 else 'NO - CHECK DATA'}")
print()
