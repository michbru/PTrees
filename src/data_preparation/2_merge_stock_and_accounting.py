"""
================================================================================
STEP 2: MERGE STOCK AND ACCOUNTING DATA
================================================================================

PURPOSE:
    Integrate Swedish stock market data (LSEG) with accounting ratios (Serrano)
    using the ISIN→ORGNR mapping as a bridge.

INPUT:
    - data/raw/lseg/ptrees_final_dataset.csv (stock prices, returns, market data)
    - data/intermediate/isin_orgnr_mapping.csv (ISIN → ORGNR crosswalk)
    - data/intermediate/serrano_nyckeltal_full.csv (accounting ratios)

OUTPUT:
    - data/intermediate/stock_with_accounting.csv

WHAT THIS DOES:
    1. Adds ORGNR to stock data via ISIN mapping
       - Stock data has ISIN (SE0000108656)
       - Mapping table provides ISIN → ORGNR bridge
       - Result: Stock data now has both ISIN and ORGNR
    
    2. Merges with Serrano accounting data on [ORGNR, year]
       - Stock data: monthly observations with ORGNR and year
       - Serrano data: annual observations with ORGNR and year
       - Join key: [ORGNR, year]
       - Left join: preserves all stock observations
    
    3. Adds 12 accounting characteristics:
       - roe, roa, operating_margin, net_margin
       - cash_liquidity, equity_ratio, debt_ratio
       - capital_turnover, inventory_turnover, receivables_turnover
       - revenue_per_employee, profit_pct

WHY WE DO THIS:
    - Stock prices alone don't tell the full story
    - Accounting fundamentals (profitability, leverage, efficiency) are critical
      predictors of future returns
    - Serrano provides comprehensive Swedish accounting data not in LSEG
    - Integration increases characteristics from 19 → ~34

KEY TECHNICAL DETAIL - THE MERGE STRUCTURE:
    
    Stock Data (Monthly):          Serrano Data (Annual):
    ┌─────────────────────┐        ┌──────────────────┐
    │ ISIN  │ Year│ Month │        │ ORGNR │ Year│ROE│
    │ SE01  │ 2012│ Jan   │   +    │556223 │2012 │15%│
    │ SE01  │ 2012│ Feb   │   =    │556223 │2012 │15%│
    │ SE01  │ 2012│ Mar   │        │556223 │2012 │15%│
    └─────────────────────┘        └──────────────────┘
            ↓
    Step 1: Map ISIN→ORGNR         Step 2: Join on [ORGNR, year]
            ↓                               ↓
    ┌──────────────────────┐        ┌──────────────────────┐
    │ ISIN  │ ORGNR │ Year │        │ ISIN  │ Year│Month│ROE│
    │ SE01  │556223 │ 2012 │        │ SE01  │ 2012│ Jan │15%│
    │ SE01  │556223 │ 2012 │        │ SE01  │ 2012│ Feb │15%│
    │ SE01  │556223 │ 2012 │        │ SE01  │ 2012│ Mar │15%│
    └──────────────────────┘        └──────────────────────┘
    
    IMPORTANT: All months in 2012 get the SAME accounting data (Dec 31, 2012
    fiscal year-end). This creates a forward-looking bias that MUST be corrected
    with publication lag in Step 3.

COVERAGE EXPECTATIONS:
    - Not all stocks will have accounting data (~80-90% coverage)
    - Reasons for missing data:
      1. ISIN doesn't map to ORGNR (foreign companies, ETFs, bonds)
      2. ORGNR exists but not in Serrano (small/private companies)
      3. Year mismatch (Serrano 1997-2024, stocks 1997-2022)
    
    - Typical coverage: 15-25% of stock-month observations
      (concentrated in larger, publicly traded Swedish companies)

ASSUMPTIONS & LIMITATIONS:
    1. Merge Structure:
       - Match on publication date (accounting_year/month), not fiscal period
       - Assumes Step 1 correctly calculated 4-month publication lag
       - Left join preserves ALL stock observations (accounting is optional feature)

    2. Share Classes:
       - Multiple share classes (A/B shares) share same ORGNR
       - All classes get same accounting data (correct - same underlying company)
       - Example: Volvo A and Volvo B both get same ROE

    3. Forward-Fill Logic:
       - Once accounting published, remains valid until next update
       - Example: Apr 2012 fiscal 2011 ROE → used through Mar 2013
       - This matches real-world information availability

    4. Coverage:
       - Not all stocks have accounting data (~80-90% coverage expected)
       - Missing data reasons:
         a) Foreign companies (non-Swedish ISIN, no ORGNR)
         b) Small/private companies (ORGNR exists, not in Serrano)
         c) Timing mismatches (Serrano 1997-2024, stocks may differ)
       - Missing accounting treated as optional features (filled with neutral ranks later)

    5. Data Timing:
       - Serrano accounting: 4-month publication lag from Step 1
       - Stock data: Real-time prices, returns (no lag needed)
       - Merge preserves Serrano timing (no additional lag applied here)

VERIFICATION STATUS (2025-01-26):
    ✓ Merge logic verified with company examples (Lundin Oil, Active Biotech, AGA)
    ✓ Confirmed merge on [orgnr, year, month] = [orgnr, accounting_year, accounting_month]
    ✓ Forward-fill verified to work correctly within stocks
    ✓ Fiscal 1997 data correctly matched to April 1998 stock observations

Author: Michael
Date: 2025-01-23
================================================================================
"""

import pandas as pd
import numpy as np
from pathlib import Path

