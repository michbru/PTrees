"""
PTree Data Preparation - Attempt 2
Relaxed NA requirements: Keep stocks with at least 10/19 characteristics
"""

import pandas as pd
import numpy as np
from pathlib import Path

def rank_cross_sectional(df, col):
    """Apply cross-sectional ranking by date, normalized to [0, 1]"""
    def rank_normalize(x):
        if x.isna().all():
            return x
        return x.rank(pct=True, method='average')

    return df.groupby('date')[col].transform(rank_normalize)

def prepare_ptree_data_relaxed(input_file, output_file, min_characteristics=10):
    """
    Prepare data with RELAXED missing data requirements

    Key changes from Attempt 1:
    - Don't drop rows with ANY missing characteristics
    - Only drop rows missing critical fields (return, market cap)
    - Keep stocks with at least min_characteristics (default 10/19)
    - Fill remaining NAs with cross-sectional medians
    """

    print("="*70)
    print("PTREE DATA PREPARATION - ATTEMPT 2 (RELAXED NA HANDLING)")
    print("="*70)

    print(f"\nLoading Swedish stock data...")
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df):,} observations")

    # Convert date
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['isin', 'date']).reset_index(drop=True)

    # Create identifiers
    isin_to_permno = {isin: i+1 for i, isin in enumerate(df['isin'].unique())}
    df['permno'] = df['isin'].map(isin_to_permno)
    df['gvkey'] = df['permno']
    df['exchcd'] = 1
    df['shrcd'] = 10

    # Returns and market cap
    # Use current_return for target (ret/xret), not return_1m which is now lagged
    df['ret'] = df['current_return']
    df['xret'] = df['ret']  # Can adjust for risk-free rate later
    df['lag_me'] = df.groupby('isin')['market_cap'].shift(1)
    df['log_me'] = np.log(df['market_cap'])
    df['lag_me'] = df['lag_me'].fillna(df['market_cap'])

    # Drop rows with missing CRITICAL fields
    critical_fields = ['ret', 'xret', 'market_cap', 'lag_me']
    before_drop = len(df)
    df = df.dropna(subset=critical_fields)
    print(f"\nDropped {before_drop - len(df):,} rows with missing critical fields (return, market cap)")
    print(f"Remaining: {len(df):,} observations")

    # Create ranked characteristics
    print(f"\nCreating ranked characteristics...")

    characteristic_mapping = {
        'market_cap': 'rank_me',
        'book_to_market': 'rank_bm',
        'momentum_12m': 'rank_mom12m',
        'return_1m': 'rank_mom1m',
        'volatility_12m': 'rank_beta',
        'turnover': 'rank_turn',
        'roa': 'rank_roa',
        'ep_ratio': 'rank_ep',
        'cfp_ratio': 'rank_cfp',
        'sp_ratio': 'rank_sp',
        'gross_profitability': 'rank_gma',
        'capex_to_assets': 'rank_cinvest',
        'debt_to_equity': 'rank_lev',
        'sales_growth': 'rank_sgr',
        'asset_turnover': 'rank_ato',
        'asset_quality': 'rank_noa',
        'cfo_to_assets': 'rank_roe',
        'asset_growth': 'rank_agr',
        'price_to_assets': 'rank_bm_ia'
    }

    # Create ranked characteristics
    for swedish_col, ptree_col in characteristic_mapping.items():
        if swedish_col in df.columns:
            df[ptree_col] = rank_cross_sectional(df, swedish_col)

    rank_cols = [col for col in df.columns if col.startswith('rank_')]

    # Count available characteristics per observation
    df['n_chars_available'] = df[rank_cols].notna().sum(axis=1)

    # Filter: keep only observations with at least min_characteristics
    print(f"\nFiltering: Keeping stocks with at least {min_characteristics}/{len(rank_cols)} characteristics...")
    before_filter = len(df)
    df = df[df['n_chars_available'] >= min_characteristics].copy()
    print(f"Dropped {before_filter - len(df):,} observations with < {min_characteristics} characteristics")
    print(f"Remaining: {len(df):,} observations")

    # Fill remaining NAs with cross-sectional medians (standard practice)
    print(f"\nImputing remaining NAs with cross-sectional medians...")
    for col in rank_cols:
        na_count_before = df[col].isna().sum()
        if na_count_before > 0:
            # Fill with cross-sectional median for each date
            df[col] = df.groupby('date')[col].transform(
                lambda x: x.fillna(x.median())
            )
            na_count_after = df[col].isna().sum()
            if na_count_after > 0:
                # If still NAs (entire cross-section is NA), use overall median
                df[col] = df[col].fillna(df[col].median())
            print(f"  {col}: Filled {na_count_before:,} NAs")

    # Add dummy industry codes
    df['ffi49'] = 1
    df['sic'] = 1000

    # Final data quality check
    print(f"\n" + "="*70)
    print("FINAL DATA SUMMARY")
    print("="*70)
    print(f"Total observations: {len(df):,}")
    print(f"Unique stocks: {df['permno'].nunique()}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Number of months: {df['date'].nunique()}")
    print(f"Characteristics: {len(rank_cols)}")

    # Stocks per month analysis
    stocks_per_month = df.groupby('date')['permno'].nunique()
    print(f"\nStocks per month:")
    print(f"  Mean: {stocks_per_month.mean():.0f}")
    print(f"  Median: {stocks_per_month.median():.0f}")
    print(f"  Min: {stocks_per_month.min()}")
    print(f"  Max: {stocks_per_month.max()}")

    # Check for remaining NAs
    print(f"\nRemaining NAs:")
    for col in rank_cols:
        na_count = df[col].isna().sum()
        if na_count > 0:
            print(f"  {col}: {na_count} ({na_count/len(df)*100:.2f}%)")

    # Verify no NAs in rank columns
    assert df[rank_cols].isna().sum().sum() == 0, "ERROR: Still have NAs in rank columns!"

    # Select output columns
    output_cols = [
        'gvkey', 'permno', 'sic', 'ret', 'exchcd', 'shrcd', 'date', 'ffi49',
        'lag_me', 'log_me'
    ] + rank_cols + ['xret']

    df_output = df[output_cols].copy()

    # Save
    print(f"\n" + "="*70)
    print("SAVING FILES")
    print("="*70)

    # Save feather (full data)
    feather_file = output_file
    df_output.to_feather(feather_file)
    print(f"Saved full data: {feather_file}")

    # Save CSV (full data for R)
    csv_file = str(output_file).replace('.feather', '_full.csv')
    df_output.to_csv(csv_file, index=False)
    print(f"Saved CSV: {csv_file}")

    # Save summary CSV (first 1000 rows for inspection)
    sample_file = str(output_file).replace('.feather', '_sample.csv')
    df_output.head(1000).to_csv(sample_file, index=False)
    print(f"Saved sample: {sample_file}")

    print(f"\n" + "="*70)
    print("SUCCESS! Data ready for PTree Attempt 2")
    print("="*70)
    print(f"\nKey improvements over Attempt 1:")
    print(f"  - Relaxed NA requirements (10+ chars instead of all 19)")
    print(f"  - Imputed remaining NAs with cross-sectional medians")
    print(f"  - Preserved early time periods (1997-2005)")
    print(f"  - Expected: More observations, especially in early years")

    return df_output

if __name__ == "__main__":
    # Paths (all relative to this folder - self-contained)
    script_dir = Path(__file__).parent
    analysis_root = script_dir.parent

    input_file = analysis_root / "data" / "ptrees_final_dataset.csv"
    output_file = analysis_root / "results" / "ptree_ready_data.feather"

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Run conversion with relaxed requirements
    df = prepare_ptree_data_relaxed(
        str(input_file),
        str(output_file),
        min_characteristics=10  # Require at least 10/19 characteristics
    )

    print("\n" + "="*70)
    print("READY TO RUN PTREE ANALYSIS")
    print("="*70)
    print("\nNext step: Run the R script for Attempt 2")
