"""
Step 3: Build ISIN-ORGNR Mapping (Automated via LSEG)
=====================================================
This script creates automated mappings using LSEG TaxID and conservative
name matching against Serrano. Manual mappings are kept separate and merged
later (Step 4).

Output: data/mappings/automated/isin_orgnr_automated.csv
"""

import pandas as pd
import lseg.data as ld
from pathlib import Path
import json
import time
import re

FINBAS_PATH = Path('data/intermediate/finbas/finbas_daily_clean.csv')
SERRANO_RAW_DIR = Path('data/raw/serrano/Stata_2025')
OUTPUT_AUTO = Path('data/mappings/automated/isin_orgnr_automated.csv')


def connect_lseg():
    """Connect to LSEG API."""
    try:
        config_path = Path('./lseg-data.config.json').resolve()
        with open(config_path, 'r') as f:
            config = json.load(f)

        p_config = config['sessions']['platform']
        if 'rdp' in p_config:
            p_config = p_config['rdp']

        session = ld.session.platform.Definition(
            app_key=p_config.get('app-key'),
            grant=ld.session.platform.GrantPassword(
                username=p_config.get('username'),
                password=p_config.get('password')
            ),
            signon_control=True
        ).get_session()
        session.open()
        ld.session.set_default(session)
        return True
    except Exception as e:
        print(f"LSEG connection failed: {e}")
        return False


def extract_orgnr(tax_id: str) -> int | None:
    """Extract a 10-digit Swedish ORGNR from a TaxID string.

    - Uppercase and strip; drop leading 'SE' if present
    - Remove all non-digits (hyphens, spaces)
    - If 12 digits ending with '01', drop trailing two (common VAT form)
    - Return 10-digit integer or None
    """
    if pd.isna(tax_id):
        return None
    s = str(tax_id).upper().strip()
    if s.startswith('SE'):
        s = s[2:]
    s = re.sub(r'[^0-9]', '', s)
    if len(s) == 12 and s.endswith('01'):
        s = s[:-2]
    if len(s) == 10 and s.isdigit():
        try:
            return int(s)
        except Exception:
            return None
    return None


