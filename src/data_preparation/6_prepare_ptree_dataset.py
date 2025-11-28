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

def aggregate_to_monthly(df):
    """Aggregate daily to monthly (month-end)."""
    print("  Aggregating to monthly...")

    df = df.sort_values(['isin', 'date'])
    df['year_month'] = df['date'].dt.to_period('M')

    # Take last trading day of each month
    df_monthly = df.groupby(['isin', 'year_month']).last().reset_index()

    # Calculate monthly returns
    df_monthly = df_monthly.sort_values(['isin', 'date'])
    df_monthly['ret_monthly'] = df_monthly.groupby('isin')['close'].pct_change()

    print(f"    Monthly observations: {len(df_monthly):,}")
    return df_monthly

def apply_lags(df):
    """Apply 12-month lag to accounting vars, 1-month lag to market_cap for ratios."""
    print("  Applying lags...")

    df = df.sort_values(['isin', 'date'])

    # Accounting variables to lag by 12 months
    accounting_vars = [
        'sales', 'cogs_materials', 'cogs_goods', 'personnel_expense',
        'depreciation', 'operating_income', 'interest_income', 'interest_expense',
        'tax_expense', 'net_income', 'total_assets', 'fixed_assets',
        'intangible_assets', 'tangible_assets', 'ppe_buildings', 'ppe_machinery',
        'current_assets', 'inventory', 'cash', 'receivables', 'book_equity',
        'share_capital', 'long_term_debt', 'current_liabilities', 'accounts_payable',
        'num_employees', 'fiscal_year', 'fiscal_year_start', 'fiscal_year_end'
    ]

    for var in accounting_vars:
        if var in df.columns:
            df[f'{var}_lag12'] = df.groupby('isin')[var].shift(12)

    # Market cap for ratios (1-month lag)
    df['market_cap_lag1'] = df.groupby('isin')['market_cap'].shift(1)

    rows_with_acct = df['sales_lag12'].notna().sum()
    print(f"    Rows with lagged accounting: {rows_with_acct:,} ({rows_with_acct/len(df)*100:.1f}%)")

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

    # CHTX: Change in tax expense
    df['CHTX'] = df.groupby('isin')['tax_expense_lag12'].pct_change(12)

    # DEPR: Depreciation rate
    df['ppe_lag12'] = df['ppe_buildings_lag12'].fillna(0) + df['ppe_machinery_lag12'].fillna(0)
    df['DEPR'] = df['depreciation_lag12'] / df['ppe_lag12']

    return df

def calculate_value_chars(df):
    """Calculate value characteristics."""
    print("  Calculating value characteristics...")

    # BM: Book-to-Market (no lag - book_value from Finbas is already reported)
    df['BM'] = df['book_value'] / df['market_cap']

    # EP, SP, CFP: Use lagged accounting + lagged market cap
    df['EP'] = df['net_income_lag12'] / df['market_cap_lag1']
    df['SP'] = df['sales_lag12'] / df['market_cap_lag1']

    # CFP: Operating cash flow approximation
    df['operating_cashflow'] = df['net_income_lag12'] + df['depreciation_lag12']
    df['CFP'] = df['operating_cashflow'] / df['market_cap_lag1']

    # Pure accounting ratios
    df['CASH'] = df['cash_lag12'] / df['total_assets_lag12']

    df['total_debt_lag12'] = df['long_term_debt_lag12'] + df['current_liabilities_lag12']
    df['CASHDEBT'] = df['cash_lag12'] / df['total_debt_lag12']

    df['LEV'] = df['total_debt_lag12'] / df['total_assets_lag12']

    df['SGR'] = df.groupby('isin')['sales_lag12'].pct_change(12)

    return df

def calculate_investment_chars(df):
    """Calculate investment characteristics."""
    print("  Calculating investment characteristics...")

    # AGR: Asset growth
    df['AGR'] = df.groupby('isin')['total_assets_lag12'].pct_change(12)

    # GMA: Gross profitability
    df['cogs_total'] = df['cogs_materials_lag12'].fillna(0) + df['cogs_goods_lag12'].fillna(0)
    df['gross_profit'] = df['sales_lag12'] - df['cogs_total']
    df['GMA'] = df['gross_profit'] / df['total_assets_lag12']

    # LGR: Long-term debt growth
    df['LGR'] = df.groupby('isin')['long_term_debt_lag12'].pct_change(12)

    # ACC: Operating accruals
    df['working_capital'] = df['current_assets_lag12'] - df['current_liabilities_lag12']
    df['wc_lag12'] = df.groupby('isin')['working_capital'].shift(12)
    df['delta_wc'] = df['working_capital'] - df['wc_lag12']
    df['total_assets_lag24'] = df.groupby('isin')['total_assets_lag12'].shift(12)
    df['avg_assets'] = (df['total_assets_lag12'] + df['total_assets_lag24']) / 2
    df['ACC'] = (df['delta_wc'] - df['depreciation_lag12']) / df['avg_assets']

    # CHCSHO: Change in shares outstanding
    df['shares'] = df['market_cap'] / df['close']
    df['shares_lag12'] = df.groupby('isin')['shares'].shift(12)
    df['CHCSHO'] = (df['shares'] - df['shares_lag12']) / df['shares_lag12']

    # NI: Net equity issuance
    df['NI'] = np.log(df['shares'] / df['shares_lag12'])

    # NOA: Net operating assets
    df['operating_assets'] = df['total_assets_lag12'] - df['cash_lag12']
    df['operating_liabilities'] = df['total_assets_lag12'] - df['book_equity_lag12'] - df['long_term_debt_lag12']
    df['NOA'] = (df['operating_assets'] - df['operating_liabilities']) / df['total_assets_lag24']

    # PCTACC: Percent accruals
    df['PCTACC'] = (df['ACC'] * df['avg_assets']) / np.abs(df['net_income_lag12'])

    # CINVEST: Corporate investment (change in capex / lagged PPE)
    # Approximation: change in PPE / lagged PPE
    df['ppe_current'] = df['ppe_buildings_lag12'].fillna(0) + df['ppe_machinery_lag12'].fillna(0)
    df['ppe_lag24'] = df.groupby('isin')['ppe_lag12'].shift(12)
    df['CINVEST'] = (df['ppe_current'] - df['ppe_lag12']) / df['ppe_lag24']

    # GRLTNOA: Growth in long-term NOA (simplified version)
    df['GRLTNOA'] = df.groupby('isin')['NOA'].pct_change(12)

    return df

