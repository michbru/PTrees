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
    - results/ptree_33chars/ptree_ready_data_33chars.csv    (P-Tree ready dataset)

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

ASSUMPTIONS & LIMITATIONS:
-------------------------
    1. LAG STRUCTURE (CRITICAL FOR PREVENTING LOOK-AHEAD BIAS):

       A. Serrano Accounting (from Steps 1-2):
          - Publication lag: 4 months (applied in Step 1)
          - Portfolio formation lag: 1 month (applied here via shift(1))
          - Total lag: ~5 months from fiscal year-end
          - Example: Fiscal 2011 (Dec 31) → First tradeable May 2012

       B. LSEG Accounting (applied here in Step 1.5):
          - LSEG timing: Annual reports appear in January (~1 month native lag)
          - Additional shift(4): Adds 4 more months for consistency
          - Portfolio formation lag: 1 month (applied via shift(1))
          - Total lag: ~6 months (1m native + 4m adjustment + 1m formation)
          - Rationale: Being MORE conservative than Serrano is acceptable

       C. Market Characteristics (prices, returns, volume):
          - No publication lag needed (observable in real-time)
          - Only portfolio formation lag: 1 month (shift(1))
          - Example: March market cap → used in April portfolio

       D. Price-Based Accounting Ratios (B/M, E/P, etc.):
          - Numerator (accounting): Shifted by shift(4) + shift(1)
          - Denominator (market cap): Current period
          - Recalculated after shifts to maintain ratio correctness
          - This ensures we use latest price with available accounting only

    2. CROSS-SECTIONAL RANKING:
       - Ranks computed within each month (cross-sectional)
       - Scaled to [-1, 1] via: rank(pct=True) * 2 - 1
       - Missing values filled with 0.0 (neutral rank, middle of scale)
       - Rationale: P-Tree handles scale better with normalized inputs

    3. MISSING DATA STRATEGY:
       - Characteristics: Fill with 0.0 rank (neutral, not informative)
       - Alternative (dropping) would lose too many observations
       - P-Tree can learn to ignore low-coverage characteristics
       - Coverage stats printed at end to monitor data quality

    4. INDUSTRY ADJUSTMENT:
       - Originally attempted industry-adjusted B/M and market cap
       - REMOVED: data['marketname'] is exchange (SSE, NGM), not industry
       - Proper industry classification (GICS, ICB) not available in dataset
       - Using raw characteristics instead (book_to_market, market_cap)

    5. CHARACTERISTICS CALCULATION:
       - Momentum: Compound returns using (1+r).prod()-1 (handles negatives)
       - SUE: Standardized by rolling std, capped at ±10 (outlier control)
       - Profit margin: Capped at ±100% (outlier control)
       - Net issuance: Uses market cap changes (investor perspective), not book equity

    6. FORWARD-FILL FROM STEP 2:
       - Serrano data forward-filled within stocks (from Step 2)
       - Represents real information availability (stale but valid)
       - Shift(1) here operates on forward-filled data (correct)

VERIFICATION STATUS (2025-01-26):
    ✓ shift(1) verified to correctly create lag_me and lag_roe
    ✓ LSEG shift(4) adds ~1 month extra lag vs Serrano (acceptable/conservative)
    ✓ Ranking verified to scale [-1, 1] with 0.0 for missing
    ✓ Total lag structure: Serrano ~5 months, LSEG ~6 months, Market 1 month

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
# STEP 1.5: APPLY PUBLICATION LAG TO LSEG ACCOUNTING DATA
# ==============================================================================
print("\n[1.5] Applying 4-month publication lag to LSEG accounting data...")
# LSEG data often aligns to fiscal year-end (e.g., Jan 2012 has 2011 annual data)
# We must shift it to simulate publication delay (approx 4 months)

# 1. Shift Raw Inputs (used for calculations)
lseg_raw_cols = ['total_revenue', 'net_income', 'book_value', 'cogs', 
                 'total_assets', 'capex', 'cfo']
for col in lseg_raw_cols:
    if col in data.columns:
        data[col] = data.groupby('permno')[col].shift(4)

