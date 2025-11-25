"""
================================================================================
STEP 3: PREPARE P-TREE DATASET WITH LAGS AND CHARACTERISTICS
================================================================================

PURPOSE:
--------
This script prepares the complete P-Tree dataset, applying 1-month lag to all
characteristics and creating cross-sectional ranks for P-Tree analysis.

INPUT FILES:
-----------
    - data/intermediate/stock_with_accounting.csv  (Stock + accounting, publication lag already applied)
    - data/raw/macro/macro_variables_with_dates.csv (Risk-free rate, market returns)

OUTPUT FILES:
------------
    - results/ptree_34chars/ptree_ready_data_34chars.csv    (P-Tree ready dataset)

PROCESS OVERVIEW:
----------------
    1. Load merged data (accounting publication timing already correct from Steps 1-2)
    2. Merge with macro data (risk-free rate)
    3. Calculate additional characteristics
    4. Apply 1-month lag to ALL characteristics (portfolio formation lag)
    5. Create cross-sectional ranks (percentiles within each month, scaled to [-1, 1])
    6. Save P-Tree ready dataset

KEY CONCEPTS:
------------
    PERMNO: Stock identifier (panel ID)
        - Why: Standard in finance literature (from CRSP database convention)
        - Created from 'isin' (unique stock identifier)
        - Usage: Group operations (rolling windows, lags) and panel identification
        - NOTE: Final dataset uses ONLY permno (drops isin, orgnr, id for simplicity)

    EXCESS RETURNS (xret): return - risk_free_rate
        - Why: Accounts for time value of money, what investors earn above safe rate
        - P-Tree predicts excess returns, not raw returns

    LAGGED MARKET CAP (lag_me): Previous month's market capitalization
        - Why: Value-weighted portfolios weight by t-1 market cap, not current
        - Prevents look-ahead bias (can't know current cap when forming portfolios)

    LAG STRUCTURE (SIMPLIFIED - CORRECT VERSION):
        - Accounting data: 4-month publication lag ALREADY APPLIED in Steps 1-2
          * Fiscal year 2011 (Dec 31) → Available April 2012
          * No additional lag needed here!
        - All characteristics: 1-month lag (standard portfolio formation)
          * Can't use month M data to predict month M returns
        - Total accounting lag: ~5 months from fiscal year-end (4m pub + 1m standard)

Author: Michael
Date: 2025-01-23 (Updated: 2025-11-25)
================================================================================
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Set up paths
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent

# ==============================================================================
# STEP 1: LOAD AND MERGE RAW DATA SOURCES
# ==============================================================================

print("\n[1] Loading merged stock + accounting data...")
# Load base stock market dataset (LSEG + Serrano accounting already merged with correct timing)
base = pd.read_csv(project_root / 'data/intermediate/stock_with_accounting.csv', low_memory=False)
base['date'] = pd.to_datetime(base['date'])

# Create PERMNO from ISIN (unique, stable stock identifier)
# PERMNO = Permanent Number (standard in finance from CRSP database)
# Sequential numbering (0, 1, 2...) is more efficient than string ISINs for groupby operations
base['permno'] = base.groupby('isin').ngroup()

# Sort by stock and date for proper lagging
base = base.sort_values(['permno', 'date'])

# Load macro variables (risk-free rate, market returns)
macro = pd.read_csv(project_root / 'data/raw/macro/macro_variables_with_dates.csv')
macro['date'] = pd.to_datetime(macro['date'])

# Merge with macro variables (left join to preserve all stock observations)
data = base.merge(macro[['date', 'rf', 'rm_rf']], on='date', how='left')
print(f"  Loaded: {len(data):,} observations, {data['permno'].nunique()} stocks")

# ==============================================================================
# STEP 2: CREATE P-TREE REQUIRED FIELDS
# ==============================================================================

print("\n[2] Calculating excess returns & characteristics...")
# EXCESS RETURNS: What investors earn above the risk-free rate
# xret = return - risk_free_rate (standard in asset pricing literature)
data['xret'] = data['current_return'] - data['rf'].fillna(0)

# Clean: Remove observations without required data
data = data[data['xret'].notna()].copy()

# ==============================================================================
# Calculate additional stock characteristics (raw values, no lags yet)
# ==============================================================================

# -----------------------------------------------------------------------------
# GROUP A: CRITICAL CHARACTERISTICS (Top splits in P-Tree paper)
# -----------------------------------------------------------------------------

# A1. SUE - Standardized Unexpected Earnings
# Formula: (earnings_t - earnings_{t-12}) / std(earnings_surprise)
data['earnings_lag1y'] = data.groupby('permno')['net_income'].shift(12)
data['earnings_surprise'] = data['net_income'] - data['earnings_lag1y']
data['earnings_surprise_std'] = data.groupby('permno')['earnings_surprise'].transform(
    lambda x: x.rolling(window=12, min_periods=6).std()
)
data['sue'] = data['earnings_surprise'] / data['earnings_surprise_std']
data.loc[data['sue'].abs() > 10, 'sue'] = np.nan  # Cap extreme outliers

# A2. DOLVOL - Dollar Trading Volume
data['dolvol'] = data['price'] * data['volume']

# A3. BM_IA - Industry-Adjusted Book-to-Market
data['industry'] = data['marketname']
industry_medians_bm = data.groupby(['date', 'industry'])['book_to_market'].transform('median')
data['bm_ia'] = np.log(data['book_to_market'].clip(lower=0.01) / industry_medians_bm)

# A4. ME_IA - Industry-Adjusted Market Equity
industry_medians_mc = data.groupby(['date', 'industry'])['market_cap'].transform('median')
data['me_ia'] = np.log(data['market_cap'] / industry_medians_mc)

# A5. ROE - Already in data from Serrano (use existing, don't recalculate)

# A6. ZEROTRADE - Zero Trading Days Proxy
data['zerotrade'] = (data['turnover'] < 0.01).astype(int)

# -----------------------------------------------------------------------------
# GROUP B: MOMENTUM CHARACTERISTICS
# -----------------------------------------------------------------------------

# B2. MOM6M - 6-Month Momentum
data['mom6m'] = data.groupby('permno')['current_return'].transform(
    lambda x: x.rolling(window=6, min_periods=4).apply(lambda r: (1 + r).prod() - 1)
)

# B4. MOM36M - 36-Month Momentum
data['mom36m'] = data.groupby('permno')['current_return'].transform(
    lambda x: x.rolling(window=36, min_periods=24).apply(lambda r: (1 + r).prod() - 1)
)

# -----------------------------------------------------------------------------
# GROUP C: VALUE & SIZE CHARACTERISTICS
# -----------------------------------------------------------------------------

# C2. ME - Log Market Equity
data['me'] = np.log(data['market_cap'])

# -----------------------------------------------------------------------------
# GROUP D: PROFITABILITY CHARACTERISTICS
# -----------------------------------------------------------------------------

# D3. OP - Operating Profitability
data['op'] = (data['total_revenue'] - data['cogs']) / data['book_value']
data.loc[data['op'].abs() > 10, 'op'] = np.nan

# D4. PM - Profit Margin
data['pm'] = data['net_income'] / data['total_revenue']
data.loc[data['pm'].abs() > 1, 'pm'] = np.nan

# -----------------------------------------------------------------------------
# GROUP E: INVESTMENT & GROWTH CHARACTERISTICS
# -----------------------------------------------------------------------------

# E4. NI - Net Equity Issuance
data['market_cap_lag1'] = data.groupby('permno')['market_cap'].shift(1)
data['ni'] = (data['market_cap'] - data['market_cap_lag1'] * (1 + data['current_return'])) / data['market_cap_lag1']
data.loc[data['ni'].abs() > 1, 'ni'] = np.nan

# -----------------------------------------------------------------------------
# GROUP F: FRICTION & TRADING CHARACTERISTICS
# -----------------------------------------------------------------------------

# F2. SVAR - Return Variance
data['svar'] = data['volatility_12m'] ** 2

# F3. STD_TURN - Turnover Volatility
data['std_turn'] = data.groupby('permno')['turnover'].transform(
    lambda x: x.rolling(window=12, min_periods=6).std()
)

# F4. STD_DOLVOL - Dollar Volume Volatility
data['std_dolvol'] = data.groupby('permno')['dolvol'].transform(
    lambda x: x.rolling(window=12, min_periods=6).std()
)

# Clean up temporary calculation columns
data = data.drop(['earnings_lag1y', 'earnings_surprise', 'earnings_surprise_std',
                  'market_cap_lag1', 'industry'], axis=1, errors='ignore')

print(f"  ✓ Characteristics calculated")

# ==============================================================================
# STEP 3: APPLY 1-MONTH LAG TO ALL CHARACTERISTICS
# ==============================================================================
"""
LAG STRATEGY:
-------------
Steps 1-2 already handle accounting publication timing:
  - Fiscal year 2011 (Dec 31) → Available April 2012 (4-month lag built-in)

