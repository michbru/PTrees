"""
Data Preparation for P-Tree Analysis

Prepares Swedish stock market data for P-Tree analysis:
1. Loads raw data
2. Creates cross-sectional ranked characteristics
3. Saves prepared dataset

Input: data/ptrees_final_dataset.csv
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
        print(f"  ✓ rank_{char}")

# Create output directory
output_dir = Path('results')
output_dir.mkdir(exist_ok=True)

# Save prepared data
output_file = output_dir / 'ptree_ready_data_full.csv'
data.to_csv(output_file, index=False)

print(f"\n✓ Data preparation complete")
print(f"  Saved to: {output_file}")
print(f"  Final observations: {len(data):,}")
print(f"  Ranked characteristics: {len([c for c in data.columns if c.startswith('rank_')])}")
print()
