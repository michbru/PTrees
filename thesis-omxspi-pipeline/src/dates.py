from __future__ import annotations
import pandas as pd
from pandas.tseries.offsets import MonthEnd


def month_ends(start: str, end: str) -> pd.DatetimeIndex:
    """Inclusive list of month-end dates [start, end]."""
    idx = pd.date_range(start, end, freq="ME").to_period("M").to_timestamp("M")
    return idx


def to_yyyymmdd(dt) -> str:
    return pd.Timestamp(dt).strftime("%Y%m%d")
