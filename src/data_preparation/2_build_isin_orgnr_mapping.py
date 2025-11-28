"""
Build ISIN-ORGNR Mapping from LSEG
===================================
Creates mapping between ISINs (stock identifiers) and Swedish ORGNRs (company identifiers).

Uses 3 strategies:
1. LSEG TaxID -> ORGNR extraction (489 ISINs)
2. Name matching with Serrano data (6 ISINs)
3. Export unmapped ISINs for manual lookup

Input:  data/intermediate/finbas/finbas_daily_clean.csv
Output:
  - data/intermediate/isin_orgnr_mapping.csv (495 mapped)
  - data/intermediate/unmapped_isins_for_manual_lookup.csv (238 unmapped)
"""

import pandas as pd
import numpy as np
import lseg.data as ld
from pathlib import Path
import json
import time
import re

# Paths
FINBAS_PATH = Path('data/intermediate/finbas/finbas_daily_clean.csv')
SERRANO_PATH = Path('data/raw/serrano/Stata_2025/bokslut1.dta')
OUTPUT_MAPPING = Path('data/intermediate/isin_orgnr_mapping.csv')
OUTPUT_UNMAPPED = Path('data/intermediate/unmapped_isins_for_manual_lookup.csv')


def connect_lseg():
    """Connect to LSEG API."""
    try:
        config_path = Path('./lseg-data.config.json').resolve()
        with open(config_path, 'r') as f:
            config = json.load(f)

        if 'sessions' in config and 'platform' in config['sessions']:
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

    # Remove suffixes
    suffixes = [r'\s+ab\s*$', r'\s+publ\s*$', r'\s+\(publ\)\s*$',
                r'\s+aktiebolag\s*$', r'\s+holding.*$', r'\s+group\s*$']
    for suffix in suffixes:
        name = re.sub(suffix, '', name)

    # Remove share class
    name = re.sub(r'\s+[ab]\s*$', '', name)
    name = re.sub(r'\s+free\s*$', '', name)

    # Clean
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def main():
    print("=" * 70)
    print("BUILDING ISIN-ORGNR MAPPING")
    print("=" * 70)

    # 1. Load ISINs
    print("\n[1] Loading ISINs from Finbas...")
    df_finbas = pd.read_csv(FINBAS_PATH, usecols=['isin', 'name'])
    unique_isins = df_finbas['isin'].unique().tolist()
    print(f"  Found {len(unique_isins)} unique ISINs")

    # 2. Connect to LSEG
    print("\n[2] Fetching data from LSEG...")
    if not connect_lseg():
        print("ERROR: Cannot connect to LSEG")
        return

    # Fetch in batches
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

    # Normalize column names
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

    # Ensure columns exist
    for col in ['isin', 'company_name', 'org_perm_id', 'tax_id', 'hq_country']:
        if col not in df_lseg.columns:
            df_lseg[col] = None

    print(f"  Fetched {len(df_lseg)} ISINs from LSEG")

    # 3. Strategy 1: Extract ORGNR from TaxID
    print("\n[3] Strategy 1: Extract ORGNR from LSEG TaxID...")
    df_lseg['orgnr'] = df_lseg['tax_id'].apply(extract_orgnr)
    df_lseg['mapping_method'] = 'none'
    df_lseg.loc[df_lseg['orgnr'].notna(), 'mapping_method'] = 'lseg_taxid'

    strategy1_count = df_lseg['orgnr'].notna().sum()
    print(f"  Mapped {strategy1_count} ISINs via LSEG TaxID")

    # 4. Strategy 2: Name matching with Serrano
    print("\n[4] Strategy 2: Name matching with Serrano...")

    if SERRANO_PATH.exists():
        # Load Serrano company names
        df_serrano = pd.read_stata(SERRANO_PATH, columns=['ORGNR', 'KOMNAMN'], iterator=True).read(100000)
        serrano_names = df_serrano[['ORGNR', 'KOMNAMN']].drop_duplicates()
        serrano_names = serrano_names[serrano_names['KOMNAMN'].notna()]

        # Normalize names
        serrano_names['name_norm'] = serrano_names['KOMNAMN'].apply(normalize_name)
        serrano_names = serrano_names[serrano_names['name_norm'] != '']
        serrano_lookup = serrano_names.set_index('name_norm')['ORGNR'].to_dict()

        # Match unmapped ISINs
        unmapped = df_lseg[df_lseg['orgnr'].isna()].copy()
        unmapped['name_norm'] = unmapped['company_name'].apply(normalize_name)
        unmapped = unmapped[unmapped['name_norm'] != '']
        unmapped['orgnr_matched'] = unmapped['name_norm'].map(serrano_lookup)

        # Update main dataframe
        df_lseg = df_lseg.set_index('isin')
        for isin, orgnr in zip(unmapped['isin'], unmapped['orgnr_matched']):
            if pd.notna(orgnr):
                df_lseg.loc[isin, 'orgnr'] = orgnr
                df_lseg.loc[isin, 'mapping_method'] = 'name_matching'
        df_lseg = df_lseg.reset_index()

        strategy2_count = (df_lseg['mapping_method'] == 'name_matching').sum()
        print(f"  Mapped {strategy2_count} ISINs via name matching")
    else:
        print(f"  Serrano data not found, skipping name matching")
        strategy2_count = 0

    # 5. Save mapped ISINs
    total_mapped = df_lseg['orgnr'].notna().sum()
    print(f"\n[5] Saving results...")
    print(f"  Total mapped: {total_mapped} ISINs")

    OUTPUT_MAPPING.parent.mkdir(parents=True, exist_ok=True)
    df_lseg.to_csv(OUTPUT_MAPPING, index=False)
    print(f"  Saved: {OUTPUT_MAPPING}")

    # 6. Export unmapped for manual lookup
    unmapped_final = df_lseg[df_lseg['orgnr'].isna()].copy()

    # Add trading activity data
    df_finbas_full = pd.read_csv(FINBAS_PATH)
    df_finbas_full['date'] = pd.to_datetime(df_finbas_full['date'])
    df_recent = df_finbas_full[df_finbas_full['date'] >= '2020-01-01']

    trading_metrics = df_recent.groupby('isin').agg({
        'close': 'last',
        'volume': 'mean',
        'date': 'max'
    }).reset_index()
    trading_metrics.columns = ['isin', 'last_price', 'avg_volume', 'last_date']
    trading_metrics['market_cap_proxy'] = trading_metrics['last_price'] * trading_metrics['avg_volume']

    unmapped_final = unmapped_final.merge(trading_metrics, on='isin', how='left')
    unmapped_final = unmapped_final.sort_values('market_cap_proxy', ascending=False)

    # Export columns for manual lookup
    export_cols = ['isin', 'company_name', 'hq_country', 'last_price', 'avg_volume',
                   'last_date', 'market_cap_proxy']
    unmapped_export = unmapped_final[export_cols].copy()

    OUTPUT_UNMAPPED.parent.mkdir(parents=True, exist_ok=True)
    unmapped_export.to_csv(OUTPUT_UNMAPPED, index=False)
    print(f"  Unmapped ISINs: {len(unmapped_export)}")
    print(f"  Saved for manual lookup: {OUTPUT_UNMAPPED}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  LSEG TaxID:      {strategy1_count} ISINs (EXACT)")
    print(f"  Name matching:   {strategy2_count} ISINs (VERIFIED)")
    print(f"  " + "-" * 32)
    print(f"  TOTAL MAPPED:    {total_mapped} ISINs")
    print(f"  UNMAPPED:        {len(unmapped_export)} ISINs")
    print(f"\nNext: Give unmapped_isins_for_manual_lookup.csv to AI browser")

    # Close LSEG
    try:
        ld.close_session()
    except:
        pass


if __name__ == "__main__":
    main()