def calculate_profitability_chars(df):
    """Calculate profitability characteristics."""
    print("  Calculating profitability characteristics...")

    df['ROA'] = df['net_income_lag12'] / df['total_assets_lag12']
    df['ROE'] = df['net_income_lag12'] / df['book_equity_lag12']
    df['ATO'] = df['sales_lag12'] / df['avg_assets']
    df['PM'] = df['net_income_lag12'] / df['sales_lag12']

    # CHPM: Change in profit margin
    df['PM_lag12'] = df.groupby('isin')['PM'].shift(12)
    df['CHPM'] = df['PM'] - df['PM_lag12']

    # OP: Operating profitability
    df['OP'] = (df['operating_income_lag12'] - df['interest_expense_lag12']) / df['book_equity_lag12']

    # RNA: Return on NOA
    df['NOA_denominator'] = df['operating_assets'] - df['operating_liabilities']
    df['RNA'] = df['operating_income_lag12'] / df['NOA_denominator']

    return df

def calculate_intangibles_chars(df):
    """Calculate intangibles characteristics."""
    print("  Calculating intangibles characteristics...")

    # HIRE: Employee growth
    df['HIRE'] = df.groupby('isin')['num_employees_lag12'].pct_change(12)

    # HERF: Industry concentration (skip for now - needs SNI codes)
    # TODO: Add HERF using SNI industry codes from Serrano ftg files

    return df

def calculate_frictions_chars(df):
    """Calculate frictions characteristics."""
    print("  Calculating frictions characteristics...")

    df = df.sort_values(['isin', 'date'])

    # ME: Market equity (log)
    df['ME'] = np.log(df['market_cap'])

    # For daily-based chars, we need to calculate from daily data
    # For now, we'll create placeholders - these need daily aggregation

    # BASPREAD: Bid-ask spread (needs daily data)
    # DOLVOL: Dollar volume (needs daily data)
    # ILL: Illiquidity (needs daily data)
    # MAXRET: Max return (needs daily data)
    # STD_DOLVOL: Std of dollar volume (needs daily data)
    # STD_TURN: Std of turnover (needs daily data)
    # TURN: Turnover (needs daily data)
    # ZEROTRADE: Zero trading days (needs daily data)
    # SVAR: Return variance (needs daily data)
    # BETA: Market beta (needs daily returns + FF factors)
    # RVAR_CAPM, RVAR_FF3: Idiosyncratic volatility (needs daily returns + FF factors)

    # These will be calculated in a separate function that operates on daily data

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

    # Get characteristic columns
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
    """Calculate and report coverage for each characteristic."""
    print("\n  CHARACTERISTIC COVERAGE:")
    print("  " + "=" * 78)

    char_cols = sorted([col for col in df.columns if col.isupper() and len(col) <= 10])

    for char in char_cols:
        coverage = df[char].notna().mean() * 100
        count = df[char].notna().sum()
        print(f"    {char:10s}: {coverage:5.1f}% ({count:,} obs)")

    print("  " + "=" * 78)

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

    # 2. Aggregate to monthly
    print("\n2. Aggregating to monthly...")
    df_monthly = aggregate_to_monthly(df)

    # 3. Apply lags
    print("\n3. Applying lags (12m for accounting, 1m for market cap)...")
    df_monthly = apply_lags(df_monthly)

    # 4. Calculate characteristics
    print("\n4. Calculating characteristics...")
    df_monthly = calculate_momentum_chars(df_monthly)
    df_monthly = calculate_value_chars(df_monthly)
    df_monthly = calculate_investment_chars(df_monthly)
    df_monthly = calculate_profitability_chars(df_monthly)
    df_monthly = calculate_intangibles_chars(df_monthly)
    df_monthly = calculate_frictions_chars(df_monthly)

    # 5. Rank characteristics
    print("\n5. Ranking characteristics...")
    df_monthly, rank_cols = rank_characteristics(df_monthly)

    # 6. Clean and finalize
    print("\n6. Cleaning and finalizing...")
    df_final = clean_and_finalize(df_monthly, rank_cols)

    # 7. Coverage report
    print("\n7. Coverage analysis...")
    calculate_coverage(df_final)

    # 8. Save
    print(f"\n8. Saving to {OUTPUT_PATH}...")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(OUTPUT_PATH, index=False)
    print("   Done.")

    # 9. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Output: {OUTPUT_PATH}")
    print(f"  Observations: {len(df_final):,}")
    print(f"  Companies: {df_final['isin'].nunique()}")
    print(f"  Date range: {df_final['date'].min()} to {df_final['date'].max()}")
    print(f"  Months: {df_final['date'].nunique()}")
    print(f"  Avg companies/month: {len(df_final) / df_final['date'].nunique():.0f}")

    rank_cols_in_final = [col for col in df_final.columns if col.startswith('rank_')]
    print(f"\n  Ranked characteristics: {len(rank_cols_in_final)}/50")
    print(f"  All characteristics scaled to [-1, 1]")
    print(f"  Missing values filled with 0 (neutral)")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