def merge_stock_and_accounting():
    """Merge stock data with Serrano accounting via ISIN→ORGNR mapping."""
    
    print("="*80)
    print("STEP 2: MERGING STOCK AND ACCOUNTING DATA")
    print("="*80)
    
    script_dir = Path(__file__).parent
    
    # Load stock data (monthly observations with prices, returns, market data)
    print("\nLoading data files...")
    stock = pd.read_csv((script_dir / '../../data/raw/lseg/ptrees_final_dataset.csv').resolve())
    print(f"  Stock data: {len(stock):,} observations, {stock['isin'].nunique()} stocks")
    
    # Load ISIN-to-ORGNR mapping (pre-existing)
    mapping = pd.read_csv((script_dir / '../../data/intermediate/isin_orgnr_mapping.csv').resolve())
    print(f"  ISIN→ORGNR mapping: {len(mapping)} ISINs → {mapping['orgnr'].nunique()} ORGNRs")
    
    # Add ORGNR to stock data via ISIN
    # This gives us the bridge to connect with Serrano data
    stock_with_orgnr = stock.merge(
        mapping[['isin', 'orgnr']],
        on='isin',
        how='left'  # Left join: keep all stock records, even without ORGNR
    )
    has_orgnr = stock_with_orgnr['orgnr'].notna()
    print(f"  Matched: {has_orgnr.sum():,} ({100*has_orgnr.mean():.1f}%) stock observations have ORGNR")
    
    # Load Serrano accounting data (annual observations with pre-calculated availability)
    serrano = pd.read_csv((script_dir / '../../data/intermediate/serrano_nyckeltal_full.csv').resolve())
    print(f"  Serrano data: {len(serrano):,} company-years, {serrano['orgnr'].nunique():,} companies")
    
    # Ensure ORGNR format matches
    stock_with_orgnr['orgnr'] = stock_with_orgnr['orgnr'].astype(str)
    serrano['orgnr'] = serrano['orgnr'].astype(str)
    
    # MERGE LOGIC - HOW FISCAL DATA MAPS TO STOCK OBSERVATIONS:
    # -----------------------------------------------------------------
    # Stock observations have (year, month) from their trading date.
    # Serrano has (accounting_year, accounting_month) = when data becomes public.
    #
    # Example walkthrough:
    #   1. Fiscal year 2011 ends Dec 31, 2011
    #   2. Step 1 calculates: accounting_year=2012, accounting_month=4 (Apr)
    #   3. This merge matches stock observations at 2012-04 with that accounting data
    #   4. Result: April 2012 stock data gets fiscal 2011 accounting (correct!)
    #
    # Key insight: We're matching on the PUBLICATION date, not the fiscal period.
    # This ensures we only use accounting data that was actually available at trade time.
    print("\nMerging stock + accounting...")
    final = stock_with_orgnr.merge(
        serrano,
        left_on=['orgnr', 'year', 'month'],
        right_on=['orgnr', 'accounting_year', 'accounting_month'],
        how='left',
        suffixes=('', '_serrano')
    )
    
    # Calculate coverage statistics BEFORE forward-fill
    # Use roe as indicator (first Serrano column)
    has_serrano = final['roe'].notna()
    coverage_pct_before = 100 * has_serrano.sum() / len(final)
    
    # Forward-fill accounting data within each stock
    # Once accounting is published, it remains valid until next update
    # Example: April 2012 gets fiscal 2011 ROE, May-Dec 2012 carry it forward
    print(f"  Coverage before forward-fill: {coverage_pct_before:.1f}%")
    print(f"  Applying forward-fill within each stock...")
    
    accounting_cols = ['roe', 'roa_serrano', 'operating_margin', 'net_margin',
                      'cash_liquidity', 'equity_ratio', 'debt_ratio',
                      'capital_turnover', 'inventory_turnover', 'receivables_turnover',
                      'revenue_per_employee', 'profit_pct']
    
    # Only forward-fill columns that exist
    accounting_cols = [col for col in accounting_cols if col in final.columns]
    
    # Sort by stock and date to ensure proper forward-fill order
    final = final.sort_values(['isin', 'year', 'month'])
    
    # Forward-fill within each stock (group by isin)
    # .ffill() carries last non-NaN value forward (standard pandas method)
    for col in accounting_cols:
        final[col] = final.groupby('isin')[col].ffill()
    
    # Calculate coverage statistics AFTER forward-fill
    has_serrano_after = final['roe'].notna()
    coverage_pct_after = 100 * has_serrano_after.sum() / len(final)
    
    print(f"  Coverage after forward-fill: {coverage_pct_after:.1f}% (+{coverage_pct_after - coverage_pct_before:.1f}pp)")
    
    companies_with_data = final[has_serrano_after][['name', 'orgnr']].drop_duplicates()
    
    # Save integrated dataset
    output_file = (script_dir / '../../data/intermediate/stock_with_accounting.csv').resolve()
    final.to_csv(output_file, index=False)
    
    # Summary statistics
    print(f"\n{'='*80}")
    print("STOCK + ACCOUNTING MERGED")
    print(f"{'='*80}")
    print(f"  Records:                {len(final):,}")
    print(f"  Companies w/ accounting: {len(companies_with_data)}")
    print(f"  Accounting coverage:     {coverage_pct_after:.1f}%")
    print(f"  Publication lag:         4 months (built into merge)")
    print(f"  Forward-fill:            Within each stock until next update")
    print(f"  Output:                  {output_file.name}")
    print(f"{'='*80}\n")
    
    return final

if __name__ == '__main__':
    merge_stock_and_accounting()
