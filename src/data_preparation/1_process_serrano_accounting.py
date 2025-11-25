"""
================================================================================
STEP 1: PROCESS SERRANO ACCOUNTING DATA
================================================================================

PURPOSE:
    Extract and consolidate Swedish accounting ratios from Serrano database
    Stata files (nyckeltal1-10) into a single normalized dataset.

INPUT:
    - data/raw/serrano/Stata_2025/nyckeltal{1-10}.dta (10 Stata files)

OUTPUT:
    - data/intermediate/serrano_nyckeltal_full.csv

WHAT THIS DOES:
    1. Reads 10 Stata files containing pre-calculated accounting ratios
       - Each file covers different company-year observations
       - Total: ~666k firm-year observations from 1997-2024
    
    2. Extracts 12 key accounting ratios per company-year:
       - Profitability: ROE, ROA, operating margin, net margin, profit %
       - Liquidity: Cash liquidity ratio
       - Leverage: Equity ratio, debt ratio
       - Efficiency: Capital turnover, inventory turnover, receivables turnover
       - Productivity: Revenue per employee
    
    3. Standardizes company identifiers:
       - Converts ORGNR (Swedish organization number) to string format
       - Removes hyphens: "556223-9227" → "5562239227"
       - ORGNR is the key for matching with stock data via ISIN mapping
    
    4. Removes duplicate records:
       - Keeps most recent fiscal year-end when multiple exist
       - Deduplicates on [ORGNR, year]

WHY WE DO THIS:
    - Serrano provides comprehensive Swedish accounting data not available in LSEG
    - Pre-calculated ratios (nyckeltal) are faster than computing from raw statements
    - ORGNR is the Swedish standard company identifier needed for data integration
    - Consolidated file simplifies downstream merging with stock data

ASSUMPTIONS:
    - Fiscal year-end is typically December 31 for Swedish companies
    - When duplicates exist, the last record (by BSLSLUT date) is most accurate
    - All 10 files use consistent variable naming conventions

Author: Michael
Date: 2025-01-23
================================================================================
"""

import pandas as pd
import numpy as np
from pathlib import Path
import glob
import os

def clean_orgnr(val):
    """
    Robustly clean ORGNR to standard string format.
    Handles: ints (556223), floats (556223.0), strings ("556223-9227")
    """
    try:
        s = str(val).strip()
        # Remove hyphens and spaces
        s = s.replace('-', '').replace(' ', '')
        # If it looks like a float (ends in .0), strip it
        if s.endswith('.0'):
            s = s[:-2]
        return s
    except:
        return str(val)

