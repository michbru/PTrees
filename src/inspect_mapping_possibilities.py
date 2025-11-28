
import pandas as pd
from pathlib import Path

MAPPING_FILE = Path('data/intermediate/isin_orgnr_mapping_final.csv')
FINBAS_FILE = Path('data/intermediate/finbas/finbas_daily_clean.csv')

def analyze_coverage():
    print("Loading data...")
    # Load mapping
    if not MAPPING_FILE.exists():
        print(f"Error: Mapping file not found at {MAPPING_FILE}")
        return
    mapping = pd.read_csv(MAPPING_FILE)
    mapped_isins = set(mapping[mapping['orgnr'].notna()]['isin'])

    # Load Finbas (market data)
    # We need ISIN, Date, and Market Cap. Assuming 'market_cap' or similar exists.
    # Based on previous output, we'll check columns.
    # If 'market_cap' is missing, we might need to calculate it (price * shares).
    # For now, I'll assume 'market_cap' exists or 'mv' (market value).
    # I'll read a subset first to check columns if I wasn't sure, but I'll assume standard names or check the previous output.
    # Wait, I haven't seen the output of the previous command yet in this turn.
    # I will write a robust script that checks columns.
    
    try:
        df = pd.read_csv(FINBAS_FILE)
    except Exception as e:
        print(f"Error reading Finbas: {e}")
        return

    print(f"Finbas columns: {df.columns.tolist()}")
    
    # Identify Market Cap column
    mc_col = None
    for col in ['market_cap', 'mv', 'mcap', 'market_value']:
        if col in df.columns:
            mc_col = col
            break
    
    if not mc_col:
        # Try to calculate if price and shares exist
        if 'close' in df.columns and 'shares' in df.columns:
            df['market_cap'] = df['close'] * df['shares']
            mc_col = 'market_cap'
        else:
            print("Could not find or calculate Market Cap column.")
            return

    # Filter for 2020 as per user context "actively trading stocks in 2020"
    # Or just take the latest available date for each stock to get current coverage.
    # The user example showed "336/430 actively trading stocks in 2020".
    # Let's try to replicate that logic: Filter for year 2020.
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df_2020 = df[df['date'].dt.year == 2020].copy()
    else:
        print("No date column found.")
        df_2020 = df.copy()

    # Calculate average market cap for each ISIN in 2020
    isin_mcap = df_2020.groupby('isin')[mc_col].mean().sort_values(ascending=False)
    total_mcap = isin_mcap.sum()
    
    # Calculate coverage
    mapped_mcap = isin_mcap[isin_mcap.index.isin(mapped_isins)].sum()
    coverage_pct = (mapped_mcap / total_mcap) * 100
    
    print(f"\nMarket Cap Coverage (2020 data): {coverage_pct:.2f}%")
    print(f"Total Market Cap: {total_mcap:,.0f}")
    print(f"Mapped Market Cap: {mapped_mcap:,.0f}")

    # Top unmapped companies
    unmapped = isin_mcap[~isin_mcap.index.isin(mapped_isins)]
    print("\nTOP 30 UNMAPPED COMPANIES (by market cap):")
    
    # Get company names if available
    # We can get names from Finbas or the mapping file (even if unmapped, it might have a name in Finbas)
    # Finbas usually has 'name' or 'company_name'
    name_col = 'name' if 'name' in df.columns else 'company_name'
    
    if name_col in df.columns:
        isin_names = df_2020.groupby('isin')[name_col].first()
    else:
        isin_names = pd.Series(index=isin_mcap.index, data=isin_mcap.index)

    for isin, mcap in unmapped.head(30).items():
        name = isin_names.get(isin, "Unknown")
        pct = (mcap / total_mcap) * 100
        print(f"   {isin:<15} {name:<40} {pct:.2f}%")

    # Count stats
    total_isins = len(isin_mcap)
    mapped_count = len(isin_mcap[isin_mcap.index.isin(mapped_isins)])
    print(f"\nISIN Count Coverage: {mapped_count}/{total_isins} ({mapped_count/total_isins*100:.1f}%)")

    # Export unmapped to CSV for user
    print("\nExporting unmapped ISINs to 'data/intermediate/unmapped_isins_for_research.csv'...")
    unmapped_df = pd.DataFrame({
        'isin': unmapped.index,
        'market_cap_2020': unmapped.values,
        'company_name': [isin_names.get(i, "") for i in unmapped.index]
    })
    unmapped_df.to_csv('data/intermediate/unmapped_isins_for_research.csv', index=False)
    print("Done.")

if __name__ == '__main__':
    analyze_coverage()
