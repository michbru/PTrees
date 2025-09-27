from __future__ import annotations
import pandas as pd


def merge_all(universe: pd.DataFrame, prices: pd.DataFrame, fundamentals: pd.DataFrame | None) -> pd.DataFrame:
    """Merge monthly membership with prices and fundamentals.
    - Universe: [date, ric]
    - Prices: [ric, date, close, volume, adj_close?, ret?]
    - Fundamentals: [ric, date, columns...], quarterly/annual; we FFILL to month-end
    """
    uni = universe.copy()
    uni["date"] = pd.to_datetime(uni["date"]).dt.normalize()

    # Handle empty prices dataframe
    if prices.empty or "ric" not in prices.columns:
        print("Warning: prices dataframe is empty or missing 'ric' column")
        # Create empty prices structure that matches expected columns
        prices = pd.DataFrame(columns=["ric", "date", "close", "volume"])

    # Ensure date column exists and is normalized
    if "date" in prices.columns:
        prices = prices.copy()
        prices["date"] = pd.to_datetime(prices["date"]).dt.normalize()

    panel = uni.merge(prices, on=["ric", "date"], how="left")

    if fundamentals is not None and not fundamentals.empty:
        fund = fundamentals.copy()

        # Debug: print fundamentals structure
        print(f"   Fundamentals columns: {list(fund.columns)}")
        print(f"   Fundamentals shape: {fund.shape}")

        # Check if date column exists before processing
        if "date" in fund.columns:
            fund["date"] = pd.to_datetime(fund["date"]).dt.normalize()
            # forward-fill fundamentals to month-end per ric
            fund = fund.sort_values(["ric", "date"]).groupby("ric", group_keys=False).apply(lambda g: g.ffill().infer_objects(copy=False)).reset_index(drop=True)
            panel = panel.merge(fund, on=["ric", "date"], how="left")
            print(f"   Merged fundamentals successfully")
        else:
            print(f"   Warning: fundamentals dataframe missing 'date' column")
            print(f"   Available columns: {list(fund.columns)}")
            print("   Skipping fundamentals merge")

    # Simple extra: market cap if we have shares outstanding and close
    if "commonsharesoutstanding" in panel.columns:
        price_col = "adj_close" if "adj_close" in panel.columns else "close"
        if price_col in panel.columns:
            panel["mkt_cap"] = panel["commonsharesoutstanding"] * panel[price_col]
    return panel
