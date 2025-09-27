#!/usr/bin/env python3
"""
Fundamentals-Only Pipeline for P-Trees Data Processing

Fetches fundamental data for specified RICs and date ranges.
Returns monthly data with all basic market data, balance sheet,
income statement, and corporate actions fields.
"""

import os
import warnings
import numpy as np
import pandas as pd
from contextlib import contextmanager
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()

try:
    import lseg.data as ld
except ImportError:
    print("Warning: lseg.data not available - running in test mode")
    ld = None


# --- Session Management ------------------------------------------------------

SESSION_TYPE = (os.getenv('LSEG_SESSION_TYPE') or 'desktop').lower()

def _open_session():
    """Open LSEG session based on configuration"""
    if ld is None:
        return None
    if SESSION_TYPE == 'platform':
        return ld.open_session('platform.rdp')
    return ld.open_session()

@contextmanager
def session_scope():
    """Context manager for LSEG session"""
    if ld is None:
        yield None
        return
    with _open_session() as sess:
        yield sess


def fetch_fundamentals_data(rics, start_date, end_date):
    """
    Fetch fundamental data with proper date handling
    """
    print("Fetching fundamentals data...")
    print(f"RICs: {rics}")
    print(f"Date Range: {start_date} to {end_date}")

    if ld is None:
        print("Warning: lseg.data not available - returning empty DataFrame")
        return pd.DataFrame()

    all_data_parts = []

    with session_scope():
        print("Fetching price and volume data...")

        for ric in rics:
            ric_data = {}

            # Generate month-end date range
            date_range = pd.date_range(start=start_date, end=end_date, freq='M')

            # Fetch price data (same as before)
            try:
                close_data = ld.get_data(
                    universe=[ric],
                    fields=["TR.PriceClose"],
                    parameters={
                        "SDate": start_date,
                        "EDate": end_date,
                        "Frq": "M"
                    }
                )
                if close_data is not None and not close_data.empty:
                    close_values = close_data.iloc[:, -1].values
                    ric_data['close'] = close_values[:len(date_range)]
            except Exception as e:
                pass  # Price data unavailable

            # Fetch adjusted close
            try:
                adj_close_data = ld.get_data(
                    universe=[ric],
                    fields=["TR.ClosePrice"],
                    parameters={
                        "SDate": start_date,
                        "EDate": end_date,
                        "Frq": "M"
                    }
                )
                if adj_close_data is not None and not adj_close_data.empty:
                    adj_close_values = adj_close_data.iloc[:, -1].values
                    ric_data['adj_close'] = adj_close_values[:len(date_range)]
            except Exception as e:
                if 'close' in ric_data:
                    ric_data['adj_close'] = ric_data['close']

            # Fetch volume
            try:
                volume_data = ld.get_data(
                    universe=[ric],
                    fields=["TR.Volume"],
                    parameters={
                        "SDate": start_date,
                        "EDate": end_date,
                        "Frq": "M"
                    }
                )
                if volume_data is not None and not volume_data.empty:
                    volume_values = volume_data.iloc[:, -1].values
                    ric_data['volume_msum'] = volume_values[:len(date_range)]
            except Exception as e:
                pass  # Volume data unavailable

            # Create price DataFrame
            if ric_data:
                price_df = pd.DataFrame({
                    'ric': ric,
                    'date': date_range
                })

                for col, values in ric_data.items():
                    if len(values) == len(date_range):
                        price_df[col] = values
                    else:
                        padded_values = list(values) + [np.nan] * (len(date_range) - len(values))
                        price_df[col] = padded_values[:len(date_range)]

                all_data_parts.append(price_df)

        print("Fetching fundamental data...")

        # Define fundamental fields
        field_map = {
            'TR.SharesOutstanding': 'shares_outstanding',
            'TR.ShareholdersEquity': 'shareholders_equity',
            'TR.TotalAssets': 'total_assets',
            'TR.TotalDebt': 'total_debt',
            'TR.LongTermDebt': 'long_term_debt',
            'TR.CurrentAssets': 'current_assets',
            'TR.CurrentLiabilities': 'current_liabilities',
            'TR.NetIncome': 'net_income',
            'TR.OperatingIncome': 'operating_income',
            'TR.Revenue': 'revenue',
            'TR.GrossProfit': 'gross_profit',
            'TR.DepreciationAmort': 'depreciation_amortization',
            'TR.CapitalExpenditures': 'capital_expenditures'
        }

        fundamentals_parts = []

        # Fetch quarterly fundamental data
        # Extend start date to get previous year's Q4 data for filling early months
        extended_start = f"{int(start_date.split('-')[0]) - 1}-10-01"  # Start from Q4 of previous year

        try:
            fund_data = ld.get_data(
                universe=rics,
                fields=list(field_map.keys()),
                parameters={
                    "SDate": extended_start,
                    "EDate": end_date,
                    "Frq": "FQ",
                    "Curn": "SEK"
                }
            )

            if fund_data is not None and not fund_data.empty:
                df = fund_data.copy()

                # Clean column names
                df.columns = [c.strip().lower().replace(' ', '_').replace(',', '').replace('-', '_') for c in df.columns]

                # Map actual LSEG column names to our target names
                actual_column_mappings = {
                    'instrument': 'ric',
                    'outstanding_shares': 'shares_outstanding',
                    'shareholders_equity___broker_estimate': 'shareholders_equity',
                    'total_assets': 'total_assets',
                    'total_debt': 'total_debt',
                    'long_term_debt': 'long_term_debt',
                    'current_assets': 'current_assets',
                    'current_liabilities': 'current_liabilities',
                    'net_income_incl_extra_before_distributions': 'net_income',
                    'operating_income': 'operating_income',
                    'revenue': 'revenue',
                    'gross_profit': 'gross_profit',
                    'depreciationamort': 'depreciation_amortization',
                    'capitalexpenditures': 'capital_expenditures'
                }

                # Apply mappings
                for old_col, new_col in actual_column_mappings.items():
                    if old_col in df.columns and new_col not in df.columns:
                        df = df.rename(columns={old_col: new_col})

                # Generate quarterly dates including previous year's Q4 for filling early months
                start_year = int(start_date.split('-')[0])
                end_year = int(end_date.split('-')[0])

                # Include Q4 of previous year to fill Jan-Feb
                quarterly_dates = []

                # Add Q4 of previous year
                prev_year_q4 = pd.Timestamp(f"{start_year - 1}-12-31")
                quarterly_dates.append(prev_year_q4)

                # Add quarters from current year range
                for year in range(start_year, end_year + 1):
                    for quarter in [1, 2, 3, 4]:
                        if quarter == 1:
                            quarter_end = pd.Timestamp(f"{year}-03-31")
                        elif quarter == 2:
                            quarter_end = pd.Timestamp(f"{year}-06-30")
                        elif quarter == 3:
                            quarter_end = pd.Timestamp(f"{year}-09-30")
                        else:
                            quarter_end = pd.Timestamp(f"{year}-12-31")

                        if quarter_end <= pd.Timestamp(end_date):
                            quarterly_dates.append(quarter_end)

                # Take the most recent data points (first rows typically have data)
                # Filter to rows with actual data
                data_rows = []
                for idx, row in df.iterrows():
                    # Check if the row has some non-null fundamental data
                    fundamental_cols = ['shares_outstanding', 'total_assets', 'revenue', 'net_income']
                    has_data = any(pd.notna(row.get(col)) for col in fundamental_cols if col in row)
                    if has_data:
                        data_rows.append(row)
                        if len(data_rows) >= len(quarterly_dates):
                            break

                if data_rows:
                    # Create a proper DataFrame with quarterly dates
                    fund_df = pd.DataFrame()

                    # Map each quarter to its corresponding data row
                    # The LSEG API typically returns quarterly data in reverse chronological order
                    # So we need to map quarters correctly to their actual reported data
                    for i, quarter_date in enumerate(quarterly_dates):
                        if i < len(data_rows):
                            # Use the corresponding quarterly data
                            row_data = data_rows[i].copy()
                        else:
                            # If we have fewer data rows than quarters, skip this quarter
                            continue

                        row_data['date'] = quarter_date
                        fund_df = pd.concat([fund_df, row_data.to_frame().T], ignore_index=True)

                    fundamentals_parts.append(fund_df)

        except Exception as e:
            pass  # Fundamentals data unavailable

        # Combine and forward-fill fundamentals
        fundamentals = pd.DataFrame()
        if fundamentals_parts:
            fundamentals = pd.concat(fundamentals_parts, ignore_index=True)

            # Generate month-end dates for the requested period
            monthly_dates = pd.date_range(
                pd.to_datetime(start_date).to_period('M').end_time,
                pd.to_datetime(end_date).to_period('M').end_time,
                freq='M'
            )

            filled_parts = []
            for ric in fundamentals['ric'].unique():
                ric_data = fundamentals[fundamentals['ric'] == ric].copy()

                # Sort by date and forward fill quarterly data to monthly
                ric_data = ric_data.sort_values('date')

                # Create a monthly series that maps each month to the appropriate quarter
                monthly_fund_data = pd.DataFrame({'date': monthly_dates})
                monthly_fund_data['ric'] = ric

                # For each month, find the most recent quarterly data
                for _, month_row in monthly_fund_data.iterrows():
                    month_date = month_row['date']

                    # Find the most recent quarterly data before or on this month
                    available_quarters = ric_data[ric_data['date'] <= month_date]

                    if not available_quarters.empty:
                        # Use the most recent quarterly data
                        latest_quarter = available_quarters.iloc[-1]

                        # Copy all fundamental data columns
                        for col in ric_data.columns:
                            if col not in ['date', 'ric']:
                                monthly_fund_data.loc[monthly_fund_data['date'] == month_date, col] = latest_quarter[col]

                filled_parts.append(monthly_fund_data)

            if filled_parts:
                fundamentals = pd.concat(filled_parts, ignore_index=True)

    # Combine and forward-fill prices to monthly frequency
    if all_data_parts:
        prices = pd.concat(all_data_parts, ignore_index=True)
        prices['date'] = prices['date'].dt.to_period('M').dt.end_time.dt.date
        prices['date'] = pd.to_datetime(prices['date'])
        prices = prices.sort_values(['ric', 'date']).reset_index(drop=True)

        # Forward-fill prices to monthly frequency (same as fundamentals)
        monthly_dates = pd.date_range(
            pd.to_datetime(start_date).to_period('M').end_time,
            pd.to_datetime(end_date).to_period('M').end_time,
            freq='M'
        )

        filled_price_parts = []
        for ric in prices['ric'].unique():
            ric_data = prices[prices['ric'] == ric].copy()
            ric_data = ric_data.set_index('date').reindex(monthly_dates, method='ffill')
            ric_data['ric'] = ric
            ric_data = ric_data.reset_index().rename(columns={'index': 'date'})
            filled_price_parts.append(ric_data)

        if filled_price_parts:
            prices = pd.concat(filled_price_parts, ignore_index=True)
    else:
        prices = pd.DataFrame(columns=['ric', 'date', 'close', 'adj_close', 'volume_msum'])

    # Merge data
    if not prices.empty and not fundamentals.empty:
        prices['date'] = pd.to_datetime(prices['date'])
        fundamentals['date'] = pd.to_datetime(fundamentals['date'])
        # Use outer join to ensure we don't lose any data, but both should have same monthly coverage now
        merged = pd.merge(prices, fundamentals, on=['ric', 'date'], how='outer')
    elif not prices.empty:
        merged = prices.copy()
    elif not fundamentals.empty:
        merged = fundamentals.copy()
    else:
        merged = pd.DataFrame()

    # Clean up duplicate dates and sort
    if not merged.empty:
        # Keep only month-end dates and sort
        merged = merged.sort_values(['ric', 'date'])

        # Remove duplicates, keeping the row with more non-null values
        def select_best_row(group):
            if len(group) == 1:
                return group
            # Count non-null values for each row
            non_null_counts = group.notna().sum(axis=1)
            # Return the row with the most non-null values
            best_idx = non_null_counts.idxmax()
            return group.loc[[best_idx]]

        merged = merged.groupby(['ric', merged['date'].dt.date]).apply(select_best_row).reset_index(drop=True)

        # Ensure we have proper month-end dates
        merged['date'] = pd.to_datetime(merged['date']).dt.to_period('M').dt.end_time

    # Clean up and ensure numeric types
    if not merged.empty:
        numeric_cols = [
            'close', 'adj_close', 'volume_msum', 'shares_outstanding', 'shareholders_equity',
            'total_assets', 'total_debt', 'long_term_debt', 'current_assets', 'current_liabilities',
            'net_income', 'operating_income', 'revenue', 'gross_profit',
            'depreciation_amortization', 'capital_expenditures'
        ]

        for col in numeric_cols:
            if col in merged.columns:
                merged[col] = pd.to_numeric(merged[col], errors='coerce')

        # Remove unwanted columns
        cols_to_remove = [col for col in merged.columns if 'level_' in str(col).lower() or col == 'index']
        if cols_to_remove:
            merged = merged.drop(columns=cols_to_remove)

    return merged


