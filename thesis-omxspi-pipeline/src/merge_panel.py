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

    panel = uni.merge(prices, on=["ric", "date"], how="left")

    if fundamentals is not None and not fundamentals.empty:
        fund = fundamentals.copy()
        fund["date"] = pd.to_datetime(fund["date"]).dt.normalize()
        # forward-fill fundamentals to month-end per ric
        fund = fund.sort_values(["ric", "date"]).groupby("ric").apply(lambda g: g.ffill()).reset_index(drop=True)
        panel = panel.merge(fund, on=["ric", "date"], how="left")

    # Simple extra: market cap if we have shares outstanding and close
    if "commonsharesoutstanding" in panel.columns:
        price_col = "adj_close" if "adj_close" in panel.columns else "close"
        if price_col in panel.columns:
            panel["mkt_cap"] = panel["commonsharesoutstanding"] * panel[price_col]
    return panel
