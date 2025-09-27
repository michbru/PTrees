#!/usr/bin/env python3
"""
Final Working Pipeline for P-Trees Data Processing

This pipeline implements the exact specifications for P-Trees preprocessing:
- Historical data seeding: 5+ quarters before start for TTM, prices from 2013-12 for momentum
- Field-level monthly API calls with proper fallbacks
- Proper fundamentals handling with Q&A data in SEK currency
- TTM calculations with 4-quarter rolling sums (min_periods=4)
- 12-month averages for assets and equity (min_periods=12)
- Complete characteristics calculations with exact formulas
- NaN handling: keep NaN until sufficient data, don't default to 0
- P-Trees preprocessing: winsorize, min-max to [-1,1], then fill remaining NaN to 0
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


# --- Data Fetching Functions ------------------------------------------------

def fetch_working_data(rics, start_date, end_date):
    """
    Fetch complete dataset with extended historical data for proper calculations.

    Historical seeding strategy:
    - Fundamentals: Start 5+ quarters before first month (2+ years) for TTM calculations
    - Prices: Start from 2013-12 for mom_12_1 coverage and sufficient momentum history
    """
    print("1) Calculating extended date ranges for historical data seeding...")

    # Calculate extended start dates for sufficient history
    start_year = int(start_date.split('-')[0])
    fund_start = f"{start_year - 2}-01-01"  # 5+ quarters before first month
    price_start = f"{start_year - 2}-12-01"  # For mom_12_1 coverage

    print(f"   Fundamentals range: {fund_start} to {end_date}")
    print(f"   Price range: {price_start} to {end_date}")

    # Fetch price data with field-level calls and fallbacks
    print("2) Fetching price data (field-level API calls)...")

    if ld is None:
        # Test mode - return empty DataFrame
        return pd.DataFrame()

    # Fetch field-level data by RIC for better control
    print("   Fetching field-level price and volume data by RIC...")

    all_data_parts = []

    with session_scope():
        for ric in rics:
            print(f"     Processing {ric}...")
            ric_data = {}

            # Generate month-end date range for this RIC
            date_range = pd.date_range(start=price_start, end=end_date, freq='M')  # Month-end frequency

            # Fetch TR.PriceClose (close)
            try:
                close_data = ld.get_data(
                    universe=[ric],
                    fields=["TR.PriceClose"],
                    parameters={
                        "SDate": price_start,
                        "EDate": end_date,
                        "Frq": "M"
                    }
                )
                if close_data is not None and not close_data.empty:
                    # Extract close prices
                    close_values = close_data.iloc[:, -1].values  # Last column should be the price
                    ric_data['close'] = close_values[:len(date_range)]
            except Exception as e:
                print(f"       TR.PriceClose failed for {ric}: {e}")

            # Fetch TR.ClosePrice (adjusted close)
            try:
                adj_close_data = ld.get_data(
                    universe=[ric],
                    fields=["TR.ClosePrice"],
                    parameters={
                        "SDate": price_start,
                        "EDate": end_date,
                        "Frq": "M",
                        "Adjusted": "Y"
                    }
                )
                if adj_close_data is not None and not adj_close_data.empty:
                    # Extract adjusted close prices
                    adj_close_values = adj_close_data.iloc[:, -1].values
                    ric_data['adj_close'] = adj_close_values[:len(date_range)]
            except Exception as e:
                print(f"       TR.ClosePrice(Adjusted=Y) failed for {ric}: {e}")
                # Use close as fallback
                if 'close' in ric_data:
                    ric_data['adj_close'] = ric_data['close']

            # Fetch TR.Volume (monthly sum)
            try:
                volume_data = ld.get_data(
                    universe=[ric],
                    fields=["TR.Volume"],
                    parameters={
                        "SDate": price_start,
                        "EDate": end_date,
                        "Frq": "M",
                        "Calc": "Sum"
                    }
                )
                if volume_data is not None and not volume_data.empty:
                    volume_values = volume_data.iloc[:, -1].values
                    ric_data['volume_msum'] = volume_values[:len(date_range)]
            except Exception as e:
                print(f"       TR.Volume(Calc=Sum) failed for {ric}: {e}")
                try:
                    # Fallback without Calc parameter
                    volume_data = ld.get_data(
                        universe=[ric],
                        fields=["TR.Volume"],
                        parameters={
                            "SDate": price_start,
                            "EDate": end_date,
                            "Frq": "M"
                        }
                    )
                    if volume_data is not None and not volume_data.empty:
                        volume_values = volume_data.iloc[:, -1].values
                        ric_data['volume_msum'] = volume_values[:len(date_range)]
                except Exception as e2:
                    print(f"       TR.Volume fallback also failed for {ric}: {e2}")

            # Create DataFrame for this RIC
            if ric_data:  # Only if we got some data
                ric_df = pd.DataFrame({
                    'ric': ric,
                    'date': date_range
                })

                # Add the fetched data columns
                for col, values in ric_data.items():
                    if len(values) == len(date_range):
                        ric_df[col] = values
                    else:
                        # Pad or truncate if length mismatch
                        padded_values = list(values) + [np.nan] * (len(date_range) - len(values))
                        ric_df[col] = padded_values[:len(date_range)]

                all_data_parts.append(ric_df)

    # Combine all RIC data
    if all_data_parts:
        prices = pd.concat(all_data_parts, ignore_index=True)
    else:
        prices = pd.DataFrame(columns=['ric', 'date', 'close', 'adj_close', 'volume_msum'])

    # Ensure dates are month-end and clean up
    print("3) Converting to month-end dates and cleaning data...")
    if not prices.empty:
        # Convert any first-of-month dates to month-end dates
        prices['date'] = prices['date'].dt.to_period('M').dt.end_time.dt.date
        prices['date'] = pd.to_datetime(prices['date'])

        # Sort by RIC and date
        prices = prices.sort_values(['ric', 'date']).reset_index(drop=True)
        print(f"   Retrieved {prices.shape[0]} price records with month-end dates")
    else:
        print("   No price data retrieved")

    # Calculate returns (first observation will be NaN)
    if not prices.empty and 'adj_close' in prices.columns:
        prices = prices.sort_values(['ric', 'date'])
        prices['ret'] = prices.groupby('ric')['adj_close'].pct_change()

        # Ensure volume_msum is numeric and keep 0 values (don't convert to NaN)
        if 'volume_msum' in prices.columns:
            prices['volume_msum'] = pd.to_numeric(prices['volume_msum'], errors='coerce')
            # Keep 0 as 0, only replace actual NaN with 0 for thin trading months
            prices['volume_msum'] = prices['volume_msum'].fillna(0)

    # Fetch fundamentals data
    print("4) Fetching fundamentals data (Q + A frequency, SEK currency)...")
    fundamentals_parts = []

    if ld is not None:
        # Field mappings using commonly available TR fields (fallback to working variants)
        field_map = {
            'TR.TotalAssets': 'total_assets',  # More common than TR.TotalAssetsActual
            'TR.ShareholdersEquity': 'shareholders_equity',
            'TR.SharesOutstanding': 'shares_outstanding',  # More common than TR.CommonSharesOutstanding
            'TR.NetIncome': 'net_income',
            'TR.OperatingIncome': 'operating_income',
            'TR.Revenue': 'revenue',
            'TR.GrossProfit': 'gross_profit',
            'TR.CashFromOperations': 'cash_from_ops',
            'TR.CapitalExpenditures': 'capex',
            'TR.DepreciationAmort': 'dep_amort',
            'TR.TotalDebt': 'total_debt',
            'TR.LongTermDebt': 'long_term_debt',
            'TR.CurrentAssets': 'current_assets',
            'TR.CurrentLiabilities': 'current_liabilities'
        }

        with session_scope():
            for freq in ['FQ', 'FY']:  # Fiscal Quarterly and Fiscal Year
                print(f"   Fetching {freq} frequency fundamentals...")
                try:
                    fund_data = ld.get_data(
                        universe=rics,
                        fields=list(field_map.keys()),
                        parameters={
                            "SDate": fund_start,
                            "EDate": end_date,
                            "Frq": freq,
                            "Curn": "SEK"  # SEK currency
                        }
                    )

                    if fund_data is not None and not fund_data.empty:
                        df = fund_data.copy()
                        df.columns = [c.strip().replace(' ', '_').lower() for c in df.columns]
                        df = df.rename(columns={'instrument': 'ric'})

                        # Handle date column
                        df = df.reset_index()
                        if 'date' not in df.columns:
                            date_cols = [c for c in df.columns if 'date' in str(c).lower()]
                            if date_cols:
                                df['date'] = df[date_cols[0]]
                            elif 'index' in df.columns:
                                df['date'] = df['index']

                        # Try different date parsing approaches
                        try:
                            df['date'] = pd.to_datetime(df['date'])
                        except:
                            try:
                                # If it's numeric, treat as days since epoch or similar
                                df['date'] = pd.to_datetime(df['date'], unit='D', origin='1900-01-01')
                            except:
                                # Last resort: try as string
                                df['date'] = pd.to_datetime(df['date'], errors='coerce')

                        # Rename fields to canonical names
                        for tr_field, canonical in field_map.items():
                            tr_lower = tr_field.lower().replace('.', '_').replace('tr_', '')
                            if tr_lower in df.columns:
                                df = df.rename(columns={tr_lower: canonical})

                        df['freq'] = freq
                        fundamentals_parts.append(df)

                except Exception as e:
                    print(f"     {freq} frequency fundamentals failed: {e}")

    # Combine and process fundamentals
    if fundamentals_parts:
        fundamentals = pd.concat(fundamentals_parts, ignore_index=True)
        fundamentals = fundamentals.sort_values(['ric', 'date', 'freq'])

        # Prefer FQ over FY for same date
        fundamentals = fundamentals.drop_duplicates(['ric', 'date'], keep='first')
        fundamentals = fundamentals.drop(columns=['freq'])
    else:
        fundamentals = pd.DataFrame(columns=['ric', 'date'] + list(field_map.values()))

    print("5) Building TTM calculations...")
    # TTM calculations (4-quarter rolling sums with min_periods=4)
    # ⚠️ IMPORTANT: Keep NaN until genuinely 4 quarters available
    if not fundamentals.empty:
        fundamentals = fundamentals.sort_values(['ric', 'date'])

        # TTM fields: rolling 4Q sums
        ttm_fields = {
            'net_income': 'ni_ttm',
            'revenue': 'sales_ttm',
            'operating_income': 'oi_ttm',
            'gross_profit': 'gp_ttm'
        }

        for source_field, ttm_field in ttm_fields.items():
            if source_field in fundamentals.columns:
                print(f"     Building {ttm_field} from {source_field}")
                # Rolling 4Q sum, keep NaN until we have 4 quarters
                fundamentals[ttm_field] = (fundamentals.groupby('ric')[source_field]
                                         .rolling(4, min_periods=4)
                                         .sum()
                                         .reset_index(0, drop=True))
            else:
                print(f"     Warning: {source_field} not found for {ttm_field}")
                fundamentals[ttm_field] = np.nan

    print("6) Forward-filling fundamentals to monthly frequency...")
    # Forward-fill fundamentals to monthly frequency
    if not fundamentals.empty:
        # Create monthly date range with month-end dates to match prices
        monthly_dates = pd.date_range(
            pd.to_datetime(fund_start).to_period('M').end_time,
            pd.to_datetime(end_date).to_period('M').end_time,
            freq='M'  # Month end
        )

        # Forward fill for each RIC
        filled_parts = []
        for ric in fundamentals['ric'].unique():
            ric_data = fundamentals[fundamentals['ric'] == ric].copy()
            ric_data = ric_data.set_index('date').reindex(monthly_dates, method='ffill')
            ric_data['ric'] = ric
            ric_data = ric_data.reset_index().rename(columns={'index': 'date'})
            filled_parts.append(ric_data)

        if filled_parts:
            fundamentals = pd.concat(filled_parts, ignore_index=True)
            print(f"   Retrieved {fundamentals.shape[0]} fundamental records")
        else:
            print("   No fundamentals data after forward filling")

    print("7) Computing 12-month averages and lags...")
    # 12-month averages (min_periods=12) and 6-month lags per P-Trees spec
    if not fundamentals.empty:
        fundamentals = fundamentals.sort_values(['ric', 'date'])

        # 12-month rolling averages: mean(current, t-12)
        if 'total_assets' in fundamentals.columns:
            print("     Building assets_avg (12-month mean)")
            fundamentals['assets_avg'] = (fundamentals.groupby('ric')['total_assets']
                                        .rolling(12, min_periods=12)
                                        .mean()
                                        .reset_index(0, drop=True))
        else:
            fundamentals['assets_avg'] = np.nan

        if 'shareholders_equity' in fundamentals.columns:
            print("     Building equity_avg (12-month mean)")
            fundamentals['equity_avg'] = (fundamentals.groupby('ric')['shareholders_equity']
                                        .rolling(12, min_periods=12)
                                        .mean()
                                        .reset_index(0, drop=True))

            print("     Building book_equity_lag6m (6-month lag)")
            # 6-month lag for book equity (shifted 6 calendar months)
            fundamentals['book_equity_lag6m'] = (fundamentals.groupby('ric')['shareholders_equity']
                                               .shift(6))
        else:
            fundamentals['equity_avg'] = np.nan
            fundamentals['book_equity_lag6m'] = np.nan

    # Merge prices and fundamentals
    print("8) Merging prices and fundamentals...")
    if not prices.empty and not fundamentals.empty:
        # Ensure consistent date types before merging
        prices['date'] = pd.to_datetime(prices['date'])
        fundamentals['date'] = pd.to_datetime(fundamentals['date'])
        merged = pd.merge(prices, fundamentals, on=['ric', 'date'], how='outer')
    elif not prices.empty:
        merged = prices.copy()
        merged['date'] = pd.to_datetime(merged['date'])
    elif not fundamentals.empty:
        merged = fundamentals.copy()
        merged['date'] = pd.to_datetime(merged['date'])
    else:
        merged = pd.DataFrame()

    print(f"   Created merged dataset with {merged.shape[0]} records")

    print("9) Computing derived fields (only when inputs exist)...")
    # D) Complete derived fields implementation per P-Trees specifications
    if not merged.empty:
        merged = merged.sort_values(['ric', 'date'])

        print("     Computing market cap and size...")
        # mkt_cap = shares_outstanding * adj_close
        if 'adj_close' in merged.columns and 'shares_outstanding' in merged.columns:
            valid_mask = (merged['adj_close'].notna() & merged['shares_outstanding'].notna() &
                         (merged['shares_outstanding'] != 0))
            merged.loc[valid_mask, 'mkt_cap'] = (merged.loc[valid_mask, 'adj_close'] *
                                               merged.loc[valid_mask, 'shares_outstanding'])

            # size = log(mkt_cap)
            mkt_cap_valid = merged['mkt_cap'].notna() & (merged['mkt_cap'] > 0)
            merged.loc[mkt_cap_valid, 'size'] = np.log(merged.loc[mkt_cap_valid, 'mkt_cap'])

        print("     Computing valuation ratios...")
        # sp = sales_ttm / mkt_cap
        if 'sales_ttm' in merged.columns and 'mkt_cap' in merged.columns:
            valid_mask = (merged['sales_ttm'].notna() & merged['mkt_cap'].notna() &
                         (merged['mkt_cap'] != 0))
            merged.loc[valid_mask, 'sp'] = (merged.loc[valid_mask, 'sales_ttm'] /
                                          merged.loc[valid_mask, 'mkt_cap'])

        # bm = book_equity_lag6m / mkt_cap
        if 'book_equity_lag6m' in merged.columns and 'mkt_cap' in merged.columns:
            valid_mask = (merged['book_equity_lag6m'].notna() & merged['mkt_cap'].notna() &
                         (merged['mkt_cap'] != 0))
            merged.loc[valid_mask, 'bm'] = (merged.loc[valid_mask, 'book_equity_lag6m'] /
                                          merged.loc[valid_mask, 'mkt_cap'])

        print("     Computing growth measures...")
        # sgr = sales_ttm.pct_change()
        if 'sales_ttm' in merged.columns:
            merged['sgr'] = merged.groupby('ric')['sales_ttm'].pct_change()

        # assets_growth = total_assets.pct_change()
        if 'total_assets' in merged.columns:
            merged['assets_growth'] = merged.groupby('ric')['total_assets'].pct_change()

        print("     Computing profitability ratios...")
        # op_prof = oi_ttm / total_assets (fallback to shareholders_equity if assets missing)
        if 'oi_ttm' in merged.columns:
            if 'total_assets' in merged.columns:
                valid_mask = (merged['oi_ttm'].notna() & merged['total_assets'].notna() &
                             (merged['total_assets'] != 0))
                merged.loc[valid_mask, 'op_prof'] = (merged.loc[valid_mask, 'oi_ttm'] /
                                                   merged.loc[valid_mask, 'total_assets'])
            elif 'shareholders_equity' in merged.columns:
                print("       Using shareholders_equity fallback for op_prof")
                valid_mask = (merged['oi_ttm'].notna() & merged['shareholders_equity'].notna() &
                             (merged['shareholders_equity'] != 0))
                merged.loc[valid_mask, 'op_prof'] = (merged.loc[valid_mask, 'oi_ttm'] /
                                                   merged.loc[valid_mask, 'shareholders_equity'])

        # pm = ni_ttm / sales_ttm
        if 'ni_ttm' in merged.columns and 'sales_ttm' in merged.columns:
            valid_mask = (merged['ni_ttm'].notna() & merged['sales_ttm'].notna() &
                         (merged['sales_ttm'] != 0))
            merged.loc[valid_mask, 'pm'] = (merged.loc[valid_mask, 'ni_ttm'] /
                                          merged.loc[valid_mask, 'sales_ttm'])

        # roe = ni_ttm / equity_avg
        if 'ni_ttm' in merged.columns and 'equity_avg' in merged.columns:
            valid_mask = (merged['ni_ttm'].notna() & merged['equity_avg'].notna() &
                         (merged['equity_avg'] != 0))
            merged.loc[valid_mask, 'roe'] = (merged.loc[valid_mask, 'ni_ttm'] /
                                           merged.loc[valid_mask, 'equity_avg'])

        # ato = sales_ttm / assets_avg
        if 'sales_ttm' in merged.columns and 'assets_avg' in merged.columns:
            valid_mask = (merged['sales_ttm'].notna() & merged['assets_avg'].notna() &
                         (merged['assets_avg'] != 0))
            merged.loc[valid_mask, 'ato'] = (merged.loc[valid_mask, 'sales_ttm'] /
                                           merged.loc[valid_mask, 'assets_avg'])

        print("     Computing leverage...")
        # leverage = total_debt / total_assets
        if 'total_debt' in merged.columns and 'total_assets' in merged.columns:
            valid_mask = (merged['total_debt'].notna() & merged['total_assets'].notna() &
                         (merged['total_assets'] != 0))
            merged.loc[valid_mask, 'leverage'] = (merged.loc[valid_mask, 'total_debt'] /
                                                merged.loc[valid_mask, 'total_assets'])

        print("     Computing issuance...")
        # issuance_eq = (shares_outstanding / shares_outstanding.shift(12)) - 1
        if 'shares_outstanding' in merged.columns:
            shares_lag12 = merged.groupby('ric')['shares_outstanding'].shift(12)
            valid_mask = (merged['shares_outstanding'].notna() & shares_lag12.notna() &
                         (shares_lag12 != 0))
            merged.loc[valid_mask, 'issuance_eq'] = ((merged.loc[valid_mask, 'shares_outstanding'] /
                                                    shares_lag12.loc[valid_mask]) - 1)

        print("     Computing liquidity measures...")
        # turnover = volume_msum / shares_outstanding
        if 'volume_msum' in merged.columns and 'shares_outstanding' in merged.columns:
            valid_mask = (merged['volume_msum'].notna() & merged['shares_outstanding'].notna() &
                         (merged['shares_outstanding'] != 0))
            merged.loc[valid_mask, 'turnover'] = (merged.loc[valid_mask, 'volume_msum'] /
                                                merged.loc[valid_mask, 'shares_outstanding'])

        # dolvol = volume_msum * close
        if 'volume_msum' in merged.columns and 'close' in merged.columns:
            valid_mask = merged['volume_msum'].notna() & merged['close'].notna()
            merged.loc[valid_mask, 'dolvol'] = (merged.loc[valid_mask, 'volume_msum'] *
                                              merged.loc[valid_mask, 'close'])

        # std_turn_3m = turnover.rolling(3).std()
        if 'turnover' in merged.columns:
            merged['std_turn_3m'] = (merged.groupby('ric')['turnover']
                                   .rolling(3, min_periods=3)
                                   .std()
                                   .reset_index(0, drop=True))

        # std_dolvol_3m = dolvol.rolling(3).std()
        if 'dolvol' in merged.columns:
            merged['std_dolvol_3m'] = (merged.groupby('ric')['dolvol']
                                     .rolling(3, min_periods=3)
                                     .std()
                                     .reset_index(0, drop=True))

        print("     Computing momentum measures...")
        # Momentum calculations with exact formulas (skip t-1)
        if 'ret' in merged.columns:
            # Shift returns by 1 period (skip t-1)
            ret_lagged = merged.groupby('ric')['ret'].shift(1)

            # mom_12_1 = (1+ret.shift(1)).rolling(11).prod() - 1
            merged['mom_12_1'] = ((1 + ret_lagged).groupby(merged['ric'])
                                .rolling(11, min_periods=11)
                                .apply(np.prod, raw=True)
                                .reset_index(0, drop=True) - 1)

            # mom_6 = (1+ret.shift(1)).rolling(5).prod() - 1
            merged['mom_6'] = ((1 + ret_lagged).groupby(merged['ric'])
                             .rolling(5, min_periods=5)
                             .apply(np.prod, raw=True)
                             .reset_index(0, drop=True) - 1)

            # mom_36 = (1+ret.shift(1)).rolling(35).prod() - 1
            merged['mom_36'] = ((1 + ret_lagged).groupby(merged['ric'])
                              .rolling(35, min_periods=35)
                              .apply(np.prod, raw=True)
                              .reset_index(0, drop=True) - 1)

            # rvar_3m = ret.rolling(3).var()
            merged['rvar_3m'] = (merged.groupby('ric')['ret']
                               .rolling(3, min_periods=3)
                               .var()
                               .reset_index(0, drop=True))

        print("     Ensuring numeric data types...")
        # E) Ensure numeric dtypes (float) for all numeric columns
        # Never default missing TTM/averages to 0 - keep NaN for P-Trees preprocessing
        numeric_cols = [
            'close', 'adj_close', 'volume_msum', 'ret',
            'total_assets', 'shareholders_equity', 'shares_outstanding',
            'net_income', 'operating_income', 'revenue', 'gross_profit',
            'cash_from_ops', 'capex', 'dep_amort', 'total_debt', 'long_term_debt',
            'current_assets', 'current_liabilities',
            'ni_ttm', 'sales_ttm', 'oi_ttm', 'gp_ttm',
            'assets_avg', 'equity_avg', 'book_equity_lag6m',
            'mkt_cap', 'size', 'sp', 'bm', 'sgr', 'op_prof', 'pm', 'roe', 'ato',
            'assets_growth', 'leverage', 'issuance_eq',
            'turnover', 'dolvol', 'std_turn_3m', 'std_dolvol_3m',
            'mom_12_1', 'mom_6', 'mom_36', 'rvar_3m'
        ]

        for col in numeric_cols:
            if col in merged.columns:
                merged[col] = pd.to_numeric(merged[col], errors='coerce')

    return merged


def qa_checks(df, rics, start_date, end_date):
    """
    F) QA checks and validation per P-Trees requirements
    """
    print("12) Running QA checks...")

    if df.empty:
        print("     Warning: No data for QA checks")
        return

    for ric in rics:
        ric_data = df[df['ric'] == ric].copy()
        if ric_data.empty:
            continue

        print(f"     QA checks for {ric}:")

        # Check volume_msum coverage
        volume_missing = ric_data['volume_msum'].isna() | (ric_data['volume_msum'] == 0)
        if volume_missing.sum() > 0:
            missing_months = ric_data[volume_missing]['date'].dt.strftime('%Y-%m').tolist()
            print(f"       volume_msum missing/zero in {len(missing_months)} months: {missing_months[:5]}{'...' if len(missing_months) > 5 else ''}")
        else:
            print(f"       volume_msum: OK Non-blank in all months")

        # Check TTM availability (should be non-NaN by mid-year after 4Q)
        mid_year_idx = len(ric_data) // 2
        if 'sales_ttm' in ric_data.columns and len(ric_data) > mid_year_idx:
            sales_ttm_midyear = ric_data.iloc[mid_year_idx]['sales_ttm']
            if pd.notna(sales_ttm_midyear):
                print(f"       sales_ttm: OK Available by mid-year ({sales_ttm_midyear:.2e})")
            else:
                print(f"       sales_ttm: WARNING Still NaN by mid-year")

        # Check 12-month averages (should be non-NaN after 12 months)
        if len(ric_data) >= 12:
            assets_avg_12m = ric_data.iloc[11]['assets_avg'] if 'assets_avg' in ric_data.columns else np.nan
            equity_avg_12m = ric_data.iloc[11]['equity_avg'] if 'equity_avg' in ric_data.columns else np.nan

            if pd.notna(assets_avg_12m):
                print(f"       assets_avg: OK Available after 12 months ({assets_avg_12m:.2e})")
            else:
                print(f"       assets_avg: WARNING Still NaN after 12 months")

            if pd.notna(equity_avg_12m):
                print(f"       equity_avg: OK Available after 12 months ({equity_avg_12m:.2e})")
            else:
                print(f"       equity_avg: WARNING Still NaN after 12 months")

        # Check book_equity_lag6m (should be non-NaN once 6m lag exists)
        if len(ric_data) >= 7 and 'book_equity_lag6m' in ric_data.columns:
            bm_7th_month = ric_data.iloc[6]['book_equity_lag6m']
            if pd.notna(bm_7th_month):
                print(f"       book_equity_lag6m: OK Available after 6m lag ({bm_7th_month:.2e})")
            else:
                print(f"       book_equity_lag6m: WARNING Still NaN after 6m lag")

        # Check momentum (mom_12_1 should be non-NaN once ≥12 months history, skip t-1)
        if len(ric_data) >= 13 and 'mom_12_1' in ric_data.columns:
            mom_12_1_available = ric_data.iloc[12]['mom_12_1']
            if pd.notna(mom_12_1_available):
                print(f"       mom_12_1: OK Available after 12m+ history ({mom_12_1_available:.4f})")
            else:
                print(f"       mom_12_1: WARNING Still NaN after 12m+ history")

        # Check rvar_3m (should be non-NaN from month 3 onward)
        if len(ric_data) >= 3 and 'rvar_3m' in ric_data.columns:
            rvar_3rd_month = ric_data.iloc[2]['rvar_3m']
            if pd.notna(rvar_3rd_month):
                print(f"       rvar_3m: OK Available from month 3 ({rvar_3rd_month:.6f})")
            else:
                print(f"       rvar_3m: WARNING Still NaN from month 3")

        # Summary statistics
        print(f"       Data range: {ric_data['date'].min().strftime('%Y-%m-%d')} to {ric_data['date'].max().strftime('%Y-%m-%d')}")
        print(f"       Total observations: {len(ric_data)}")


def preprocess_for_ptrees(df, start_date, end_date, winsor_pct=(1, 99)):
    """
    P-Trees preprocessing: trim to requested window, winsorize, min-max normalize, fill NaN to 0
    """
    if df.empty:
        return df

    print("10) P-Trees preprocessing...")

    # Trim to requested date window
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)].copy()

    if df.empty:
        return df

    # Create month-year grouping for cross-sectional operations
    df['year_month'] = df['date'].dt.to_period('M')

    # Define characteristics columns (exclude basic data columns)
    exclude_cols = {'ric', 'date', 'year_month', 'close', 'adj_close', 'volume_msum', 'shares_outstanding',
                   'total_assets', 'revenue', 'gross_profit', 'operating_income', 'total_debt',
                   'long_term_debt', 'current_assets', 'current_liabilities', 'shareholders_equity', 'ret'}

    char_cols = [col for col in df.columns
                 if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col])]

    print(f"   Processing {len(char_cols)} characteristics columns...")

    for col in char_cols:
        # Winsorize per month (cross-sectional)
        def winsorize_month(group):
            if group.notna().sum() < 2:  # Need at least 2 non-NaN values
                return group
            lower = np.percentile(group.dropna(), winsor_pct[0])
            upper = np.percentile(group.dropna(), winsor_pct[1])
            return group.clip(lower=lower, upper=upper)

        df[col] = df.groupby('year_month')[col].transform(winsorize_month)

        # Min-max normalize to [-1, 1] per month
        def minmax_normalize(group):
            valid_group = group.dropna()
            if len(valid_group) < 2:
                return group
            min_val = valid_group.min()
            max_val = valid_group.max()
            if max_val == min_val:
                return group * 0  # All same value -> 0
            return 2 * (group - min_val) / (max_val - min_val) - 1

        df[col] = df.groupby('year_month')[col].transform(minmax_normalize)

        # Fill remaining NaN with 0 (P-Trees requirement)
        df[col] = df[col].fillna(0)

    # Drop the temporary grouping column and any stray index columns
    df = df.drop(columns=['year_month'])

    # Remove any stray index columns (level_0, level_1, etc.)
    stray_cols = [col for col in df.columns if 'level_' in str(col).lower() or col == 'index']
    if stray_cols:
        print(f"   Removing stray index columns: {stray_cols}")
        df = df.drop(columns=stray_cols)

    return df


def run_pipeline(rics, start_date, end_date, output_file=None):
    """
    Main pipeline orchestrator
    """
    print("=" * 80)
    print("FINAL WORKING PIPELINE - P-Trees Data Processing")
    print("=" * 80)
    print(f"RICs: {rics}")
    print(f"Date Range: {start_date} to {end_date}")
    print()

    # Fetch and process all data with extended historical range
    merged_data = fetch_working_data(rics, start_date, end_date)

    if merged_data.empty:
        print("No data retrieved. Returning empty DataFrame.")
        return pd.DataFrame()

    # Run QA checks on the complete dataset before P-Trees preprocessing
    qa_checks(merged_data, rics, start_date, end_date)

    # Apply P-Trees preprocessing
    final_data = preprocess_for_ptrees(merged_data, start_date, end_date)

    print(f"11) Pipeline complete!")
    print(f"    Final dataset: {len(final_data)} rows × {len(final_data.columns)} columns")
    print(f"    Date range in output: {final_data['date'].min()} to {final_data['date'].max()}")

    # Save output
    if output_file:
        # Save both CSV and Parquet formats
        csv_file = output_file.replace('.parquet', '.csv') if output_file.endswith('.parquet') else output_file
        parquet_file = output_file.replace('.csv', '.parquet') if output_file.endswith('.csv') else output_file + '.parquet'

        final_data.to_csv(csv_file, index=False)
        final_data.to_parquet(parquet_file, index=False)
        print(f"    Saved: {csv_file}")
        print(f"    Saved: {parquet_file}")

    return final_data


if __name__ == '__main__':
    # Example usage
    result = run_pipeline(
        rics=['ERICb.ST'],
        start_date='2015-01-01',
        end_date='2015-12-31',
        output_file='final_pipeline_output.csv'
    )

    if not result.empty:
        print(f"\nSample of final output:")
        # Display available columns
        available_cols = ['ric', 'date', 'ret']
        for col in ['size', 'sp', 'bm', 'mom_12_1', 'mom_6', 'rvar_3m']:
            if col in result.columns:
                available_cols.append(col)
        print(result[available_cols].head(10))