from __future__ import annotations
import pandas as pd
from pathlib import Path

# Expect SHoF CSV files downloaded manually, e.g.,
#  - data/external/shof_ff_nordic_monthly.csv  (contains Mkt-Rf, SMB, HML, RMW, CMA, MOM, RF)
# Adjust the filenames/columns to your actual downloads.


def load_shof_monthly(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Try common date col names
    for candidate in ["date", "Date", "YYYYMM", "yyyymm"]:
        if candidate in df.columns:
            if candidate.lower() == "yyyymm":
                # parse YYYYMM into month-end
                df["date"] = pd.to_datetime(df[candidate].astype(str) + "01", format="%Y%m%d") + pd.offsets.MonthEnd(0)
            else:
                df["date"] = pd.to_datetime(df[candidate])
            break
    df = df.rename(columns={c: c.lower() for c in df.columns})
    return df
