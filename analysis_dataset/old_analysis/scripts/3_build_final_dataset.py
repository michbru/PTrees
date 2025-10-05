#!/usr/bin/env python3
"""
PTrees Final Dataset Builder - Robust Version

This script builds the comprehensive analysis dataset from scratch using the two best sources:
1. data/finbas_market_data.csv (high-quality monthly market data)
2. results/lseg_basic_fundamentals.csv (annual fundamental data)

The script ensures no data is lost by:
- Starting from the original Finbas data
- Calculating ALL market-based characteristics BEFORE merging
- Properly forward-filling and merging LSEG data
- Calculating LSEG-dependent characteristics only after safe merge
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_and_prepare_finbas_data():
    """Load and prepare the core Finbas market data."""
    print("PART 1: LOADING AND PREPARING FINBAS DATA")
    print("=" * 50)

    # Load the original Finbas data
    finbas_path = "data/finbas_market_data.csv"
    if not Path(finbas_path).exists():
        raise FileNotFoundError(f"Cannot find core Finbas data: {finbas_path}")

    print(f"Loading core Finbas data from {finbas_path}...")
    df = pd.read_csv(finbas_path, sep=';')
    print(f"  Loaded: {len(df):,} observations")
    print(f"  Original columns: {list(df.columns)}")

    # Standardize column names for consistency - only rename columns that exist
    column_mapping = {
        'day': 'date',
        'lastad': 'price',
        'oatad': 'volume',
        'marketvalue': 'market_cap',
        'bookvalue': 'book_value'
    }

    # Check which columns exist before renaming
    existing_columns = df.columns.tolist()
    actual_mapping = {old: new for old, new in column_mapping.items() if old in existing_columns}
    print(f"  Renaming columns: {actual_mapping}")

    df = df.rename(columns=actual_mapping)

    # Convert date and create time columns
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month

    # Sort by company and date for all future operations
    df = df.sort_values(['isin', 'date'])

    print(f"  Standardized columns and dates")
    print(f"  Final columns: {list(df.columns)}")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Companies: {df['isin'].nunique()}")

    return df

def forward_fill_finbas_data(df):
    """Forward-fill book values within each company before calculating characteristics."""
    print("\nForward-filling book values within companies...")

    # Forward-fill book_value within each company
    df['book_value'] = df.groupby('isin')['book_value'].ffill()

    coverage = df['book_value'].notna().mean() * 100
    print(f"  Book value coverage after forward-fill: {coverage:.1f}%")

    return df

def forward_fill_fundamentals(panel_data, fundamental_data, fund_type="fundamentals"):
    """Forward-fill annual fundamental data to monthly observations."""
    if fundamental_data is None:
        print(f"  Skipping {fund_type} - no data available")
        return panel_data

    print(f"  Processing {fund_type} data...")

    # Prepare the fundamental data
    fund_df = fundamental_data.copy()

    # Create merge key for fundamentals (company-year)
    fund_df['merge_key'] = fund_df['isin'] + '_' + fund_df['year'].astype(str)

    # Prepare panel data
    panel_df = panel_data.copy()
    panel_df['date'] = pd.to_datetime(panel_df['date'])
    panel_df['year'] = panel_df['date'].dt.year
    panel_df['merge_key'] = panel_df['isin'] + '_' + panel_df['year'].astype(str)

    # Get columns to merge (exclude keys)
    fund_cols = [col for col in fund_df.columns if col not in ['isin', 'year', 'merge_key']]
    merge_cols = ['merge_key'] + fund_cols

    print(f"    Merging {len(fund_cols)} fundamental columns: {fund_cols}")

    # Merge the data
    merged_df = panel_df.merge(fund_df[merge_cols], on='merge_key', how='left')

    # Forward-fill missing fundamental data
    print(f"    Forward-filling missing fundamental data...")
    merged_df = merged_df.sort_values(['isin', 'date'])

    for col in fund_cols:
        if col in merged_df.columns:
            # Forward fill within each company
            merged_df[col] = merged_df.groupby('isin')[col].ffill()

    # Clean up
    merged_df = merged_df.drop(['merge_key'], axis=1)

    # Report coverage
    for col in fund_cols:
        if col in merged_df.columns:
            coverage = merged_df[col].notna().mean() * 100
            print(f"    {col}: {coverage:.1f}% coverage")

    return merged_df

def calculate_finbas_characteristics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate characteristics derivable purely from Finbas data before any merges.

    Adds: book_to_market, return_1m, momentum_12m, volatility_12m, turnover
    """
    print("\nCalculating Finbas-only characteristics (pre-merge)...")
    print(f"  Available columns for calculations: {list(df.columns)}")
    out = df.copy()

    # Book-to-market: guard against zero/NaN market cap
    if 'book_value' in out.columns and 'market_cap' in out.columns:
        out['book_to_market'] = np.where(out['market_cap'] > 0, out['book_value'] / out['market_cap'], np.nan)
        coverage = out['book_to_market'].notna().mean() * 100
        print(f"  Calculated book_to_market ({coverage:.1f}% coverage)")
    else:
        print(f"  SKIPPING book_to_market - missing columns. Available: {[c for c in ['book_value', 'market_cap'] if c in out.columns]}")

    # Monthly simple returns
    if 'price' in out.columns:
        out = out.sort_values(['isin', 'date'])
        # Calculate CURRENT return (for target variable ret/xret)
        out['current_return'] = out.groupby('isin')['price'].pct_change()
        # FIX: Lag return_1m to avoid look-ahead bias (for characteristic)
        # return_1m at time t now represents return from t-2 to t-1
        out['return_1m'] = out['current_return'].shift(1)
        coverage = out['return_1m'].notna().mean() * 100
        print(f"  Calculated return_1m (LAGGED to avoid look-ahead bias, {coverage:.1f}% coverage)")
        print(f"  Calculated current_return (for target variable, {out['current_return'].notna().mean() * 100:.1f}% coverage)")

        # Momentum: 12-month cumulative return (price/lag12 - 1)
        price_lag12 = out.groupby('isin')['price'].shift(12)
        out['momentum_12m'] = np.where(price_lag12.notna() & (price_lag12 != 0), out['price'] / price_lag12 - 1.0, np.nan)
        coverage = out['momentum_12m'].notna().mean() * 100
        print(f"  Calculated momentum_12m ({coverage:.1f}% coverage)")

        # Volatility: rolling 12m std of monthly returns
        out['volatility_12m'] = (
            out.groupby('isin')['return_1m']
               .transform(lambda s: s.rolling(window=12, min_periods=6).std())
        )
        coverage = out['volatility_12m'].notna().mean() * 100
        print(f"  Calculated volatility_12m ({coverage:.1f}% coverage)")
    else:
        print("  SKIPPING momentum and volatility calculations - missing price column")

    # Turnover proxy: traded value / market cap = (volume * price) / market_cap
    if all(c in out.columns for c in ['volume', 'price', 'market_cap']):
        out['turnover'] = np.where(out['market_cap'] > 0, (out['volume'] * out['price']) / out['market_cap'], np.nan)
        coverage = out['turnover'].notna().mean() * 100
        print(f"  Calculated turnover ({coverage:.1f}% coverage)")
    else:
        missing = [c for c in ['volume', 'price', 'market_cap'] if c not in out.columns]
        print(f"  SKIPPING turnover - missing columns: {missing}")

    return out

