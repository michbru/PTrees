"""
Data Preparation for P-Tree Analysis - 24 Matched Characteristics

Prepares Swedish stock market data with ONLY the 24 characteristics that match
the US study (Cong et al. 2024) for P-Tree analysis.

Input: data/ptrees_24_matched_chars.csv, data/macro_variables_with_dates.csv
Output: results/ptree_ready_data_24chars.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("DATA PREPARATION FOR P-TREE ANALYSIS (24 MATCHED CHARACTERISTICS)")
print("="*80)

# Load data
print("\nLoading 24-characteristic dataset...")
data = pd.read_csv('data/ptrees_24_matched_chars.csv')
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

# 23 unique characteristics that match US study (24 US chars map to 23 Swedish)
characteristics = [
    'asset_growth',        # agr
    'asset_turnover',      # ato
    'book_to_market',      # bm
    'cash_liquidity',      # cash
    'cfp_ratio',           # cfp
    'ep_ratio',            # ep
    'gross_profitability', # gma
    'debt_to_equity',      # lev
    'market_cap',          # me
    'momentum_12m',        # mom12m
    'return_1m',           # mom1m
    'operating_margin',    # op
    'net_margin',          # pm
    'roa',                 # Roa1
    'roe',                 # roe
    'sales_growth',        # sgr
    'sp_ratio',            # sp
    'turnover',            # turn
    'capex',               # cinvest
    'volume',              # dolvol
    'revenue_per_employee',# hire
    'volatility_12m',      # rvar_capm, rvar_mean
    'current_return',      # abr
]

print(f"\nCreating ranked characteristics...")
print(f"  Processing {len(characteristics)} characteristics (matched to US study)")

# Lag characteristics by 1 month (following Cong et al. 2024)
print("  Step 1: Lagging all characteristics by 1 month...")
for char in characteristics:
    if char in data.columns:
        data[f'lag_{char}'] = data.groupby('permno')[char].shift(1)
    else:
        print(f"  [WARNING] {char} not found in dataset")

# Cross-sectional ranking by month using LAGGED values
print("  Step 2: Ranking lagged characteristics within each month...")
for char in characteristics:
    lag_col = f'lag_{char}'
    if lag_col in data.columns:
        data[f'rank_{char}'] = data.groupby('date')[lag_col].rank(pct=True)
        print(f"  [OK] rank_{char} (from {lag_col})")
    else:
        print(f"  [SKIP] {char} not available")

# Handle missing values in ranked characteristics
print("\nHandling missing values in ranked characteristics...")
ranked_cols = [c for c in data.columns if c.startswith('rank_')]
nan_before = data[ranked_cols].isna().sum().sum()

# REMOVE observations where ANY ranked characteristic is NaN
# This removes first observation per stock (which has no prior data)
data = data[data[ranked_cols].notna().all(axis=1)].copy()

nan_after = data[ranked_cols].isna().sum().sum()
print(f"  Removed {nan_before:,} observations with NaN ranks")
print(f"  Remaining observations: {len(data):,}")
print(f"  Remaining NaN values: {nan_after}")

# Create output directory
output_dir = Path('results')
output_dir.mkdir(exist_ok=True)

# Save prepared data
output_file = output_dir / 'ptree_ready_data_24chars.csv'
data.to_csv(output_file, index=False)

print(f"\n[SUCCESS] Data preparation complete")
print(f"  Saved to: {output_file}")
print(f"  Final observations: {len(data):,}")
print(f"  P-Tree required columns: xret, permno, lag_me (all non-null)")
print(f"  Ranked characteristics: {len([c for c in data.columns if c.startswith('rank_')])} (from 24 matched US chars)")

# Final verification - check only P-Tree required columns
print("\nFinal data verification:")
ptree_required_cols = ['xret', 'permno', 'lag_me'] + ranked_cols
nan_in_required = data[ptree_required_cols].isna().sum().sum()
print(f"  NaN in P-Tree required columns: {nan_in_required}")
print(f"  Ready for P-Tree analysis: {'YES' if nan_in_required == 0 else 'NO - CHECK DATA'}")
print()
