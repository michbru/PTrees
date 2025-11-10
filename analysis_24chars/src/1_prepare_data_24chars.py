"""
Data Preparation for P-Tree Analysis - 24 Matched Characteristics

Prepares Swedish stock market data with ONLY the 24 characteristics that match
the US study (Cong et al. 2024) for P-Tree analysis.

Input: 
  - ../data/ptrees_24_matched_chars.csv
  - ../data/macro_variables_with_dates.csv
  
Output: 
  - results/ptree_ready_data_24chars.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("DATA PREPARATION FOR P-TREE ANALYSIS (24 MATCHED CHARACTERISTICS)")
print("="*80)
print()

# Load the 24-characteristic dataset
print("Loading 24-characteristic dataset...")
df = pd.read_csv('../data/ptrees_24_matched_chars.csv')
df['date'] = pd.to_datetime(df['date'])
print(f"[OK] Loaded {len(df):,} records")
print(f"     Date range: {df['date'].min()} to {df['date'].max()}")
print()

# Load macro variables
print("Loading macro variables...")
macro = pd.read_csv('../data/macro_variables_with_dates.csv')
macro['date'] = pd.to_datetime(macro['date'])
print(f"[OK] Loaded {len(macro):,} macro observations")
print()

# Merge macro variables
print("Merging macro variables...")
df = df.merge(macro, on='date', how='left')
print(f"[OK] Merged dataset: {len(df):,} records")
print()

# Rename current_return to xret for consistency with original analysis
df = df.rename(columns={'current_return': 'xret'})

# Define the 23 matched characteristics from the US study
# (24 US chars map to 23 Swedish chars since rvar_capm and rvar_mean both map to volatility_12m)
matched_chars = [
    'asset_growth',      # agr
    'asset_turnover',    # ato
    'book_to_market',    # bm
    'cash_liquidity',    # cash
    'cfp_ratio',         # cfp
    'ep_ratio',          # ep
    'gross_profitability', # gma
    'debt_to_equity',    # lev
    'market_cap',        # me
    'momentum_12m',      # mom12m
    'return_1m',         # mom1m
    'operating_margin',  # op
    'net_margin',        # pm
    'roa',               # Roa1
    'roe',               # roe
    'sales_growth',      # sgr
    'sp_ratio',          # sp
    'turnover',          # turn
    'capex',             # cinvest
    'volume',            # dolvol
    'revenue_per_employee', # hire
    'volatility_12m',    # rvar_capm & rvar_mean
]

# Filter to only keep matched characteristics that exist in the dataset
char_cols = [col for col in matched_chars if col in df.columns]

print(f"Identified {len(char_cols)} matched characteristic columns:")
for col in sorted(char_cols):
    print(f"  - {col}")
print()

# Rank characteristics within each month
print("Ranking characteristics within each month...")
for col in char_cols:
    df[f'rank_{col}'] = df.groupby('date')[col].rank(pct=True, method='average')
print(f"[OK] Created {len(char_cols)} ranked characteristics")
print()

# Create lagged versions
print("Creating lagged characteristics (t-1)...")
df = df.sort_values(['id', 'date'])
lag_cols = [f'rank_{col}' for col in char_cols]

for col in lag_cols:
    df[f'lag_{col}'] = df.groupby('id')[col].shift(1)

# Also lag market_cap for portfolio weighting
df['lag_me'] = df.groupby('id')['market_cap'].shift(1)
print(f"[OK] Created lagged versions")
print()

# Remove rows with missing lagged characteristics or returns
print("Removing rows with missing values...")
required_cols = [f'lag_rank_{col}' for col in char_cols] + ['xret', 'lag_me']
df_clean = df.dropna(subset=required_cols)

print(f"  Before: {len(df):,} records")
print(f"  After:  {len(df_clean):,} records")
print(f"  Removed: {len(df) - len(df_clean):,} records ({100*(len(df) - len(df_clean))/len(df):.1f}%)")
print()

# Prepare final dataset for P-Tree
print("Preparing final dataset...")

# Select columns for output
output_cols = ['id', 'date', 'xret', 'lag_me'] + [f'lag_rank_{col}' for col in char_cols]

# Rename for cleaner column names (remove 'lag_' prefix from rank columns)
df_final = df_clean[output_cols].copy()
rename_dict = {f'lag_rank_{col}': f'rank_{col}' for col in char_cols}
df_final = df_final.rename(columns=rename_dict)

# Use 'id' as 'permno' for compatibility with R script
df_final = df_final.rename(columns={'id': 'permno'})

print(f"Final dataset shape: {df_final.shape}")
print(f"  Records: {len(df_final):,}")
print(f"  Columns: {len(df_final.columns)}")
print(f"  - permno, date, xret, lag_me")
print(f"  - {len(char_cols)} ranked characteristics (lagged)")
print()

print("Summary statistics:")
print(f"  Date range: {df_final['date'].min()} to {df_final['date'].max()}")
print(f"  Unique stocks: {df_final['permno'].nunique()}")
print(f"  Unique months: {df_final['date'].nunique()}")
print(f"  Mean return: {df_final['xret'].mean():.4f}")
print(f"  Median return: {df_final['xret'].median():.4f}")
print(f"  Return std: {df_final['xret'].std():.4f}")
print()

# Save
output_file = 'results/ptree_ready_data_24chars.csv'
Path('results').mkdir(exist_ok=True)
print(f"Saving to {output_file}...")
df_final.to_csv(output_file, index=False)
print("[OK] Saved successfully")
print()

print("="*80)
print("DATA PREPARATION COMPLETE")
print("="*80)
print()
print(f"Output: {output_file}")
print(f"Ready for P-Tree analysis with {len(char_cols)} characteristics")
print()
