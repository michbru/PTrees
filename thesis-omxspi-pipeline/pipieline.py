#!/usr/bin/env python3
"""
Single-file final working pipeline.

What it does:
- Fetch prices with adjusted closes and summed monthly volume
- Fetch fundamentals (Q + A) in SEK, align to months, and build TTM + averages
- Compute characteristics including liquidity, momentum, and risk
- Preprocess for P-Trees: winsorize per month, min-max to [-1,1], then fill NaN to 0

Only dependency besides pandas/numpy is lseg-data; session management is inlined.
"""

import os
import warnings
import numpy as np
import pandas as pd
from contextlib import contextmanager
from dotenv import load_dotenv
import lseg.data as ld

warnings.filterwarnings('ignore')
load_dotenv()


# --- Session management (inlined) -------------------------------------------------

SESSION_TYPE = (os.getenv('LSEG_SESSION_TYPE') or 'desktop').lower()


def _open_session():
    if SESSION_TYPE == 'platform':
        return ld.open_session('platform.rdp')
    return ld.open_session()


@contextmanager
def session_scope():
    with _open_session() as sess:
        yield sess


# --- Data fetch -------------------------------------------------------------------

def fetch_prices(rics, start_date, end_date):
    print('2) Fetching price data...')
    with session_scope():
        price = ld.get_data(
            universe=rics,
            fields=['TR.PriceClose', 'TR.Volume'],
            parameters={'SDate': start_date, 'EDate': end_date, 'Frq': 'M', 'Calc': 'Sum'}
        )

        if price is None or price.empty:
            return pd.DataFrame()

        df = price.copy()
        df.columns = [c.strip().replace(' ', '_').lower() for c in df.columns]
        df = df.rename(columns={'instrument': 'ric', 'price_close': 'close', 'volume': 'volume_msum'})

        # Adjusted closes
        try:
            adj = ld.get_data(
                universe=rics,
                fields=['TR.ClosePrice'],
                parameters={'SDate': start_date, 'EDate': end_date, 'Frq': 'M', 'Adjusted': 'Y'}
            )
            if adj is not None and not adj.empty:
                adj.columns = [c.strip().replace(' ', '_').lower() for c in adj.columns]
                adj = adj.rename(columns={'instrument': 'ric', 'close_price': 'adj_close', 'price_close': 'adj_close'})
                # date column normalization
                dcol = [c for c in adj.columns if 'date' in c]
                if dcol:
                    adj['date'] = adj[dcol[0]]
                adj = adj[['ric', 'date', 'adj_close']].dropna()
                # date in main
                dcol2 = [c for c in df.columns if 'date' in c]
                if dcol2:
                    df['date'] = df[dcol2[0]]
                df = pd.merge(df, adj, on=['ric', 'date'], how='left')
            else:
                df['adj_close'] = df['close']
        except Exception:
            df['adj_close'] = df['close']

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(['ric', 'date'])
        df['ret'] = df.groupby('ric')['adj_close'].pct_change()
        return df[['ric', 'date', 'close', 'adj_close', 'volume_msum', 'ret']]


def fetch_fundamentals(rics, start_date, end_date):
    print('3) Fetching fundamentals (Q + A, SEK)...')
    fields = [
        'TR.TotalAssetsActual', 'TR.ShareholdersEquity', 'TR.CommonSharesOutstanding',
        'TR.NetIncome', 'TR.OperatingIncome', 'TR.Revenue', 'TR.GrossProfit',
        'TR.CashFromOperations', 'TR.CapitalExpenditures', 'TR.DepreciationAmort',
        'TR.TotalDebt', 'TR.LongTermDebt', 'TR.CurrentAssets', 'TR.CurrentLiabilities'
    ]

    def clean_and_map(df):
        df = df.copy()
        df.columns = [c.strip().replace(' ', '_').lower() for c in df.columns]
        df = df.rename(columns={'instrument': 'ric'})
        dcol = [c for c in df.columns if 'date' in c]
        if dcol:
            df['date'] = df[dcol[0]]
        vendor_to_canonical = {
            'tr_totalassetsactual': 'total_assets',
            'tr_shareholdersequity': 'shareholders_equity',
            'tr_commonsharesoutstanding': 'shares_outstanding',
            'tr_netincome': 'net_income',
            'tr_operatingincome': 'operating_income',
            'tr_revenue': 'revenue',
            'tr_grossprofit': 'gross_profit',
            'tr_cashfromoperations': 'cash_from_ops',
            'tr_capitalexpenditures': 'capex',
            'tr_depreciationamort': 'dep_amort',
            'tr_totaldebt': 'total_debt',
            'tr_longtermdebt': 'long_term_debt',
            'tr_currentassets': 'current_assets',
            'tr_currentliabilities': 'current_liabilities',
        }
        for k, v in vendor_to_canonical.items():
            if k in df.columns:
                df = df.rename(columns={k: v})
        keep = ['ric', 'date'] + list(vendor_to_canonical.values())
        keep = [c for c in keep if c in df.columns]
        return df[keep].dropna(subset=['ric', 'date']) if keep else pd.DataFrame()

    all_parts = []
    with session_scope():
        for freq in ['Q', 'A']:
            raw = ld.get_data(
                universe=rics,
                fields=fields,
                parameters={'SDate': start_date, 'EDate': end_date, 'Frq': freq, 'Curn': 'SEK'}
            )
            if raw is not None and not raw.empty:
                df = clean_and_map(raw)
                if not df.empty:
                    df['freq'] = freq
                    all_parts.append(df)

    if not all_parts:
        return pd.DataFrame()

    combined = pd.concat(all_parts, ignore_index=True)
    combined['date'] = pd.to_datetime(combined['date'])
    # Prefer quarterly; fill missing from annual on the same report date
    q = combined[combined['freq'] == 'Q']
    a = combined[combined['freq'] == 'A']
    if q.empty:
        return a.drop(columns=['freq'])
    if a.empty:
        return q.drop(columns=['freq'])
    fill_cols = [c for c in q.columns if c not in ['ric', 'date', 'freq']]
    merged = pd.merge(q, a[['ric', 'date'] + fill_cols], on=['ric', 'date'], how='left', suffixes=('', '_a'))
    for c in fill_cols:
        merged[c] = merged[c].fillna(merged[f'{c}_a'])
        merged = merged.drop(columns=[f'{c}_a'])
    return merged.drop(columns=['freq'])


