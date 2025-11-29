"""
Step 6: Prepare P-Tree Dataset with Proper Lagging
===================================================
Calculate all 50 characteristics with proper lagging according to VARIABLE_REGISTRY.

Lagging Strategy (from VARIABLE_REGISTRY):
- "none": Use data up to month-end t (22 characteristics)
- "1 year (accounting)": Shift accounting by 12 months (25 characteristics)
- "1 year (accounting) + 1 month (market)": Shift accounting by 12, market_cap by 1 (3 characteristics)

Input:
  - data/processed/merged_data_daily.csv

Output:
  - data/processed/ptree_dataset_monthly.csv (monthly with all characteristics)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Paths
INPUT_PATH = Path('data/processed/merged_data_daily.csv')
OUTPUT_PATH = Path('data/processed/ptree_dataset_monthly.csv')


def safe_div(numer, denom, eps: float = 1e-12):
    """Safe elementwise division: returns NaN where denom is near zero or non-finite.

    Supports pandas Series or numpy arrays. Keeps shape.
    """
    num = pd.to_numeric(numer, errors='coerce') if isinstance(numer, pd.Series) else numer
    den = pd.to_numeric(denom, errors='coerce') if isinstance(denom, pd.Series) else denom
    with np.errstate(divide='ignore', invalid='ignore'):
        out = num / den
        if isinstance(out, pd.Series):
            mask = (~np.isfinite(out)) | (np.abs(den) < eps)
            out = out.mask(mask)
        else:
            mask = (~np.isfinite(out)) | (np.abs(den) < eps)
            out[mask] = np.nan
    return out

def calculate_daily_characteristics(df):
    """
    Calculate characteristics from daily data that need to be aggregated to monthly.

    These require 3-month rolling windows on daily data:
    - ZEROTRADE, BASPREAD, DOLVOL, ILL, MAXRET, SVAR, STD_DOLVOL, STD_TURN, TURN
    """
    print("  Calculating daily-based characteristics (3-month windows)...")

    df = df.sort_values(['isin', 'date'])

    # Calculate daily returns if not already present
    if 'ret' not in df.columns or df['ret'].isna().all():
        df['ret'] = df.groupby('isin')['close'].pct_change()

    # ZEROTRADE: Fraction of zero-volume days
    df['zero_volume'] = (df['volume'] == 0).astype(int)
    df['ZEROTRADE'] = df.groupby('isin')['zero_volume'].transform(
        lambda x: x.rolling(window=63, min_periods=20).mean()  # ~3 months of trading days
    )

    # BASPREAD: Bid-ask spread
    df['spread'] = (df['ask'] - df['bid']) / ((df['ask'] + df['bid']) / 2)
    df['BASPREAD'] = df.groupby('isin')['spread'].transform(
        lambda x: x.rolling(window=63, min_periods=20).mean()
    )

    # DOLVOL: Log of average dollar volume
    df['DOLVOL'] = df.groupby('isin')['turnover_sek'].transform(
        lambda x: np.log(x.rolling(window=63, min_periods=20).mean() + 1)
    )

    # ILL: Amihud illiquidity
    df['illiq_daily'] = np.abs(df['ret']) / (df['turnover_sek'] + 1) * 1e6
    df['ILL'] = df.groupby('isin')['illiq_daily'].transform(
        lambda x: x.rolling(window=63, min_periods=20).mean()
    )

    # MAXRET: Maximum daily return
    df['MAXRET'] = df.groupby('isin')['ret'].transform(
        lambda x: x.rolling(window=63, min_periods=20).max()
    )

    # SVAR: Return variance
    df['SVAR'] = df.groupby('isin')['ret'].transform(
        lambda x: x.rolling(window=63, min_periods=20).var()
    )

    # STD_DOLVOL: Std of log dollar volume
    df['log_dolvol'] = np.log(df['turnover_sek'] + 1)
    df['STD_DOLVOL'] = df.groupby('isin')['log_dolvol'].transform(
        lambda x: x.rolling(window=63, min_periods=20).std()
    )

    # TURN: Share turnover
    # Use market_cap_filled (forward-filled) instead of market_cap for better coverage
    market_cap_col = 'market_cap_filled' if 'market_cap_filled' in df.columns else 'market_cap'
    df['shares_out'] = df[market_cap_col] / df['close']
    df['daily_turn'] = df['volume'] / df['shares_out']
    df['TURN'] = df.groupby('isin')['daily_turn'].transform(
        lambda x: x.rolling(window=63, min_periods=20).mean()
    )

    # STD_TURN: Std of turnover
    df['STD_TURN'] = df.groupby('isin')['daily_turn'].transform(
        lambda x: x.rolling(window=63, min_periods=20).std()
    )

    print(f"    Calculated 9 daily-based characteristics")

    return df

def detect_and_adjust_splits(df):
    """
    Detect stock splits/reverse splits in daily data and mark affected months.

    Strategy:
    - Detect single-day price changes > 200% (likely splits)
    - These are NOT real returns but corporate actions
    - We'll flag these for later removal from monthly returns
    """
    print("  Detecting stock splits/reverse splits...")

    df = df.sort_values(['isin', 'date'])

    # Calculate daily returns
    df['daily_ret'] = df.groupby('isin')['close'].pct_change()

    # Flag extreme single-day moves (likely splits/reverse splits)
    # Use 200% threshold (3x price change) to catch splits
    split_threshold = 2.0
    df['potential_split'] = df['daily_ret'].abs() > split_threshold

    splits_detected = df['potential_split'].sum()

    if splits_detected > 0:
        print(f"    Detected {splits_detected:,} potential split events")
        print(f"    These will be excluded from return calculations")

        # Show some examples
        split_examples = df[df['potential_split']][['isin', 'date', 'close', 'daily_ret']].head(5)
        print(f"\n    Example split events:")
        for _, row in split_examples.iterrows():
            print(f"      {row['isin']} on {row['date'].strftime('%Y-%m-%d')}: {row['daily_ret']:.1%} price change")
    else:
        print(f"    No splits detected (good!)")

    return df

def aggregate_to_monthly(df):
    """Aggregate daily to monthly (month-end)."""
    print("  Aggregating to monthly...")

    df = df.sort_values(['isin', 'date'])
    df['year_month'] = df['date'].dt.to_period('M')

    # Detect splits BEFORE aggregating
    df = detect_and_adjust_splits(df)

    # Take last trading day of each month
    df_monthly = df.groupby(['isin', 'year_month']).last().reset_index()

    # CRITICAL FIX: Align all dates to actual month-end
    # This ensures all stocks in the same month share the same date,
    # preventing PTrees from treating each unique date as a separate time period
    print("  Aligning all dates to month-end...")
    df_monthly['date'] = df_monthly['date'] + pd.offsets.MonthEnd(0)

    # Verify alignment
    dates_before = df_monthly['year_month'].nunique()
    dates_after = df_monthly['date'].nunique()
    print(f"    Year-months: {dates_before}, Unique dates after alignment: {dates_after}")
    if dates_after > dates_before:
        print(f"    WARNING: Still have {dates_after - dates_before} extra dates after alignment!")

    # Ensure market_cap present: fill with market_cap_filled if available
    if 'market_cap' in df_monthly.columns and 'market_cap_filled' in df_monthly.columns:
        df_monthly['market_cap'] = df_monthly['market_cap'].fillna(df_monthly['market_cap_filled'])

    # Calculate monthly returns
    print("  Calculating monthly returns...")
    df_monthly = df_monthly.sort_values(['isin', 'date'])
    df_monthly['ret_monthly'] = df_monthly.groupby('isin')['close'].pct_change()

    # ADDITIONAL SPLIT DETECTION: Check for extreme monthly returns
    # These indicate splits that happened on last day of month
    print("  Detecting splits via extreme monthly returns...")
    monthly_split_threshold = 0.99  # 99% monthly return (likely split/data error)
    extreme_monthly = df_monthly['ret_monthly'].abs() > monthly_split_threshold

    # Combine with daily split detection
    if 'potential_split' in df_monthly.columns:
        total_splits = df_monthly['potential_split'] | extreme_monthly
    else:
        total_splits = extreme_monthly

    split_count = total_splits.sum()
    if split_count > 0:
        print(f"    Detected {split_count:,} total split/data error events")
        print(f"    Setting these monthly returns to NaN")

        # Show some examples before removing
        examples = df_monthly[total_splits][['isin', 'date', 'ret_monthly', 'market_cap']].head(5)
        print(f"\n    Example split-affected returns:")
        for _, row in examples.iterrows():
            print(f"      {row['isin']} on {row['date'].strftime('%Y-%m-%d')}: {row['ret_monthly']:.2%}")

        df_monthly.loc[total_splits, 'ret_monthly'] = np.nan

    print(f"    Monthly observations: {len(df_monthly):,}")
    return df_monthly

def _months_between(date_a: pd.Series, date_b: pd.Series) -> pd.Series:
    """Whole months difference: date_a - date_b (>= 0 when a >= b)."""
    return (date_a.dt.year - date_b.dt.year) * 12 + (date_a.dt.month - date_b.dt.month)


def apply_publication_lag(df, pub_lag_months: int = 6):
    """Apply publication lag to accounting vars and 1-month lag to market cap.

    Logic:
    - df contains monthly rows with accounting variables already aligned to the latest
      fiscal_year_end <= date (from Step 5 as-of merge, i.e., no lag).
    - For each month, if months_since_fye >= pub_lag_months, use current FY values;
      else use previous FY values for accounting variables.
    - This avoids double-lagging and enforces a realistic publication lag.
    """
    print(f"  Applying publication lag (accounting: {pub_lag_months} months, market_cap: 1 month)...")

    df = df.sort_values(['isin', 'date']).copy()

    # Ensure fiscal_year is integer
    if 'fiscal_year' in df.columns:
        df['fiscal_year'] = pd.to_numeric(df['fiscal_year'], errors='coerce').astype('Int64')

    # Market cap 1-month lag for ratios/weights
    if 'market_cap' in df.columns:
        df['market_cap_lag1'] = df.groupby('isin')['market_cap'].shift(1)
    elif 'market_cap_filled' in df.columns:
        # Fallback if only filled variant exists
        df['market_cap_lag1'] = df.groupby('isin')['market_cap_filled'].shift(1)

    # Publication-lagged accounting variables
    accounting_vars = [
        'sales', 'cogs_materials', 'cogs_goods', 'personnel_expense',
        'depreciation', 'operating_income', 'interest_income', 'interest_expense',
        'tax_expense', 'net_income', 'total_assets', 'fixed_assets',
        'intangible_assets', 'tangible_assets', 'ppe_buildings', 'ppe_machinery',
        'current_assets', 'inventory', 'cash', 'receivables', 'book_equity',
        'share_capital', 'long_term_debt', 'current_liabilities', 'accounts_payable',
        'num_employees'
    ]

    if 'fiscal_year_end' not in df.columns:
        raise ValueError("fiscal_year_end missing; Step 5 output expected.")

    # Compute months since fiscal year end
    df['months_since_fye'] = _months_between(df['date'], df['fiscal_year_end'])

    # Build FY-level frames to get previous-FY values per ISIN
    # We take the last value within each (isin, fiscal_year) group (constant within FY segment)
    base_cols = ['isin', 'fiscal_year'] + [col for col in accounting_vars if col in df.columns]
    df_fy = df[base_cols].dropna(subset=['fiscal_year']).copy()
    df_fy = df_fy.groupby(['isin', 'fiscal_year']).last().reset_index()
    # For each var, compute previous FY value by group-wise shift
    df_fy = df_fy.sort_values(['isin', 'fiscal_year'])
    for var in accounting_vars:
        if var in df_fy.columns:
            df_fy[f'{var}_prev_fy'] = df_fy.groupby('isin')[var].shift(1)

    # Merge FY-level previous values back to monthly df
    df = df.merge(
        df_fy[['isin', 'fiscal_year'] + [f'{v}_prev_fy' for v in accounting_vars if f'{v}_prev_fy' in df_fy.columns]],
        on=['isin', 'fiscal_year'], how='left'
    )

    # Choose current vs previous FY according to publication lag
    for var in accounting_vars:
        if var in df.columns:
            prev_col = f'{var}_prev_fy'
            pub_col = f'{var}_pub'
            if prev_col in df.columns:
                df[pub_col] = np.where(df['months_since_fye'] >= pub_lag_months, df[var], df[prev_col])

    rows_with_acct = df[[f'{v}_pub' for v in accounting_vars if f'{v}_pub' in df.columns]].notna().any(axis=1).sum()
    print(f"    Rows with publication-lagged accounting: {rows_with_acct:,} ({rows_with_acct/len(df)*100:.1f}%)")

    # Verification (representative variable: sales)
    if {'sales', 'sales_prev_fy', 'sales_pub'}.issubset(df.columns):
        cond_prev = df['months_since_fye'] < pub_lag_months
        # Only compare where both sides are non-null
        prev_mask = cond_prev & df['sales_prev_fy'].notna() & df['sales_pub'].notna()
        cur_mask = (~cond_prev) & df['sales'].notna() & df['sales_pub'].notna()
        prev_eq = np.isclose(df.loc[prev_mask, 'sales_pub'], df.loc[prev_mask, 'sales_prev_fy'], rtol=1e-6, atol=1e-8)
        cur_eq = np.isclose(df.loc[cur_mask, 'sales_pub'], df.loc[cur_mask, 'sales'], rtol=1e-6, atol=1e-8)
        prev_share = prev_eq.mean() * 100 if prev_mask.sum() > 0 else float('nan')
        cur_share = cur_eq.mean() * 100 if cur_mask.sum() > 0 else float('nan')
        print(f"    Pub-lag check (sales): prev-FY used agreement {prev_share:.1f}% | current-FY used agreement {cur_share:.1f}%")

    return df

def calculate_momentum_chars(df):
    """Calculate momentum characteristics (lag=none, except skip t-1 for some)."""
    print("  Calculating momentum characteristics...")

    df = df.sort_values(['isin', 'date'])

    # Price lags for momentum
    for lag in [1, 2, 6, 12, 13, 36, 60]:
        df[f'close_lag{lag}'] = df.groupby('isin')['close'].shift(lag)

    # MOM1M: Previous month return
    df['MOM1M'] = df.groupby('isin')['ret_monthly'].shift(1)

    # MOM6M: t-6 to t-2 (skip t-1)
    df['MOM6M'] = (df['close_lag2'] / df['close_lag6']) - 1

    # MOM12M: t-12 to t-2
    df['MOM12M'] = (df['close_lag2'] / df['close_lag12']) - 1

    # MOM36M: t-36 to t-13
    df['MOM36M'] = (df['close_lag13'] / df['close_lag36']) - 1

    # MOM60M: t-60 to t-13
    df['MOM60M'] = (df['close_lag13'] / df['close_lag60']) - 1

    # SEAS1A: Same month last year
    df['SEAS1A'] = df.groupby('isin')['ret_monthly'].shift(12)

    # CHTX: Change in tax expense (YoY on publication-lagged series)
    if 'tax_expense_pub' in df.columns:
        df['CHTX'] = df.groupby('isin')['tax_expense_pub'].pct_change(12)

    # DEPR: Depreciation rate (publication-lagged)
    if ('ppe_buildings_pub' in df.columns) or ('ppe_machinery_pub' in df.columns):
        df['ppe_pub'] = df.get('ppe_buildings_pub', 0).fillna(0) + df.get('ppe_machinery_pub', 0).fillna(0)
    if 'depreciation_pub' in df.columns and 'ppe_pub' in df.columns:
        df['DEPR'] = safe_div(df['depreciation_pub'], df['ppe_pub'])

    return df

def calculate_value_chars(df):
    """Calculate value characteristics."""
    print("  Calculating value characteristics...")

    # Helper for safe division
    # BM: Book-to-Market using Serrano book equity (publication-lagged) and lagged market cap
    if 'book_equity_pub' in df.columns:
        df['BM'] = safe_div(df['book_equity_pub'], df['market_cap_lag1'])

    # EP, SP, CFP: Use lagged accounting + lagged market cap
    if 'net_income_pub' in df.columns:
        df['EP'] = safe_div(df['net_income_pub'], df['market_cap_lag1'])
    if 'sales_pub' in df.columns:
        df['SP'] = safe_div(df['sales_pub'], df['market_cap_lag1'])

    # CFP: Operating cash flow approximation
    if 'net_income_pub' in df.columns and 'depreciation_pub' in df.columns:
        df['operating_cashflow'] = df['net_income_pub'] + df['depreciation_pub']
        df['CFP'] = safe_div(df['operating_cashflow'], df['market_cap_lag1'])

    # Pure accounting ratios
    if 'cash_pub' in df.columns and 'total_assets_pub' in df.columns:
        df['CASH'] = safe_div(df['cash_pub'], df['total_assets_pub'])

    if 'long_term_debt_pub' in df.columns and 'current_liabilities_pub' in df.columns:
        df['total_debt_pub'] = df['long_term_debt_pub'] + df['current_liabilities_pub']
        if 'cash_pub' in df.columns:
            df['CASHDEBT'] = safe_div(df['cash_pub'], df['total_debt_pub'])

    if 'total_debt_pub' in df.columns and 'total_assets_pub' in df.columns:
        df['LEV'] = safe_div(df['total_debt_pub'], df['total_assets_pub'])

    if 'sales_pub' in df.columns:
        df['SGR'] = df.groupby('isin')['sales_pub'].pct_change(12)

    return df

def calculate_investment_chars(df):
    """Calculate investment characteristics."""
    print("  Calculating investment characteristics...")

    # AGR: Asset growth
    if 'total_assets_pub' in df.columns:
        df['AGR'] = df.groupby('isin')['total_assets_pub'].pct_change(12)

    # GMA: Gross profitability
    if ('cogs_materials_pub' in df.columns) or ('cogs_goods_pub' in df.columns):
        df['cogs_total'] = df.get('cogs_materials_pub', 0).fillna(0) + df.get('cogs_goods_pub', 0).fillna(0)
    if 'sales_pub' in df.columns:
        df['gross_profit'] = df['sales_pub'] - df['cogs_total']
    if 'total_assets_pub' in df.columns:
        df['GMA'] = safe_div(df['gross_profit'], df['total_assets_pub'])

    # LGR: Long-term debt growth
    if 'long_term_debt_pub' in df.columns:
        df['LGR'] = df.groupby('isin')['long_term_debt_pub'].pct_change(12)

    # ACC: Operating accruals
    if 'current_assets_pub' in df.columns and 'current_liabilities_pub' in df.columns:
        df['working_capital'] = df['current_assets_pub'] - df['current_liabilities_pub']
        df['wc_lag12'] = df.groupby('isin')['working_capital'].shift(12)
        df['delta_wc'] = df['working_capital'] - df['wc_lag12']
    if 'total_assets_pub' in df.columns:
        df['total_assets_pub_lag12'] = df.groupby('isin')['total_assets_pub'].shift(12)
        df['total_assets_pub_lag24'] = df.groupby('isin')['total_assets_pub'].shift(24)
        df['avg_assets'] = (df['total_assets_pub'] + df['total_assets_pub_lag12']) / 2
    if 'depreciation_pub' in df.columns and 'avg_assets' in df.columns:
        df['ACC'] = safe_div(df['delta_wc'] - df['depreciation_pub'], df['avg_assets'])

    # CHCSHO: Change in shares outstanding
    mkt_col = 'market_cap'
    if mkt_col not in df.columns and 'market_cap_filled' in df.columns:
        mkt_col = 'market_cap_filled'
    df['shares'] = safe_div(df[mkt_col], df['close'])
    df['shares_lag12'] = df.groupby('isin')['shares'].shift(12)
    df['CHCSHO'] = (df['shares'] - df['shares_lag12']) / df['shares_lag12']

    # NI: Net equity issuance
    df['NI'] = np.log(df['shares'] / df['shares_lag12'])

    # NOA: Net operating assets
    if 'total_assets_pub' in df.columns and 'cash_pub' in df.columns:
        df['operating_assets'] = df['total_assets_pub'] - df['cash_pub']
    if 'book_equity_pub' in df.columns and 'long_term_debt_pub' in df.columns:
        df['operating_liabilities'] = df['total_assets_pub'] - df['book_equity_pub'] - df['long_term_debt_pub']
    if 'total_assets_pub_lag24' in df.columns:
        df['NOA'] = safe_div(df['operating_assets'] - df['operating_liabilities'], df['total_assets_pub_lag24'])

    # PCTACC: Percent accruals
    if 'ACC' in df.columns and 'avg_assets' in df.columns and 'net_income_pub' in df.columns:
        df['PCTACC'] = safe_div(df['ACC'] * df['avg_assets'], np.abs(df['net_income_pub']))

    # CINVEST: Corporate investment (change in capex / lagged PPE)
    # Approximation: change in PPE / lagged PPE
    # ppe_lag12 was already calculated in momentum_chars
    if 'ppe_pub' in df.columns:
        df['ppe_pub_lag12'] = df.groupby('isin')['ppe_pub'].shift(12)
        df['CINVEST'] = safe_div(df['ppe_pub'] - df['ppe_pub_lag12'], df['ppe_pub_lag12'])

    # GRLTNOA: Growth in long-term NOA (simplified version)
    if 'NOA' in df.columns:
        df['GRLTNOA'] = df.groupby('isin')['NOA'].pct_change(12)

    return df

def calculate_profitability_chars(df):
    """Calculate profitability characteristics."""
    print("  Calculating profitability characteristics...")

    if 'net_income_pub' in df.columns and 'total_assets_pub' in df.columns:
        df['ROA'] = safe_div(df['net_income_pub'], df['total_assets_pub'])
    if 'net_income_pub' in df.columns and 'book_equity_pub' in df.columns:
        df['ROE'] = safe_div(df['net_income_pub'], df['book_equity_pub'])
    if 'sales_pub' in df.columns and 'avg_assets' in df.columns:
        df['ATO'] = safe_div(df['sales_pub'], df['avg_assets'])
    if 'net_income_pub' in df.columns and 'sales_pub' in df.columns:
        df['PM'] = safe_div(df['net_income_pub'], df['sales_pub'])

    # CHPM: Change in profit margin
    df['PM_lag12'] = df.groupby('isin')['PM'].shift(12)
    df['CHPM'] = df['PM'] - df['PM_lag12']

    # OP: Operating profitability
    # OP: Define as operating profitability distinct from GMA
    if 'operating_income_pub' in df.columns and 'total_assets_pub' in df.columns:
        df['OP'] = safe_div(df['operating_income_pub'], df['total_assets_pub'])

    # RNA: Return on NOA
    if 'operating_assets' in df.columns and 'operating_liabilities' in df.columns:
        df['NOA_denominator'] = df['operating_assets'] - df['operating_liabilities']
    if 'operating_income_pub' in df.columns and 'NOA_denominator' in df.columns:
        df['RNA'] = safe_div(df['operating_income_pub'], df['NOA_denominator'])

    return df

def calculate_intangibles_chars(df):
    """Calculate intangibles characteristics."""
    print("  Calculating intangibles characteristics...")

    # HIRE: Employee growth
    if 'num_employees_pub' in df.columns:
        df['HIRE'] = df.groupby('isin')['num_employees_pub'].pct_change(12)

    # HERF: Industry concentration (skip for now - needs SNI codes)
    # TODO: Add HERF using SNI industry codes from Serrano ftg files

    return df

def calculate_beta_volatility(df):
    """
    Calculate market beta and idiosyncratic volatility.

    BETA: Market beta using 36-month rolling window
    RVAR_CAPM: Idiosyncratic volatility from CAPM
    RVAR_FF3: Idiosyncratic volatility from FF3 (if factors available)
    """
    print("  Calculating beta and idiosyncratic volatility...")

    df = df.sort_values(['isin', 'date'])

    # For now, calculate market beta using simple approach
    # TODO: Load FF factors for proper calculation

    # Simple market beta: cov(ret, mkt) / var(mkt)
    # We'll use a simplified version for now
    # Proper implementation would require FF factors

    # BETA: 36-month rolling beta
    # For now, set to None - will be calculated if FF factors available
    df['BETA'] = np.nan

    # RVAR_CAPM: Residual variance from CAPM
    df['RVAR_CAPM'] = np.nan

    # RVAR_FF3: Residual variance from FF3
    df['RVAR_FF3'] = np.nan

    print(f"    Beta/volatility characteristics set to NaN (need FF factors)")
    print(f"    TODO: Download FF factors from Ken French website")

    return df

def calculate_frictions_chars(df):
    """Calculate frictions characteristics."""
    print("  Calculating frictions characteristics...")

    df = df.sort_values(['isin', 'date'])

    # ME: Market equity (log)
    mkt_col = 'market_cap' if 'market_cap' in df.columns else ('market_cap_filled' if 'market_cap_filled' in df.columns else None)
    if mkt_col:
        df['ME'] = np.log(df[mkt_col])

    # Daily-based characteristics are already calculated in monthly aggregation
    # (ZEROTRADE, BASPREAD, DOLVOL, ILL, MAXRET, SVAR, STD_DOLVOL, STD_TURN, TURN)

    return df

def rank_characteristics(df):
    """
    Rank characteristics cross-sectionally to [-1, 1] scale.

    Following P-Tree paper methodology:
    - Rank within each date (cross-sectional)
    - Scale to [-1, 1] range
    - Missing values filled with 0 (neutral)
    """
    print("  Ranking characteristics to [-1, 1] scale...")

    # Get characteristic columns (raw uppercase feature names)
    char_cols = sorted([col for col in df.columns if col.isupper() and len(col) <= 10])
    # Exclude placeholders not computed yet
    char_cols = [c for c in char_cols if c not in {'BETA', 'RVAR_CAPM', 'RVAR_FF3'}]

    print(f"    Ranking {len(char_cols)} characteristics")

    # Rank each characteristic within each date
    for char in char_cols:
        # Create ranked version
        # Rank by month (common cross-section), not literal date per stock
        df[f'rank_{char.lower()}'] = df.groupby('year_month')[char].transform(
            lambda x: rank_to_minus1_plus1(x)
        )

    # Get all rank columns
    rank_cols = [f'rank_{char.lower()}' for char in char_cols]

    # Fill missing ranks with 0 (neutral position)
    for col in rank_cols:
        df[col] = df[col].fillna(0.0)

    print(f"    Created {len(rank_cols)} ranked characteristics")
    print(f"    Missing values filled with 0.0 (neutral)")

    return df, rank_cols

def rank_to_minus1_plus1(x):
    """
    Rank series to exactly [-1, 1] scale.

    Formula: 2 * ((rank - 1) / (n - 1)) - 1

    Example:
    - Lowest value: rank=1 -> 2*(0/(n-1)) - 1 = -1
    - Highest value: rank=n -> 2*((n-1)/(n-1)) - 1 = 1
    - Median: rank≈n/2 -> ≈0
    """
    import pandas as pd

    ranks = x.rank()
    n = x.count()

    if n <= 1:
        return pd.Series(0.0, index=x.index)

    return 2 * ((ranks - 1) / (n - 1)) - 1

def clean_and_finalize(df, rank_cols):
    """Select final columns for P-Tree dataset."""
    print("  Finalizing dataset...")

    # Identifiers and date
    id_cols = ['isin', 'date', 'year', 'month']

    # Returns
    ret_cols = ['ret_monthly']

    # Market data for weighting (lag_me for portfolio weighting)
    market_cols = ['market_cap']
    df['lag_me'] = df.groupby('isin')['market_cap'].shift(1).fillna(df['market_cap'])

    # Select columns: identifiers + returns + market data + ranked characteristics
    final_cols = id_cols + ret_cols + market_cols + ['lag_me'] + rank_cols
    final_cols = [col for col in final_cols if col in df.columns]

    df_final = df[final_cols].copy()

    # Remove rows with missing returns or market_cap
    df_final = df_final.dropna(subset=['ret_monthly', 'market_cap'])

    # Sort
    df_final = df_final.sort_values(['isin', 'date'])

    print(f"    Final dataset: {len(df_final):,} rows")
    print(f"    Ranked characteristics: {len(rank_cols)}")

    return df_final

def calculate_coverage(df):
    """Calculate and report coverage for ranked characteristics (non-zero share)."""
    print("\n  CHARACTERISTIC COVERAGE:")
    print("  " + "=" * 78)

    # Look at ranked features; measure non-zero share (since zeros denote neutral/missing)
    rank_cols = sorted([col for col in df.columns if col.startswith('rank_')])
    for col in rank_cols:
        nonzero = (df[col] != 0).mean() * 100
        count = (df[col] != 0).sum()
        print(f"    {col:25s}: {nonzero:5.1f}% ({count:,} obs)")

    print("  " + "=" * 78)

def validate_data_quality(df):
    """Validate data quality for PTrees analysis."""
    print("\n  DATA QUALITY VALIDATION:")
    print("  " + "=" * 78)

    # Check 1: All dates should be month-end
    df['is_month_end'] = df['date'] == (df['date'] + pd.offsets.MonthEnd(0))
    month_end_pct = df['is_month_end'].mean() * 100
    print(f"    Month-end alignment: {month_end_pct:.1f}% ({df['is_month_end'].sum():,}/{len(df):,})")
    if month_end_pct < 100:
        non_me_count = (~df['is_month_end']).sum()
        print(f"    ⚠️  WARNING: {non_me_count:,} rows are NOT month-end dates!")
        print(f"        This will cause PTrees to treat each date as separate time period")

    # Check 2: Stocks per time period
    stocks_per_date = df.groupby('date')['isin'].nunique()
    print(f"\n    Stocks per month:")
    print(f"      Min: {stocks_per_date.min()}")
    print(f"      Median: {stocks_per_date.median():.0f}")
    print(f"      Mean: {stocks_per_date.mean():.0f}")
    print(f"      Max: {stocks_per_date.max()}")

    if stocks_per_date.min() < 10:
        low_count = (stocks_per_date < 10).sum()
        print(f"    ⚠️  WARNING: {low_count} months have <10 stocks!")
        print(f"        This can cause overfitting on individual stocks")

    # Check 3: Extreme returns
    extreme_returns = df['ret_monthly'].abs() > 1.0
    extreme_pct = extreme_returns.mean() * 100
    print(f"\n    Extreme returns (|ret| > 100%):")
    print(f"      Count: {extreme_returns.sum():,} ({extreme_pct:.2f}%)")
    if extreme_returns.any():
        print(f"      Max positive: {df['ret_monthly'].max():.2%}")
        print(f"      Max negative: {df['ret_monthly'].min():.2%}")
        if extreme_pct > 0.5:
            print(f"    ⚠️  WARNING: High frequency of extreme returns!")
            print(f"        Consider winsorizing at 1st/99th percentile")

    # Check 4: Unique dates vs unique months
    unique_dates = df['date'].nunique()
    unique_months = df['date'].dt.to_period('M').nunique()
    print(f"\n    Time period structure:")
    print(f"      Unique dates: {unique_dates}")
    print(f"      Unique months: {unique_months}")
    if unique_dates > unique_months:
        extra_dates = unique_dates - unique_months
        print(f"    ⚠️  WARNING: {extra_dates} extra dates beyond expected months!")
        print(f"        Expected ~{unique_months} dates, found {unique_dates}")

    print("  " + "=" * 78)

    # Return validation status
    is_valid = (month_end_pct == 100.0 and
                stocks_per_date.min() >= 10 and
                unique_dates == unique_months and
                extreme_pct < 0.5)

    return is_valid

def main():
    print("=" * 80)
    print("Step 6: Prepare P-Tree Dataset with Proper Lagging")
    print("=" * 80)

    # 1. Load merged daily data
    print("\n1. Loading merged daily data...")
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    df['date'] = pd.to_datetime(df['date'])
    df['fiscal_year_end'] = pd.to_datetime(df['fiscal_year_end'])
    df['fiscal_year_start'] = pd.to_datetime(df['fiscal_year_start'])
    print(f"   Loaded: {len(df):,} rows, {df['isin'].nunique()} ISINs")

    # 2. Calculate daily-based characteristics (BEFORE monthly aggregation)
    print("\n2. Calculating daily-based characteristics...")
    df = calculate_daily_characteristics(df)

    # 3. Aggregate to monthly
    print("\n3. Aggregating to monthly...")
    df_monthly = aggregate_to_monthly(df)

    # 4. Apply publication lag (accounting) and 1m lag for market cap
    print("\n4. Applying publication lag (accounting) and 1m lag (market cap)...")
    df_monthly = apply_publication_lag(df_monthly, pub_lag_months=6)

    # 5. Calculate monthly-based characteristics
    print("\n5. Calculating monthly-based characteristics...")
    df_monthly = calculate_momentum_chars(df_monthly)
    df_monthly = calculate_value_chars(df_monthly)
    df_monthly = calculate_investment_chars(df_monthly)
    df_monthly = calculate_profitability_chars(df_monthly)
    df_monthly = calculate_intangibles_chars(df_monthly)
    df_monthly = calculate_beta_volatility(df_monthly)
    df_monthly = calculate_frictions_chars(df_monthly)

    # 6. Rank characteristics
    print("\n6. Ranking characteristics...")
    df_monthly, rank_cols = rank_characteristics(df_monthly)

    # 7. Clean and finalize
    print("\n7. Cleaning and finalizing...")
    df_final = clean_and_finalize(df_monthly, rank_cols)

    # 8. Coverage report
    print("\n8. Coverage analysis...")
    calculate_coverage(df_final)

    # 9. Data quality validation
    print("\n9. Data quality validation...")
    is_valid = validate_data_quality(df_final)

    # 10. Save
    print(f"\n10. Saving to {OUTPUT_PATH}...")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(OUTPUT_PATH, index=False)
    print("   Done.")

    if not is_valid:
        print("\n" + "!" * 80)
        print("⚠️  DATA QUALITY WARNINGS DETECTED - Review validation output above")
        print("!" * 80)

    # 11. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Output: {OUTPUT_PATH}")
    print(f"  Observations: {len(df_final):,}")
    print(f"  Companies: {df_final['isin'].nunique()}")
    print(f"  Date range: {df_final['date'].min()} to {df_final['date'].max()}")
    months_count = df_final['date'].dt.to_period('M').nunique()
    print(f"  Months: {months_count}")
    print(f"  Avg companies/month: {len(df_final) / df_final['date'].nunique():.0f}")

    rank_cols_in_final = [col for col in df_final.columns if col.startswith('rank_')]
    print(f"\n  Ranked characteristics: {len(rank_cols_in_final)}/50")
    print(f"  All characteristics scaled to [-1, 1]")
    print(f"  Missing values filled with 0 (neutral)")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
