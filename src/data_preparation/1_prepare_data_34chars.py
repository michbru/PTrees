"""
Data Preparation for P-Tree Analysis (34 Characteristics)

Prepares Swedish stock market data with ENHANCED characteristics for P-Tree analysis:
1. Loads enhanced data (with 34 characteristics)
2. Merges with macro variables (risk-free rate)
3. Creates required P-Tree columns (xret, permno, lag_me)
4. Creates cross-sectional ranked characteristics
5. Saves prepared dataset

Input: ../../data/processed/ptrees_enhanced_dataset.csv, ../../data/macro/macro_variables_with_dates.csv
Output: ../../results/ptree_34chars/ptree_ready_data_34chars.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

print("="*80)
print("DATA PREPARATION FOR P-TREE ANALYSIS (34 CHARACTERISTICS)")
print("="*80)

# Load data
print("\nLoading enhanced data with 34 characteristics...")
data = pd.read_csv('../../data/processed/ptrees_enhanced_dataset.csv')
print(f"  [OK] Loaded enhanced dataset")
print(f"  Loaded {len(data):,} observations")
print(f"  Period: {data['date'].min()} to {data['date'].max()}")

# Convert date
data['date'] = pd.to_datetime(data['date'])

# Load macro variables (for risk-free rate)
print("\nLoading macro variables...")
macro = pd.read_csv('../../data/macro/macro_variables_with_dates.csv')
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
# Fill NaN lag_me with current market_cap (for first observation per stock)
data['lag_me'] = data['lag_me'].fillna(data['market_cap'])
# Final safety: drop any remaining NaN in lag_me
data = data[data['lag_me'].notna()].copy()
print(f"  Created lag_me (lagged market cap for value-weighting)")

# Remove observations without required data
print("\nRemoving observations with missing required data...")
before = len(data)
data = data[data['xret'].notna() & data['lag_me'].notna()].copy()
print(f"  Removed {before - len(data):,} observations")
print(f"  Remaining observations: {len(data):,}")

# Characteristics to rank - ENHANCED SET (34 characteristics)
# Prioritized by importance in original P-Tree paper
characteristics = [
    # CRITICAL characteristics (used in top P-Tree splits)
    'sue',              # Standardized Unexpected Earnings (Split 1 in paper!)
    'dolvol',           # Dollar Trading Volume (Splits 2, 3 in paper)
    'bm_ia',            # Industry-adjusted Book-to-Market (Splits 4, 5)
    'me_ia',            # Industry-adjusted Market Equity (Split 7)
    'roe',              # Return on Equity (Split 5)
    'zerotrade',        # Zero Trading Days (Split 6)

    # Original characteristics - Value & Size
    'market_cap', 'book_to_market', 'me',

    # Original characteristics - Profitability
    'ep_ratio', 'cfp_ratio', 'sp_ratio', 'roa',
    'gross_profitability', 'op', 'pm',

    # Original characteristics - Investment & Growth
    'sales_growth', 'asset_growth', 'capex_to_assets', 'ni',

    # Original characteristics - Momentum
    'momentum_12m', 'return_1m', 'mom6m', 'mom36m',

    # Original characteristics - Frictions & Trading
    'volatility_12m', 'svar', 'turnover', 'std_turn', 'std_dolvol',

    # Original characteristics - Efficiency & Quality
    'cfo_to_assets', 'asset_turnover', 'debt_to_equity',
    'asset_quality', 'price_to_assets'
]

# Filter to only include characteristics that exist in the dataset
characteristics = [c for c in characteristics if c in data.columns]

print(f"\nCreating ranked characteristics...")
print(f"  Processing {len(characteristics)} characteristics")

# Define accounting characteristics that require 3-month lag (reporting delay)
accounting_chars = [
    'roe', 'roa', 'gross_profitability', 'op', 'pm',
    'asset_growth', 'sales_growth', 'ni',
    'debt_to_equity', 'asset_quality', 'capex_to_assets',
    'cfo_to_assets', 'asset_turnover', 'ep_ratio', 'cfp_ratio', 'sp_ratio'
]

# Lag characteristics (1 month for market data, 3 months for accounting data)
print("  Step 1: Lagging characteristics by 1 or 3 months...")
for char in characteristics:
    if char in data.columns:
        # Use 3-month lag for accounting data (to account for reporting delays)
        lag_periods = 3 if char in accounting_chars else 1
        data[f'lag_{char}'] = data.groupby('permno')[char].shift(lag_periods)
        if lag_periods == 3:
            print(f"    [OK] lag_{char} (3-month lag for accounting data)")

# Cross-sectional ranking by month using LAGGED values
print("  Step 2: Ranking lagged characteristics within each month...")
for char in characteristics:
    lag_col = f'lag_{char}'
    if lag_col in data.columns:
        data[f'rank_{char}'] = data.groupby('date')[lag_col].rank(pct=True)
        print(f"  [OK] rank_{char} (from {lag_col})")

# Handle missing values in ranked characteristics
print("\nHandling missing values in ranked characteristics...")
ranked_cols = [c for c in data.columns if c.startswith('rank_')]
nan_before = data[ranked_cols].isna().sum().sum()

# FILL NaN with 0.5 (neutral rank) instead of dropping observations
# This preserves data while indicating no information for that characteristic
# P-Tree will naturally down-weight characteristics with many NaN values
for col in ranked_cols:
    data[col] = data[col].fillna(0.5)

nan_after = data[ranked_cols].isna().sum().sum()
print(f"  Filled {nan_before:,} NaN values with 0.5 (neutral rank)")
print(f"  Remaining observations: {len(data):,}")
print(f"  Remaining NaN values: {nan_after}")

# Final data cleaning - remove any remaining NaN in required columns
print("\nFinal data cleaning...")
ptree_core_cols = ['xret', 'permno', 'lag_me']
before_final = len(data)
data = data[data[ptree_core_cols].notna().all(axis=1)].copy()
print(f"  Dropped {before_final - len(data):,} obs with NaN in core columns")
print(f"  Final observations: {len(data):,}")

# Create output directory
output_dir = Path('../../results/ptree_34chars')
output_dir.mkdir(parents=True, exist_ok=True)

# Save prepared data
output_file = output_dir / 'ptree_ready_data_34chars.csv'
data.to_csv(output_file, index=False)

print(f"\n[SUCCESS] Data preparation complete")
print(f"  Saved to: {output_file}")
print(f"  Final observations: {len(data):,}")
print(f"  Characteristics: {len([c for c in data.columns if c.startswith('rank_')])} (enhanced from 19 to 34)")

# Final verification
print("\nFinal data verification:")
nan_core = data[ptree_core_cols].isna().sum().sum()
nan_ranks = data[ranked_cols].isna().sum().sum()
print(f"  NaN in core columns (xret, permno, lag_me): {nan_core}")
print(f"  NaN in ranked characteristics: {nan_ranks}")
print(f"  [OK] Ready for P-Tree analysis: {'YES' if nan_core == 0 and nan_ranks == 0 else 'NO - CHECK DATA'}")

# Print summary statistics
print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)
print(f"Date range: {data['date'].min().strftime('%Y-%m')} to {data['date'].max().strftime('%Y-%m')}")
print(f"Number of months: {data['date'].nunique()}")
print(f"Number of stocks: {data['permno'].nunique()}")
print(f"Average stocks per month: {len(data) / data['date'].nunique():.0f}")
print(f"Total observations: {len(data):,}")
print(f"Characteristics: {len(characteristics)}")
print()