def get_stockholm_exchange_rics():
    """
    Fetch all current and historical Stockholm Exchange companies to avoid survivorship bias
    """
    if ld is None:
        print("Warning: lseg.data not available - returning empty list")
        return []

    with session_scope():
        try:
            # Get current Stockholm Exchange companies
            print("Fetching current Stockholm Exchange companies...")
            current_companies = ld.get_data(
                universe="0#.OMXSPI",  # OMX Stockholm PI constituents
                fields=["TR.CommonName", "TR.CompanyMarketCap"]
            )

            current_rics = []
            if current_companies is not None and not current_companies.empty:
                # Use the 'Instrument' column if it exists, otherwise use index
                if 'Instrument' in current_companies.columns:
                    current_rics = current_companies['Instrument'].dropna().astype(str).tolist()
                else:
                    current_rics = [str(ric) for ric in current_companies.index.tolist()]
                print(f"Found {len(current_rics)} current OMX Stockholm companies")
                print(f"Sample RICs: {current_rics[:5]}")

            # Get historical Stockholm Exchange companies (including delisted)
            print("Fetching historical/delisted Stockholm Exchange companies...")
            historical_companies = ld.get_data(
                universe="SCREEN(U(IN(Equity(active or inactive),ExchangeCountryCode,SE);IN(ExchangeMarketIdCode,XSTO)))",
                fields=["TR.CommonName", "TR.CompanyMarketCap", "TR.CompanyStatus"]
            )

            historical_rics = []
            if historical_companies is not None and not historical_companies.empty:
                # Use the 'Instrument' column if it exists, otherwise use index
                if 'Instrument' in historical_companies.columns:
                    historical_rics = historical_companies['Instrument'].dropna().astype(str).tolist()
                else:
                    historical_rics = [str(ric) for ric in historical_companies.index.tolist()]
                print(f"Found {len(historical_rics)} historical Stockholm Exchange companies")

            # Combine and deduplicate
            all_rics = list(set(current_rics + historical_rics))
            print(f"Total unique Stockholm Exchange companies: {len(all_rics)}")

            return all_rics

        except Exception as e:
            print(f"Error fetching Stockholm Exchange companies: {e}")
            # Fallback: try to get just the main index
            try:
                fallback = ld.get_data(
                    universe="0#.OMXSPI",
                    fields=["TR.CommonName"]
                )
                if fallback is not None and not fallback.empty:
                    # Use the 'Instrument' column if it exists, otherwise use index
                    if 'Instrument' in fallback.columns:
                        fallback_rics = fallback['Instrument'].dropna().astype(str).tolist()
                    else:
                        fallback_rics = [str(ric) for ric in fallback.index.tolist()]
                    print(f"Using fallback: {len(fallback_rics)} companies from OMXSPI")
                    print(f"Sample fallback RICs: {fallback_rics[:5]}")
                    return fallback_rics
            except:
                pass

            return []


