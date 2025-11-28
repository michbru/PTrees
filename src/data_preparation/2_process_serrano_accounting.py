"""
Step 2: Process Serrano Accounting Data

This script:
1. Loads and merges all 10 nyckeltal files (financial ratios)
2. Loads and merges all 10 bokslut files (balance sheets)
3. Keeps only relevant variables for our characteristics
4. Saves to data/intermediate/serrano/serrano_accounting.csv

Date: 2025-11-28
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

RAW_DIR = Path('data/raw/serrano/Stata_2025')
OUTPUT_DIR = Path('data/intermediate/serrano')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Key variables we need from the Serrano data
# Based on VARIABLE_REGISTRY.py characteristics

NYCKELTAL_VARS = {
    # Identifiers and dates (always keep)
    'ORGNR': 'orgnr',
    'BSLSTART': 'fiscal_year_start',
    'BSLSLUT': 'fiscal_year_end',
    'BSTYP': 'accounting_type',

    # Financial ratios (from nyckeltal files)
    'AVKEGKAP': 'roe',  # Return on equity
    'AVKTOTKAP': 'roa',  # Return on assets
    'KAPOMS': 'asset_turnover',  # Asset turnover
    'RORMARG': 'operating_margin',  # Operating margin
    'NETTOMARG': 'net_margin',  # Net margin
    'FONTOMS': 'sales_growth',  # Sales growth
    'SKULDGRAD': 'debt_equity_ratio',  # Debt/Equity
    'SOLIDITET': 'equity_ratio',  # Equity/Assets
    'KASSLIKV': 'quick_ratio',  # Quick ratio
}

BOKSLUT_VARS = {
    # Identifiers (always keep)
    'ORGNR': 'orgnr',
    'BSLSTART': 'fiscal_year_start',
    'BSLSLUT': 'fiscal_year_end',

    # Income statement items
    'NTOMS': 'sales',  # Net sales
    'RAVAR': 'cogs_materials',  # Cost of goods sold - materials
    'HANDVAR': 'cogs_goods',  # Cost of goods sold - goods
    'PERSKOS': 'personnel_expense',  # Personnel expenses
    'AVSKRIV': 'depreciation',  # Depreciation
    'RORRESUL': 'operating_income',  # Operating profit/loss
    'RTEINEXT': 'interest_income',  # External interest income
    'RTEKOEXT': 'interest_expense',  # External interest expense
    'SKATTER': 'tax_expense',  # Taxes
    'RESAR': 'net_income',  # Net profit/loss

    # Balance sheet - Assets
    'TILLGSU': 'total_assets',  # Total assets
    'ANLTSU': 'fixed_assets',  # Total fixed assets
    'IMANLSU': 'intangible_assets',  # Intangible fixed assets
    'MATANLSU': 'tangible_assets',  # Tangible fixed assets (PPE)
    'BYGGMARK': 'ppe_buildings',  # Buildings and land
    'MASKINV': 'ppe_machinery',  # Machinery and equipment
    'OMSTGSU': 'current_assets',  # Total current assets
    'LAGERSU': 'inventory',  # Total inventories
    'KABASU': 'cash',  # Liquid assets (cash)
    'KUNDFORD': 'receivables',  # Accounts receivable

    # Balance sheet - Equity and Liabilities
    'EKSU': 'book_equity',  # Total equity
    'AKTIEKAP': 'share_capital',  # Share capital
    'LSKSU': 'long_term_debt',  # Total non-current liabilities
    'KSKSU': 'current_liabilities',  # Total current liabilities
    'KSKLEV': 'accounts_payable',  # Accounts payable

    # Other useful items
    'ANTANST': 'num_employees',  # Number of employees
    'STATUS': 'active_status',  # Active at year end
}

# =============================================================================
# FUNCTIONS
# =============================================================================

def load_and_merge_files(file_pattern: str, var_mapping: dict, num_files: int = 10) -> pd.DataFrame:
    """
    Load and combine multiple Stata files for one dataset family (nyckeltal or bokslut).
    - Reads only available columns (intersection with var_mapping keys), robust to schema differences.
    - Ensures dates are parsed, fiscal_year extracted, and duplicates resolved deterministically.
    - Concatenates vertically across files (typical Serrano distribution). If files carry different
      subsets of variables, vertical concat is still safe since columns align by name.

    Args:
        file_pattern: Pattern with {} for file number (e.g., 'nyckeltal{}.dta')
        var_mapping: Mapping of raw columns to standardized names
        num_files: Number of files to load (default: 10)

    Returns:
        Cleaned, deduplicated DataFrame with standardized column names
    """
    print(f"Loading {file_pattern.replace('{}', '1-' + str(num_files))}...")

    dfs = []
    total_rows = 0

    wanted_cols = list(var_mapping.keys())

    for i in range(1, num_files + 1):
        file_path = RAW_DIR / file_pattern.format(i)
        if not file_path.exists():
            print(f"  Warning: {file_path} not found, skipping...")
            continue

        print(f"  Loading {file_path.name}...", end='', flush=True)

        # Attempt to read only needed columns; fall back to full read if unsupported
        try:
            df_raw = pd.read_stata(file_path, columns=wanted_cols)
        except Exception:
            df_full = pd.read_stata(file_path)
            available = [c for c in wanted_cols if c in df_full.columns]
            df_raw = df_full[available].copy()

        print(f" {len(df_raw):,} rows -> ", end='', flush=True)

        # Clean immediately to reduce memory
        df_raw = clean_orgnr(df_raw)
        df_raw = ensure_datetime_columns(df_raw)
        df_raw = extract_fiscal_year(df_raw)
        df_raw = remove_duplicates(df_raw, subset=['ORGNR', 'fiscal_year'])

        # Rename standardized columns and keep only mapped + fiscal_year
        df_tidy = rename_columns(df_raw, var_mapping)

        print(f"{len(df_tidy):,} rows after cleaning")

        total_rows += len(df_tidy)
        dfs.append(df_tidy)

    if not dfs:
        return pd.DataFrame(columns=[v for v in var_mapping.values()] + ['fiscal_year'])

    # Concatenate all files
    print(f"  Concatenating all files...")
    merged = pd.concat(dfs, ignore_index=True)
    print(f"  Total after concat: {len(merged):,} rows")

    # Final dedup across all files on standardized cols
    merged = remove_duplicates(merged, subset=['orgnr', 'fiscal_year'])
    print(f"  Total after final dedup: {len(merged):,} rows")

    return merged

def clean_orgnr(df: pd.DataFrame) -> pd.DataFrame:
    """Convert ORGNR to integer and remove any invalid values."""
    df = df.copy()

    # Convert to integer (some might be float)
    df['ORGNR'] = df['ORGNR'].astype('Int64')

    # Remove any NaN or zero ORGNR
    before = len(df)
    df = df[df['ORGNR'].notna() & (df['ORGNR'] > 0)]
    after = len(df)

    if before > after:
        print(f"  Removed {before - after:,} rows with invalid ORGNR")

    return df

def extract_fiscal_year(df: pd.DataFrame) -> pd.DataFrame:
    """Extract fiscal year from BSLSLUT (end date)."""
    df = df.copy()

    # Critical: Drop rows where BSLSLUT is missing. 
    # A report without a date cannot be used.
    df = df.dropna(subset=['BSLSLUT'])

    # Extract year from fiscal year end date
    df['fiscal_year'] = pd.to_datetime(df['BSLSLUT']).dt.year

    return df

def ensure_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure date columns are proper datetimes when present."""
    df = df.copy()
    if 'BSLSLUT' in df.columns:
        df['BSLSLUT'] = pd.to_datetime(df['BSLSLUT'], errors='coerce')
    if 'BSLSTART' in df.columns:
        df['BSLSTART'] = pd.to_datetime(df['BSLSTART'], errors='coerce')
    return df