Step 3 applies standard portfolio formation lag:
  - 1 month lag for ALL characteristics (can't use month M to predict month M)

TOTAL EFFECTIVE LAGS:
---------------------
- Market characteristics: 1 month
- Accounting characteristics: ~5 months (4m publication + 1m standard)
"""

print("\n[3] Applying 1-month portfolio formation lag...")

# Define all characteristics (both calculated and from base data)
characteristics = [
    # Critical (Group A)
    'sue', 'dolvol', 'bm_ia', 'me_ia', 'roe', 'zerotrade',
    # Momentum (Group B)
    'return_1m', 'mom6m', 'momentum_12m', 'mom36m',
    # Value & Size (Group C)
    'market_cap', 'me', 'book_to_market', 'ep_ratio', 'cfp_ratio', 'sp_ratio',
    # Profitability (Group D)
    'roa', 'gross_profitability', 'op', 'pm',
    # Investment (Group E)
    'asset_growth', 'sales_growth', 'capex_to_assets', 'ni',
    # Frictions (Group F)
    'turnover', 'svar', 'std_turn', 'std_dolvol',
    # Other (Group G)
    'asset_turnover', 'debt_to_equity', 'asset_quality',
    'cfo_to_assets', 'price_to_assets'
]

# Keep only characteristics that exist in the data
characteristics = [c for c in characteristics if c in data.columns]

# SHIFT(1): Lag ensures portfolio at time t uses only info from t-1 (prevents look-ahead)
# Example: March portfolio uses February characteristics
for char in characteristics:
    data[f'lag_{char}'] = data.groupby('permno')[char].shift(1)

# Create lag_me for portfolio weighting (fillna with current for first obs)
data['lag_me'] = data.groupby('permno')['market_cap'].shift(1).fillna(data['market_cap'])

print(f"  {len(characteristics)} characteristics lagged")

# ==============================================================================
# STEP 4: CREATE CROSS-SECTIONAL RANKS
# ==============================================================================
"""
WHY RANK?
---------
P-Tree works better with normalized ranks than raw values:
1. Scale invariance: $1M market cap and $100B market cap both become ranks in [-1, 1]
2. Handles outliers: Extreme values become high ranks, not extreme numbers
3. Consistent treatment: All characteristics on same scale [-1, 1]

RANKING PROCESS:
---------------
1. For each month, rank all stocks by each characteristic
2. Convert to percentiles [0, 1] using rank(pct=True)
3. Scale to [-1, 1] via: rank * 2 - 1
4. Fill missing with 0.0 (neutral rank)

MISSING VALUE HANDLING:
----------------------
Fill with 0.0 (neutral rank) rather than drop observations
- Rationale: Preserves observations, maximizes sample size
- P-Tree can learn to ignore low-coverage characteristics
- Alternative (dropping) would lose too many observations
"""

print("\n[4] Creating cross-sectional ranks...")

# RANK(pct=True): Convert to percentiles [0,1], then scale to [-1,1] via rank*2-1
# Why? P-Tree needs normalized inputs on same scale
# Example: Lowest stock = 0 → -1, Median = 0.5 → 0, Highest = 1 → 1
for char in characteristics:
    lag_col = f'lag_{char}'
    if lag_col in data.columns:
        data[f'rank_{char}'] = data.groupby('date')[lag_col].rank(pct=True) * 2 - 1

# FILLNA(0.0): Missing ranks become neutral rank (middle of [-1,1] scale)
# Rationale: Preserves sample size, P-Tree can learn to handle low-coverage chars
ranked_cols = [c for c in data.columns if c.startswith('rank_')]
for col in ranked_cols:
    data[col] = data[col].fillna(0.0)

print(f"  {len(ranked_cols)} ranked characteristics created")

# ==============================================================================
# STEP 5: FINAL VALIDATION AND SAVE
# ==============================================================================

print("\n[5] Final validation and save...")

# Final validation: Ensure core columns have no missing values
ptree_core_cols = ['xret', 'permno', 'lag_me']
data = data[data[ptree_core_cols].notna().all(axis=1)].copy()

# Select final columns for P-Tree dataset
# Keep only: permno, date, xret, lag_me, and all ranked characteristics
keep_cols = ['permno', 'date', 'year', 'month', 'xret', 'lag_me'] + ranked_cols
ptree_data = data[keep_cols].copy()

# Save P-Tree ready dataset
output_dir = project_root / 'results/ptree_34chars'
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'ptree_ready_data_34chars.csv'
ptree_data.to_csv(output_file, index=False)

# ==============================================================================
# SUMMARY STATISTICS
# ==============================================================================

print("\n" + "="*80)
print("P-TREE DATASET PREPARATION COMPLETE")
print("="*80)
print(f"\nOutput: {output_file}")
print(f"  Observations: {len(ptree_data):,}")
print(f"  Unique stocks: {ptree_data['permno'].nunique()}")
print(f"  Period: {ptree_data['date'].min().strftime('%Y-%m')} to {ptree_data['date'].max().strftime('%Y-%m')}")
print(f"  Characteristics: {len(characteristics)}")
print(f"  Avg stocks per month: {len(ptree_data) / ptree_data['date'].nunique():.0f}")

# Summary table of all characteristics
accounting_chars = ['roe', 'roa']  # Serrano accounting in our dataset

summary_data = []
for char in characteristics:
    coverage = data[f'lag_{char}'].notna().sum() if f'lag_{char}' in data.columns else 0
    pct = 100 * coverage / len(data)

    if char in accounting_chars:
        lag = "~5m (4m pub + 1m)"
        char_type = "Accounting"
    else:
        lag = "1m"
        char_type = "Market"

    summary_data.append({
        'Characteristic': char,
        'Coverage_%': f"{pct:.1f}%",
        'Total_Lag': lag,
        'Type': char_type
    })

summary_df = pd.DataFrame(summary_data)
print("\nCHARACTERISTIC SUMMARY:")
print(summary_df.to_string(index=False))
print(f"\nTotal: {len(characteristics)} characteristics")
print(f"Lag structure: Market=1m, Accounting=~5m (4m publication via Steps 1-2 + 1m standard)")
print("\nFinal columns: permno, date, year, month, xret, lag_me, rank_* (ranks only)")
print("="*80)
