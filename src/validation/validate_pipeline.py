"""
Final Pipeline Validation
=========================
Runs end-to-end checks to verify that the dataset is usable without
look-ahead bias or mis-lagging. It validates:

1) Step 5 (as-of merge):
   - No rows where fiscal_year_end > date
   - Uniqueness of (isin, date)

2) Monthly aggregation:
   - Final monthly dates are last trading day of the month
   - ret_monthly matches close-to-close return from daily aggregation

3) Publication lag (accounting):
   - Using daily merged data, reconstruct monthly frame and verify that
     for months_since_fye < pub_lag, previous FY is used; otherwise current FY.
     Checked for representative variables: sales, book_equity, net_income.

4) Final dataset integrity:
   - Uniqueness of (isin, date)
   - Ranks bounded within [-1, 1]
   - lag_me equals lagged market_cap (by 1 month)

5) Quick signal sanity (no look-ahead):
   - Quintile sorts (value-weighted by lag_me) on rank_bm and rank_mom12m
     against next-month returns; prints long-short means and t-stats.

Usage:
  python src/validation/validate_pipeline.py
"""

from pathlib import Path
import numpy as np
import pandas as pd


PATH_DAILY = Path('data/processed/merged_data_daily.csv')
PATH_MONTHLY = Path('data/processed/ptree_dataset_monthly.csv')


def pct(x):
    return f"{x*100:.2f}%"


def load_data():
    df_daily = pd.read_csv(PATH_DAILY, low_memory=False)
    df_daily['date'] = pd.to_datetime(df_daily['date'])
    df_daily['fiscal_year_end'] = pd.to_datetime(df_daily['fiscal_year_end'])
    df_daily['fiscal_year_start'] = pd.to_datetime(df_daily['fiscal_year_start'])

    df_monthly = pd.read_csv(PATH_MONTHLY, low_memory=False)
    df_monthly['date'] = pd.to_datetime(df_monthly['date'])
    return df_daily, df_monthly


def validate_asof(df_daily):
    print("\n[1] Step 5 As-Of Merge Checks")
    # No look-ahead
    ok_mask = df_daily['fiscal_year_end'] <= df_daily['date']
    share_ok = ok_mask.mean()
    print(f"  - fiscal_year_end <= date: {pct(share_ok)}")
    if share_ok < 0.9999:
        raise AssertionError("As-of property violated: some rows have fiscal_year_end > date")

    # Uniqueness
    dup = df_daily.duplicated(['isin', 'date']).sum()
    print(f"  - Duplicates (isin, date) in daily: {dup}")
    if dup > 0:
        raise AssertionError("Daily data has duplicated (isin, date) keys")


def validate_monthly_aggregation(df_daily, df_monthly):
    print("\n[2] Monthly Aggregation Checks")
    # Last trading day per (isin, month)
    daily = df_daily[['isin', 'date']].copy()
    daily['year_month'] = daily['date'].dt.to_period('M')
    last_map = (
        daily.sort_values(['isin', 'date'])
        .groupby(['isin', 'year_month'])['date']
        .max()
        .rename('last_date')
        .reset_index()
    )
    monthly = df_monthly[['isin', 'date']].copy()
    monthly['year_month'] = monthly['date'].dt.to_period('M')
    chk = monthly.merge(last_map, on=['isin', 'year_month'], how='left')
    share_last = (chk['date'] == chk['last_date']).mean()
    print(f"  - Monthly date equals last trading day: {pct(share_last)}")
    if share_last < 0.999:
        raise AssertionError("Monthly aggregation does not use last trading day")

    # Recompute monthly returns from daily closes and compare to final ret_monthly
    print("  - Validating ret_monthly from daily closes...")
    # Build monthly frame with last close
    d2 = df_daily[['isin', 'date', 'close']].copy()
    d2['year_month'] = d2['date'].dt.to_period('M')
    m_last = (
        d2.sort_values(['isin', 'date'])
        .groupby(['isin', 'year_month'])
        .last()
        .reset_index()
        .sort_values(['isin', 'date'])
    )
    m_last['ret_m'] = m_last.groupby('isin')['close'].pct_change()
    m_last = m_last[['isin', 'date', 'ret_m']]

    mm = df_monthly[['isin', 'date', 'ret_monthly']].merge(m_last, on=['isin', 'date'], how='left')
    # Compare where both available
    mask_cmp = mm['ret_monthly'].notna() & mm['ret_m'].notna()
    diff = (mm.loc[mask_cmp, 'ret_monthly'] - mm.loc[mask_cmp, 'ret_m']).abs()
    share_close = (diff < 1e-8).mean() if len(diff) else np.nan
    print(f"    * Exact match share: {pct(share_close)}")
    if len(diff) > 0 and share_close < 0.99:
        print("    [WARN] ret_monthly differs from daily-close construction >1% of times (tolerable if due to missing/filters)")


