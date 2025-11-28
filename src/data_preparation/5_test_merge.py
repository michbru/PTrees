"""
Test Merge Script - Small Sample
=================================
Tests the merge logic on small samples to debug quickly.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Config
FINBAS_PATH = Path('data/intermediate/finbas/finbas_daily_clean.csv')
SERRANO_PATH = Path('data/intermediate/serrano/serrano_accounting.csv')
MAPPING_PATH = Path('data/intermediate/isin_orgnr_mapping_final.csv')

# Sample sizes for testing
SAMPLE_ISINS = 10  # Test with 10 companies
SAMPLE_ROWS = 1000  # Sample 1000 rows from each dataset

def main():
    print("=" * 70)
    print("TEST MERGE - SMALL SAMPLE")
    print("=" * 70)
    
    # 1. Load Mapping (full, it's small)
    print("\n[1] Loading mapping...")
    df_mapping = pd.read_csv(MAPPING_PATH)
    df_mapping = df_mapping.dropna(subset=['orgnr'])
    
    # Clean ORGNR
    df_mapping['orgnr'] = df_mapping['orgnr'].astype(str).str.replace('-', '', regex=False)
    df_mapping['orgnr'] = pd.to_numeric(df_mapping['orgnr'], errors='coerce').astype('Int64')
    
    print(f"  Loaded {len(df_mapping)} mappings")
    print(f"  Sample ORGNRs: {df_mapping['orgnr'].head().tolist()}")
    
    # Get sample ISINs (only those with mappings)
    sample_isins = df_mapping['isin'].head(SAMPLE_ISINS).tolist()
    sample_orgnrs = df_mapping[df_mapping['isin'].isin(sample_isins)]['orgnr'].tolist()
    
    print(f"\n  Testing with {len(sample_isins)} ISINs:")
    for isin, orgnr in zip(sample_isins, sample_orgnrs):
        print(f"    {isin} -> {orgnr}")
    
    # 2. Load Finbas (sample)
    print(f"\n[2] Loading Finbas sample ({SAMPLE_ROWS} rows)...")
    df_finbas = pd.read_csv(FINBAS_PATH, nrows=SAMPLE_ROWS)
    
    # Filter to sample ISINs
    df_finbas = df_finbas[df_finbas['isin'].isin(sample_isins)]
    print(f"  Filtered to {len(df_finbas)} rows with sample ISINs")
    
    # Add ORGNR
    isin_map = df_mapping.set_index('isin')['orgnr'].to_dict()
    df_finbas['orgnr'] = df_finbas['isin'].map(isin_map)
    
    print(f"  Mapped {df_finbas['orgnr'].notna().sum()} / {len(df_finbas)} rows")
    
    # 3. Load Serrano (filter for our ORGNRs)
    print(f"\n[3] Loading Serrano for sample ORGNRs...")
    
    # Load Serrano in chunks and filter for our ORGNRs
    df_serrano_list = []
    chunk_size = 100000
    for chunk in pd.read_csv(SERRANO_PATH, chunksize=chunk_size):
        # Filter to our sample ORGNRs
        chunk_filtered = chunk[chunk['orgnr'].isin(sample_orgnrs)]
        if len(chunk_filtered) > 0:
            df_serrano_list.append(chunk_filtered)
        
        # Stop if we have enough data
        if len(df_serrano_list) > 0 and sum(len(df) for df in df_serrano_list) > 100:
            break
    
    if len(df_serrano_list) == 0:
        print("\n  [ERROR] No Serrano data found for sample ORGNRs!")
        print(f"  Sample ORGNRs we're looking for: {sample_orgnrs}")
        return
    
    df_serrano = pd.concat(df_serrano_list, ignore_index=True)
    
    print(f"  Loaded {len(df_serrano)} rows for sample ORGNRs")
    print(f"  Serrano ORGNR dtype: {df_serrano['orgnr'].dtype}")
    print(f"  Unique ORGNRs in Serrano: {df_serrano['orgnr'].unique().tolist()}")
    
    # 4. Prepare for merge
    print("\n[4] Preparing for merge...")
    df_finbas['date'] = pd.to_datetime(df_finbas['date'])
    df_serrano['fiscal_year_end'] = pd.to_datetime(df_serrano['fiscal_year_end'])
    
    df_finbas['orgnr'] = df_finbas['orgnr'].astype('Int64')
    df_serrano['orgnr'] = df_serrano['orgnr'].astype('Int64')
    
    # Split mapped/unmapped
    df_finbas_mapped = df_finbas.dropna(subset=['orgnr']).copy()
    df_finbas_unmapped = df_finbas[df_finbas['orgnr'].isna()].copy()
    
    print(f"  Finbas mapped: {len(df_finbas_mapped)} rows")
    print(f"  Finbas unmapped: {len(df_finbas_unmapped)} rows")
    
    # Sort
    df_finbas_mapped = df_finbas_mapped.sort_values('date')
    df_serrano = df_serrano.sort_values('fiscal_year_end')
    
    # 5. Perform merge
    print("\n[5] Performing merge...")
    print(f"  Finbas date range: {df_finbas_mapped['date'].min()} to {df_finbas_mapped['date'].max()}")
    print(f"  Serrano fiscal_year_end range: {df_serrano['fiscal_year_end'].min()} to {df_serrano['fiscal_year_end'].max()}")
    
    merged = pd.merge_asof(
        df_finbas_mapped,
        df_serrano,
        left_on='date',
        right_on='fiscal_year_end',
        by='orgnr',
        direction='backward'
    )
    
    print(f"  Merged: {len(merged)} rows")
    
    # 6. Check results
    print("\n[6] Checking results...")
    rows_with_accounting = merged['sales'].notna().sum()
    print(f"  Rows with accounting data: {rows_with_accounting} / {len(merged)} ({rows_with_accounting/len(merged)*100:.1f}%)")
    
    if rows_with_accounting > 0:
        print("\n  SUCCESS! Sample merged rows:")
        sample = merged.dropna(subset=['sales']).head(5)
        for idx, row in sample.iterrows():
            print(f"\n    ISIN: {row['isin']}, ORGNR: {row['orgnr']}")
            print(f"    Date: {row['date']}")
            print(f"    Fiscal Year End: {row['fiscal_year_end']}")
            print(f"    Sales: {row['sales']:,.0f}")
            lag_days = (pd.to_datetime(row['date']) - pd.to_datetime(row['fiscal_year_end'])).days
            print(f"    Lag: {lag_days} days")
    else:
        print("\n  [ERROR] No accounting data matched!")
        print("\n  Debugging info:")
        print(f"  Unique ORGNRs in Finbas: {df_finbas_mapped['orgnr'].unique().tolist()}")
        print(f"  Unique ORGNRs in Serrano: {df_serrano['orgnr'].unique().tolist()}")
        
        # Check for overlap
        finbas_orgnrs = set(df_finbas_mapped['orgnr'].unique())
        serrano_orgnrs = set(df_serrano['orgnr'].unique())
        overlap = finbas_orgnrs & serrano_orgnrs
        print(f"  Overlapping ORGNRs: {overlap}")

if __name__ == "__main__":
    main()