def normalize_name(name):
    """Normalize company name for matching."""
    if pd.isna(name):
        return ""
    name = str(name).lower()
    suffixes = [r'\s+ab\s*$', r'\s+publ\s*$', r'\s+\(publ\)\s*$',
                r'\s+aktiebolag\s*$', r'\s+holding.*$', r'\s+group\s*$']
    for suffix in suffixes:
        name = re.sub(suffix, '', name)
    name = re.sub(r'\s+[ab]\s*$', '', name)
    name = re.sub(r'\s+free\s*$', '', name)
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def main():
    print("=" * 80)
    print("STEP 3: BUILD AUTOMATED ISIN-ORGNR MAPPING (LSEG)")
    print("=" * 80)

    # Load ISINs
    print("\n[1] Loading ISINs...")
    df_finbas = pd.read_csv(FINBAS_PATH, usecols=['isin', 'name'])
    df_finbas['isin'] = df_finbas['isin'].astype(str).str.upper().str.strip()
    unique_isins = df_finbas['isin'].dropna().unique().tolist()
    print(f"  Found {len(unique_isins)} unique ISINs")

    # Connect to LSEG
    print("\n[2] Fetching from LSEG...")
    if not connect_lseg():
        return

    fields = ['TR.CommonName', 'TR.OrganizationId', 'TR.TaxId', 'TR.HQCountryCode']
    all_results = []
    batch_size = 100

    for i in range(0, len(unique_isins), batch_size):
        batch = unique_isins[i:i+batch_size]
        try:
            df_batch = ld.get_data(universe=batch, fields=fields)
            all_results.append(df_batch)
            time.sleep(0.3)
        except Exception as e:
            print(f"  Batch {i//batch_size + 1} failed: {e}")

    if not all_results:
        print("  No results returned from LSEG.")
        return
    df_lseg = pd.concat(all_results, ignore_index=True)

    # Normalize columns
    col_map = {
        'Instrument': 'isin',
        'Company Common Name': 'company_name',
        'TR.CommonName': 'company_name',
        'Organization PermID': 'org_perm_id',
        'TR.OrganizationId': 'org_perm_id',
        'TaxID': 'tax_id',
        'TR.TaxId': 'tax_id',
        'Country ISO Code of Headquarters': 'hq_country',
        'TR.HQCountryCode': 'hq_country',
    }
    df_lseg = df_lseg.rename(columns=col_map)

    for col in ['isin', 'company_name', 'org_perm_id', 'tax_id', 'hq_country']:
        if col not in df_lseg.columns:
            df_lseg[col] = None
    df_lseg['isin'] = df_lseg['isin'].astype(str).str.upper().str.strip()
    df_lseg['company_name'] = df_lseg['company_name'].astype(str)

    # Strategy 1: Extract ORGNR from TaxID
    print("\n[3] Extracting ORGNR from TaxID...")
    is_se_hq = (df_lseg['hq_country'].astype(str).str.upper() == 'SE')
    taxid_orgnr = df_lseg['tax_id'].apply(extract_orgnr)
    taxid_is_se = df_lseg['tax_id'].astype(str).str.upper().str.startswith('SE')
    df_lseg['orgnr'] = taxid_orgnr.where(is_se_hq | taxid_is_se, other=None)
    df_lseg['method'] = 'none'
    df_lseg.loc[df_lseg['orgnr'].notna(), 'method'] = 'lseg_taxid'

    strategy1_count = df_lseg['orgnr'].notna().sum()
    print(f"  Mapped {strategy1_count} ISINs via TaxID")

    # Strategy 2: Name matching
    print("\n[4] Name matching with Serrano (conservative)...")
    serrano_frames = []
    for i in range(1, 11):
        f = SERRANO_RAW_DIR / f'bokslut{i}.dta'
        if not f.exists():
            continue
        try:
            df_ser = pd.read_stata(f, columns=['ORGNR', 'KOMNAMN'])
        except Exception:
            df_ser = pd.read_stata(f)[['ORGNR', 'KOMNAMN']]
        serrano_frames.append(df_ser)

    if serrano_frames:
        df_serrano = pd.concat(serrano_frames, ignore_index=True)
        serrano_names = df_serrano[['ORGNR', 'KOMNAMN']].dropna()
        serrano_names = serrano_names.rename(columns={'ORGNR': 'orgnr', 'KOMNAMN': 'name'})
        serrano_names['name_norm'] = serrano_names['name'].apply(normalize_name)
        serrano_names = serrano_names[serrano_names['name_norm'] != '']

        grp = serrano_names.groupby('name_norm')['orgnr']
        unique_mask = grp.transform('nunique') == 1
        serrano_unique = serrano_names[unique_mask].drop_duplicates('name_norm')
        serrano_lookup = serrano_unique.set_index('name_norm')['orgnr'].to_dict()

        unmapped = df_lseg[df_lseg['orgnr'].isna()].copy()
        unmapped['name_norm'] = unmapped['company_name'].apply(normalize_name)
        unmapped = unmapped[unmapped['name_norm'] != '']
        unmapped['orgnr_matched'] = unmapped['name_norm'].map(serrano_lookup)

        to_apply = unmapped[unmapped['orgnr_matched'].notna()][['isin', 'orgnr_matched']]
        if not to_apply.empty:
            df_lseg = df_lseg.set_index('isin')
            for isin, orgnr in to_apply.itertuples(index=False):
                if pd.notna(orgnr) and isin in df_lseg.index:
                    if pd.isna(df_lseg.loc[isin, 'orgnr']):
                        df_lseg.loc[isin, 'orgnr'] = int(orgnr)
                        df_lseg.loc[isin, 'method'] = 'name_matching'
            df_lseg = df_lseg.reset_index()
        strategy2_count = (df_lseg['method'] == 'name_matching').sum()
        print(f"  Mapped {strategy2_count} ISINs via name matching (unique names only)")
    else:
        print("  No Serrano bokslut files found for name matching.")
        strategy2_count = 0

    # Save automated mappings only
    # Finalize: standardize dtypes, deduplicate by ISIN with method priority
    method_rank = {'lseg_taxid': 1, 'name_matching': 2, 'none': 99}
    if 'method' not in df_lseg.columns:
        df_lseg['method'] = 'none'
    df_lseg['method_rank'] = df_lseg['method'].map(method_rank).fillna(99)
    df_lseg['orgnr'] = pd.to_numeric(df_lseg['orgnr'], errors='coerce').astype('Int64')
    df_lseg = df_lseg.sort_values(['isin', 'method_rank'])
    df_lseg = df_lseg.drop_duplicates(subset=['isin'], keep='first')

    total_auto = df_lseg['orgnr'].notna().sum()
    print(f"\n[5] Saving automated mappings...")
    print(f"  Total automated: {total_auto} ISINs")

    OUTPUT_AUTO.parent.mkdir(parents=True, exist_ok=True)
    df_lseg.to_csv(OUTPUT_AUTO, index=False)
    print(f"  Saved: {OUTPUT_AUTO}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  LSEG TaxID:      {strategy1_count} ISINs")
    print(f"  Name matching:   {strategy2_count} ISINs")
    print(f"  " + "-" * 32)
    print(f"  TOTAL AUTOMATED: {total_auto} ISINs")

    try:
        ld.close_session()
    except:
        pass


if __name__ == "__main__":
    main()
