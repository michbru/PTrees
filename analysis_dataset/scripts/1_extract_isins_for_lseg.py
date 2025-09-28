#!/usr/bin/env python3
"""
Extract Unique ISINs for LSEG Data Request

This script extracts all unique ISIN codes from the final_analysis_panel.csv
file and creates a clean list for targeted LSEG data requests.
"""

import pandas as pd
from pathlib import Path

def extract_unique_isins():
    """Extract unique ISINs from the final analysis panel."""

    print("EXTRACTING UNIQUE ISINs FOR LSEG REQUEST")
    print("=" * 50)

    # Check if the file exists - try different possible locations
    possible_files = ["data/finbas_market_data.csv", "final_analysis_panel.csv", "results/ptrees_final_dataset.csv"]

    input_file = None
    for file_path in possible_files:
        if Path(file_path).exists():
            input_file = Path(file_path)
            break

    if input_file is None:
        print(f"Error: No source data file found")
        print(f"Looked for: {possible_files}")
        print("   Please make sure you have source data available.")
        return

    try:
        # Load the data file
        print(f"Loading data from: {input_file}")

        # Try different separators
        try:
            df = pd.read_csv(input_file, sep=';')
        except:
            df = pd.read_csv(input_file)

        print(f"Loaded {len(df):,} rows")

        # Check if ISIN column exists
        if 'isin' not in df.columns:
            print("Error: 'isin' column not found")
            print("Available columns:", df.columns.tolist())
            return

        print(f"Found ISIN column")

        # Extract unique ISINs
        print("\nExtracting unique ISINs...")

        # Get all ISINs, remove nulls, and get unique values
        all_isins = df['isin'].dropna()
        unique_isins = all_isins.unique()

        print(f"Total ISIN observations: {len(all_isins):,}")
        print(f"Unique ISINs found: {len(unique_isins):,}")

        # Create DataFrame with unique ISINs
        isin_df = pd.DataFrame({'isin': sorted(unique_isins)})

        # Save to CSV
        output_file = Path("results/isin_target_list_for_lseg.csv")
        output_file.parent.mkdir(exist_ok=True)
        isin_df.to_csv(output_file, index=False)

        print(f"\nRESULTS SAVED")
        print("=" * 30)
        print(f"File saved: {output_file}")
        print(f"Unique ISINs exported: {len(unique_isins):,}")

        # Show a few examples
        print(f"\nSample ISINs (first 10):")
        for i, isin in enumerate(unique_isins[:10]):
            print(f"   {i+1:2d}. {isin}")

        if len(unique_isins) > 10:
            print(f"   ... and {len(unique_isins)-10:,} more")

        print(f"\nNEXT STEPS:")
        print("=" * 15)
        print("1. Use the file 'results/isin_target_list_for_lseg.csv' for your LSEG data request")
        print("2. Request the following data for years 1997-2022:")
        print("   - Total Assets (annual)")
        print("   - Net Income (annual)")
        print("   - Any other fundamental data you need")
        print("3. Save the LSEG results as 'lseg_fundamentals.csv'")
        print("4. Re-run the main analysis script to merge the data")

    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    extract_unique_isins()