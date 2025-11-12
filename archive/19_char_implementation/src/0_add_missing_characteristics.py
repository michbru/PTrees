"""
Add Missing Key Characteristics for P-Tree Analysis

This script adds critical characteristics from Cong et al. (2024) that are missing
from the Swedish dataset but can be calculated from existing data:

Priority characteristics (used in top splits of P-Tree):
1. SUE - Standardized Unexpected Earnings (earnings surprise)
2. DOLVOL - Dollar Trading Volume
3. BM_IA - Industry-adjusted Book-to-Market
4. ME_IA - Industry-adjusted Market Equity (size)
5. ROE - Return on Equity
6. ZEROTRADE - Number of zero-trading days
7. Additional momentum, profitability, and friction metrics

Input: data/ptrees_final_dataset.csv
Output: data/ptrees_enhanced_dataset.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("ADDING MISSING KEY CHARACTERISTICS FOR P-TREE")
print("="*80)

# Load data
print("\n[1/6] Loading data...")
data = pd.read_csv('data/ptrees_final_dataset.csv')
data['date'] = pd.to_datetime(data['date'])
print(f"  Loaded {len(data):,} observations")
print(f"  Period: {data['date'].min()} to {data['date'].max()}")
print(f"  Stocks: {data['id'].nunique()}")

# Sort by stock and date
data = data.sort_values(['id', 'date'])

# ============================================================================
# [2/6] CALCULATE KEY MISSING CHARACTERISTICS
# ============================================================================
print("\n[2/6] Calculating missing characteristics...")

# ----------------------------------------------------------------------------
# 1. DOLVOL - Dollar Trading Volume (Critical - used in splits 2 & 3)
# ----------------------------------------------------------------------------
print("\n  [1] DOLVOL (Dollar Trading Volume)")
data['dolvol'] = data['price'] * data['volume']
print(f"      [OK] Created: {data['dolvol'].notna().sum():,} observations")

# ----------------------------------------------------------------------------
# 2. ROE - Return on Equity (Critical - used in split 5)
# ----------------------------------------------------------------------------
print("\n  [2] ROE (Return on Equity)")
# ROE = Net Income / Book Value
data['roe'] = data['net_income'] / data['book_value']
# Handle infinite values
data.loc[data['roe'].abs() > 10, 'roe'] = np.nan  # Cap extreme values
print(f"      [OK] Created: {data['roe'].notna().sum():,} observations")

# ----------------------------------------------------------------------------
# 3. SUE - Standardized Unexpected Earnings (Critical - #1 split characteristic!)
# ----------------------------------------------------------------------------
print("\n  [3] SUE (Standardized Unexpected Earnings)")
# SUE = (Earnings_t - Earnings_t-4) / StdDev(Earnings_diff)
# Using quarterly earnings, compare to same quarter last year

# Calculate seasonal earnings (4 quarters ago)
data['earnings_lag4q'] = data.groupby('id')['net_income'].shift(4)

# Calculate earnings surprise
data['earnings_surprise'] = data['net_income'] - data['earnings_lag4q']

# Calculate rolling std of earnings surprise (over 8 quarters)
data['earnings_surprise_std'] = data.groupby('id')['earnings_surprise'].transform(
    lambda x: x.rolling(window=8, min_periods=4).std()
)

# Calculate SUE
data['sue'] = data['earnings_surprise'] / data['earnings_surprise_std']

# Handle infinite/extreme values
data.loc[data['sue'].abs() > 10, 'sue'] = np.nan
print(f"      [OK] Created: {data['sue'].notna().sum():,} observations")
print(f"      [INFO] Note: SUE requires 4-8 quarters of history, so early observations are NA")

# ----------------------------------------------------------------------------
# 4. ZEROTRADE - Zero Trading Days (Critical - used in split 6)
# ----------------------------------------------------------------------------
print("\n  [4] ZEROTRADE (Number of Zero Trading Days)")
# Approximate using very low volume days (bottom 5% of volume distribution)
# Since we have monthly data, we'll use a proxy based on turnover

# Zero trade indicator: very low turnover (< 1% monthly)
data['zerotrade'] = (data['turnover'] < 0.01).astype(int)
print(f"      [OK] Created: {data['zerotrade'].notna().sum():,} observations")
print(f"      [INFO] Note: Proxy based on low turnover (< 1% per month)")

# ----------------------------------------------------------------------------
# 5. ME_IA - Industry-Adjusted Market Equity
# 6. BM_IA - Industry-Adjusted Book-to-Market (Critical - used in splits 4 & 5)
# ----------------------------------------------------------------------------
print("\n  [5-6] Industry-Adjusted Metrics (ME_IA, BM_IA)")

# Use market name as industry proxy (e.g., SSEFN, SSELQ, etc.)
data['industry'] = data['marketname']

# Calculate industry medians by month
industry_medians = data.groupby(['date', 'industry']).agg({
    'market_cap': 'median',
    'book_to_market': 'median'
}).reset_index()

industry_medians.columns = ['date', 'industry', 'market_cap_ind', 'book_to_market_ind']

# Merge back
data = data.merge(industry_medians, on=['date', 'industry'], how='left')

# Calculate industry-adjusted metrics (ratio to industry median)
data['me_ia'] = data['market_cap'] / data['market_cap_ind']
data['bm_ia'] = data['book_to_market'] / data['book_to_market_ind']

# Log transform for better distribution
data['me_ia'] = np.log(data['me_ia'].clip(lower=0.01))
data['bm_ia'] = np.log(data['bm_ia'].clip(lower=0.01))

print(f"      [OK] ME_IA created: {data['me_ia'].notna().sum():,} observations")
print(f"      [OK] BM_IA created: {data['bm_ia'].notna().sum():,} observations")
print(f"      [INFO] Note: Using market segment as industry proxy")

# ----------------------------------------------------------------------------
# 7. Additional Profitability Metrics
# ----------------------------------------------------------------------------
print("\n  [7] Additional Profitability Metrics")

# Operating Profitability (OP) - similar to gross_profitability but using revenue
data['op'] = (data['total_revenue'] - data['cogs']) / data['book_value']
data.loc[data['op'].abs() > 10, 'op'] = np.nan

# Profit Margin (PM)
data['pm'] = data['net_income'] / data['total_revenue']
data.loc[data['pm'].abs() > 1, 'pm'] = np.nan

print(f"      [OK] OP (Operating Profitability): {data['op'].notna().sum():,} obs")
print(f"      [OK] PM (Profit Margin): {data['pm'].notna().sum():,} obs")

# ----------------------------------------------------------------------------
# 8. Additional Momentum Metrics
# ----------------------------------------------------------------------------
print("\n  [8] Additional Momentum Metrics")

# MOM6M - 6-month momentum
data['mom6m'] = data.groupby('id')['current_return'].transform(
    lambda x: x.rolling(window=6, min_periods=4).apply(lambda r: (1 + r).prod() - 1)
)

# MOM36M - 3-year momentum (36 months)
data['mom36m'] = data.groupby('id')['current_return'].transform(
    lambda x: x.rolling(window=36, min_periods=24).apply(lambda r: (1 + r).prod() - 1)
)

print(f"      [OK] MOM6M (6-month momentum): {data['mom6m'].notna().sum():,} obs")
print(f"      [OK] MOM36M (36-month momentum): {data['mom36m'].notna().sum():,} obs")

# ----------------------------------------------------------------------------
# 9. Additional Friction Metrics
# ----------------------------------------------------------------------------
print("\n  [9] Additional Friction Metrics")

# Market Equity (ME) - same as market_cap, but log transformed
data['me'] = np.log(data['market_cap'])

# Volatility (SVAR) - same as volatility_12m but annualized
data['svar'] = data['volatility_12m'] ** 2  # Variance

# Turnover metrics
data['std_turn'] = data.groupby('id')['turnover'].transform(
    lambda x: x.rolling(window=12, min_periods=6).std()
)

# Dollar volume volatility
data['std_dolvol'] = data.groupby('id')['dolvol'].transform(
    lambda x: x.rolling(window=12, min_periods=6).std()
)

print(f"      [OK] ME (Log Market Equity): {data['me'].notna().sum():,} obs")
print(f"      [OK] SVAR (Variance): {data['svar'].notna().sum():,} obs")
print(f"      [OK] STD_TURN (Std of Turnover): {data['std_turn'].notna().sum():,} obs")
print(f"      [OK] STD_DOLVOL (Std of Dollar Volume): {data['std_dolvol'].notna().sum():,} obs")

# ----------------------------------------------------------------------------
# 10. Investment Metrics
# ----------------------------------------------------------------------------
print("\n  [10] Investment Metrics")

# Net Equity Issuance (approximation using market cap growth adjusted for returns)
data['market_cap_lag1'] = data.groupby('id')['market_cap'].shift(1)
data['ni'] = (data['market_cap'] - data['market_cap_lag1'] * (1 + data['current_return'])) / data['market_cap_lag1']
data.loc[data['ni'].abs() > 1, 'ni'] = np.nan

print(f"      [OK] NI (Net Equity Issuance): {data['ni'].notna().sum():,} obs")

# Clean up temporary columns
data = data.drop(['market_cap_ind', 'book_to_market_ind', 'earnings_lag4q',
                  'earnings_surprise', 'earnings_surprise_std', 'market_cap_lag1'], axis=1)

# ============================================================================
# [3/6] SUMMARY OF NEW CHARACTERISTICS
# ============================================================================
print("\n[3/6] Summary of new characteristics added:")
print("="*80)

new_chars = {
    'Critical (used in P-Tree top splits)': [
        'sue', 'dolvol', 'bm_ia', 'me_ia', 'roe', 'zerotrade'
    ],
    'Profitability': ['op', 'pm'],
    'Momentum': ['mom6m', 'mom36m'],
    'Frictions': ['me', 'svar', 'std_turn', 'std_dolvol'],
    'Investment': ['ni']
}

for category, chars in new_chars.items():
    print(f"\n{category}:")
    for char in chars:
        coverage = data[char].notna().sum()
        pct = 100 * coverage / len(data)
        print(f"  {char:15s}: {coverage:8,} obs ({pct:5.1f}% coverage)")

# ============================================================================
# [4/6] COUNT TOTAL CHARACTERISTICS
# ============================================================================
print("\n[4/6] Total characteristic count:")
print("="*80)

# Original characteristics for P-Tree (excluding identifiers and returns)
original_ptree_chars = [
    'market_cap', 'book_to_market', 'ep_ratio', 'cfp_ratio', 'sp_ratio',
    'price_to_assets', 'momentum_12m', 'return_1m', 'volatility_12m',
    'roa', 'gross_profitability', 'cfo_to_assets', 'sales_growth',
    'asset_growth', 'capex_to_assets', 'asset_turnover', 'debt_to_equity',
    'asset_quality', 'turnover'
]

new_ptree_chars = [
    'sue', 'dolvol', 'bm_ia', 'me_ia', 'roe', 'zerotrade',
    'op', 'pm', 'mom6m', 'mom36m', 'me', 'svar', 'std_turn', 'std_dolvol', 'ni'
]

print(f"Original characteristics: {len(original_ptree_chars)}")
print(f"New characteristics added: {len(new_ptree_chars)}")
print(f"Total characteristics: {len(original_ptree_chars) + len(new_ptree_chars)}")
print(f"\nTarget (Cong et al. 2024): 61 characteristics")
print(f"Swedish dataset coverage: {100*(len(original_ptree_chars) + len(new_ptree_chars))/61:.1f}%")

# ============================================================================
# [5/6] DATA QUALITY CHECK
# ============================================================================
print("\n[5/6] Data quality check:")
print("="*80)

all_ptree_chars = original_ptree_chars + new_ptree_chars

# Check coverage for each characteristic
low_coverage = []
for char in all_ptree_chars:
    coverage = data[char].notna().sum()
    pct = 100 * coverage / len(data)
    if pct < 50:
        low_coverage.append((char, pct))

if low_coverage:
    print("\n[WARNING] Characteristics with <50% coverage:")
    for char, pct in sorted(low_coverage, key=lambda x: x[1]):
        print(f"  {char:20s}: {pct:5.1f}%")
else:
    print("[OK] All characteristics have >50% coverage")

# ============================================================================
# [6/6] SAVE ENHANCED DATASET
# ============================================================================
print("\n[6/6] Saving enhanced dataset...")

output_file = 'data/ptrees_enhanced_dataset.csv'
data.to_csv(output_file, index=False)

print(f"\n[OK] SUCCESS! Enhanced dataset saved to: {output_file}")
print(f"  Total observations: {len(data):,}")
print(f"  Total characteristics: {len(all_ptree_chars)}")
print(f"  Period: {data['date'].min()} to {data['date'].max()}")

# ============================================================================
# DOCUMENTATION OF LIMITATIONS
# ============================================================================
print("\n" + "="*80)
print("LIMITATIONS & NOTES")
print("="*80)
print("""
Swedish Market Data Limitations vs US Study (Cong et al. 2024):

