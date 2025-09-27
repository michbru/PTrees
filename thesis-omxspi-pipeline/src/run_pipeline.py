from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import warnings

# Suppress FutureWarning about downcasting in pandas operations
pd.set_option('future.no_silent_downcasting', False)
warnings.filterwarnings('ignore', message='.*Downcasting object dtype arrays.*', category=FutureWarning)
from .universe import build_universe
from .prices import pull_prices, pull_daily_aux
from .corporate_actions import pull_corporate_actions
from .fundamentals import pull_fundamentals
from .merge_panel import merge_all
from .industries import pull_industry_codes, attach_industry
from .characteristics import finalize_characteristics
from .characteristics_liquidity import add_liquidity_characteristics
from .characteristics_vol import add_volatility_characteristics
from .ptree_prep import prepare_tree_input, load_risk_factors


def main():
    p = argparse.ArgumentParser(description="Build OMXSPI survivorship-free panel with P-Trees characteristics")
    p.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    p.add_argument("--freq", default="M", choices=["M", "D"], help="Price frequency: M(monthly) or D(daily)")
    p.add_argument("--universe", default="omxspi", choices=["omxspi"], help="Universe backbone")

    # Data pulling options
    p.add_argument("--pull-ca", action="store_true", help="Pull corporate actions")
    p.add_argument("--pull-fund", action="store_true", help="Pull fundamentals (quarterly & annual)")
    p.add_argument("--daily-aux", action="store_true", help="Pull daily prices for enhanced characteristics")
    p.add_argument("--industries", action="store_true", help="Pull industry codes (TRBC/ICB)")

    # Characteristics options (new simplified flags)
    p.add_argument("--chars", action="store_true", help="Compute characteristics & tree_input (includes --characteristics --tree-prep)")
    p.add_argument("--with-factors", action="store_true", help="Load factors for excess returns (default: data/external/FF4F_monthly.csv)")
    p.add_argument("--factors-path", default="data/external/FF4F_monthly.csv", help="Path to factors CSV file")
    p.add_argument("--industry-adjust", action="store_true", help="Compute industry-adjusted variants")

    # Legacy detailed options (for compatibility)
    p.add_argument("--characteristics", action="store_true", help="Compute comprehensive characteristics")
    p.add_argument("--liquidity", action="store_true", help="Include enhanced liquidity characteristics")
    p.add_argument("--volatility", action="store_true", help="Include enhanced volatility characteristics")

    # P-Trees preprocessing
    p.add_argument("--tree-prep", action="store_true", help="Apply P-Trees preprocessing (winsorize, standardize)")
    p.add_argument("--winsorize", default="0.01,0.99", help="Winsorization percentiles (default: 0.01,0.99)")
    p.add_argument("--standardize", default="minmax", choices=["minmax", "zscore"], help="Standardization method")

    # Output options
    p.add_argument("--outdir", default="data", help="Output directory")
    p.add_argument("--skip-raw", action="store_true", help="Skip saving raw data files")

    args = p.parse_args()

    # Handle convenience flags
    if args.chars:
        # --chars enables characteristics and tree-prep automatically
        args.characteristics = True
        args.tree_prep = True
        args.pull_fund = True  # Need fundamentals for characteristics
        # Enable liquidity/volatility by default if daily-aux is also specified
        if args.daily_aux:
            args.liquidity = True
            args.volatility = True

    outdir = Path(args.outdir)
    (outdir / "raw").mkdir(parents=True, exist_ok=True)
    (outdir / "processed").mkdir(parents=True, exist_ok=True)

    # Parse winsorization percentiles
    winsorize_pcts = [float(x) for x in args.winsorize.split(",")]
    if len(winsorize_pcts) != 2:
        raise ValueError("--winsorize must be two comma-separated values (e.g., '0.01,0.99')")

    print("=" * 60)
    print("OMXSPI SURVIVORSHIP-FREE PANEL WITH P-TREES CHARACTERISTICS")
    print("=" * 60)

    # Step 1: Build universe
    print("\n1) Building historical universe…")
    uni = build_universe(args.start, args.end)
    if not args.skip_raw:
        uni.to_parquet(outdir / "raw" / "universe_omxspi.parquet")
    print(f"   Universe: {len(uni)} observations, {uni['ric'].nunique()} unique RICs")

    # Step 2: Pull prices
    print("\n2) Pulling prices…")
    prices = pull_prices(uni, args.start, args.end, freq=args.freq, adjusted=True)
    if not args.skip_raw:
        prices.to_parquet(outdir / "raw" / f"prices_{args.freq.lower()}.parquet")
    print(f"   Prices: {len(prices)} observations")

    # Step 3: Pull daily auxiliary data if requested
    daily_aux = pd.DataFrame()
    if args.daily_aux:
        print("\n3) Pulling daily auxiliary data…")
        daily_aux = pull_daily_aux(uni, args.start, args.end)
        if not args.skip_raw and not daily_aux.empty:
            daily_aux.to_parquet(outdir / "raw" / "daily_aux.parquet")
        print(f"   Daily aux: {len(daily_aux)} observations")

    # Step 4: Pull corporate actions
    ca = pd.DataFrame()
    if args.pull_ca:
        print(f"\n4) Pulling corporate actions…")
        rics = sorted(uni["ric"].unique())
        ca = pull_corporate_actions(rics, args.start, args.end)
        if not args.skip_raw:
            ca.to_parquet(outdir / "raw" / "corporate_actions.parquet")
        print(f"   Corporate actions: {len(ca)} records")

    # Step 5: Pull fundamentals
    fund = pd.DataFrame()
    if args.pull_fund:
        print(f"\n5) Pulling fundamentals…")
        fund = pull_fundamentals(uni, args.start, args.end, curn="SEK")
        if not args.skip_raw:
            fund.to_parquet(outdir / "raw" / "fundamentals.parquet")
        print(f"   Fundamentals: {len(fund)} records")

    # Step 6: Pull industry codes
    industry_codes = pd.DataFrame()
    if args.industries or args.industry_adjust:
        print(f"\n6) Pulling industry codes…")
        industry_codes = pull_industry_codes(uni)
        if not args.skip_raw and not industry_codes.empty:
            industry_codes.to_parquet(outdir / "raw" / "industry_codes.parquet")
        print(f"   Industry codes: {len(industry_codes)} RICs classified")

    # Step 7: Load risk factors if requested
    factors = None
    if args.with_factors:
        print(f"\n7) Loading risk factors…")
        factors_path = Path(args.factors_path)
        factors = load_risk_factors(factors_path)
        if factors is not None and not args.skip_raw:
            # Save under SHoF-style name as requested
            factors.to_parquet(outdir / "processed" / "shof_factors.parquet", index=False)
            print(f"   Risk factors: {len(factors)} monthly observations")

    # Step 8: Merge panel
    print(f"\n8) Merging panel…")
    panel = merge_all(uni, prices, fund if args.pull_fund else None)

    # Attach industry codes if available
    if not industry_codes.empty:
        panel = attach_industry(panel, industry_codes)

    basic_panel_path = outdir / "processed" / f"panel_{args.freq.lower()}.parquet"
    panel.to_parquet(basic_panel_path)
    print(f"   Basic panel: {len(panel)} observations saved to {basic_panel_path}")

    # Step 9: Compute characteristics if requested
    if args.characteristics:
        print(f"\n9) Computing characteristics…")

        # Add enhanced liquidity characteristics
        if args.liquidity and not daily_aux.empty:
            panel = add_liquidity_characteristics(panel, daily_aux)

        # Add enhanced volatility characteristics
        if args.volatility:
            panel = add_volatility_characteristics(panel, daily_aux if not daily_aux.empty else None)

        # Compute comprehensive characteristics (including industry-adjusted if requested)
        panel_with_chars = finalize_characteristics(
            panel,
            daily_aux if not daily_aux.empty else None,
            include_industry_adjusted=args.industry_adjust
        )

        chars_path = outdir / "processed" / f"characteristics_{args.freq.lower()}.parquet"
        panel_with_chars.to_parquet(chars_path)
        print(f"   Characteristics: {len(panel_with_chars)} observations, {len(panel_with_chars.columns)-4} features")

        # Step 10: P-Trees preprocessing if requested
        if args.tree_prep:
            print(f"\n10) Applying P-Trees preprocessing…")
            tree_ready = prepare_tree_input(
                panel_with_chars,
                output_path=outdir / "processed",
                factors=factors,
                winsorize_pcts=tuple(winsorize_pcts),
                standardization=args.standardize,
                fill_missing=0.0
            )
            print(f"   Tree-ready data: {len(tree_ready)} observations exported")
        else:
            # Just save basic CSV for compatibility
            panel_with_chars.to_csv(outdir / "processed" / f"characteristics_{args.freq.lower()}.csv", index=False)

    else:
        # Save basic panel CSV (optional, skip if permission denied)
        try:
            panel.to_csv(outdir / "processed" / f"panel_{args.freq.lower()}.csv", index=False)
        except PermissionError:
            print(f"   Warning: Could not write CSV (file may be open in Excel)")

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(f"Output directory: {outdir.resolve()}")

    # Show key output files
    print(f"\nKey outputs:")
    panel_file = outdir / "processed" / f"panel_{args.freq.lower()}.parquet"
    if panel_file.exists():
        print(f"  📊 Panel: {panel_file}")

    if args.characteristics:
        chars_file = outdir / "processed" / f"characteristics_{args.freq.lower()}.parquet"
        if chars_file.exists():
            print(f"  🧮 Characteristics: {chars_file}")

    if args.tree_prep:
        tree_file = outdir / "processed" / "tree_input.parquet"
        if tree_file.exists():
            print(f"  🌳 Tree input: {tree_file}")
            print(f"  🌳 Tree input CSV: {outdir / 'processed' / 'tree_input.csv'}")

    print("=" * 60)


if __name__ == "__main__":
    main()
