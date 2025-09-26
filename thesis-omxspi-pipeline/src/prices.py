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
                # Use correct LSEG field names
                hist = _history_batch(batch, start, end, interval, fields=["TR.PriceClose", "TR.Volume"])
                hist = hist.rename(columns={"Price Close": "close", "Volume": "volume"})
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
        # Handle MultiIndex columns (RIC, field) format
        if isinstance(prices.columns, pd.MultiIndex):
            # The MultiIndex is (RIC, field) - need to stack properly
            # First preserve the original index (dates) before stacking
            original_index = prices.index
            prices = prices.stack(level=0, future_stack=True)  # Stack RIC level
            prices = prices.reset_index()
            # Now we have: [original_date_index, RIC, close, volume]
            prices.columns = ['date', 'ric', 'close', 'volume']
            # The date column is currently the row index numbers, we need actual dates
            # The dates should be in the original index
            if len(original_index) > 0:
                # Map the integer index back to actual dates
                date_mapping = {i: date for i, date in enumerate(original_index)}
                prices['date'] = prices['date'].map(date_mapping)
        else:
            # Standard format
            prices = prices.rename(columns={"Instrument": "ric", "Date": "date"})

    if adjusted and not adj.empty:
        adj = adj.rename(columns={"Instrument": "ric", "Date": "date"})
        # Ensure both dataframes have the required columns for merge
        if "date" not in adj.columns or "ric" not in adj.columns:
            # Skip adjusted close merge if data structure is wrong
            adj = pd.DataFrame()
        else:
            prices = prices.merge(adj, on=["ric", "date"], how="left")
            # Compute returns from adjusted close
            prices = prices.sort_values(["ric", "date"])\
                           .assign(ret=lambda d: d.groupby("ric")["adj_close"].pct_change())

    return prices


def pull_daily_aux(universe: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Pull daily CLOSE, VOLUME, and optional BID/ASK for volatility & Amihud calculations.
    Returns: [ric, date, close, volume, bid?, ask?]
    """
    rics = sorted(universe["ric"].unique())

    frames = []
    with session_scope():
        # Pull basic daily data
        for batch in tqdm(list(chunks(rics, 100)), desc="Daily aux prices"):
            try:
                hist = _history_batch(batch, start, end, "daily", fields=["TR.PriceClose", "TR.Volume"])
                hist = hist.rename(columns={"Price Close": "close", "Volume": "volume"})
                frames.append(hist)
            except Exception as e:
                frames.append(pd.DataFrame({"Instrument": batch, "error": str(e)}))

        # Try to pull bid/ask if entitled (skip gracefully if not)
        bid_ask_frames = []
        for batch in tqdm(list(chunks(rics, 50)), desc="Daily bid/ask (optional)"):
            try:
                df = ld.get_data(
                    batch,
                    [
                        f"TR.Bid(SDate={start},EDate={end},Frq=D).date",
                        f"TR.Bid(SDate={start},EDate={end},Frq=D)",
                        f"TR.Ask(SDate={start},EDate={end},Frq=D).date",
                        f"TR.Ask(SDate={start},EDate={end},Frq=D)",
                    ],
                )
                if not df.empty:
                    # Reshape bid/ask data similar to fundamentals
                    inst_col = "Instrument"
                    bid_data = df[[inst_col, f"TR.Bid(SDate={start},EDate={end},Frq=D).date", f"TR.Bid(SDate={start},EDate={end},Frq=D)"]]
                    ask_data = df[[inst_col, f"TR.Ask(SDate={start},EDate={end},Frq=D).date", f"TR.Ask(SDate={start},EDate={end},Frq=D)"]]

                    bid_data.columns = ["ric", "date", "bid"]
                    ask_data.columns = ["ric", "date", "ask"]

                    # Merge bid and ask
                    ba_data = bid_data.merge(ask_data, on=["ric", "date"], how="outer")
                    bid_ask_frames.append(ba_data.dropna())
            except Exception as e:
                # Skip bid/ask if not entitled or error
                print(f"Warning: Could not pull bid/ask data: {e}")
                continue

    # Process main daily data
    daily_prices = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not daily_prices.empty:
        # Handle MultiIndex columns similar to main prices function
        if isinstance(daily_prices.columns, pd.MultiIndex):
            original_index = daily_prices.index
            daily_prices = daily_prices.stack(level=0, future_stack=True)
            daily_prices = daily_prices.reset_index()
            daily_prices.columns = ['date', 'ric', 'close', 'volume']
            if len(original_index) > 0:
                date_mapping = {i: date for i, date in enumerate(original_index)}
                daily_prices['date'] = daily_prices['date'].map(date_mapping)
        else:
            daily_prices = daily_prices.rename(columns={"Instrument": "ric", "Date": "date"})

    # Merge bid/ask if available
    if bid_ask_frames:
        bid_ask_data = pd.concat(bid_ask_frames, ignore_index=True)
        if not bid_ask_data.empty:
            daily_prices = daily_prices.merge(bid_ask_data, on=["ric", "date"], how="left")

    return daily_prices