1. COVERAGE: 34/61 characteristics (55.7% coverage)
   - US study uses 61 firm characteristics from Compustat
   - Swedish market has limited accounting data availability

2. MISSING CATEGORIES:
   - Detailed intangibles (R&D, advertising, seasonality)
   - High-frequency trading metrics (bid-ask spread, intraday volatility)
   - Industry concentration measures
   - Analyst forecast data

3. APPROXIMATIONS:
   - SUE: Calculated from quarterly earnings (not consensus estimates)
   - ZEROTRADE: Proxied by low turnover (<1% monthly)
   - Industry adjustments: Based on market segment (coarse classification)

4. DATA FREQUENCY:
   - Monthly data (vs daily in US study)
   - Limits precision of trading-based metrics

5. STRENGTHS:
   - All critical characteristics from top P-Tree splits are included
   - Good coverage of momentum, value, profitability, and basic frictions
   - Sufficient for meaningful P-Tree training and testing

CONCLUSION:
The enhanced Swedish dataset is suitable for P-Tree analysis, with focus
on the most important characteristics identified in the original study.
""")

print("\n" + "="*80)
print("Next steps:")
print("  1. Run: python src/1_prepare_data.py")
print("  2. This will use the enhanced dataset with 34 characteristics")
print("  3. P-Tree will automatically select the most relevant ones")
print("="*80)
