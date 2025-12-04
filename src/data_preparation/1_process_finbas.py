"""
Step 1: Process Finbas Data to Monthly
=======================================
Input:  data/raw/finbas/raw_finbas_monthly.csv
Output: data/intermediate/finbas/finbas_monthly_clean.csv

Note: Aggregates to monthly (month-end) to align with P-Tree methodology.
      Market cap is taken at month-end (no forward-filling needed).
"""

import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_PATH = PROJECT_ROOT / 'data' / 'raw' / 'finbas' / 'raw_finbas_monthly.csv'
OUTPUT_PATH = PROJECT_ROOT / 'data' / 'intermediate' / 'finbas' / 'finbas_monthly_clean.csv'


def main():
    print("Step 1: Processing Finbas monthly data...")
    
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
    
    # 2. Exclude off-exchange and OTC data (unreliable, mostly redundant)
    # INOFF = unofficial/off-exchange, NOROTC = Nordic OTC
    # Analysis shows 72%+ of these ISINs already appear on proper exchanges
    if 'marketname' in df.columns:
        before_otc = len(df)
        df = df[~df['marketname'].isin(['INOFF', 'NOROTC'])].copy()
        print(f"  After excluding INOFF/NOROTC: {len(df):,} rows ({before_otc - len(df):,} removed)")
    
    # Standardize identifiers early
    if 'isin' in df.columns:
        df['isin'] = df['isin'].astype(str).str.upper().str.strip()

    # Rename columns
    # Note: Use totalmarketvalue (company-level) instead of marketvalue (share-class level)
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
        'totalmarketvalue': 'market_cap',  # Use total company market cap
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
    # Map observed exchange codes/variants to a small preference rank (lower is better)
    exchange_pref = {
        # Nasdaq Stockholm / main market (common codes/variants)
        'SSE': 1,
        'NASDAQ STOCKHOLM': 1,
        'NASDAQ OMX STOCKHOLM': 1,
        'NASDAQ': 1,

        # First North (alternative market)
        'SSEFN': 2,
        'FIRST NORTH STOCKHOLM': 2,
        'NASDAQ FIRST NORTH': 2,
        'FIRST NORTH': 2,

        # Nordic Growth Market
        'NGM': 3,
        'NGM EQUITY': 3,

        # Spotlight / AktieTorget
        'ATORG': 4,
        'SPOTLIGHT': 4,
        'SPOTLIGHT STOCK MARKET': 4,
        'AKTIETORGET': 4,
    }

    if 'exchange' in df.columns:
        # normalize and clean common variants
        df['exchange_norm'] = (
            df['exchange'].astype(str)
            .str.upper()
            .str.strip()
        )

        # map normalized values to our preference mapping; unknown -> 99 (low priority)
        df['exchange_rank'] = df['exchange_norm'].map(exchange_pref).fillna(99).astype('Int64')

        # Diagnostic: print coverage of the most common exchange codes (first run; cheap)
        try:
            top_ex = df['exchange_norm'].value_counts().head(20)
            print('  Exchange coverage (top values):')
            for exch, ct in top_ex.items():
                print(f"    {exch}: {ct:,}")
            unknowns = [v for v in df['exchange_norm'].unique() if v not in exchange_pref]
            if unknowns:
                sample_unknowns = unknowns[:20]
                print(f"  Unknown exchange_norm values (sample up to 20): {sample_unknowns}")
        except Exception:
            # diagnostics must not break the pipeline
            pass
    else:
        df['exchange_rank'] = pd.Series(99, index=df.index, dtype='Int64')

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

    # 4. Aggregate to monthly (month-end)
    # Take last trading day of each month for all variables
    print(f"  Aggregating to monthly (month-end)...")
    df['year_month'] = df['date'].dt.to_period('M')
    
    # Take last trading day of each month
    df_monthly = df.sort_values(['isin', 'date']).groupby(['isin', 'year_month']).last().reset_index()
    
    # Align all dates to actual month-end for consistency
    df_monthly['date'] = df_monthly['date'] + pd.offsets.MonthEnd(0)
    
    print(f"  Monthly observations: {len(df_monthly):,}")
    
    # 5. Calculate monthly returns
    df_monthly = df_monthly.sort_values(['isin', 'date'])
    df_monthly['ret_monthly'] = df_monthly.groupby('isin')['close'].pct_change(fill_method=None)
    
    # Select output columns
    output_cols = [
        'isin', 'ticker', 'name', 'exchange', 'date', 'year', 'month',
        'close', 'high', 'low', 'bid', 'ask',
        'turnover_sek', 'volume', 'book_value',
        'market_cap',  # Month-end market cap (no forward-fill needed)
        'ret_monthly',
    ]
    
    # Ensure all columns exist
    available_cols = [c for c in output_cols if c in df_monthly.columns]
    df_out = df_monthly[available_cols].copy()
    
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
    for col in ['close', 'market_cap', 'ret_monthly']:
        if col in df_out.columns:
            print(f"    {col}: {df_out[col].notna().mean()*100:.1f}%")
    
    return df_out


if __name__ == '__main__':
    df = main()
