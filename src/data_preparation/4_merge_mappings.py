"""
Step 4: Merge Automated and Manual ISIN-ORGNR Mappings
======================================================
Combines:
  - Automated mappings from LSEG (Step 3)
  - Manual mappings (data/mappings/manual/isin_orgnr_manual.csv)

Manual mappings take priority over automated ones.

Output: data/mappings/isin_orgnr_final.csv
"""

import pandas as pd
from pathlib import Path


def standardize_isin(s: pd.Series) -> pd.Series:
    return s.astype(str).str.upper().str.strip()


def clean_orgnr_series(s: pd.Series) -> pd.Series:
    """Normalize Swedish ORGNR strings and return as nullable Int64.

    - Remove 'SE' prefix if present
    - Drop non-digits (hyphens, spaces)
    - Convert 12-digit numbers ending with '01' to 10-digit by trimming
    - Keep only 10-digit results; others become NaN
    """
    if s is None:
        return pd.Series([], dtype='Int64')
    x = s.astype(str).str.upper().str.strip()
    # Drop trailing decimal artifacts like '.0' from CSV float parsing
    x = x.str.replace(r'\.0+$', '', regex=True)
    # Remove leading country prefix if present
    x = x.str.replace('SE', '', regex=False)
    # Remove any non-digits (hyphens, spaces, dots)
    x = x.str.replace(r'[^0-9]', '', regex=True)
    # Trim VAT-like 12-digit codes ending with '01'
    mask_12 = x.str.len() == 12
    ends_01 = x.str.endswith('01')
    x = x.where(~(mask_12 & ends_01), x.str.slice(0, 10))
    # Keep only 10-digit strings
    x = x.where(x.str.len() == 10)
    return pd.to_numeric(x, errors='coerce').astype('Int64')

AUTO_MAPPING = Path('data/mappings/automated/isin_orgnr_automated.csv')
MANUAL_MAPPING = Path('data/mappings/manual/isin_orgnr_manual.csv')
OUTPUT_FINAL = Path('data/mappings/isin_orgnr_final.csv')


def main():
    print("=" * 80)
    print("STEP 4: MERGE AUTOMATED AND MANUAL MAPPINGS")
    print("=" * 80)

    # Load automated mappings
    print("\n[1] Loading automated mappings...")
    if not AUTO_MAPPING.exists():
        raise FileNotFoundError(f"Automated mapping not found at {AUTO_MAPPING}. Run Step 3 first.")
    df_auto = pd.read_csv(AUTO_MAPPING)
    if 'isin' not in df_auto.columns:
        raise ValueError("Automated mapping missing 'isin' column")
    # Standardize
    df_auto['isin'] = standardize_isin(df_auto['isin'])
    if 'orgnr' in df_auto.columns:
        df_auto['orgnr'] = clean_orgnr_series(df_auto['orgnr'])
    print(f"  Automated: {len(df_auto)} ISINs")
    print(f"  Mapped: {df_auto['orgnr'].notna().sum()} ISINs")

    # Load manual mappings
    print("\n[2] Loading manual mappings...")
    if not MANUAL_MAPPING.exists():
        print(f"  No manual mappings found at {MANUAL_MAPPING}")
        df_manual = pd.DataFrame(columns=['isin', 'orgnr', 'company_name', 'source'])
    else:
        df_manual = pd.read_csv(MANUAL_MAPPING)
        if 'isin' not in df_manual.columns:
            raise ValueError("Manual mapping missing 'isin' column")
        df_manual['isin'] = standardize_isin(df_manual['isin'])
        if 'orgnr' in df_manual.columns:
            df_manual['orgnr'] = clean_orgnr_series(df_manual['orgnr'])
        print(f"  Manual: {len(df_manual)} ISINs")

    # Merge (manual takes priority)
    print("\n[3] Merging...")

    # Start with automated (ensure unique ISINs)
    df_final = df_auto.copy()
    df_final = df_final.sort_values(['isin'])
    df_final = df_final.drop_duplicates(subset=['isin'], keep='first')
    df_final = df_final.set_index('isin')

    # Merge manual overrides/additions
    overrides = 0
    additions = 0
    for _, row in df_manual.iterrows():
        isin = row.get('isin')
        orgnr = row.get('orgnr')
        if pd.isna(isin):
            continue
        if isin in df_final.index:
            df_final.loc[isin, 'orgnr'] = orgnr
            df_final.loc[isin, 'method'] = 'manual'
            overrides += 1
        else:
            new_row = {
                'company_name': row.get('company_name', ''),
                'org_perm_id': None,
                'tax_id': None,
                'hq_country': 'SE',
                'orgnr': orgnr,
                'method': 'manual'
            }
            df_final.loc[isin] = new_row
            additions += 1

    df_final = df_final.reset_index().rename(columns={'index': 'isin'})
    df_final['isin'] = standardize_isin(df_final['isin'])
    df_final['orgnr'] = clean_orgnr_series(df_final['orgnr'])

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
    print(f"Manual overrides applied: {overrides}")
    print(f"Manual-only additions: {additions}")
    print()
    print("Breakdown by method:")
    print(df_final['method'].value_counts())

    # Save
    OUTPUT_FINAL.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(OUTPUT_FINAL, index=False)
    print(f"\n[OK] Saved to: {OUTPUT_FINAL}")


if __name__ == "__main__":
    main()
