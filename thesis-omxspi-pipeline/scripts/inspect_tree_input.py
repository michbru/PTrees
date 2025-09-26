from __future__ import annotations
import sys
from pathlib import Path
import random
import pandas as pd


def identify_characteristics(df: pd.DataFrame) -> list[str]:
    non_char_cols = {
        'ric', 'date', 'ret', 'excess_ret', 'mkt_cap', 'close', 'adj_close', 'volume',
        # Raw fundamentals/descriptors
        'totalassets', 'shareholdersequity', 'netincome', 'operatingincome', 'revenue',
        'commonsharesoutstanding', 'epsnormalized', 'epsreported', 'cashfromoperations',
        'grossprofit', 'grossmargin', 'operatingmargin', 'totaldebt', 'longtermdebt',
        'debttoassets', 'currentassets', 'currentliabilities', 'freq',
        # Industry codes
        'trbc_sector', 'trbc_industry', 'icb_industry', 'icb_supersector'
    }
    error_cols = {c for c in df.columns if 'error' in c.lower()}
    non_char_cols.update(error_cols)
    return [c for c in df.columns if c not in non_char_cols and pd.api.types.is_numeric_dtype(df[c])]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('data/processed/tree_input.parquet')
    if not path.exists():
        print(f"Error: file not found: {path}")
        sys.exit(2)

    df = pd.read_parquet(path)
    df['date'] = pd.to_datetime(df['date'])

    print("=== TREE INPUT INSPECTOR ===")
    print(f"File: {path}")
    print(f"Rows: {len(df):,}; Columns: {len(df.columns)}")
    print(f"Period: {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"Unique RICs: {df['ric'].nunique():,}")

    # Cross-section sizes per month
    cs = df.groupby('date')['ric'].nunique()
    print(f"Cross-section counts per month: min={cs.min()}, median={int(cs.median())}, max={cs.max()}")

    chars = identify_characteristics(df)
    print(f"Characteristics found: {len(chars)}")

    # NA check and range check
    fail = False
    for c in chars:
        na_pct = df[c].isna().mean() * 100
        if na_pct > 0.1:
            print(f"  [FAIL] {c}: NA% {na_pct:.3f} > 0.1%")
            fail = True

    # Pick 3 random months for min/max checks (or up to 3 if fewer)
    months = sorted(df['date'].unique())
    sample_months = random.sample(list(months), k=min(3, len(months))) if months else []
    tol = 1.05
    for m in sample_months:
        sub = df[df['date'] == m]
        for c in chars:
            if sub[c].notna().any():
                mn, mx = sub[c].min(), sub[c].max()
                if mn < -tol or mx > tol:
                    print(f"  [FAIL] {c} at {pd.to_datetime(m).date()}: min={mn:.3f}, max={mx:.3f} outside [-{tol},{tol}]")
                    fail = True

    if not fail:
        print("All checks passed: no excessive NA and ranges within tolerance [-1.05, 1.05].")

    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()