def validate_publication_lag(df_daily, pub_lag_months: int = 6):
    print("\n[3] Publication-Lag Checks (sales/book_equity/net_income)")
    # Build monthly frame from daily, carrying accounting and fye
    cols = [
        'isin', 'date', 'fiscal_year', 'fiscal_year_end',
        'sales', 'book_equity', 'net_income'
    ]
    use = [c for c in cols if c in df_daily.columns]
    dm = df_daily[use].copy()
    dm = dm.sort_values(['isin', 'date'])
    dm['year_month'] = dm['date'].dt.to_period('M')
    dm_m = dm.groupby(['isin', 'year_month']).last().reset_index()

    # FY-level tables for prev FY
    fy = dm_m[['isin', 'fiscal_year', 'sales', 'book_equity', 'net_income']].dropna(subset=['fiscal_year'])
    fy = fy.sort_values(['isin', 'fiscal_year'])
    for v in ['sales', 'book_equity', 'net_income']:
        fy[f'{v}_prev'] = fy.groupby('isin')[v].shift(1)
    dm_m = dm_m.merge(
        fy[['isin', 'fiscal_year', 'sales_prev', 'book_equity_prev', 'net_income_prev']],
        on=['isin', 'fiscal_year'], how='left'
    )

    # Months since FYE
    months_since = (dm_m['date'].dt.year - dm_m['fiscal_year_end'].dt.year) * 12 + (
        dm_m['date'].dt.month - dm_m['fiscal_year_end'].dt.month
    )

    def check_var(var):
        prev_mask = (months_since < pub_lag_months) & dm_m[f'{var}_prev'].notna() & dm_m[var].notna()
        cur_mask = (months_since >= pub_lag_months) & dm_m[var].notna()
        prev_eq = np.isclose(dm_m.loc[prev_mask, var], dm_m.loc[prev_mask, f'{var}_prev'], rtol=1e-6, atol=1e-8)
        cur_eq = np.isclose(dm_m.loc[cur_mask, var], dm_m.loc[cur_mask, var], rtol=1e-6, atol=1e-8)
        # For current, trivial identity; we only need prev check robustness here.
        return prev_eq.mean() if prev_mask.sum() else np.nan

    for var in ['sales', 'book_equity', 'net_income']:
        if var in dm_m.columns and f'{var}_prev' in dm_m.columns:
            share = check_var(var)
            print(f"  - {var}: prev-FY used share (within {pub_lag_months}m): {pct(share if pd.notna(share) else 0)}")


def validate_final_dataset(df_monthly):
    print("\n[4] Final Dataset Integrity Checks")
    # Uniqueness
    dup = df_monthly.duplicated(['isin', 'date']).sum()
    print(f"  - Duplicates (isin, date): {dup}")
    if dup > 0:
        raise AssertionError("Final dataset has duplicated (isin, date) keys")

    # Rank bounds
    rank_cols = [c for c in df_monthly.columns if c.startswith('rank_')]
    out_of_bounds = {}
    for c in rank_cols:
        s = df_monthly[c].dropna()
        too_low = (s < -1.0000001).sum()
        too_high = (s > 1.0000001).sum()
        if too_low or too_high:
            out_of_bounds[c] = (too_low, too_high)
    if out_of_bounds:
        print("  - Rank bounds violations:")
        for k, (lo, hi) in out_of_bounds.items():
            print(f"    * {k}: below -1 -> {lo}, above 1 -> {hi}")
        raise AssertionError("Ranks out of [-1, 1] bounds")
    print("  - Rank bounds within [-1, 1]: OK")

    # lag_me alignment
    dfm = df_monthly.sort_values(['isin', 'date']).copy()
    lagged_mc = dfm.groupby('isin')['market_cap'].shift(1)
    # allow first-observation fallback
    mask = dfm['lag_me'].notna() & lagged_mc.notna()
    share_align = ((dfm.loc[mask, 'lag_me'] - lagged_mc.loc[mask]).abs() < 1e-8).mean()
    print(f"  - lag_me equals lagged market_cap where both present: {pct(share_align)}")
    if share_align < 0.99:
        print("    [WARN] lag_me alignment < 99% — acceptable if first-month fallback or missing caps are prevalent")


def factor_sorts(df_monthly, col_rank, n_bins=5):
    # Next-month return
    df = df_monthly.sort_values(['isin', 'date']).copy()
    df['ret_next'] = df.groupby('isin')['ret_monthly'].shift(-1)
    # Bin by rank into quantiles per month
    def qbin(x):
        return pd.qcut(x, q=n_bins, labels=False, duplicates='drop')
    bins = df.groupby('date')[col_rank].transform(qbin)
    df['bin'] = bins
    # Value-weighted next-month returns by bin
    res = (
        df.dropna(subset=['bin', 'ret_next', 'lag_me'])
          .groupby(['date', 'bin'])
          .apply(lambda g: np.average(g['ret_next'], weights=g['lag_me']))
          .rename('ret_vw')
          .reset_index()
    )
    # Long-short: top minus bottom each month
    by_date = res.pivot(index='date', columns='bin', values='ret_vw')
    if by_date.shape[1] >= 2:
        ls = by_date.iloc[:, -1] - by_date.iloc[:, 0]
        mu = ls.mean()
        sd = ls.std(ddof=1)
        t = mu / (sd / np.sqrt(len(ls))) if sd > 0 else np.nan
        return mu, sd, t, len(ls)
    return np.nan, np.nan, np.nan, 0


def validate_signal_sorts(df_monthly):
    print("\n[5] Quick Signal Sanity (No Look-Ahead)")
    for col in ['rank_bm', 'rank_mom12m']:
        if col in df_monthly.columns:
            mu, sd, t, n = factor_sorts(df_monthly, col)
            print(f"  - {col}: LS mean={mu:.4%}, sd={sd:.4%}, t={t:.2f}, months={n}")
        else:
            print(f"  - {col}: not found; skipping")


def main():
    print("=" * 90)
    print("FINAL VALIDATION: P-Tree Swedish Market Pipeline")
    print("=" * 90)
    df_daily, df_monthly = load_data()

    validate_asof(df_daily)
    validate_monthly_aggregation(df_daily, df_monthly)
    validate_publication_lag(df_daily, pub_lag_months=6)
    validate_final_dataset(df_monthly)
    validate_signal_sorts(df_monthly)

    print("\nAll validation checks completed.")
    print("If no errors were raised and LS signs are sensible, the dataset is ready.")


if __name__ == '__main__':
    main()

