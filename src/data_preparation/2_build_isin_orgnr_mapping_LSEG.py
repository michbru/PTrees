"""
Build ISIN-ORGNR Mapping from LSEG (Automated)
===============================================
This script creates automated mappings using LSEG TaxID and name matching.
Manual mappings are kept separate and merged later.

Output: data/intermediate/isin_orgnr_mapping_auto.csv
"""

import pandas as pd
import lseg.data as ld
from pathlib import Path
import json
import time
import re

FINBAS_PATH = Path('data/intermediate/finbas/finbas_daily_clean.csv')
SERRANO_PATH = Path('data/raw/serrano/Stata_2025/bokslut1.dta')
OUTPUT_AUTO = Path('data/automated_mappings/isin_orgnr_mapping_auto.csv')


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


def extract_orgnr(tax_id):
    """Extract 10-digit Swedish ORGNR from TaxID."""
    if pd.isna(tax_id) or not isinstance(tax_id, str):
        return None
    clean = tax_id.upper().strip()
    if clean.startswith('SE'):
        clean = clean[2:]
    if len(clean) == 12 and clean.endswith('01'):
        clean = clean[:-2]
    if len(clean) == 10 and clean.isdigit():
        return int(clean)
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
    print("=" * 70)
    print("BUILDING AUTOMATED ISIN-ORGNR MAPPING (LSEG)")
    print("=" * 70)

    # Load ISINs
    print("\n[1] Loading ISINs...")
    df_finbas = pd.read_csv(FINBAS_PATH, usecols=['isin', 'name'])
    unique_isins = df_finbas['isin'].unique().tolist()
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

    # Strategy 1: Extract ORGNR from TaxID
    print("\n[3] Extracting ORGNR from TaxID...")
    df_lseg['orgnr'] = df_lseg['tax_id'].apply(extract_orgnr)
    df_lseg['method'] = 'none'
    df_lseg.loc[df_lseg['orgnr'].notna(), 'method'] = 'lseg_taxid'

    strategy1_count = df_lseg['orgnr'].notna().sum()
    print(f"  Mapped {strategy1_count} ISINs via TaxID")

    # Strategy 2: Name matching
    print("\n[4] Name matching with Serrano...")
    if SERRANO_PATH.exists():
        df_serrano = pd.read_stata(SERRANO_PATH, columns=['ORGNR', 'KOMNAMN'], iterator=True).read(100000)
        serrano_names = df_serrano[['ORGNR', 'KOMNAMN']].drop_duplicates()
        serrano_names = serrano_names[serrano_names['KOMNAMN'].notna()]
        serrano_names['name_norm'] = serrano_names['KOMNAMN'].apply(normalize_name)
        serrano_names = serrano_names[serrano_names['name_norm'] != '']
        serrano_lookup = serrano_names.set_index('name_norm')['ORGNR'].to_dict()

        unmapped = df_lseg[df_lseg['orgnr'].isna()].copy()
        unmapped['name_norm'] = unmapped['company_name'].apply(normalize_name)
        unmapped = unmapped[unmapped['name_norm'] != '']
        unmapped['orgnr_matched'] = unmapped['name_norm'].map(serrano_lookup)

        df_lseg = df_lseg.set_index('isin')
        for isin, orgnr in zip(unmapped['isin'], unmapped['orgnr_matched']):
            if pd.notna(orgnr):
                df_lseg.loc[isin, 'orgnr'] = orgnr
                df_lseg.loc[isin, 'method'] = 'name_matching'
        df_lseg = df_lseg.reset_index()

        strategy2_count = (df_lseg['method'] == 'name_matching').sum()
        print(f"  Mapped {strategy2_count} ISINs via name matching")
    else:
        strategy2_count = 0

    # Save automated mappings only
    total_auto = df_lseg['orgnr'].notna().sum()
    print(f"\n[5] Saving automated mappings...")
    print(f"  Total automated: {total_auto} ISINs")

    OUTPUT_AUTO.parent.mkdir(parents=True, exist_ok=True)
    df_lseg.to_csv(OUTPUT_AUTO, index=False)
    print(f"  Saved: {OUTPUT_AUTO}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
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
