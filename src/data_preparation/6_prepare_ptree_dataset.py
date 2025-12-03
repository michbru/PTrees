"""
Step 6: Prepare P-Tree Dataset with Proper Lagging (Monthly Data)
==================================================================
Calculate characteristics with proper lagging for monthly data.

Note: Working with MONTHLY data from step 5. Daily-based characteristics 
      (ZEROTRADE, BASPREAD, DOLVOL, ILL, MAXRET, SVAR, STD_DOLVOL, STD_TURN, TURN) 
      are SKIPPED as they require daily data.

Lagging Strategy:
- "none": Use data up to month-end t
- "1 year (accounting)": Apply 6-month publication lag to accounting data
- "1 year (accounting) + 1 month (market)": Apply 6-month lag to accounting + 1-month lag to market_cap

Input:
  - data/processed/merged_data_monthly.csv

Output:
  - data/processed/ptree_dataset_monthly.csv (monthly with all characteristics)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Paths
INPUT_PATH = Path('data/processed/merged_data_monthly.csv')
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
    base_cols = ['isin', 'fiscal_year'] + [col for col in accounting_vars if col in df.columns]
    df_fy = df[base_cols].dropna(subset=['fiscal_year']).copy()
    df_fy = df_fy.groupby(['isin', 'fiscal_year']).last().reset_index()
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
    
    # FILTER ROWS: Exclude rows with more than 4 missing accounting variables (less aggressive)
    print("  Filtering rows with insufficient data...")
    pub_cols = [f'{v}_pub' for v in accounting_vars if f'{v}_pub' in df.columns]

    # Count missing values per row for publication-lagged accounting variables
    df['missing_count'] = df[pub_cols].isna().sum(axis=1)

    rows_before = len(df)
    df = df[df['missing_count'] <= 4].copy()  # Allow up to 4 missing (balanced quality/quantity)
    rows_after = len(df)
    rows_dropped = rows_before - rows_after

    print(f"    Dropped {rows_dropped:,} rows with >4 missing accounting variables ({rows_dropped/rows_before*100:.1f}%)")
    print(f"    Remaining: {rows_after:,} rows")

    # Drop the helper column
    df = df.drop(columns=['missing_count'])

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

    # CINVEST: Corporate investment
    if 'ppe_pub' in df.columns:
        df['ppe_pub_lag12'] = df.groupby('isin')['ppe_pub'].shift(12)
        df['CINVEST'] = safe_div(df['ppe_pub'] - df['ppe_pub_lag12'], df['ppe_pub_lag12'])

    # GRLTNOA: Growth in long-term NOA
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


def calculate_frictions_chars(df):
    """Calculate frictions characteristics (ME only - daily-based skipped)."""
    print("  Calculating frictions characteristics...")

    df = df.sort_values(['isin', 'date'])

    # ME: Market equity (log)
    if 'market_cap' in df.columns:
        df['ME'] = np.log(df['market_cap'])

    # Daily-based characteristics are SKIPPED (require daily data):
    # ZEROTRADE, BASPREAD, DOLVOL, ILL, MAXRET, SVAR, STD_DOLVOL, STD_TURN, TURN

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

    print(f"    Ranking {len(char_cols)} characteristics")

    # Rank each characteristic within each date
    for char in char_cols:
        # Create ranked version
        df[f'rank_{char.lower()}'] = df.groupby('date')[char].transform(
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


def main():
    print("=" * 80)
    print("Step 6: Prepare P-Tree Dataset with Proper Lagging (Monthly Data)")
    print("=" * 80)

    # 1. Load merged monthly data
    print("\n1. Loading merged monthly data...")
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    df['date'] = pd.to_datetime(df['date'])
    df['fiscal_year_end'] = pd.to_datetime(df['fiscal_year_end'])
    df['fiscal_year_start'] = pd.to_datetime(df['fiscal_year_start'])
    print(f"   Loaded: {len(df):,} rows, {df['isin'].nunique()} ISINs")

    # 2. Apply publication lag (accounting) and 1m lag for market cap
    print("\n2. Applying publication lag (accounting) and 1m lag (market cap)...")
    df = apply_publication_lag(df, pub_lag_months=6)

    # 3. Calculate monthly-based characteristics
    print("\n3. Calculating monthly-based characteristics...")
    df = calculate_momentum_chars(df)
    df = calculate_value_chars(df)
    df = calculate_investment_chars(df)
    df = calculate_profitability_chars(df)
    df = calculate_intangibles_chars(df)
    df = calculate_frictions_chars(df)

    # 4. Rank characteristics
    print("\n4. Ranking characteristics...")
    df, rank_cols = rank_characteristics(df)

    # 5. Clean and finalize
    print("\n5. Cleaning and finalizing...")
    df_final = clean_and_finalize(df, rank_cols)

    # 6. Coverage report
    print("\n6. Coverage analysis...")
    calculate_coverage(df_final)

    # 7. Save
    print(f"\n7. Saving to {OUTPUT_PATH}...")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(OUTPUT_PATH, index=False)
    print("   Done.")

    # 8. Summary
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
    print(f"\n  Ranked characteristics: {len(rank_cols_in_final)}")
    print(f"  All characteristics scaled to [-1, 1]")
    print(f"  Missing values filled with 0 (neutral)")
    print(f"\n  NOTE: Daily-based characteristics (ZEROTRADE, BASPREAD, DOLVOL, ILL,")
    print(f"        MAXRET, SVAR, STD_DOLVOL, STD_TURN, TURN) are SKIPPED")
    print(f"        as they require daily data (not available in monthly dataset)")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
