from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from .universe import build_universe
from .prices import pull_prices
from .corporate_actions import pull_corporate_actions
from .fundamentals import pull_fundamentals
from .merge_panel import merge_all


def main():
    p = argparse.ArgumentParser(description="Build OMXSPI survivorship-free panel (LSEG)")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--freq", default="M", choices=["M", "D"], help="Price frequency: M(monthly) or D(daily)")
    p.add_argument("--universe", default="omxspi", choices=["omxspi"], help="Universe backbone")
    p.add_argument("--pull-ca", action="store_true", help="Pull corporate actions")
    p.add_argument("--pull-fund", action="store_true", help="Pull fundamentals (quarterly & annual)")
    p.add_argument("--outdir", default="data")
    args = p.parse_args()

    outdir = Path(args.outdir)
    (outdir / "raw").mkdir(parents=True, exist_ok=True)
    (outdir / "processed").mkdir(parents=True, exist_ok=True)

    print("1) Building historical universe…")
    uni = build_universe(args.start, args.end)
    uni.to_parquet(outdir / "raw" / "universe_omxspi.parquet")

    print("2) Pulling prices…")
    prices = pull_prices(uni, args.start, args.end, freq=args.freq, adjusted=True)
    prices.to_parquet(outdir / "raw" / f"prices_{args.freq.lower()}.parquet")

    ca = pd.DataFrame()
    if args.pull_ca:
        print("3) Pulling corporate actions…")
        rics = sorted(uni["ric"].unique())
        ca = pull_corporate_actions(rics, args.start, args.end)
        ca.to_parquet(outdir / "raw" / "corporate_actions.parquet")

    fund = pd.DataFrame()
    if args.pull_fund:
        print("4) Pulling fundamentals…")
        fund = pull_fundamentals(uni, args.start, args.end, curn="SEK")
        fund.to_parquet(outdir / "raw" / "fundamentals.parquet")

    print("5) Merging panel…")
    panel = merge_all(uni, prices, fund if args.pull_fund else None)
    panel.to_parquet(outdir / "processed" / f"panel_{args.freq.lower()}.parquet")
    # Optional CSV for Excel users
    panel.to_csv(outdir / "processed" / f"panel_{args.freq.lower()}.csv", index=False)

    print("Done. Files in:", outdir.resolve())


if __name__ == "__main__":
    main()