def load_and_prepare_lseg_data():
    """Load LSEG basic and extended fundamentals if available and standardize columns."""
    print("\nPART 2: LOADING LSEG FUNDAMENTALS")
    print("=" * 50)

    basic_path = "results/lseg_basic_fundamentals.csv"
    extended_path = "results/lseg_extended_fundamentals.csv"

    basic_df = None
    extended_df = None

    if Path(basic_path).exists():
        print(f"Loading basic fundamentals from {basic_path}...")
        basic_df = pd.read_csv(basic_path)
        # Standardize columns
        rename_basic = {
            'TotalAssets': 'total_assets',
            'NetIncome': 'net_income',
            'Revenue': 'total_revenue'
        }
        basic_df = basic_df.rename(columns=rename_basic)
        # Ensure required columns exist
        for col in ['isin', 'year']:
            if col not in basic_df.columns:
                raise ValueError(f"Basic fundamentals missing required column: {col}")
        basic_df['year'] = basic_df['year'].astype(int)
        print(f"  Basic rows: {len(basic_df):,}")
    else:
        print("  Warning: results/lseg_basic_fundamentals.csv not found")

    if Path(extended_path).exists():
        print(f"Loading extended fundamentals from {extended_path}...")
        extended_df = pd.read_csv(extended_path)
        # Standardize columns (keep names if already standardized)
        rename_ext = {
            'Revenue': 'total_revenue',
            'CFO': 'cfo',
            'COGS': 'cogs',
            'TotalDebt': 'total_debt',
            'Capex': 'capex'
        }
        extended_df = extended_df.rename(columns=rename_ext)
        for col in ['isin', 'year']:
            if col not in extended_df.columns:
                raise ValueError(f"Extended fundamentals missing required column: {col}")
        extended_df['year'] = extended_df['year'].astype(int)
        # Avoid duplicate total_revenue from both basic and extended when merging
        if 'total_revenue' in extended_df.columns:
            extended_df = extended_df.drop(columns=['total_revenue'])
        print(f"  Extended rows: {len(extended_df):,}")
    else:
        print("  Note: results/lseg_extended_fundamentals.csv not found (optional)")

    return basic_df, extended_df

