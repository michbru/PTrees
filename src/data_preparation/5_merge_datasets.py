"""
Step 5: Merge Datasets (Simple Merge - No Lagging)
===================================================
This script merges the daily Finbas market data with the annual Serrano accounting data.

Strategy:
---------
Simple merge without lagging to verify data alignment first.
For each date in Finbas, we match the most recent fiscal year data available
based on fiscal_year_end <= date.

Lagging will be applied in a separate step after verifying this merge works correctly.

Logic:
1. Load Finbas (Daily) and Serrano (Annual).
2. Load ISIN-ORGNR Mapping.
3. Filter Serrano to only include public companies (ORGNRs in mapping).
   - Serrano contains both public and private companies
   - We only want public companies that have ISINs
4. Add ORGNR to Finbas.
5. Perform 'merge_asof':
   - For each Finbas row (date t), find the most recent Serrano row 
     where fiscal_year_end <= t.
   - Group by ORGNR.
6. Save merged dataset.

Input:
  - data/intermediate/finbas/finbas_daily_clean.csv
  - data/intermediate/serrano/serrano_accounting.csv
  - data/mappings/isin_orgnr_final.csv

Output:
  - data/intermediate/merged_data_daily.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Config
FINBAS_PATH = Path('data/intermediate/finbas/finbas_daily_clean.csv')
SERRANO_PATH = Path('data/intermediate/serrano/serrano_accounting.csv')
MAPPING_PATH = Path('data/mappings/isin_orgnr_final.csv')
OUTPUT_PATH = Path('data/processed/merged_data_daily.csv')

def clean_orgnr(orgnr_series):
    """
    Clean and standardize ORGNR to int64.
    
    Handles:
    - Float values (from CSV reading)
    - String values with hyphens (e.g., '556056-2091')
    - Decimal points from float conversion
    
    Returns: Int64 series (nullable integer type to handle NaN)
    """
    # Convert to string, remove hyphens and decimal points
    cleaned = orgnr_series.astype(str).str.replace('-', '', regex=False).str.replace('.0', '', regex=False)
    # Convert to numeric (Int64 to handle NaN)
    return pd.to_numeric(cleaned, errors='coerce').astype('Int64')


def main():
    print("Step 5: Merging Datasets with Lagging...")
    
    # 1. Load Data
    print("  Loading datasets...")
    if not FINBAS_PATH.exists() or not SERRANO_PATH.exists() or not MAPPING_PATH.exists():
        print("  [ERROR] Input files missing.")
        return

    df_finbas = pd.read_csv(FINBAS_PATH, low_memory=False)
    df_serrano = pd.read_csv(SERRANO_PATH, low_memory=False)
    df_mapping = pd.read_csv(MAPPING_PATH)
    
    print(f"    Finbas: {len(df_finbas):,} rows")
    print(f"    Serrano: {len(df_serrano):,} rows")
    print(f"    Mapping: {len(df_mapping):,} rows")
    
    # 2. Prepare Mapping
    print("  Preparing ISIN-ORGNR mapping...")
    # Drop rows without ORGNR
    df_mapping = df_mapping.dropna(subset=['orgnr'])
    
    # Clean ORGNR using helper function
    df_mapping['orgnr'] = clean_orgnr(df_mapping['orgnr'])
    
    # Create ISIN -> ORGNR map
    isin_map = df_mapping.set_index('isin')['orgnr'].to_dict()
    
    # Get set of public company ORGNRs (for filtering Serrano)
    public_orgnrs = set(df_mapping['orgnr'].dropna())
    print(f"    Unique public ORGNRs in mapping: {len(public_orgnrs)}")
    
    # 3. Filter Serrano to Public Companies Only
    print("  Filtering Serrano to public companies...")
    print(f"    Serrano before filtering: {len(df_serrano):,} rows, {df_serrano['orgnr'].nunique():,} unique ORGNRs")
    
    df_serrano = df_serrano[df_serrano['orgnr'].isin(public_orgnrs)].copy()
    
    print(f"    Serrano after filtering: {len(df_serrano):,} rows, {df_serrano['orgnr'].nunique()} unique ORGNRs")
    
    if len(df_serrano) == 0:
        print("  [ERROR] No overlap between mapping and Serrano!")
        print("  This suggests a data type or format mismatch.")
        return

    
    # 4. Add ORGNR to Finbas
    print("  Mapping ISINs to ORGNRs...")
    df_finbas['orgnr'] = df_finbas['isin'].map(isin_map)
    
    # Filter Finbas to only those with mapped ORGNR?
    # Ideally yes, because we can't calculate accounting chars without it.
    # But we might want to keep them for price-only chars.
    # Let's keep all, but accounting cols will be NaN for unmapped.
    mapped_rows = df_finbas['orgnr'].notna().sum()
    print(f"    {mapped_rows:,} / {len(df_finbas):,} Finbas rows have mapped ORGNR ({mapped_rows/len(df_finbas)*100:.1f}%)")
    
    # 5. Prepare Serrano for Merge
    print("  Preparing accounting data...")
    
    # Ensure dates are datetime
    df_serrano['fiscal_year_end'] = pd.to_datetime(df_serrano['fiscal_year_end'])
    df_serrano['fiscal_year_start'] = pd.to_datetime(df_serrano['fiscal_year_start'])
    
    # Sort for asof merge (by fiscal_year_end)
    df_serrano = df_serrano.sort_values('fiscal_year_end')
    
    # 6. Merge (asof)
    print("  Performing as-of merge...")
    
    # We need to merge on ORGNR and Date
    # merge_asof requires both dfs to be sorted by the key (date)
    
    # Prepare Finbas
    df_finbas['date'] = pd.to_datetime(df_finbas['date'])
    df_finbas = df_finbas.sort_values('date')
    
    # We can't do a simple merge_asof with 'by' argument if there are multiple stocks.
    # Pandas merge_asof supports 'by' argument!
    
    # Strategy: Split Finbas into Mapped and Unmapped
    df_finbas_mapped = df_finbas.dropna(subset=['orgnr']).copy()
    df_finbas_unmapped = df_finbas[df_finbas['orgnr'].isna()].copy()
    
    # Ensure ORGNR types match for merge (both must be int64)
    df_finbas_mapped['orgnr'] = df_finbas_mapped['orgnr'].astype('int64')
    df_serrano['orgnr'] = df_serrano['orgnr'].astype('int64')
    
    # Sort by date for merge_asof
    df_finbas_mapped = df_finbas_mapped.sort_values('date')
    df_serrano = df_serrano.sort_values('fiscal_year_end')
    
    # Perform merge
    # For each date, get the most recent fiscal year data where fiscal_year_end <= date
    # This means we're using accounting data AS SOON AS the fiscal year ends
    # (no lag applied - we'll add that in a separate step if needed)
    merged_mapped = pd.merge_asof(
        df_finbas_mapped,
        df_serrano,
        left_on='date',
        right_on='fiscal_year_end',
        by='orgnr',
        direction='backward' # Find the latest fiscal_year_end <= date
    )
    
    # Concatenate back with unmapped?
    # USER REQUEST: "only keep these 552 companies"
    # So we DISCARD the unmapped companies and any rows that didn't find a match.
    
    print("  Filtering to only rows with valid accounting data...")
    df_final = merged_mapped.dropna(subset=['sales'])
    
    # Check how many unique ISINs remain
    unique_isins = df_final['isin'].nunique()
    print(f"    Remaining companies (ISINs): {unique_isins}")
    
    df_final = df_final.sort_values(['isin', 'date'])
    
    print(f"    Merged dataset: {len(df_final):,} rows")
    
    # 7. Save
    print(f"  Saving to {OUTPUT_PATH}...")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(OUTPUT_PATH, index=False)
    print("  Done.")
    
    # Validation
    print("\n  Validation:")
    sample = df_final.dropna(subset=['sales']).head(5)
    if not sample.empty:
        print("    Sample rows with accounting data:")
        for idx, row in sample.iterrows():
            print(f"\n    Row {idx}:")
            print(f"      ISIN: {row['isin']}")
            print(f"      Date: {row['date']}")
            print(f"      Fiscal Year End: {row['fiscal_year_end']}")
            print(f"      Fiscal Year: {row['fiscal_year']}")
            lag_days = (pd.to_datetime(row['date']) - pd.to_datetime(row['fiscal_year_end'])).days
            print(f"      Days since fiscal year end: {lag_days}")
            if lag_days < 0:
                print(f"      [ERROR] Fiscal year end is AFTER the date! Data leak!")
            else:
                print(f"      [OK] Fiscal year end is before the date.")
    
    # Summary statistics
    print("\n  Merge Statistics:")
    total_rows = len(df_final)
    rows_with_accounting = df_final['sales'].notna().sum()
    print(f"    Total rows: {total_rows:,}")
    print(f"    Rows with accounting data: {rows_with_accounting:,} ({rows_with_accounting/total_rows*100:.1f}%)")
    print(f"    Rows without accounting: {total_rows - rows_with_accounting:,}")

if __name__ == "__main__":
    main()