# --- Alignment and construction ---------------------------------------------------

def forward_fill_fundamentals_monthly(df, month_start: pd.Timestamp, month_end: pd.Timestamp):
    if df.empty:
        return df
    df = df.copy().sort_values(['ric', 'date'])
    month_index = pd.period_range(month_start.to_period('M'), month_end.to_period('M'), freq='M').to_timestamp('M')
    fund_cols = [c for c in df.columns if c not in ['ric', 'date'] and 'date' not in c]
    out = []
    for ric, g in df.groupby('ric'):
        g = g.sort_values('date').set_index('date')
        g = g.reindex(month_index)
        g['ric'] = ric
        for c in fund_cols:
            g[c] = g[c].ffill()
        out.append(g.reset_index().rename(columns={'index': 'date'})[['ric', 'date'] + fund_cols])
    return pd.concat(out, ignore_index=True)


def build_ttm(df):
    if df.empty:
        return df
    out = df.copy().sort_values(['ric', 'date'])
    ttm_map = {
        'net_income': 'ni_ttm',
        'revenue': 'sales_ttm',
        'operating_income': 'oi_ttm',
        'gross_profit': 'gp_ttm',
    }
    for s, t in ttm_map.items():
        if s in out.columns:
            out[t] = out.groupby('ric')[s].rolling(4, min_periods=4).sum().reset_index(0, drop=True)
    return out


def add_monthly_avgs_and_lags(df):
    if df.empty:
        return df
    out = df.copy().sort_values(['ric', 'date'])
    if 'total_assets' in out.columns:
        out['assets_avg'] = out.groupby('ric')['total_assets'].rolling(12, min_periods=12).mean().reset_index(0, drop=True)
    if 'shareholders_equity' in out.columns:
        out['equity_avg'] = out.groupby('ric')['shareholders_equity'].rolling(12, min_periods=12).mean().reset_index(0, drop=True)
        out['be_lag6m'] = out.groupby('ric')['shareholders_equity'].shift(6)
    return out


def compute_characteristics(df):
    if df.empty:
        return df
    out = df.copy()
    # Valuation
    if 'shares_outstanding' in out.columns:
        out['shares_outstanding'] = out.groupby('ric')['shares_outstanding'].ffill()
    if 'shares_outstanding' in out.columns and 'adj_close' in out.columns:
        out['mkt_cap'] = out['shares_outstanding'] * out['adj_close']
        out['size'] = np.log(out['mkt_cap'])
    if 'ni_ttm' in out.columns and 'mkt_cap' in out.columns:
        out['ep'] = out['ni_ttm'] / out['mkt_cap']
    if 'sales_ttm' in out.columns and 'mkt_cap' in out.columns:
        out['sp'] = out['sales_ttm'] / out['mkt_cap']
    if 'be_lag6m' in out.columns and 'mkt_cap' in out.columns:
        out['bm'] = out['be_lag6m'] / out['mkt_cap']
    # Growth and profitability
    if 'sales_ttm' in out.columns:
        out['sgr'] = out.groupby('ric')['sales_ttm'].pct_change()
    if 'oi_ttm' in out.columns and 'total_assets' in out.columns:
        out['op_prof'] = out['oi_ttm'] / out['total_assets']
    if 'ni_ttm' in out.columns and 'sales_ttm' in out.columns:
        out['pm'] = out['ni_ttm'] / out['sales_ttm']
    if 'ni_ttm' in out.columns and 'equity_avg' in out.columns:
        out['roe'] = out['ni_ttm'] / out['equity_avg']
    if 'sales_ttm' in out.columns and 'assets_avg' in out.columns:
        out['ato'] = out['sales_ttm'] / out['assets_avg']
    if 'total_assets' in out.columns:
        out['assets_growth'] = out.groupby('ric')['total_assets'].pct_change()
    if 'total_debt' in out.columns and 'total_assets' in out.columns:
        out['leverage'] = out['total_debt'] / out['total_assets']
    if 'shares_outstanding' in out.columns:
        out['issuance_eq'] = out.groupby('ric')['shares_outstanding'].pct_change(periods=12)
    return out


