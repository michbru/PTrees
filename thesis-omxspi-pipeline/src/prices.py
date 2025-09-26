from __future__ import annotations
import pandas as pd
from tqdm import tqdm
import lseg.data as ld
from .lseg_session import session_scope
from .utils import chunks, backoff_retry


@backoff_retry
def _history_batch(rics, start, end, interval, fields):
    return ld.get_history(
        universe=rics,
        start=start,
        end=end,
        interval=interval,
        fields=fields,
    )


def pull_prices(universe: pd.DataFrame, start: str, end: str, freq: str = "M", adjusted: bool = True) -> pd.DataFrame:
    """Pull OHLC/Close + Volume. If adjusted=True, also fetch adjusted close via TR.ClosePrice(Adjusted=Y).
    Returns long dataframe: columns [ric, date, close, volume, ...].
    """
    # Use monthly or daily history for close & volume.
    interval = "monthly" if freq.upper().startswith("M") else "daily"

    rics = sorted(universe["ric"].unique())

    frames = []
    with session_scope():
        for batch in tqdm(list(chunks(rics, 100)), desc=f"Price history {interval}"):
            try:
                # get_history supports standard price fields
                hist = _history_batch(batch, start, end, interval, fields=["CLOSE", "VOLUME"])
                hist = hist.rename(columns={"CLOSE": "close", "VOLUME": "volume"})
                frames.append(hist)
            except Exception as e:
                frames.append(pd.DataFrame({"Instrument": batch, "error": str(e)}))

        adj = pd.DataFrame()
        if adjusted:
            adj_frames = []
            frq = "M" if interval == "monthly" else "D"
            for batch in tqdm(list(chunks(rics, 50)), desc="Adjusted close"):
                try:
                    df = ld.get_data(
                        batch,
                        [
                            f"TR.ClosePrice(SDate={start},EDate={end},Frq={frq},Adjusted=Y).date",
                            f"TR.ClosePrice(SDate={start},EDate={end},Frq={frq},Adjusted=Y)",
                        ],
                    )
                    if not df.empty:
                        inst_col = "Instrument"
                        # Handle common return shape where timeseries is already in long form
                        if "TR.ClosePrice(SDate=" in "".join(df.columns):
                            date_cols = [c for c in df.columns if c.endswith(".date")]
                            val_cols = [c for c in df.columns if c.startswith("TR.ClosePrice(") and not c.endswith(".date")]
                            if date_cols and val_cols:
                                tmp = df[[inst_col, date_cols[0], val_cols[0]]].copy()
                                tmp.columns = ["Instrument", "Date", "adj_close"]
                                adj_frames.append(tmp.dropna())
                        # Fallback: if generic names
                        elif {inst_col, "Date", "TR.ClosePrice"}.issubset(df.columns):
                            tmp = df[[inst_col, "Date", "TR.ClosePrice"]].copy()
                            tmp.columns = ["Instrument", "Date", "adj_close"]
                            adj_frames.append(tmp.dropna())
                except Exception as e:
                    adj_frames.append(pd.DataFrame({"Instrument": batch, "error": str(e)}))
            adj = pd.concat(adj_frames, ignore_index=True) if adj_frames else pd.DataFrame()

    prices = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not prices.empty:
        prices = prices.rename(columns={"Instrument": "ric", "Date": "date"})

    if adjusted and not adj.empty:
        adj = adj.rename(columns={"Instrument": "ric", "Date": "date"})
        prices = prices.merge(adj, on=["ric", "date"], how="left")
        # Compute returns from adjusted close
        prices = prices.sort_values(["ric", "date"])\
                       .assign(ret=lambda d: d.groupby("ric")["adj_close"].pct_change())

    return prices