def run_fundamentals_pipeline(rics, start_date, end_date, output_file=None, batch_size=50):
    """
    Main pipeline for fundamentals data with batching support for large datasets
    """
    total_rics = len(rics)
    print(f"Processing {total_rics} companies from {start_date} to {end_date}")

    all_data = []

    # Process in batches to avoid API timeouts and memory issues
    for i in range(0, total_rics, batch_size):
        batch_rics = rics[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_rics + batch_size - 1) // batch_size

        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch_rics)} companies)")
        print(f"Companies: {', '.join(batch_rics[:5])}{'...' if len(batch_rics) > 5 else ''}")

        # Fetch data for this batch
        batch_data = fetch_fundamentals_data(batch_rics, start_date, end_date)

        if not batch_data.empty:
            all_data.append(batch_data)
            print(f"Batch {batch_num} complete: {len(batch_data)} rows")
        else:
            print(f"Batch {batch_num}: No data retrieved")

    # Combine all batches
    if all_data:
        data = pd.concat(all_data, ignore_index=True)
        data = data.sort_values(['ric', 'date']).reset_index(drop=True)
    else:
        print("No data retrieved from any batch.")
        return pd.DataFrame()

    print(f"\nPipeline complete! Dataset: {len(data)} rows × {len(data.columns)} columns")
    print(f"Companies: {data['ric'].nunique()}")
    if not data.empty:
        print(f"Date range: {data['date'].min().strftime('%Y-%m-%d')} to {data['date'].max().strftime('%Y-%m-%d')}")

    # Save output
    if output_file:
        data.to_csv(output_file, index=False)
        print(f"Saved: {output_file}")

    return data


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'omx':
        # Stockholm Exchange OMX full dataset 1999-2024
        print("=== Stockholm Exchange OMX Pipeline 1999-2024 ===")
        print("Fetching all listed and delisted companies to avoid survivorship bias...")

        stockholm_rics = get_stockholm_exchange_rics()

        if not stockholm_rics:
            print("Error: Could not fetch Stockholm Exchange companies")
            sys.exit(1)

        result = run_fundamentals_pipeline(
            rics=stockholm_rics,
            start_date='1999-01-01',
            end_date='2024-12-31',
            output_file='omx_fundamentals_1999_2024.csv',
            batch_size=25  # Smaller batches for 25-year dataset
        )

    else:
        # Example usage - test with Ericsson for 2024
        result = run_fundamentals_pipeline(
            rics=['ERICb.ST'],
            start_date='2024-01-01',
            end_date='2024-12-31',
            output_file='pipeline.csv'
        )