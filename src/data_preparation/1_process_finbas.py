"""
Step 1: Process Finbas Daily Data
=================================
Input:  data/raw/finbas/raw_finbas_daily.csv
Output: data/intermediate/finbas/finbas_daily_clean.csv

Note: Market cap only available at month-end, forward-filled to daily.
"""

import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_PATH = PROJECT_ROOT / 'data' / 'raw' / 'finbas' / 'raw_finbas_daily.csv'
OUTPUT_PATH = PROJECT_ROOT / 'data' / 'intermediate' / 'finbas' / 'finbas_daily_clean.csv'


def main():
    print("Step 1: Processing Finbas daily data...")
    
    # Load
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_PATH}")
        
    df = pd.read_csv(RAW_PATH, sep=';', low_memory=False)
    print(f"  Loaded: {len(df):,} rows, {df['isin'].nunique():,} ISINs")
    
    # 1. Filter to Swedish SEK stocks (SE ISIN + SEK Currency)
    # strict filtering avoids foreign cross-listings with poor data
    df = df[
        (df['currency'] == 'SEK') & 
        (df['isin'].str.startswith('SE', na=False))
    ].copy()
    
    print(f"  After SE/SEK filters: {len(df):,} rows, {df['isin'].nunique():,} ISINs")
    
    # Standardize identifiers early
    if 'isin' in df.columns:
        df['isin'] = df['isin'].astype(str).str.upper().str.strip()

    # Rename columns
    df = df.rename(columns={
        'marketname': 'exchange',
        'day': 'date',
        'lastad': 'close',
        'askad': 'ask',
        'bidad': 'bid',
        'highad': 'high',
        'lowad': 'low',
        'oabad': 'turnover_sek',
        'oatad': 'volume',
        'bookvalue': 'book_value',
        'marketvalue': 'market_cap',
        'totalmarketvalue': 'total_market_cap',
    })
    
    # Parse dates
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date', 'isin'])
    
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    
    # 2. Coerce numeric columns to ensure math works correctly
    numeric_cols = [
        'close', 'high', 'low', 'bid', 'ask',
        'turnover_sek', 'volume', 'book_value',
        'market_cap', 'total_market_cap'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 3. Deterministic de-duplication per ISIN/Date
    # Prefer rows with higher turnover/volume and primary exchanges
    # Define a light-weight exchange preference (lower is better)
    exchange_pref = {
        'NASDAQ STOCKHOLM': 1,
        'FIRST NORTH STOCKHOLM': 2,
        'NGM EQUITY': 3,
        'SPOTLIGHT STOCK MARKET': 4,
    }
    if 'exchange' in df.columns:
        df['exchange_norm'] = df['exchange'].astype(str).str.upper().str.strip()
        df['exchange_rank'] = df['exchange_norm'].map(exchange_pref).fillna(99)
    else:
        df['exchange_rank'] = 99

    # Sort for deduplication tie-breakers:
    #  - date ascending (so time order preserved later)
    #  - exchange_rank ascending (prefer primary venues)
    #  - turnover_sek desc, volume desc (prefer liquid prints)
    sort_cols = ['isin', 'date', 'exchange_rank']
    asc_flags = [True, True, True]
    if 'turnover_sek' in df.columns:
        sort_cols.append('turnover_sek')
        asc_flags.append(False)
    if 'volume' in df.columns:
        sort_cols.append('volume')
        asc_flags.append(False)

    df = df.sort_values(sort_cols, ascending=asc_flags)
    before_dups = len(df)
    df = df.drop_duplicates(subset=['isin', 'date'], keep='first')
    after_dups = len(df)
    if before_dups != after_dups:
        print(f"  De-duplicated {before_dups - after_dups:,} rows on (isin, date) with liquidity/venue preference")

    # 4. Forward-fill market cap (Option 2: Simple & Robust)
    # We use simple forward-fill because:
    # 1. It's standard academic practice when daily shares aren't available.
    # 2. It avoids complex split-adjustment issues with "implied shares".
    # 3. Most characteristics use month-end market cap anyway.
    df['market_cap_filled'] = df.groupby('isin')['market_cap'].ffill()
    
    # 5. Calculate returns
    # Handle potential 0 prices to avoid inf
    df['close'] = df['close'].replace(0, np.nan)
    df['ret'] = df.groupby('isin')['close'].pct_change(fill_method=None)
    
    # Select output columns
    output_cols = [
        'isin', 'ticker', 'name', 'exchange', 'date', 'year', 'month',
        'close', 'high', 'low', 'bid', 'ask',
        'turnover_sek', 'volume', 'book_value',
        'market_cap', 'market_cap_filled', 'total_market_cap',
        'ret',
    ]
    
    # Ensure all columns exist
    available_cols = [c for c in output_cols if c in df.columns]
    df_out = df[available_cols].copy()
    
    # Sanity checks
    # Ensure uniqueness of (isin, date)
    dup_ct = df_out.duplicated(subset=['isin', 'date']).sum()
    if dup_ct > 0:
        raise ValueError(f"Duplicate (isin, date) pairs remain after dedup: {dup_ct}")

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(OUTPUT_PATH, index=False)
    
    # Summary
    print(f"\nOutput: {OUTPUT_PATH}")
    print(f"  Rows: {len(df_out):,}, ISINs: {df_out['isin'].nunique():,}")
    print(f"  Date range: {df_out['date'].min().date()} to {df_out['date'].max().date()}")
    
    # Coverage stats
    print(f"  Coverage:")
    for col in ['close', 'market_cap', 'market_cap_filled', 'ret']:
        if col in df_out.columns:
            print(f"    {col}: {df_out[col].notna().mean()*100:.1f}%")
    
    return df_out


if __name__ == '__main__':
    df = main()
