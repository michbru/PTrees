"""
Data Adapter for PTree Analysis
Converts Swedish stock data to PTree-compatible format
"""

import pandas as pd
import numpy as np
from pathlib import Path

def rank_cross_sectional(df, col):
    """
    Apply cross-sectional ranking by date
    Ranks are normalized to [0, 1] within each time period
    """
    def rank_normalize(x):
        if x.isna().all():
            return x
        return x.rank(pct=True, method='average')

    return df.groupby('date')[col].transform(rank_normalize)

def prepare_ptree_data(input_file, output_file):
    """
    Prepare Swedish stock data for PTree analysis

    Required PTree columns:
    - permno: Stock identifier (we'll use numeric ID from isin)
    - date: Date in YYYY-MM-DD format
    - ret: Stock return (we have return_1m)
    - xret: Excess return (ret - risk_free_rate, we'll assume 0 for now)
    - lag_me: Lagged market cap for weighting
    - rank_* : Cross-sectionally ranked characteristics (61 in original, we have 19)
    - log_me: Log of market cap
    """

    print("Loading Swedish stock data...")
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df):,} observations")

    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])

    # Sort by isin and date
    df = df.sort_values(['isin', 'date']).reset_index(drop=True)

    # Create numeric stock identifier (permno equivalent)
    isin_to_permno = {isin: i+1 for i, isin in enumerate(df['isin'].unique())}
    df['permno'] = df['isin'].map(isin_to_permno)

    # Create gvkey (use same as permno for simplicity)
    df['gvkey'] = df['permno']

    # Create exchange code (1 = main market, simplified)
    df['exchcd'] = 1

    # Create share code (10 = ordinary common shares, simplified)
    df['shrcd'] = 10

    # Returns
    df['ret'] = df['return_1m']

    # Excess return (assuming risk-free rate = 0 for now, can be adjusted)
    df['xret'] = df['ret']

    # Lagged market cap for portfolio weighting
    df['lag_me'] = df.groupby('isin')['market_cap'].shift(1)

    # Log market cap
    df['log_me'] = np.log(df['market_cap'])

    # Fill NaN in lag_me with current market_cap for first observation
    df['lag_me'] = df['lag_me'].fillna(df['market_cap'])

    print("\nCreating ranked characteristics...")

    # Map Swedish characteristics to rank_* format
    # Original PTree uses 61 characteristics, we have 19
    characteristic_mapping = {
        'market_cap': 'rank_me',           # Size
        'book_to_market': 'rank_bm',        # Value
        'momentum_12m': 'rank_mom12m',      # Momentum
        'return_1m': 'rank_mom1m',          # Short-term momentum
        'volatility_12m': 'rank_beta',      # Risk proxy (using vol as beta proxy)
        'turnover': 'rank_turn',            # Turnover
        'roa': 'rank_roa',                  # Profitability
        'ep_ratio': 'rank_ep',              # Earnings-to-price
        'cfp_ratio': 'rank_cfp',            # Cash flow-to-price
        'sp_ratio': 'rank_sp',              # Sales-to-price
        'gross_profitability': 'rank_gma',  # Gross margin
        'capex_to_assets': 'rank_cinvest',  # Investment
        'debt_to_equity': 'rank_lev',       # Leverage
        'sales_growth': 'rank_sgr',         # Sales growth
        'asset_turnover': 'rank_ato',       # Asset turnover
        'asset_quality': 'rank_noa',        # Asset quality (NOA proxy)
        'cfo_to_assets': 'rank_roe',        # Operating performance (using CFO as ROE proxy)
        'asset_growth': 'rank_agr',         # Asset growth
        'price_to_assets': 'rank_bm_ia'     # Price-to-assets (inverse BM)
    }

    # Create ranked characteristics
    for swedish_col, ptree_col in characteristic_mapping.items():
        if swedish_col in df.columns:
            print(f"  Creating {ptree_col} from {swedish_col}")
            df[ptree_col] = rank_cross_sectional(df, swedish_col)
        else:
            print(f"  WARNING: {swedish_col} not found, creating NA column for {ptree_col}")
            df[ptree_col] = np.nan

    # Add dummy industry classification (ffi49 = Fama-French 49 industries)
    # For now, assign all to industry 1 (can be refined later)
    df['ffi49'] = 1

    # Add dummy SIC code
    df['sic'] = 1000

    print("\nData preparation complete!")
    print(f"Observations: {len(df):,}")
    print(f"Stocks: {df['permno'].nunique()}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Characteristics: {len([col for col in df.columns if col.startswith('rank_')])}")

    # Check data quality
    print("\nData quality check:")
    rank_cols = [col for col in df.columns if col.startswith('rank_')]
    for col in rank_cols:
        pct_missing = df[col].isna().mean() * 100
        print(f"  {col}: {100-pct_missing:.1f}% coverage")

    # Select columns for output (matching PTree format)
    output_cols = [
        'gvkey', 'permno', 'sic', 'ret', 'exchcd', 'shrcd', 'date', 'ffi49',
        'lag_me', 'log_me'
    ] + rank_cols + ['xret']

    df_output = df[output_cols].copy()

    # Save to feather format (efficient for large datasets)
    print(f"\nSaving to {output_file}...")
    df_output.to_feather(output_file)

    # Also save a CSV version for inspection
    csv_file = output_file.replace('.feather', '.csv')
    df_output.head(1000).to_csv(csv_file, index=False)
    print(f"Saved sample (1000 rows) to {csv_file}")

    print("\nSUCCESS: Data ready for PTree analysis!")

    return df_output

if __name__ == "__main__":
    # Paths
    project_root = Path(__file__).parent.parent
    input_file = project_root / "results" / "ptrees_final_dataset.csv"
    output_file = project_root / "results" / "ptree_ready_data.feather"

    # Run conversion
    df = prepare_ptree_data(str(input_file), str(output_file))

    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Review the data quality output above")
    print("2. Check the sample CSV file for correctness")
    print("3. Consider adding risk-free rate data for proper excess returns")
    print("4. Run a test PTree model with subset of data")
    print("5. Create R script to load this data into PTree package")