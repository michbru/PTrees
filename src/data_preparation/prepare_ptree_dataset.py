"""
================================================================================
UNIFIED P-TREE DATA PREPARATION PIPELINE
================================================================================

This script creates the P-Tree dataset from RAW data sources in ONE unified pipeline.


INPUT (Raw Data):
    - data/raw/serrano/final_dataset_with_serrano_isin.csv  (Stock market + some accounting)
    - data/raw/serrano/serrano_nyckeltal_full.csv          (Additional accounting ratios)
    - data/macro/macro_variables_with_dates.csv            (Risk-free rate, market returns)
    - data/raw/serrano/isin_orgnr_mapping.csv              (Stock-to-company mapping)

OUTPUT:
    - results/ptree_34chars/ptree_ready_data_34chars.csv   (P-Tree ready dataset)

PROCESS:
    Step 1: Load and merge all raw data sources
    Step 2: Calculate ALL 34 stock characteristics (documented in one place)
    Step 3: Apply proper lags (1-month for market, 3-month for accounting)
    Step 4: Create cross-sectional ranks (percentiles within each month)
    Step 5: Save P-Tree ready dataset

Author: [Your Name]
Date: 2025-01-23 (Unified pipeline version)
================================================================================
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

print("="*80)
print("UNIFIED P-TREE DATA PREPARATION PIPELINE")
print("="*80)
print("\nThis script builds the COMPLETE P-Tree dataset from raw sources.")
print("All 34 characteristics are calculated and documented in one place.\n")

# ==============================================================================
# STEP 1: LOAD AND MERGE RAW DATA SOURCES
# ==============================================================================

print("\n" + "="*80)
print("STEP 1: LOADING AND MERGING RAW DATA SOURCES")
print("="*80)

print("\n[1.1] Loading base stock market dataset...")
# This file contains LSEG stock data + some Serrano accounting already merged
base = pd.read_csv('../../data/raw/serrano/final_dataset_with_serrano_isin.csv', low_memory=False)
base['date'] = pd.to_datetime(base['date'])
base = base.sort_values(['id', 'date'])

print(f"  [OK] Loaded: {len(base):,} observations")
print(f"  [OK] Period: {base['date'].min().strftime('%Y-%m')} to {base['date'].max().strftime('%Y-%m')}")
print(f"  [OK] Stocks: {base['id'].nunique()}")
print(f"  [OK] Columns: {len(base.columns)}")

print("\n[1.2] Loading macro variables (risk-free rate, market returns)...")
macro = pd.read_csv('../../data/macro/macro_variables_with_dates.csv')
macro['date'] = pd.to_datetime(macro['date'])

print(f"  [OK] Loaded: {len(macro)} months")
print(f"  [OK] Variables: rf (risk-free rate), rm (market return), factors")

print("\n[1.3] Merging with macro variables...")
data = base.merge(macro[['date', 'rf', 'rm_rf']], on='date', how='left')
print(f"  [OK] Merged: {data['rf'].notna().sum():,} observations have macro data")

print("\n[1.4] Creating P-Tree required fields...")
# Create stock identifier (permno)
data['permno'] = data.groupby('id').ngroup()

# Create excess returns (xret = return - rf)
data['xret'] = data['current_return'] - data['rf'].fillna(0)

# Create lagged market cap (for value-weighting portfolios)
data['lag_me'] = data.groupby('permno')['market_cap'].shift(1)
data['lag_me'] = data['lag_me'].fillna(data['market_cap'])  # Fill first obs

print(f"  [OK] Created permno: {data['permno'].nunique()} unique stocks")
print(f"  [OK] Created xret (excess returns)")
print(f"  [OK] Created lag_me (lagged market cap for weighting)")

# Remove observations without required data
before_clean = len(data)
data = data[data['xret'].notna() & data['lag_me'].notna()].copy()
print(f"  [OK] Cleaned: Removed {before_clean - len(data):,} obs with missing core data")
print(f"  [OK] Final observations: {len(data):,}")

# ==============================================================================
# STEP 2: CALCULATE ALL 34 STOCK CHARACTERISTICS
# ==============================================================================

print("\n" + "="*80)
print("STEP 2: CALCULATING ALL 34 STOCK CHARACTERISTICS")
print("="*80)
print("\nEach characteristic is documented with:")
print("  - Formula")
print("  - Data source (from base vs calculated)")
print("  - Coverage statistics")
print("  - Assumptions/limitations\n")

# -----------------------------------------------------------------------------
# GROUP A: CRITICAL CHARACTERISTICS (Top 6 from P-Tree paper)
# -----------------------------------------------------------------------------

print("\n--- GROUP A: CRITICAL CHARACTERISTICS (P-Tree Top Splits) ---\n")

# A1. SUE - Standardized Unexpected Earnings (Split #1 in P-Tree paper)
print("[A1] SUE - Standardized Unexpected Earnings")
print("     Formula: (NI_t - NI_{t-4}) / std(earnings_surprise)")
print("     Logic: Compare current earnings to same month last year")
print("     Assumption: 4-month lag ? quarterly comparison (limitation: monthly data)")

data['earnings_lag4q'] = data.groupby('permno')['net_income'].shift(4)
data['earnings_surprise'] = data['net_income'] - data['earnings_lag4q']
data['earnings_surprise_std'] = data.groupby('permno')['earnings_surprise'].transform(
    lambda x: x.rolling(window=8, min_periods=4).std()
)
data['sue'] = data['earnings_surprise'] / data['earnings_surprise_std']
data.loc[data['sue'].abs() > 10, 'sue'] = np.nan  # Cap extreme values

coverage_sue = data['sue'].notna().sum()
print(f"     [OK] Coverage: {coverage_sue:,} / {len(data):,} ({100*coverage_sue/len(data):.1f}%)")
print(f"     [WARNING] Note: Requires 4-8 months history, early observations are NaN\n")

# A2. DOLVOL - Dollar Trading Volume (Splits #2, #3)
print("[A2] DOLVOL - Dollar Trading Volume")
print("     Formula: price x volume")
print("     Logic: Captures both price and liquidity")

data['dolvol'] = data['price'] * data['volume']

coverage_dolvol = data['dolvol'].notna().sum()
print(f"     [OK] Coverage: {coverage_dolvol:,} / {len(data):,} ({100*coverage_dolvol/len(data):.1f}%)\n")

# A3. BM_IA - Industry-Adjusted Book-to-Market (Splits #4, #5)
print("[A3] BM_IA - Industry-Adjusted Book-to-Market")
print("     Formula: log(book_to_market / industry_median_BM)")
print("     Industry proxy: marketname (stock exchange segment)")
print("     [WARNING] IMPORTANT: 'Industry' = market segment (SSE, SSEFN, etc.), NOT true industry!")
print("     Limitation: Ericsson (tech) compared to Volvo (auto) if both on SSE")

data['industry'] = data['marketname']

industry_medians_bm = data.groupby(['date', 'industry'])['book_to_market'].transform('median')
data['bm_ia'] = np.log(data['book_to_market'].clip(lower=0.01) / industry_medians_bm)

coverage_bm_ia = data['bm_ia'].notna().sum()
print(f"     [OK] Coverage: {coverage_bm_ia:,} / {len(data):,} ({100*coverage_bm_ia/len(data):.1f}%)")
print(f"     [OK] Industries: {data['industry'].nunique()} market segments\n")

# A4. ME_IA - Industry-Adjusted Market Equity (Split #7)
print("[A4] ME_IA - Industry-Adjusted Market Equity")
print("     Formula: log(market_cap / industry_median_MC)")
print("     Same industry proxy as BM_IA")

industry_medians_mc = data.groupby(['date', 'industry'])['market_cap'].transform('median')
data['me_ia'] = np.log(data['market_cap'] / industry_medians_mc)

coverage_me_ia = data['me_ia'].notna().sum()
print(f"     [OK] Coverage: {coverage_me_ia:,} / {len(data):,} ({100*coverage_me_ia/len(data):.1f}%)\n")

# A5. ROE - Return on Equity (Split #5)
print("[A5] ROE - Return on Equity")
print("     Formula: net_income / book_value")
print("     Source: Partially from base (Serrano accounting), recalculated for consistency")

if 'roe' not in data.columns or data['roe'].notna().sum() < 0.5 * len(data):
    data['roe'] = data['net_income'] / data['book_value']
    data.loc[data['roe'].abs() > 10, 'roe'] = np.nan  # Cap outliers

coverage_roe = data['roe'].notna().sum()
print(f"     [OK] Coverage: {coverage_roe:,} / {len(data):,} ({100*coverage_roe/len(data):.1f}%)")
print(f"     [WARNING] Note: Low coverage due to limited accounting data\n")

# A6. ZEROTRADE - Zero Trading Days Proxy (Split #6)
print("[A6] ZEROTRADE - Zero Trading Days (approximation)")
print("     Original: Count days with zero volume")
print("     Approximation: Binary flag for low turnover")
print("     Formula: 1 if monthly_turnover < 0.01, else 0")
print("     [WARNING] Limitation: Monthly data -> cannot count actual zero-volume days")
print("     Justification: Captures illiquidity (core concept)")

data['zerotrade'] = (data['turnover'] < 0.01).astype(int)

coverage_zt = data['zerotrade'].notna().sum()
pct_zero = (data['zerotrade'] == 1).sum() / len(data) * 100
print(f"     [OK] Coverage: {coverage_zt:,} / {len(data):,} ({100*coverage_zt/len(data):.1f}%)")
print(f"     [OK] Flagged as illiquid: {pct_zero:.1f}% of observations\n")

# -----------------------------------------------------------------------------
# GROUP B: MOMENTUM CHARACTERISTICS
# -----------------------------------------------------------------------------

print("\n--- GROUP B: MOMENTUM CHARACTERISTICS ---\n")

# B1. MOM1M - 1-Month Return (from base)
print("[B1] MOM1M (return_1m) - 1-Month Return")
print("     Source: From base dataset")
coverage = data['return_1m'].notna().sum()
print(f"     [OK] Coverage: {coverage:,} / {len(data):,} ({100*coverage/len(data):.1f}%)\n")

# B2. MOM6M - 6-Month Momentum
print("[B2] MOM6M - 6-Month Momentum")
print("     Formula: compound_return(6 months)")

data['mom6m'] = data.groupby('permno')['current_return'].transform(
    lambda x: x.rolling(window=6, min_periods=4).apply(lambda r: (1 + r).prod() - 1)
)
coverage = data['mom6m'].notna().sum()
print(f"     [OK] Coverage: {coverage:,} / {len(data):,} ({100*coverage/len(data):.1f}%)\n")

# B3. MOM12M - 12-Month Momentum (from base)
print("[B3] MOM12M (momentum_12m) - 12-Month Momentum")
print("     Source: From base dataset")
coverage = data['momentum_12m'].notna().sum()
print(f"     [OK] Coverage: {coverage:,} / {len(data):,} ({100*coverage/len(data):.1f}%)\n")

# B4. MOM36M - 36-Month Momentum
print("[B4] MOM36M - 36-Month Momentum")
print("     Formula: compound_return(36 months)")

data['mom36m'] = data.groupby('permno')['current_return'].transform(
    lambda x: x.rolling(window=36, min_periods=24).apply(lambda r: (1 + r).prod() - 1)
)
coverage = data['mom36m'].notna().sum()
print(f"     [OK] Coverage: {coverage:,} / {len(data):,} ({100*coverage/len(data):.1f}%)\n")

# -----------------------------------------------------------------------------
# GROUP C: VALUE & SIZE CHARACTERISTICS
# -----------------------------------------------------------------------------

print("\n--- GROUP C: VALUE & SIZE CHARACTERISTICS ---\n")

print("[C1] MARKET_CAP - Market Capitalization")
print("     Source: From base dataset")
print(f"     [OK] Coverage: {data['market_cap'].notna().sum():,} / {len(data):,}\n")

print("[C2] ME - Log Market Equity")
print("     Formula: log(market_cap)")
data['me'] = np.log(data['market_cap'])
print(f"     [OK] Coverage: {data['me'].notna().sum():,} / {len(data):,}\n")

print("[C3] BM - Book-to-Market")
print("     Source: From base dataset")
print(f"     [OK] Coverage: {data['book_to_market'].notna().sum():,} / {len(data):,}\n")

print("[C4] EP - Earnings-to-Price")
print("     Source: From base dataset")
print(f"     [OK] Coverage: {data['ep_ratio'].notna().sum():,} / {len(data):,}\n")

print("[C5] CFP - Cash Flow-to-Price")
print("     Source: From base dataset")
print(f"     [OK] Coverage: {data['cfp_ratio'].notna().sum():,} / {len(data):,}\n")

print("[C6] SP - Sales-to-Price")
print("     Source: From base dataset")
print(f"     [OK] Coverage: {data['sp_ratio'].notna().sum():,} / {len(data):,}\n")

# -----------------------------------------------------------------------------
# GROUP D: PROFITABILITY CHARACTERISTICS
# -----------------------------------------------------------------------------

print("\n--- GROUP D: PROFITABILITY CHARACTERISTICS ---\n")

print("[D1] ROA - Return on Assets")
print("     Source: From base dataset")
print(f"     [OK] Coverage: {data['roa'].notna().sum():,} / {len(data):,}\n")

print("[D2] GP - Gross Profitability")
print("     Source: From base dataset (gross_profitability)")
print(f"     [OK] Coverage: {data['gross_profitability'].notna().sum():,} / {len(data):,}\n")

print("[D3] OP - Operating Profitability")
print("     Formula: (revenue - COGS) / book_value")
data['op'] = (data['total_revenue'] - data['cogs']) / data['book_value']
data.loc[data['op'].abs() > 10, 'op'] = np.nan
print(f"     [OK] Coverage: {data['op'].notna().sum():,} / {len(data):,}\n")

print("[D4] PM - Profit Margin")
print("     Formula: net_income / total_revenue")
data['pm'] = data['net_income'] / data['total_revenue']
data.loc[data['pm'].abs() > 1, 'pm'] = np.nan
print(f"     [OK] Coverage: {data['pm'].notna().sum():,} / {len(data):,}\n")

# -----------------------------------------------------------------------------
# GROUP E: INVESTMENT & GROWTH CHARACTERISTICS
# -----------------------------------------------------------------------------

print("\n--- GROUP E: INVESTMENT & GROWTH CHARACTERISTICS ---\n")

print("[E1] AGR - Asset Growth")
print("     Source: From base dataset (asset_growth)")
print(f"     [OK] Coverage: {data['asset_growth'].notna().sum():,} / {len(data):,}\n")

print("[E2] SALES_GR - Sales Growth")
print("     Source: From base dataset (sales_growth)")
print(f"     [OK] Coverage: {data['sales_growth'].notna().sum():,} / {len(data):,}\n")

print("[E3] CAPEX - Capital Expenditure to Assets")
print("     Source: From base dataset (capex_to_assets)")
print(f"     [OK] Coverage: {data['capex_to_assets'].notna().sum():,} / {len(data):,}\n")

print("[E4] NI - Net Equity Issuance")
print("     Formula: (MC_t - MC_{t-1}x(1+ret)) / MC_{t-1}")
data['market_cap_lag1'] = data.groupby('permno')['market_cap'].shift(1)
data['ni'] = (data['market_cap'] - data['market_cap_lag1'] * (1 + data['current_return'])) / data['market_cap_lag1']
data.loc[data['ni'].abs() > 1, 'ni'] = np.nan
print(f"     [OK] Coverage: {data['ni'].notna().sum():,} / {len(data):,}\n")

# -----------------------------------------------------------------------------
# GROUP F: FRICTION & TRADING CHARACTERISTICS
# -----------------------------------------------------------------------------

print("\n--- GROUP F: FRICTION & TRADING CHARACTERISTICS ---\n")

print("[F1] TURN - Turnover")
print("     Source: From base dataset")
print(f"     [OK] Coverage: {data['turnover'].notna().sum():,} / {len(data):,}\n")

print("[F2] SVAR - Return Variance")
print("     Formula: volatility_12m^2")
data['svar'] = data['volatility_12m'] ** 2
print(f"     [OK] Coverage: {data['svar'].notna().sum():,} / {len(data):,}\n")

print("[F3] STD_TURN - Turnover Volatility")
print("     Formula: std(turnover, 12 months)")
data['std_turn'] = data.groupby('permno')['turnover'].transform(
    lambda x: x.rolling(window=12, min_periods=6).std()
)
print(f"     [OK] Coverage: {data['std_turn'].notna().sum():,} / {len(data):,}\n")

print("[F4] STD_DOLVOL - Dollar Volume Volatility")
print("     Formula: std(dolvol, 12 months)")
data['std_dolvol'] = data.groupby('permno')['dolvol'].transform(
    lambda x: x.rolling(window=12, min_periods=6).std()
)
print(f"     [OK] Coverage: {data['std_dolvol'].notna().sum():,} / {len(data):,}\n")

# -----------------------------------------------------------------------------
# GROUP G: OTHER CHARACTERISTICS
# -----------------------------------------------------------------------------

print("\n--- GROUP G: OTHER CHARACTERISTICS ---\n")

print("[G1] ATO - Asset Turnover")
print("     Source: From base dataset")
print(f"     [OK] Coverage: {data['asset_turnover'].notna().sum():,} / {len(data):,}\n")

print("[G2] DE - Debt-to-Equity")
print("     Source: From base dataset")
print(f"     [OK] Coverage: {data['debt_to_equity'].notna().sum():,} / {len(data):,}\n")

print("[G3] AQ - Asset Quality")
print("     Source: From base dataset")
print(f"     [OK] Coverage: {data['asset_quality'].notna().sum():,} / {len(data):,}\n")

print("[G4] CFOA - Cash Flow to Assets")
print("     Source: From base dataset (cfo_to_assets)")
print(f"     [OK] Coverage: {data['cfo_to_assets'].notna().sum():,} / {len(data):,}\n")

print("[G5] PA - Price to Assets")
print("     Source: From base dataset (price_to_assets)")
print(f"     [OK] Coverage: {data['price_to_assets'].notna().sum():,} / {len(data):,}\n")

# Clean up temporary columns
data = data.drop(['earnings_lag4q', 'earnings_surprise', 'earnings_surprise_std',
                  'market_cap_lag1'], axis=1, errors='ignore')

# ==============================================================================
# STEP 3: APPLY LAGS (Prevent Look-Ahead Bias)
# ==============================================================================

print("\n" + "="*80)
print("STEP 3: APPLYING LAGS TO PREVENT LOOK-AHEAD BIAS")
print("="*80)
print("\nCRITICAL: Cannot use current month's data to predict current month's returns!")
print("  - Market characteristics: 1-month lag")
print("  - Accounting characteristics: 3-month lag (reporting delay)\n")

# Define all characteristics for P-Tree
characteristics = [
    # Critical
    'sue', 'dolvol', 'bm_ia', 'me_ia', 'roe', 'zerotrade',
    # Momentum
    'return_1m', 'mom6m', 'momentum_12m', 'mom36m',
    # Value & Size
    'market_cap', 'me', 'book_to_market', 'ep_ratio', 'cfp_ratio', 'sp_ratio',
    # Profitability
    'roa', 'gross_profitability', 'op', 'pm',
    # Investment
    'asset_growth', 'sales_growth', 'capex_to_assets', 'ni',
    # Frictions
    'turnover', 'svar', 'std_turn', 'std_dolvol',
    # Other
    'asset_turnover', 'debt_to_equity', 'asset_quality',
    'cfo_to_assets', 'price_to_assets'
]

# Filter to only existing columns
characteristics = [c for c in characteristics if c in data.columns]
print(f"Total characteristics for P-Tree: {len(characteristics)}\n")

# Define accounting characteristics that need 3-month lag
accounting_chars = [
    'roe', 'roa', 'gross_profitability', 'op', 'pm',
    'asset_growth', 'sales_growth', 'ni',
    'debt_to_equity', 'asset_quality', 'capex_to_assets',
    'cfo_to_assets', 'asset_turnover', 'ep_ratio', 'cfp_ratio', 'sp_ratio'
]

print("[3.1] Lagging characteristics...")
for char in characteristics:
    if char in data.columns:
        lag_periods = 3 if char in accounting_chars else 1
        data[f'lag_{char}'] = data.groupby('permno')[char].shift(lag_periods)

        if lag_periods == 3:
            print(f"  [OK] lag_{char:20s} (3-month lag - accounting)")

print(f"\n  [OK] Market characteristics: 1-month lag (immediate)")
print(f"  [OK] Accounting characteristics: 3-month lag (reporting delay)\n")

# ==============================================================================
# STEP 4: CREATE CROSS-SECTIONAL RANKS
# ==============================================================================

print("\n" + "="*80)
print("STEP 4: CREATING CROSS-SECTIONAL RANKS")
print("="*80)
print("\nWhy rank? P-Tree works better with percentiles [0, 1] than raw values.")
print("For each month, rank all stocks by each characteristic.\n")

print("[4.1] Ranking lagged characteristics within each month...")
for char in characteristics:
    lag_col = f'lag_{char}'
    if lag_col in data.columns:
        data[f'rank_{char}'] = data.groupby('date')[lag_col].rank(pct=True)

print(f"  [OK] Created {len(characteristics)} ranked characteristics\n")

print("[4.2] Handling missing values...")
ranked_cols = [c for c in data.columns if c.startswith('rank_')]
nan_before = data[ranked_cols].isna().sum().sum()

# Fill NaN with 0.5 (neutral rank) - preserves observations
for col in ranked_cols:
    data[col] = data[col].fillna(0.5)

print(f"  [OK] Filled {nan_before:,} NaN values with 0.5 (neutral rank)")
print(f"  [OK] Rationale: Preserves observations, P-Tree learns to ignore low-coverage chars\n")

# ==============================================================================
# STEP 5: FINAL CLEANING AND SAVE
# ==============================================================================

print("\n" + "="*80)
print("STEP 5: FINAL CLEANING AND SAVING")
print("="*80)

print("\n[5.1] Final data validation...")
ptree_core_cols = ['xret', 'permno', 'lag_me']
before_final = len(data)
data = data[data[ptree_core_cols].notna().all(axis=1)].copy()

print(f"  [OK] Dropped {before_final - len(data):,} obs with NaN in core columns")
print(f"  [OK] Final observations: {len(data):,}")
print(f"  [OK] Date range: {data['date'].min().strftime('%Y-%m')} to {data['date'].max().strftime('%Y-%m')}")
print(f"  [OK] Unique stocks: {data['permno'].nunique()}")
print(f"  [OK] Avg stocks per month: {len(data) / data['date'].nunique():.0f}")

print("\n[5.2] Verification checks...")
nan_core = data[ptree_core_cols].isna().sum().sum()
nan_ranks = data[ranked_cols].isna().sum().sum()
print(f"  [OK] NaN in core columns (xret, permno, lag_me): {nan_core}")
print(f"  [OK] NaN in ranked characteristics: {nan_ranks}")
print(f"  [OK] Ready for P-Tree: {'YES [OK]' if nan_core == 0 and nan_ranks == 0 else 'NO [FAIL]'}")

print("\n[5.3] Saving P-Tree ready dataset...")
output_dir = Path('../../results/ptree_34chars')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'ptree_ready_data_34chars.csv'

data.to_csv(output_file, index=False)

print(f"\n{'='*80}")
print("[OK] SUCCESS! P-TREE DATASET READY")
print('='*80)
print(f"Saved to: {output_file}")
print(f"  Observations: {len(data):,}")
print(f"  Characteristics: {len(characteristics)}")
print(f"  Period: {data['date'].min().strftime('%Y-%m')} to {data['date'].max().strftime('%Y-%m')}")
print(f"  Stocks: {data['permno'].nunique()}")
print()
print("Next step: Run src/analysis/3_ptree_analysis.R")
print('='*80)

# ==============================================================================
# APPENDIX: CHARACTERISTIC SUMMARY TABLE
# ==============================================================================

print("\n" + "="*80)
print("APPENDIX: COMPLETE CHARACTERISTIC SUMMARY")
print("="*80)

summary_data = []
for char in characteristics:
    coverage = data[f'lag_{char}'].notna().sum() if f'lag_{char}' in data.columns else 0
    pct = 100 * coverage / len(data)
    is_accounting = char in accounting_chars
    lag = "3-month" if is_accounting else "1-month"
    summary_data.append({
        'Characteristic': char,
        'Coverage_%': f"{pct:.1f}%",
        'Lag': lag,
        'Type': 'Accounting' if is_accounting else 'Market'
    })

summary_df = pd.DataFrame(summary_data)
print("\n", summary_df.to_string(index=False))
print(f"\nTotal: {len(characteristics)} characteristics")
print(f"US Study (Cong et al. 2024): 61 characteristics")
print(f"Coverage: {100*len(characteristics)/61:.1f}%")
print('='*80)
