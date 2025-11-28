"""
Step 3: Prepare P-Tree Dataset with Characteristics and Ranks
==============================================================
Calculate characteristics and create cross-sectional ranks for P-Tree analysis.

Input:
  - data/intermediate/stock_with_accounting.csv (merged data from Step 2)
  - data/raw/macro/macro_variables_with_dates.csv (risk-free rate)

Output:
  - results/ptree_33chars/ptree_ready_data_33chars.csv

Lag Structure (applied in Steps 1-2):
  - Serrano accounting: 1-year lag (fiscal_year + 1)
  - LSEG accounting: 1-month lag (shift in Step 2)
  - Market data: No lag (observable at month-end)
"""

import pandas as pd
import numpy as np
from pathlib import Path

script_dir = Path(__file__).parent
project_root = script_dir.parent.parent

# ==============================================================================
# LOAD DATA
# ==============================================================================

print("\n[1] Loading data...")

base = pd.read_csv(project_root / 'data/intermediate/stock_with_accounting.csv', low_memory=False)
base['date'] = pd.to_datetime(base['date'])

# Create PERMNO from ISIN
base['permno'] = base.groupby('isin').ngroup()
base = base.sort_values(['permno', 'date'])

# Load macro variables
macro = pd.read_csv(project_root / 'data/raw/macro/macro_variables_with_dates.csv')
macro['date'] = pd.to_datetime(macro['date'])

# Merge
data = base.merge(macro[['date', 'rf', 'rm_rf']], on='date', how='left')
print(f"  Loaded: {len(data):,} observations, {data['permno'].nunique()} stocks")

# ==============================================================================
# CALCULATE EXCESS RETURNS AND CHARACTERISTICS
# ==============================================================================

print("\n[2] Calculating characteristics...")

# Excess returns
data['xret'] = data['current_return'] - data['rf'].fillna(0)
data = data[data['xret'].notna()].copy()

# SUE - Standardized Unexpected Earnings (earnings surprise / market cap)
data['earnings_lag1y'] = data.groupby('permno')['net_income'].shift(12)
data['earnings_surprise'] = data['net_income'] - data['earnings_lag1y']
data['sue'] = data['earnings_surprise'] / data['market_cap']
data.loc[data['sue'].abs() > 1, 'sue'] = np.nan

# DOLVOL - Dollar Trading Volume
data['dolvol'] = data['price'] * data['volume']

# NI - Net Equity Issuance
data['market_cap_lag1'] = data.groupby('permno')['market_cap'].shift(1)
data['ni'] = (data['market_cap'] - data['market_cap_lag1'] * (1 + data['current_return'])) / data['market_cap_lag1']
data.loc[data['ni'].abs() > 1, 'ni'] = np.nan

# STD_TURN - Turnover Volatility (3 months per paper)
data['std_turn'] = data.groupby('permno')['turnover'].transform(
    lambda x: x.rolling(window=3, min_periods=2).std()
)

# STD_DOLVOL - Dollar Volume Volatility (3 months per paper)
data['std_dolvol'] = data.groupby('permno')['dolvol'].transform(
    lambda x: x.rolling(window=3, min_periods=2).std()
)

# Cleanup temp columns
data = data.drop(['earnings_lag1y', 'earnings_surprise', 'market_cap_lag1'], axis=1, errors='ignore')

print("  [OK] Characteristics calculated")

# ==============================================================================
# CREATE CROSS-SECTIONAL RANKS
# ==============================================================================

print("\n[3] Creating cross-sectional ranks...")

# All characteristics to rank
characteristics = [
    # Momentum
    'return_1m', 'momentum_12m',
    # Value & Size
    'market_cap', 'book_to_market', 'ep_ratio', 'cfp_ratio', 'sp_ratio',
    # Profitability
    'roe', 'roa', 'gross_profitability',
    # Serrano accounting
    'operating_margin', 'net_margin', 'cash_liquidity', 'equity_ratio', 
    'debt_ratio', 'capital_turnover', 'inventory_turnover', 
    'receivables_turnover', 'revenue_per_employee', 'profit_pct',
    # Investment
    'asset_growth', 'sales_growth', 'capex_to_assets', 'ni',
    # Frictions
    'dolvol', 'turnover', 'std_turn', 'std_dolvol',
    # Other
    'sue', 'asset_turnover', 'debt_to_equity', 'asset_quality',
    'cfo_to_assets', 'price_to_assets'
]

characteristics = [c for c in characteristics if c in data.columns]

# Lag market cap for portfolio weighting
data['lag_me'] = data.groupby('permno')['market_cap'].shift(1).fillna(data['market_cap'])


def rank_to_minus1_plus1(x):
    """Rank to exactly [-1, 1] scale."""
    ranks = x.rank()
    n = x.count()
    if n <= 1:
        return pd.Series(0.0, index=x.index)
    return ((ranks - 1) / (n - 1)) * 2 - 1


for char in characteristics:
    if char in data.columns:
        data[f'rank_{char}'] = data.groupby('date')[char].transform(rank_to_minus1_plus1)

# Fill missing ranks with 0.0 (neutral)
ranked_cols = [c for c in data.columns if c.startswith('rank_')]
for col in ranked_cols:
    data[col] = data[col].fillna(0.0)

print(f"  {len(ranked_cols)} ranked characteristics created")

# ==============================================================================
# SAVE OUTPUT
# ==============================================================================

print("\n[4] Saving P-Tree dataset...")

# Final validation
ptree_core_cols = ['xret', 'permno', 'lag_me']
data = data[data[ptree_core_cols].notna().all(axis=1)].copy()

# Select final columns
keep_cols = ['permno', 'date', 'year', 'month', 'xret', 'lag_me'] + ranked_cols
ptree_data = data[keep_cols].copy()

# Save
output_dir = project_root / 'results/ptree_33chars'
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'ptree_ready_data_33chars.csv'
ptree_data.to_csv(output_file, index=False)

# ==============================================================================
# SUMMARY
# ==============================================================================

print(f"\n{'='*60}")
print("P-TREE DATASET COMPLETE")
print(f"{'='*60}")
print(f"\nOutput: {output_file}")
print(f"  Observations: {len(ptree_data):,}")
print(f"  Unique stocks: {ptree_data['permno'].nunique()}")
print(f"  Period: {ptree_data['date'].min().strftime('%Y-%m')} to {ptree_data['date'].max().strftime('%Y-%m')}")
print(f"  Characteristics: {len(characteristics)}")
print(f"  Avg stocks/month: {len(ptree_data) / ptree_data['date'].nunique():.0f}")

# Coverage summary
print("\nCharacteristic coverage:")
for char in characteristics:
    if char in data.columns:
        coverage = data[char].notna().mean() * 100
        print(f"  {char}: {coverage:.1f}%")
print(f"{'='*60}")
