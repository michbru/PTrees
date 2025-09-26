from __future__ import annotations
import pandas as pd
from tqdm import tqdm
from .lseg_session import session_scope
import lseg.data as ld
from .dates import month_ends, to_yyyymmdd

INDEX_RIC = ".OMXSPI"  # OMX Stockholm All-Share


def _fetch_constituents_asof(date: pd.Timestamp) -> pd.DataFrame:
    """Return RIC list for .OMXSPI *as of* the given date (historical snapshot).
    Uses chain syntax 0#.INDEXRIC(YYYYMMDD).
    """
    chain = f"0#{INDEX_RIC}({to_yyyymmdd(date)})"
    df = ld.get_data(chain, ["TR.RIC"])  # can add TR.CommonName if desired
    # Normalize
    out = pd.DataFrame({
        "date": [date] * len(df),
        "ric": df["TR.RIC"].tolist()
    })
    return out


def build_universe(start: str, end: str) -> pd.DataFrame:
    """Historical universe by month-end. Columns: date, ric.
    """
    dates = month_ends(start, end)
    frames = []
    with session_scope():
        for d in tqdm(dates, desc="OMXSPI constituents by month-end"):
            try:
                frames.append(_fetch_constituents_asof(d))
            except Exception as e:
                frames.append(pd.DataFrame({"date": [d], "ric": [None], "error": [str(e)]}))
    uni = pd.concat(frames, ignore_index=True)
    uni = uni.dropna(subset=["ric"]).drop_duplicates()
    return uni