def calculate_extended_characteristics(df):
    """Calculate extended firm characteristics."""
    print("\nCalculating extended characteristics...")
    print(f"  Available columns: {list(df.columns)}")

    # Ensure we have the required base data
    extended_df = df.copy()

    # Handle duplicate total_revenue columns if they exist
    revenue_col = None
    if 'total_revenue' in df.columns:
        revenue_col = 'total_revenue'
    elif 'total_revenue_x' in df.columns:
        revenue_col = 'total_revenue_x'
        # Clean up duplicate columns
        if 'total_revenue_y' in df.columns:
            # Use the column with more data
            x_coverage = df['total_revenue_x'].notna().sum()
            y_coverage = df['total_revenue_y'].notna().sum()
            if y_coverage > x_coverage:
                revenue_col = 'total_revenue_y'
            extended_df = extended_df.drop(columns=['total_revenue_y'])
        # Rename for consistency
        extended_df = extended_df.rename(columns={revenue_col: 'total_revenue'})
        revenue_col = 'total_revenue'
    elif 'total_revenue_y' in df.columns:
        revenue_col = 'total_revenue_y'
        extended_df = extended_df.rename(columns={revenue_col: 'total_revenue'})
        revenue_col = 'total_revenue'

    if revenue_col:
        print(f"  Using revenue column: {revenue_col}")

    # 10. ROA - CRITICAL missing ratio (must come first)
    if 'net_income' in df.columns and 'total_assets' in df.columns:
        extended_df['roa'] = np.where(df['total_assets'] != 0, df['net_income'] / df['total_assets'], np.nan)
        coverage = extended_df['roa'].notna().mean() * 100
        print(f"  Calculated roa ({coverage:.1f}% coverage)")

    # 1. Earnings-to-Price ratio (E/P)
    if 'net_income' in df.columns and 'market_cap' in df.columns:
        extended_df['ep_ratio'] = np.where(df['market_cap'] > 0, df['net_income'] / df['market_cap'], np.nan)
        coverage = extended_df['ep_ratio'].notna().mean() * 100
        print(f"  Calculated ep_ratio ({coverage:.1f}% coverage)")

    # 2. Cash Flow-to-Price ratio (CF/P)
    if 'cfo' in df.columns and 'market_cap' in df.columns:
        extended_df['cfp_ratio'] = np.where(df['market_cap'] > 0, df['cfo'] / df['market_cap'], np.nan)
        coverage = extended_df['cfp_ratio'].notna().mean() * 100
        print(f"  Calculated cfp_ratio ({coverage:.1f}% coverage)")

    # 3. Sales-to-Price ratio (S/P)
    if 'total_revenue' in extended_df.columns and 'market_cap' in df.columns:
        extended_df['sp_ratio'] = np.where(df['market_cap'] > 0, extended_df['total_revenue'] / df['market_cap'], np.nan)
        coverage = extended_df['sp_ratio'].notna().mean() * 100
        print(f"  Calculated sp_ratio ({coverage:.1f}% coverage)")

    # 4. Gross Profitability
    if all(col in extended_df.columns for col in ['total_revenue', 'cogs', 'total_assets']):
        extended_df['gross_profitability'] = np.where(
            extended_df['total_assets'] != 0,
            (extended_df['total_revenue'] - extended_df['cogs']) / extended_df['total_assets'],
            np.nan
        )
        coverage = extended_df['gross_profitability'].notna().mean() * 100
        print(f"  Calculated gross_profitability ({coverage:.1f}% coverage)")

    # 5. Capital Expenditure to Assets
    if 'capex' in df.columns and 'total_assets' in df.columns:
        extended_df['capex_to_assets'] = np.where(df['total_assets'] > 0, df['capex'] / df['total_assets'], np.nan)
        coverage = extended_df['capex_to_assets'].notna().mean() * 100
        print(f"  Calculated capex_to_assets ({coverage:.1f}% coverage)")

    # 6. Debt-to-Equity ratio
    if 'total_debt' in df.columns and 'book_value' in df.columns:
        extended_df['debt_to_equity'] = np.where(
            df['book_value'] != 0,
            df['total_debt'] / df['book_value'],
            np.nan
        )
        coverage = extended_df['debt_to_equity'].notna().mean() * 100
        print(f"  Calculated debt_to_equity ({coverage:.1f}% coverage)")

    # 7. Sales Growth (YoY % change in total_revenue)
    if 'total_revenue' in extended_df.columns:
        extended_df = extended_df.sort_values(['isin', 'date'])
        extended_df['revenue_lag'] = extended_df.groupby('isin')['total_revenue'].shift(12)
        extended_df['sales_growth'] = np.where(
            extended_df['revenue_lag'] != 0,
            (extended_df['total_revenue'] - extended_df['revenue_lag']) / extended_df['revenue_lag'],
            np.nan
        )
        extended_df = extended_df.drop(['revenue_lag'], axis=1)
        coverage = extended_df['sales_growth'].notna().mean() * 100
        print(f"  Calculated sales_growth ({coverage:.1f}% coverage)")

    # 8. Operating Cash Flow to Assets
    if 'cfo' in df.columns and 'total_assets' in df.columns:
        extended_df['cfo_to_assets'] = np.where(df['total_assets'] > 0, df['cfo'] / df['total_assets'], np.nan)
        coverage = extended_df['cfo_to_assets'].notna().mean() * 100
        print(f"  Calculated cfo_to_assets ({coverage:.1f}% coverage)")

    # 9. Asset Quality (1 - COGS/Revenue)
    if 'cogs' in df.columns and 'total_revenue' in extended_df.columns:
        extended_df['asset_quality'] = np.where(
            extended_df['total_revenue'] != 0,
            1 - (df['cogs'] / extended_df['total_revenue']),
            np.nan
        )
        coverage = extended_df['asset_quality'].notna().mean() * 100
        print(f"  Calculated asset_quality ({coverage:.1f}% coverage)")

    # 11. Asset growth (YoY % change in total assets)
    if 'total_assets' in df.columns:
        extended_df = extended_df.sort_values(['isin', 'date'])
        extended_df['assets_lag_12m'] = extended_df.groupby('isin')['total_assets'].shift(12)
        extended_df['asset_growth'] = np.where(
            extended_df['assets_lag_12m'] != 0,
            (extended_df['total_assets'] - extended_df['assets_lag_12m']) / extended_df['assets_lag_12m'],
            np.nan
        )
        extended_df = extended_df.drop(columns=['assets_lag_12m'])
        coverage = extended_df['asset_growth'].notna().mean() * 100
        print(f"  Calculated asset_growth ({coverage:.1f}% coverage)")

    # 12. Price-to-Assets
    if 'market_cap' in df.columns and 'total_assets' in df.columns:
        extended_df['price_to_assets'] = np.where(df['total_assets'] != 0, df['market_cap'] / df['total_assets'], np.nan)
        coverage = extended_df['price_to_assets'].notna().mean() * 100
        print(f"  Calculated price_to_assets ({coverage:.1f}% coverage)")

    # 13. Asset turnover (Sales / Assets)
    if 'total_revenue' in extended_df.columns and 'total_assets' in df.columns:
        extended_df['asset_turnover'] = np.where(df['total_assets'] != 0, extended_df['total_revenue'] / df['total_assets'], np.nan)
        coverage = extended_df['asset_turnover'].notna().mean() * 100
        print(f"  Calculated asset_turnover ({coverage:.1f}% coverage)")

    # Count new characteristics
    original_cols = set(df.columns)
    new_cols = [col for col in extended_df.columns if col not in original_cols]

    print(f"\nAdded {len(new_cols)} new characteristics: {new_cols}")

    return extended_df