def rename_columns(df: pd.DataFrame, var_mapping: dict) -> pd.DataFrame:
    """Rename columns according to mapping, keep only mapped columns + fiscal_year."""
    # Select only columns that exist in the mapping
    existing_cols = [col for col in var_mapping.keys() if col in df.columns]

    # Also keep fiscal_year if it exists (created in extract_fiscal_year)
    if 'fiscal_year' in df.columns:
        cols_to_keep = existing_cols + ['fiscal_year']
    else:
        cols_to_keep = existing_cols

    df_subset = df[cols_to_keep].copy()

    # Rename to our standardized names
    df_subset = df_subset.rename(columns=var_mapping)

    return df_subset

def remove_duplicates(df: pd.DataFrame, subset: list) -> pd.DataFrame:
    """
    Remove duplicate rows, keeping the entry with the latest fiscal year end date.
    This handles cases where a company has multiple reports in the same year 
    (e.g., restructuring).
    """
    before = len(df)
    
    # Build robust sort keys to make dedup deterministic.
    # Prefer active status if present, then latest fiscal year end date.
    sort_cols = []
    asc = []

    if 'ORGNR' in df.columns:
        sort_cols.append('ORGNR'); asc.append(True)
    elif 'orgnr' in df.columns:
        sort_cols.append('orgnr'); asc.append(True)

    # Prefer active rows (STATUS or active_status)
    if 'STATUS' in df.columns:
        sort_cols.append('STATUS'); asc.append(False)
    elif 'active_status' in df.columns:
        sort_cols.append('active_status'); asc.append(False)

    # Fiscal year end date desc
    if 'BSLSLUT' in df.columns:
        # Ensure dtype
        if not np.issubdtype(df['BSLSLUT'].dtype, np.datetime64):
            df['BSLSLUT'] = pd.to_datetime(df['BSLSLUT'], errors='coerce')
        sort_cols.append('BSLSLUT'); asc.append(False)
    elif 'fiscal_year_end' in df.columns:
        if not np.issubdtype(df['fiscal_year_end'].dtype, np.datetime64):
            df['fiscal_year_end'] = pd.to_datetime(df['fiscal_year_end'], errors='coerce')
        sort_cols.append('fiscal_year_end'); asc.append(False)

    # BSTYP/accounting_type as final tie-breaker (ascending as a stable order)
    if 'BSTYP' in df.columns:
        sort_cols.append('BSTYP'); asc.append(True)
    elif 'accounting_type' in df.columns:
        sort_cols.append('accounting_type'); asc.append(True)

    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=asc, kind='mergesort')

    df = df.drop_duplicates(subset=subset, keep='first')
    after = len(df)

    if before > after:
        print(f"  Removed {before - after:,} duplicate rows")

    return df

