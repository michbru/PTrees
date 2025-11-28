"""
Merge Automated and Manual ISIN-ORGNR Mappings
===============================================
Combines:
  - Automated mappings from LSEG (3_build_isin_orgnr_mapping_LSEG.py)
  - Manual mappings (data/manual_mappings/isin_orgnr_manual.csv)

Manual mappings take priority over automated ones.

Output: data/intermediate/isin_orgnr_mapping_final.csv
"""

import pandas as pd
from pathlib import Path

AUTO_MAPPING = Path('data/automated_mappings/isin_orgnr_mapping_auto.csv')
MANUAL_MAPPING = Path('data/manual_mappings/isin_orgnr_manual.csv')
OUTPUT_FINAL = Path('data/intermediate/isin_orgnr_mapping_final.csv')


def main():
    print("=" * 70)
    print("MERGING AUTOMATED AND MANUAL MAPPINGS")
    print("=" * 70)

    # Load automated mappings
    print("\n[1] Loading automated mappings...")
    df_auto = pd.read_csv(AUTO_MAPPING)
    print(f"  Automated: {len(df_auto)} ISINs")
    print(f"  Mapped: {df_auto['orgnr'].notna().sum()} ISINs")

    # Load manual mappings
    print("\n[2] Loading manual mappings...")
    if not MANUAL_MAPPING.exists():
        print(f"  No manual mappings found at {MANUAL_MAPPING}")
        df_manual = pd.DataFrame(columns=['isin', 'orgnr', 'company_name', 'source'])
    else:
        df_manual = pd.read_csv(MANUAL_MAPPING)
        print(f"  Manual: {len(df_manual)} ISINs")

    # Merge (manual takes priority)
    print("\n[3] Merging...")

    # Start with automated
    df_final = df_auto.copy()

    # Override with manual mappings
    df_final = df_final.set_index('isin')

    for idx, row in df_manual.iterrows():
        isin = row['isin']
        orgnr = row['orgnr']

        if isin in df_final.index:
            df_final.loc[isin, 'orgnr'] = orgnr
            df_final.loc[isin, 'method'] = 'manual'
        else:
            # Add new ISIN from manual mapping
            new_row = {
                'company_name': row.get('company_name', ''),
                'org_perm_id': None,
                'tax_id': None,
                'hq_country': 'SE',
                'orgnr': orgnr,
                'method': 'manual'
            }
            df_final.loc[isin] = new_row

    df_final = df_final.reset_index()
    df_final = df_final.rename(columns={'index': 'isin'})

    # Statistics
    print(f"\n" + "=" * 70)
    print("FINAL MAPPING STATISTICS")
    print("=" * 70)

    total = len(df_final)
    mapped = df_final['orgnr'].notna().sum()
    unmapped = total - mapped
    coverage = (mapped / total) * 100

    print(f"\nTotal ISINs: {total}")
    print(f"Mapped: {mapped} ({coverage:.1f}%)")
    print(f"Unmapped: {unmapped}")
    print()
    print("Breakdown by method:")
    print(df_final['method'].value_counts())

    # Save
    OUTPUT_FINAL.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(OUTPUT_FINAL, index=False)
    print(f"\n[OK] Saved to: {OUTPUT_FINAL}")


if __name__ == "__main__":
    main()