def generate_coverage_report(df):
    """Generate coverage report for all characteristics."""
    print(f"\nEXTENDED DATASET COVERAGE REPORT")
    print("=" * 60)

    # Define characteristic groups
    characteristic_groups = {
        'Size & Valuation': ['market_cap', 'book_to_market', 'price'],
        'Market-Based Factors': ['momentum_12m', 'volatility_12m', 'turnover'],
        'Profitability': ['roa', 'ep_ratio', 'cfp_ratio', 'gross_profitability', 'cfo_to_assets'],
        'Valuation Ratios': ['sp_ratio', 'price_to_assets'],
        'Investment & Growth': ['capex_to_assets', 'sales_growth', 'asset_turnover'],
        'Financial Health': ['debt_to_equity', 'asset_quality'],
        'Fundamental Data': ['total_assets', 'net_income', 'total_revenue', 'cfo', 'cogs', 'total_debt', 'capex']
    }

    total_obs = len(df)

    for group_name, characteristics in characteristic_groups.items():
        print(f"\n{group_name.upper()}:")
        print("-" * 40)

        for char in characteristics:
            if char in df.columns:
                non_missing = df[char].notna().sum()
                coverage_pct = (non_missing / total_obs) * 100

                # Determine status
                if coverage_pct >= 90:
                    status = "Excellent"
                elif coverage_pct >= 75:
                    status = "Good"
                elif coverage_pct >= 50:
                    status = "Moderate"
                else:
                    status = "Limited"

                print(f"{char:<25} {non_missing:>8,} {coverage_pct:>6.1f}% {status}")
            else:
                print(f"{char:<25} {'Not Available'}")

    print(f"\nTOTAL CHARACTERISTICS: {len([col for group in characteristic_groups.values() for col in group if col in df.columns])}")