# =============================================================================
# MAIN PROCESSING
# =============================================================================

def main():
    print("=" * 80)
    print("STEP 2: PROCESS SERRANO ACCOUNTING DATA")
    print("=" * 80)
    print()

    # -------------------------------------------------------------------------
    # 1. Load and merge nyckeltal files (financial ratios)
    # -------------------------------------------------------------------------
    print("1. Loading nyckeltal files (financial ratios)...")
    nyckeltal = load_and_merge_files('nyckeltal{}.dta', NYCKELTAL_VARS, num_files=10)
    print(f"  Final nyckeltal: {len(nyckeltal):,} rows, {len(nyckeltal.columns)} columns")
    if not nyckeltal.empty:
        dup_nyc = nyckeltal.duplicated(subset=['orgnr', 'fiscal_year']).sum()
        if dup_nyc:
            raise ValueError(f"Nyckeltal contains {dup_nyc} duplicate (orgnr, fiscal_year) rows after cleaning.")
    print()

    # -------------------------------------------------------------------------
    # 2. Load and merge bokslut files (balance sheets)
    # -------------------------------------------------------------------------
    print("2. Loading bokslut files (balance sheets)...")
    bokslut = load_and_merge_files('bokslut{}.dta', BOKSLUT_VARS, num_files=10)
    print(f"  Final bokslut: {len(bokslut):,} rows, {len(bokslut.columns)} columns")
    if not bokslut.empty:
        dup_bok = bokslut.duplicated(subset=['orgnr', 'fiscal_year']).sum()
        if dup_bok:
            raise ValueError(f"Bokslut contains {dup_bok} duplicate (orgnr, fiscal_year) rows after cleaning.")
    print()

    # -------------------------------------------------------------------------
    # 3. Merge nyckeltal and bokslut
    # -------------------------------------------------------------------------
    print("3. Merging nyckeltal and bokslut...")
    # Drop duplicate columns from nyckeltal before merging
    nyckeltal_cols_to_drop = ['fiscal_year_start', 'fiscal_year_end', 'accounting_type']
    nyckeltal = nyckeltal.drop(columns=[col for col in nyckeltal_cols_to_drop if col in nyckeltal.columns])

    # Merge on orgnr and fiscal_year
    merged = pd.merge(
        bokslut,
        nyckeltal,
        on=['orgnr', 'fiscal_year'],
        how='left',  # Keep all bokslut records
        suffixes=('', '_nyc')
    )
    print(f"  Merged: {len(merged):,} rows, {len(merged.columns)} columns")
    if not merged.empty:
        dup_mrg = merged.duplicated(subset=['orgnr', 'fiscal_year']).sum()
        if dup_mrg:
            raise ValueError(f"Merged dataset contains {dup_mrg} duplicate (orgnr, fiscal_year) keys.")
    # Sanity: fiscal_year_end year vs fiscal_year
    if 'fiscal_year_end' in merged.columns:
        fy_end = pd.to_datetime(merged['fiscal_year_end'], errors='coerce')
        match_rate = np.nan
        if 'fiscal_year' in merged.columns:
            match_rate = (fy_end.dt.year == merged['fiscal_year']).mean()
            print(f"  Sanity: fiscal_year_end year matches fiscal_year in {match_rate*100:.1f}% of rows")
    print()

    # -------------------------------------------------------------------------
    # 4. Save to CSV
    # -------------------------------------------------------------------------
    output_file = OUTPUT_DIR / 'serrano_accounting.csv'
    print(f"4. Saving to {output_file}...")
    merged.to_csv(output_file, index=False)
    print(f"  Saved {len(merged):,} rows, {len(merged.columns)} columns")
    print()

    # -------------------------------------------------------------------------
    # 5. Summary statistics
    # -------------------------------------------------------------------------
    print("5. Summary statistics:")
    print(f"  Unique companies (ORGNR): {merged['orgnr'].nunique():,}")
    print(f"  Fiscal years: {merged['fiscal_year'].min()} to {merged['fiscal_year'].max()}")
    print(f"  Total observations: {len(merged):,}")
    # Coverage on key variables
    key_cols = [
        'sales', 'total_assets', 'book_equity',
        'roa', 'roe', 'equity_ratio',
    ]
    for col in key_cols:
        if col in merged.columns:
            cov = merged[col].notna().mean() * 100
            print(f"  Coverage {col}: {cov:.1f}%")
    print()

    print("  Sample of data:")
    print(merged.head())
    print()

    print("  Data types:")
    print(merged.dtypes)
    print()

    print("=" * 80)
    print("STEP 2 COMPLETE!")
    print("=" * 80)

if __name__ == '__main__':
    main()