# 2. Shift Pre-calculated Ratios (Pure Accounting)
lseg_ratios = ['gross_profitability', 'asset_growth', 'sales_growth', 
               'capex_to_assets', 'asset_turnover', 'asset_quality', 
               'cfo_to_assets', 'roa', 'debt_to_equity', 'price_to_assets']
for col in lseg_ratios:
    if col in data.columns:
        data[col] = data.groupby('permno')[col].shift(4)

# 3. Recalculate Price-based Ratios (Shifted Accounting / Current Market Cap)
# This ensures we use the latest price but only available accounting info

if 'book_value' in data.columns and 'market_cap' in data.columns:
    data['book_to_market'] = data['book_value'] / data['market_cap']

if 'net_income' in data.columns and 'market_cap' in data.columns:
    data['ep_ratio'] = data['net_income'] / data['market_cap']

if 'cfo' in data.columns and 'market_cap' in data.columns:
    data['cfp_ratio'] = data['cfo'] / data['market_cap']

if 'total_revenue' in data.columns and 'market_cap' in data.columns:
    data['sp_ratio'] = data['total_revenue'] / data['market_cap']

print(f"  [OK] Applied 4-month lag to LSEG accounting variables")

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

# A3. BM_IA - REMOVED (marketname is exchange, not industry)
# NOTE: Original implementation used data['marketname'] as industry classifier,
# but marketname represents stock exchange (SSE, NGM, SSEFN, etc.), not industry sector.
# Industry adjustment would require proper industry classification (GICS, ICB, etc.)
# For now, we use raw book_to_market instead.

# A4. ME_IA - REMOVED (same reason as BM_IA)

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
# Calculate only where we have valid data (avoid 96.5% zeros issue)
has_valid_op = (
    data['total_revenue'].notna() &
    data['cogs'].notna() &
    data['book_value'].notna() &
    (data['book_value'] > 0)
)
data['op'] = np.nan  # Start with all NaN
data.loc[has_valid_op, 'op'] = (
    (data.loc[has_valid_op, 'total_revenue'] - data.loc[has_valid_op, 'cogs']) /
    data.loc[has_valid_op, 'book_value']
)
data.loc[data['op'].abs() > 10, 'op'] = np.nan  # Cap outliers

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

# -----------------------------------------------------------------------------
# GROUP G: SERRANO-DERIVED CHARACTERISTICS (Enhancement)
# -----------------------------------------------------------------------------

# G1. DEBT_TO_EQUITY - Leverage
# If not already present, calculate from Serrano ratios
if 'debt_to_equity' not in data.columns and 'debt_ratio' in data.columns and 'equity_ratio' in data.columns:
    data['debt_to_equity'] = data['debt_ratio'] / data['equity_ratio']

# Clean up temporary calculation columns
data = data.drop(['earnings_lag1y', 'earnings_surprise', 'earnings_surprise_std',
                  'market_cap_lag1'], axis=1, errors='ignore')

print(f"  [OK] Characteristics calculated")

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
    'sue', 'dolvol', 'roe', 'zerotrade',  # Removed: bm_ia, me_ia (exchange, not industry)
    # Momentum (Group B)
    'return_1m', 'mom6m', 'momentum_12m', 'mom36m',
    # Value & Size (Group C)
    'market_cap', 'me', 'book_to_market', 'ep_ratio', 'cfp_ratio', 'sp_ratio',
    # Profitability (Group D)
    'roa_serrano', 'gross_profitability', 'op', 'pm',  # Use Serrano ROA for consistency
    # Serrano Additional Accounting (High Quality)
    'operating_margin', 'net_margin', 'cash_liquidity', 'equity_ratio', 
    'debt_ratio', 'capital_turnover', 'inventory_turnover', 
    'receivables_turnover', 'revenue_per_employee', 'profit_pct',
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
output_dir = project_root / 'results/ptree_33chars'
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'ptree_ready_data_33chars.csv'
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
accounting_chars = ['roe', 'roa_serrano']  # Serrano accounting in our dataset

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