def process_serrano_accounting():
    """Process all Serrano nyckeltal files into a single dataset."""
    
    all_data = []
    
    # Dynamic file finding instead of hardcoded range
    # Resolve path relative to this script file to ensure it works from any CWD
    script_dir = Path(__file__).parent
    base_path = (script_dir / '../../data/raw/serrano/Stata_2025').resolve()
    
    files = sorted(glob.glob(str(base_path / 'nyckeltal*.dta')))
    
    if not files:
        print(f"Error: No nyckeltal files found in {base_path}")
        return pd.DataFrame()

    print(f"Processing {len(files)} Serrano files...")

    # Process all found nyckeltal files
    for idx, stata_file in enumerate(files, 1):
        try:
            file_name = os.path.basename(stata_file)
            
            # Load Stata file (contains pre-calculated ratios for Swedish companies)
            df = pd.read_stata(stata_file)
            print(f"  [{idx}/{len(files)}] {file_name}: {len(df):,} records", end="")
            
            # Extract year from fiscal year-end date
            # BSLSLUT = Balance Sheet Date (fiscal year-end)
            df['BSLSLUT'] = pd.to_datetime(df['BSLSLUT'])
            df['year'] = df['BSLSLUT'].dt.year
            
            # Rename Serrano variables to English equivalents
            # Swedish -> English mapping for clarity
            df = df.rename(columns={
                'AVKEGKAP': 'roe',                    # Return on Equity
                'AVKTOTKAP': 'roa',                   # Return on Total Assets
                'RORMARG': 'operating_margin',        # Operating Margin
                'NETTOMARG': 'net_margin',            # Net Margin
                'KASSLIKV': 'cash_liquidity',         # Cash Liquidity Ratio
                'SOLIDITET': 'equity_ratio',          # Equity Ratio (Solidity)
                'SKULDGRAD': 'debt_ratio',            # Debt Ratio
                'KAPOMS': 'capital_turnover',         # Capital Turnover
                'LAGPAGOMS': 'inventory_turnover',    # Inventory Turnover
                'FONTOMS': 'receivables_turnover',    # Receivables Turnover
                'OMSPANST': 'revenue_per_employee',   # Revenue per Employee
                'VINSTPCT': 'profit_pct'              # Profit Percentage
            })
            
            # Convert ORGNR to standardized string format using robust cleaner
            # Removes hyphens, handles floats: "556223-9227" → "5562239227"
            df['orgnr'] = df['ORGNR'].apply(clean_orgnr)
            
            # CRITICAL: Calculate when this accounting data becomes available for trading
            # Swedish Annual Accounts Act (Årsredovisningslagen, SFS 1995:1554)
            # Chapter 7, §1: Annual reports must be filed within 4 months of fiscal year-end
            # Source: https://www.riksdagen.se/sv/dokument-lagar/dokument/svensk-forfattningssamling/arsredovisningslag-19951554_sfs-1995-1554
            #
            # Example: Fiscal year ends Dec 31, 2011 → Report published April 2012 (4 months later)
            # This accounts for: preparation time + audit + regulatory filing
            
            df['fiscal_month'] = df['BSLSLUT'].dt.month  # Extract fiscal year-end month
            df['available_month'] = df['fiscal_month'] + 4  # Add mandatory 4-month publication lag
            df['available_year'] = df['year']
            
            # Handle year rollover: If fiscal month is Sep-Dec, publication is next year
            # Example: Oct 31 fiscal end → Oct + 4 = month 14 → February next year
            year_rollover = df['available_month'] > 12
            df.loc[year_rollover, 'available_year'] += 1
            df.loc[year_rollover, 'available_month'] -= 12
            
            # Store as accounting_year/month for clear join logic in Step 2
            # These represent: "This accounting is available starting from (accounting_year, accounting_month)"
            df['accounting_year'] = df['available_year']
            df['accounting_month'] = df['available_month']
            
            # Select relevant columns for output
            cols = ['orgnr', 'year', 'BSLSLUT', 'accounting_year', 'accounting_month',
                    'roe', 'roa', 'operating_margin',
                    'net_margin', 'cash_liquidity', 'equity_ratio', 'debt_ratio',
                    'capital_turnover', 'inventory_turnover', 'receivables_turnover',
                    'revenue_per_employee', 'profit_pct']
            
            # Ensure all columns exist (handle missing cols in some files gracefully)
            available_cols = [c for c in cols if c in df.columns]
            df_subset = df[available_cols].copy()
            
            all_data.append(df_subset)
            print(f" → {len(df_subset):,} final")
            
        except Exception as e:
            print(f"\nWarning: Could not process {os.path.basename(stata_file)}: {e}")
            continue
    
    # Combine all files into single dataset
    if not all_data:
        print("\nError: No data processed.")
        return pd.DataFrame()
    
    print(f"\nConsolidating...")
    combined = pd.concat(all_data, ignore_index=True)
    
    # Sort by company and year, then by fiscal year-end date
    # Use mergesort for stability to respect file order if dates are identical
    combined = combined.sort_values(['orgnr', 'year', 'BSLSLUT'], kind='mergesort')
    
    # Remove duplicate company-years (keep most recent fiscal year-end)
    # Example: If company has both Jun 2012 and Dec 2012 fiscal year-ends,
    # we keep Dec 2012 as it's more standard and complete
    before_dedup = len(combined)
    combined = combined.drop_duplicates(subset=['orgnr', 'year'], keep='last')
    duplicates_removed = before_dedup - len(combined)
    
    # Save consolidated dataset
    output_file = (script_dir / '../../data/intermediate/serrano_nyckeltal_full.csv').resolve()
    combined.to_csv(output_file, index=False)
    
    # Summary statistics
    print(f"\n{'='*80}")
    print("SERRANO ACCOUNTING DATA PROCESSED")
    print(f"{'='*80}")
    print(f"  Records:             {len(combined):,}")
    print(f"  Unique companies:    {combined['orgnr'].nunique():,}")
    print(f"  Period:              {combined['year'].min()}-{combined['year'].max()}")
    print(f"  Duplicates removed:  {duplicates_removed:,}")
    print(f"  Publication lag:     4 months (Swedish Annual Accounts Act)")
    print(f"  Output:              {output_file.name}")
    print(f"{'='*80}\n")
    
    return combined

if __name__ == '__main__':
    process_serrano_accounting()