def main():
    """Main execution function."""

    # 1) Load Finbas core data
    finbas_df = load_and_prepare_finbas_data()

    # 2) Forward-fill Finbas annual book values
    finbas_df = forward_fill_finbas_data(finbas_df)

    # 3) Compute Finbas-only characteristics BEFORE any merging
    finbas_df = calculate_finbas_characteristics(finbas_df)

    # 4) Load LSEG basic (+ extended if available)
    basic_df, extended_df = load_and_prepare_lseg_data()

    # 5) Merge LSEG basic (left-merge + forward-fill by isin)
    merged_df = finbas_df.copy()
    if basic_df is not None:
        merged_df = forward_fill_fundamentals(merged_df, basic_df, "basic fundamentals")

    # 6) Merge LSEG extended if present (drop duplicate total_revenue before merge already handled)
    if extended_df is not None:
        merged_df = forward_fill_fundamentals(merged_df, extended_df, "extended fundamentals")

    # 7) Compute LSEG-dependent and other extended characteristics
    final_df = calculate_extended_characteristics(merged_df)

    # 8) Apply quality filters
    print(f"\nApplying quality filters...")
    initial_count = len(final_df)
    final_df = final_df.dropna(subset=['price', 'market_cap'])
    print(f"After removing missing price/market_cap: {len(final_df):,} ({len(final_df)/initial_count:.1%})")
    final_df = final_df[(final_df['price'] > 0) & (final_df['market_cap'] > 0)]
    print(f"After removing non-positive price/market_cap: {len(final_df):,}")
    final_df = final_df.sort_values(['isin', 'date'])

    # 9) Save final dataset
    output_file = "results/ptrees_final_dataset.csv"
    final_df.to_csv(output_file, index=False)

    print(f"\nFINAL PTREES DATASET CREATED!")
    print("=" * 50)
    print(f"File: {output_file}")
    print(f"Total observations: {len(final_df):,}")
    print(f"Companies: {final_df['isin'].nunique()}")
    print(f"Columns: {len(final_df.columns)}")
    print(f"Date range: {final_df['date'].min()} to {final_df['date'].max()}")

    # Optional quick coverage snapshot (detailed report via data_auditor.py)
    generate_coverage_report(final_df)

    return final_df

if __name__ == "__main__":
    main()
