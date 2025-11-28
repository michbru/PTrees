import pandas as pd

print("Checking for ORGNR overlap...")

# Load mapping
df_mapping = pd.read_csv('data/intermediate/isin_orgnr_mapping_final.csv')
df_mapping = df_mapping.dropna(subset=['orgnr'])
df_mapping['orgnr'] = df_mapping['orgnr'].astype(str).str.replace('-', '', regex=False)
df_mapping['orgnr'] = pd.to_numeric(df_mapping['orgnr'], errors='coerce').astype('Int64')

mapped_orgnrs = set(df_mapping['orgnr'].dropna().unique())
print(f'Mapped ORGNRs from ISINs: {len(mapped_orgnrs)}')
print(f'Sample: {list(mapped_orgnrs)[:10]}')

print('\nChecking Serrano...')
chunk_count = 0
found_orgnrs = set()

for chunk in pd.read_csv('data/intermediate/serrano/serrano_accounting.csv', chunksize=100000):
    chunk_orgnrs = set(chunk['orgnr'].unique())
    overlap = mapped_orgnrs & chunk_orgnrs
    if overlap:
        found_orgnrs.update(overlap)
        print(f'Chunk {chunk_count}: Found {len(overlap)} overlapping ORGNRs')
    chunk_count += 1
    if chunk_count >= 10:
        break

print(f'\nTotal overlapping ORGNRs found in first {chunk_count} chunks: {len(found_orgnrs)}')
if found_orgnrs:
    print(f'Examples: {list(found_orgnrs)[:10]}')
else:
    print('NO OVERLAP FOUND!')
