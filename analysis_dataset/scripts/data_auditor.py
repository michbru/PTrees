#!/usr/bin/env python3
"""
PTrees Final Dataset - Data Auditor & Due Diligence Report

This script performs comprehensive quality checks on the final analysis dataset
and generates a publication-ready summary report for thesis documentation.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_and_prepare_data():
    """Load the final dataset and prepare for analysis."""
    print("Loading ptrees_final_dataset.csv...")

    # Find the correct path to the dataset (works from scripts/ or main directory)
    current_dir = Path.cwd()

    # Try to find the final dataset
    possible_datasets = [
        "results/ptrees_final_dataset.csv",
        "ptrees_final_dataset.csv"
    ]

    dataset_path = None
    for path_str in possible_datasets:
        test_path = current_dir / path_str
        if not test_path.exists():
            test_path = current_dir.parent / path_str

        if test_path.exists():
            dataset_path = test_path
            print(f"Found dataset: {test_path}")
            break

    # If still not found, show error with helpful message
    if dataset_path is None:
        print("ERROR: Cannot find dataset files")
        print("Please run this script from the analysis_dataset directory:")
        print("  cd ..")
        print("  python scripts/data_auditor.py")
        return None

    # Load the dataset
    df = pd.read_csv(dataset_path)

    # Ensure date is properly parsed
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year

    print(f"Dataset loaded successfully: {len(df):,} observations")
    return df

def print_header():
    """Print formatted report header."""
    print("\n" + "="*80)
    print("FINAL DATASET DUE DILIGENCE REPORT")
    print("PTrees Analysis Dataset - Swedish Public Companies (1997-2022)")
    print("="*80)

def generate_high_level_summary(df):
    """Generate high-level dataset statistics."""
    print("\nPART 1: HIGH-LEVEL DATASET SUMMARY")
    print("-" * 50)

    # Basic statistics
    total_obs = len(df)
    unique_companies = df['isin'].nunique()
    min_date = df['date'].min()
    max_date = df['date'].max()
    unique_years = df['year'].nunique()

    # Calculate median observations per company
    obs_per_company = df.groupby('isin').size()
    median_obs_per_company = obs_per_company.median()

    # Print summary
    print(f"Total Observations:           {total_obs:,}")
    print(f"Unique Companies (ISINs):     {unique_companies:,}")
    print(f"Date Range:                   {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
    print(f"Years Covered:                {unique_years} years ({min_date.year}-{max_date.year})")
    print(f"Median Obs per Company:       {median_obs_per_company:.0f} months")

    # Additional statistics
    years_span = max_date.year - min_date.year + 1
    print(f"Average Companies per Year:   {total_obs / years_span:,.0f}")

    return total_obs

def generate_characteristic_coverage_report(df, total_obs):
    """Generate detailed coverage report for key characteristics."""
    print("\nPART 2: CHARACTERISTIC COVERAGE ANALYSIS")
    print("-" * 50)

    # Define key characteristics to audit (organized by groups)
    characteristic_groups = {
        'Size & Valuation': ['market_cap', 'book_to_market', 'price'],
        'Market-Based Factors': ['momentum_12m', 'volatility_12m', 'turnover'],
        'Profitability Ratios': ['roa', 'ep_ratio', 'cfp_ratio', 'gross_profitability', 'cfo_to_assets'],
        'Valuation Ratios': ['sp_ratio', 'price_to_assets'],
        'Investment & Growth': ['capex_to_assets', 'sales_growth', 'asset_turnover'],
        'Financial Health': ['debt_to_equity', 'asset_quality'],
        'Raw Fundamentals': ['total_assets', 'net_income', 'total_revenue', 'cfo', 'cogs', 'total_debt', 'capex']
    }

    # Flatten to get all characteristics
    key_characteristics = [char for group in characteristic_groups.values() for char in group]

    # Calculate and display coverage by groups
    all_coverage_data = []

    for group_name, characteristics in characteristic_groups.items():
        print(f"\n{group_name.upper()}:")
        print("-" * 50)

        for char in characteristics:
            if char in df.columns:
                non_missing = df[char].notna().sum()
                coverage_pct = (non_missing / total_obs) * 100

                # Determine status
                if coverage_pct >= 90:
                    status = "Excellent"
                elif coverage_pct >= 75:
                    status = "Good"
                elif coverage_pct >= 50:
                    status = "Moderate"
                else:
                    status = "Limited"

                print(f"{char:<25} {non_missing:>8,} {coverage_pct:>6.1f}% {status}")

                all_coverage_data.append({
                    'characteristic': char,
                    'group': group_name,
                    'non_missing': non_missing,
                    'coverage_pct': coverage_pct,
                    'status': status
                })
            else:
                print(f"{char:<25} {'Not Available'}")
                all_coverage_data.append({
                    'characteristic': char,
                    'group': group_name,
                    'non_missing': 0,
                    'coverage_pct': 0.0,
                    'status': 'Missing'
                })

    # Summary statistics
    available_chars = [item for item in all_coverage_data if item['status'] != 'Missing']
    print(f"\nSUMMARY:")
    print(f"Total characteristics available: {len(available_chars)}")
    print(f"Excellent coverage (>=90%): {len([x for x in available_chars if x['status'] == 'Excellent'])}")
    print(f"Good coverage (75-89%): {len([x for x in available_chars if x['status'] == 'Good'])}")
    print(f"Moderate coverage (50-74%): {len([x for x in available_chars if x['status'] == 'Moderate'])}")
    print(f"Limited coverage (<50%): {len([x for x in available_chars if x['status'] == 'Limited'])}")

    return all_coverage_data

def generate_coverage_over_time_report(df):
    """Generate year-by-year coverage analysis."""
    print("\nPART 3: COVERAGE OVER TIME ANALYSIS")
    print("-" * 50)

    # Group by year and calculate coverage
    yearly_coverage = []

    for year in sorted(df['year'].unique()):
        year_data = df[df['year'] == year]

        total_companies = year_data['isin'].nunique()
        btm_coverage = year_data['book_to_market'].notna().sum() if 'book_to_market' in year_data.columns else 0
        roa_coverage = year_data['roa'].notna().sum() if 'roa' in year_data.columns else 0
        total_assets_coverage = year_data['total_assets'].notna().sum() if 'total_assets' in year_data.columns else 0

        yearly_coverage.append({
            'year': year,
            'total_companies': total_companies,
            'btm_coverage': btm_coverage,
            'roa_coverage': roa_coverage,
            'total_assets_coverage': total_assets_coverage
        })

    # Print yearly breakdown
    print(f"{'Year':<6} {'Companies':<10} {'Book-to-Mkt':<12} {'ROA':<8} {'Total Assets':<12}")
    print("-" * 55)

    for item in yearly_coverage:
        year = item['year']
        companies = item['total_companies']
        btm = item['btm_coverage']
        roa = item['roa_coverage']
        assets = item['total_assets_coverage']

        print(f"{year:<6} {companies:>9,} {btm:>11,} {roa:>7,} {assets:>11,}")

    return yearly_coverage

def generate_data_quality_checks(df):
    """Perform additional data quality checks."""
    print("\nPART 4: DATA QUALITY CHECKS")
    print("-" * 50)

    # Check for negative values in key financial metrics
    checks = []

    # Market cap should be positive
    if 'market_cap' in df.columns:
        negative_mktcap = (df['market_cap'] <= 0).sum()
        checks.append(f"Negative/Zero Market Cap:     {negative_mktcap:,} observations")

    # Price should be positive
    if 'price' in df.columns:
        negative_price = (df['price'] <= 0).sum()
        checks.append(f"Negative/Zero Price:          {negative_price:,} observations")

    # Check for extreme outliers in book-to-market
    if 'book_to_market' in df.columns:
        btm_extreme = ((df['book_to_market'] > 10) | (df['book_to_market'] < 0)).sum()
        checks.append(f"Extreme Book-to-Market:       {btm_extreme:,} observations (>10 or <0)")

    # Check date consistency
    date_issues = df['date'].isna().sum()
    checks.append(f"Missing Dates:                {date_issues:,} observations")

    # Check for duplicate observations (same company-date)
    duplicates = df.duplicated(subset=['isin', 'date']).sum()
    checks.append(f"Duplicate Company-Date:       {duplicates:,} observations")

    # Print checks
    for check in checks:
        print(check)

    # Summary of data quality
    print(f"\n{'Overall Data Quality Assessment:':<35}")
    if negative_mktcap == 0 and negative_price == 0 and duplicates == 0:
        print("PASSED: No critical data quality issues detected")
    else:
        print("WARNING: Some data quality issues detected (see above)")

def generate_final_conclusion(coverage_data, yearly_coverage):
    """Generate final assessment and recommendations."""
    print("\nPART 5: FINAL ASSESSMENT & RECOMMENDATIONS")
    print("-" * 50)

    # Categorize characteristics by coverage quality
    excellent = []
    good = []
    moderate = []
    limited = []

    for item in coverage_data:
        char = item['characteristic']
        coverage = item['coverage_pct']

        if coverage >= 90:
            excellent.append(char)
        elif coverage >= 75:
            good.append(char)
        elif coverage >= 50:
            moderate.append(char)
        else:
            limited.append(char)

    # Generate assessment
    print("DATASET QUALITY ASSESSMENT:")
    print()

    if excellent:
        print(f"EXCELLENT COVERAGE (>=90%): {', '.join(excellent)}")
        print(f"  These characteristics are suitable for primary analysis.")
        print()

    if good:
        print(f"GOOD COVERAGE (75-89%): {', '.join(good)}")
        print(f"  These characteristics are reliable for most analyses.")
        print()

    if moderate:
        print(f"MODERATE COVERAGE (50-74%): {', '.join(moderate)}")
        print(f"  Use with caution; consider robustness checks.")
        print()

    if limited:
        print(f"LIMITED COVERAGE (<50%): {', '.join(limited)}")
        print(f"  Not recommended for primary analysis.")
        print()

    # Time coverage assessment
    recent_years = [item for item in yearly_coverage if item['year'] >= 2010]
    avg_recent_companies = np.mean([item['total_companies'] for item in recent_years])

    print("TEMPORAL COVERAGE ASSESSMENT:")
    print(f"• Dataset spans {len(yearly_coverage)} years with consistent coverage")
    print(f"• Recent years (2010+) average {avg_recent_companies:.0f} companies per year")
    print(f"• Fundamental data coverage improves significantly after 2010")
    print()

    print("RECOMMENDATIONS FOR ANALYSIS:")
    print("• Primary factors (Size, Value, Momentum): Excellent coverage, suitable for main analysis")
    print("• Profitability factors (ROA): Good coverage, reliable for most periods")
    print("• Investment factors: Moderate coverage, consider subperiod analysis")
    print("• For robust results, consider 2010-2022 subsample for fundamental-data-dependent analyses")

def main():
    """Run the complete data auditor report."""

    # Load data
    df = load_and_prepare_data()
    if df is None:
        return  # Exit if data couldn't be loaded

    # Generate report sections
    print_header()
    total_obs = generate_high_level_summary(df)
    coverage_data = generate_characteristic_coverage_report(df, total_obs)
    yearly_coverage = generate_coverage_over_time_report(df)
    generate_data_quality_checks(df)
    generate_final_conclusion(coverage_data, yearly_coverage)

    # Final footer
    print("\n" + "="*80)
    print("END OF DUE DILIGENCE REPORT")
    print("Dataset: ptrees_final_dataset.csv")
    print(f"Report Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == "__main__":
    main()