def compute_liquidity_momentum_risk(df):
    if df.empty:
        return df
    out = df.copy().sort_values(['ric', 'date'])
    if 'volume_msum' in out.columns and 'shares_outstanding' in out.columns:
        out['turnover'] = out['volume_msum'] / out['shares_outstanding']
    if 'volume_msum' in out.columns and 'close' in out.columns:
        out['dolvol'] = out['volume_msum'] * out['close']
    if 'turnover' in out.columns:
        out['std_turn_3m'] = out.groupby('ric')['turnover'].rolling(3, min_periods=3).std().reset_index(0, drop=True)
    if 'dolvol' in out.columns:
        out['std_dolvol_3m'] = out.groupby('ric')['dolvol'].rolling(3, min_periods=3).std().reset_index(0, drop=True)
    if 'ret' in out.columns:
        rs = out.groupby('ric')['ret'].shift(1)
        out['mom_12_1'] = rs.rolling(11, min_periods=11).apply(lambda x: (1 + x).prod() - 1, raw=True)
        out['mom_6'] = rs.rolling(5, min_periods=5).apply(lambda x: (1 + x).prod() - 1, raw=True)
        out['mom_36'] = rs.rolling(35, min_periods=35).apply(lambda x: (1 + x).prod() - 1, raw=True)
        out['rvar_3m'] = out.groupby('ric')['ret'].rolling(3, min_periods=3).var().reset_index(0, drop=True)
    return out


# --- Preprocessing ---------------------------------------------------------------

def preprocess_for_ptrees(df, winsor=(0.01, 0.99)):
    if df.empty:
        return df
    out = df.copy()
    out['year_month'] = out['date'].dt.to_period('M')
    exclude = {'ric', 'date', 'year_month', 'ret', 'close', 'adj_close', 'volume_msum', 'shares_outstanding'}
    char_cols = [c for c in out.columns if c not in exclude and pd.api.types.is_numeric_dtype(out[c])]

    for col in char_cols:
        # convert structural zeros to NaN before winsorizing
        out.loc[out[col] == 0, col] = np.nan
        # winsorize per month
        out[col] = out.groupby('year_month')[col].transform(
            lambda x: x.clip(lower=x.quantile(winsor[0]), upper=x.quantile(winsor[1])) if x.notna().any() else x
        )
        # min-max per month
        def _minmax(x):
            if x.notna().any():
                xmin, xmax = x.min(), x.max()
                return 2 * (x - xmin) / (xmax - xmin) - 1 if xmax != xmin else 0
            return x
        out[col] = out.groupby('year_month')[col].transform(_minmax)
        out[col] = out[col].fillna(0)

    return out.drop(columns=['year_month'])


# --- Orchestrator ----------------------------------------------------------------

def run_pipeline(rics, start_date, end_date):
    print('=' * 60)
    print('FINAL WORKING PIPELINE')
    print('=' * 60)

    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    price_sdate = (start_dt - pd.DateOffset(months=36)).strftime('%Y-%m-%d')
    fund_sdate = (start_dt - pd.DateOffset(months=24)).strftime('%Y-%m-%d')

    prices = fetch_prices(rics, price_sdate, end_date)
    funds = fetch_fundamentals(rics, fund_sdate, end_date)

    # Build TTM on quarterly/annual then align monthly and add averages/lags
    if not funds.empty:
        funds_ttm = build_ttm(funds)
        funds_m = forward_fill_fundamentals_monthly(funds_ttm, pd.to_datetime(price_sdate), end_dt)
        funds_m = add_monthly_avgs_and_lags(funds_m)
    else:
        funds_m = pd.DataFrame()

    # Merge prices + fundamentals
    if not prices.empty and not funds_m.empty:
        merged = pd.merge(prices, funds_m, on=['ric', 'date'], how='outer')
    else:
        merged = prices if not prices.empty else funds_m

    # Compute characteristics
    merged = compute_characteristics(merged)
    merged = compute_liquidity_momentum_risk(merged)

    # Trim to requested window; then preprocess
    merged = merged[(merged['date'] >= start_dt) & (merged['date'] <= end_dt)]
    final = preprocess_for_ptrees(merged)

    print('Done. Rows:', len(final), 'Cols:', len(final.columns))
    return final


if __name__ == '__main__':
    # Example run for 2015 on ERICb.ST
    out = run_pipeline(['ERICb.ST'], start_date='2015-01-01', end_date='2015-12-31')
    if not out.empty:
        out.to_csv('final_pipeline_output.csv', index=False)
        print('Saved: final_pipeline_output.csv')

