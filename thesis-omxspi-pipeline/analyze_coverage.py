#!/usr/bin/env python3
"""
Quick analysis of data coverage in the OMX dataset
"""
import pandas as pd
import numpy as np

# Load the data
df = pd.read_csv('omx_fundamentals_1999_2024.csv')

print(f"Dataset: {len(df)} rows, {len(df.columns)} columns")
print(f"Companies: {df['ric'].nunique()}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")

# Check coverage for key fundamental fields
key_fields = [
    'shares_outstanding', 'shareholders_equity', 'total_assets',
    'revenue', 'net_income', 'close'
]

print("\n=== DATA COVERAGE ANALYSIS ===")

# Coverage by company
company_coverage = []
for ric in df['ric'].unique():
    ric_data = df[df['ric'] == ric]
    coverage_stats = {}
    coverage_stats['ric'] = ric
    coverage_stats['total_rows'] = len(ric_data)

    for field in key_fields:
        non_null_count = ric_data[field].notna().sum()
        coverage_pct = (non_null_count / len(ric_data)) * 100
        coverage_stats[f'{field}_coverage'] = coverage_pct

    # Calculate average fundamental coverage (excluding price data)
    fund_fields = ['shares_outstanding', 'shareholders_equity', 'total_assets', 'revenue', 'net_income']
    avg_coverage = np.mean([coverage_stats[f'{field}_coverage'] for field in fund_fields])
    coverage_stats['avg_fundamental_coverage'] = avg_coverage

    company_coverage.append(coverage_stats)

coverage_df = pd.DataFrame(company_coverage)

# Sort by coverage
coverage_df = coverage_df.sort_values('avg_fundamental_coverage', ascending=False)

print("\nTOP 20 COMPANIES BY FUNDAMENTAL DATA COVERAGE:")
print(coverage_df[['ric', 'avg_fundamental_coverage', 'shares_outstanding_coverage', 'revenue_coverage']].head(20).to_string(index=False))

print("\nBOTTOM 20 COMPANIES BY FUNDAMENTAL DATA COVERAGE:")
print(coverage_df[['ric', 'avg_fundamental_coverage', 'shares_outstanding_coverage', 'revenue_coverage']].tail(20).to_string(index=False))

# Coverage statistics
print(f"\n=== COVERAGE STATISTICS ===")
print(f"Companies with >80% fundamental coverage: {len(coverage_df[coverage_df['avg_fundamental_coverage'] > 80])}")
print(f"Companies with >50% fundamental coverage: {len(coverage_df[coverage_df['avg_fundamental_coverage'] > 50])}")
print(f"Companies with >20% fundamental coverage: {len(coverage_df[coverage_df['avg_fundamental_coverage'] > 20])}")
print(f"Companies with 0% fundamental coverage: {len(coverage_df[coverage_df['avg_fundamental_coverage'] == 0])}")

# Time period analysis
print(f"\n=== TIME PERIOD ANALYSIS ===")
df['year'] = pd.to_datetime(df['date']).dt.year

for year in [1999, 2005, 2010, 2015, 2020, 2024]:
    year_data = df[df['year'] == year]
    if not year_data.empty:
        companies_with_data = year_data['ric'].nunique()
        avg_coverage = year_data['shares_outstanding'].notna().mean() * 100
        print(f"{year}: {companies_with_data} companies, {avg_coverage:.1f}% shares_outstanding coverage")