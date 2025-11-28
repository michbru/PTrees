"""
Step 3: Merge Datasets with Lagging
===================================
This script merges the daily Finbas market data with the annual Serrano accounting data.

Lagging Strategy:
-----------------
To avoid look-ahead bias, we assume accounting data becomes available to investors
6 months after the fiscal year end. This is a standard academic assumption (Fama-French).

Logic:
1. Load Finbas (Daily) and Serrano (Annual).
2. Load ISIN-ORGNR Mapping.
3. Add ORGNR to Finbas.
4. Create 'available_date' in Serrano = fiscal_year_end + 6 months.
5. Perform 'merge_asof':
   - For each Finbas row (date t), find the most recent Serrano row 
     where available_date <= t.
   - Group by ORGNR.
6. Save merged dataset.

Input:
  - data/intermediate/finbas/finbas_daily_clean.csv
  - data/intermediate/serrano/serrano_accounting.csv
  - data/intermediate/isin_orgnr_mapping.csv

Output:
  - data/intermediate/merged_data_daily.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Config
FINBAS_PATH = Path('data/intermediate/finbas/finbas_daily_clean.csv')
SERRANO_PATH = Path('data/intermediate/serrano/serrano_accounting.csv')
MAPPING_PATH = Path('data/intermediate/isin_orgnr_mapping.csv')
OUTPUT_PATH = Path('data/intermediate/merged_data_daily.csv')

LAG_MONTHS = 6

def main():
    print("Step 3: Merging Datasets with Lagging...")
    
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
    # Create ISIN -> ORGNR map
    # Drop duplicates if any (keep first)
    df_mapping = df_mapping.dropna(subset=['orgnr'])
    df_mapping['orgnr'] = df_mapping['orgnr'].astype(int)
    isin_map = df_mapping.set_index('isin')['orgnr'].to_dict()
    
    # 3. Add ORGNR to Finbas
    print("  Mapping ISINs to ORGNRs...")
    df_finbas['orgnr'] = df_finbas['isin'].map(isin_map)
    
    # Filter Finbas to only those with mapped ORGNR?
    # Ideally yes, because we can't calculate accounting chars without it.
    # But we might want to keep them for price-only chars.
    # Let's keep all, but accounting cols will be NaN for unmapped.
    mapped_rows = df_finbas['orgnr'].notna().sum()
    print(f"    {mapped_rows:,} / {len(df_finbas):,} Finbas rows have mapped ORGNR ({mapped_rows/len(df_finbas)*100:.1f}%)")
    
    # 4. Prepare Serrano for Merge
    print("  Preparing accounting data (Lagging)...")
    
    # Ensure dates are datetime
    df_serrano['fiscal_year_end'] = pd.to_datetime(df_serrano['fiscal_year_end'])
    
    # Create available_date = fiscal_year_end + 6 months
    df_serrano['available_date'] = df_serrano['fiscal_year_end'] + pd.DateOffset(months=LAG_MONTHS)
    
    # Sort for asof merge
    df_serrano = df_serrano.sort_values('available_date')
    
    # 5. Merge (asof)
    print("  Performing as-of merge...")
    
    # We need to merge on ORGNR and Date
    # merge_asof requires both dfs to be sorted by the key (date)
    
    # Prepare Finbas
    df_finbas['date'] = pd.to_datetime(df_finbas['date'])
    df_finbas = df_finbas.sort_values('date')
    
    # We can't do a simple merge_asof with 'by' argument if there are multiple stocks.
    # Pandas merge_asof supports 'by' argument!
    
    # Ensure join columns match type
    # ORGNR in Finbas might be float due to NaNs, convert to nullable int or object
    # Serrano ORGNR is int.
    # Best to use float for both to handle NaNs safely during merge, or drop NaNs for the merge part.
    
    # Strategy: Split Finbas into Mapped and Unmapped
    df_finbas_mapped = df_finbas.dropna(subset=['orgnr']).copy()
    df_finbas_unmapped = df_finbas[df_finbas['orgnr'].isna()].copy()
    
    df_finbas_mapped['orgnr'] = df_finbas_mapped['orgnr'].astype(int)
    # Serrano orgnr is already int (from load or step 1) but let's ensure
    df_serrano['orgnr'] = df_serrano['orgnr'].astype(int)
    
    # Sort by date for merge_asof
    df_finbas_mapped = df_finbas_mapped.sort_values('date')
    df_serrano = df_serrano.sort_values('available_date')
    
    # Perform merge
    # left_on='date', right_on='available_date'
    # by='orgnr'
    merged_mapped = pd.merge_asof(
        df_finbas_mapped,
        df_serrano,
        left_on='date',
        right_on='available_date',
        by='orgnr',
        direction='backward' # Find the latest available_date <= date
    )
    
    # Concatenate back with unmapped (which will have NaN for accounting)
    # Ensure columns match
    # Get accounting columns from serrano (excluding join keys if needed)
    acct_cols = [c for c in df_serrano.columns if c not in ['orgnr', 'available_date']]
    
    # For unmapped, add these columns as NaN
    for col in acct_cols:
        df_finbas_unmapped[col] = np.nan
        
    # Also 'available_date'
    df_finbas_unmapped['available_date'] = pd.NaT
    
    # Combine
    df_final = pd.concat([merged_mapped, df_finbas_unmapped], ignore_index=True)
    df_final = df_final.sort_values(['isin', 'date'])
    
    print(f"    Merged dataset: {len(df_final):,} rows")
    
    # 6. Save
    print(f"  Saving to {OUTPUT_PATH}...")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(OUTPUT_PATH, index=False)
    print("  Done.")
    
    # Validation
    print("\n  Validation:")
    sample = df_final.dropna(subset=['sales']).head(1)
    if not sample.empty:
        print("    Sample row with accounting data:")
        print(f"      Date: {sample.iloc[0]['date']}")
        print(f"      Available Date: {sample.iloc[0]['available_date']}")
        print(f"      Fiscal Year End: {sample.iloc[0]['fiscal_year_end']}")
        lag = (sample.iloc[0]['date'] - sample.iloc[0]['fiscal_year_end']).days
        print(f"      Actual Lag: {lag} days")
        if lag < 180:
             print("      [WARNING] Lag is less than 180 days!")
        else:
             print("      [OK] Lag is sufficient.")

if __name__ == "__main__":
    main()
