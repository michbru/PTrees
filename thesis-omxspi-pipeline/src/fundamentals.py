from __future__ import annotations
import pandas as pd
import lseg.data as ld
from tqdm import tqdm
from .lseg_session import session_scope
from .utils import chunks

# You can tweak this list in Data Item Browser if any field requires entitlement change
FUND_Q_FIELDS = [
    "TR.TotalAssetsActual",            # Balance sheet
    "TR.ShareholdersEquity",
    "TR.CommonSharesOutstanding",
    "TR.NetIncome",                    # Income statement
    "TR.OperatingIncome",
    "TR.Revenue",
    "TR.DepreciationAmort",
    "TR.CapitalExpenditures",
]

FUND_A_FIELDS = [
    "TR.TotalAssetsActual",
    "TR.ShareholdersEquity",
    "TR.CommonSharesOutstanding",
    "TR.NetIncome",
    "TR.OperatingIncome",
    "TR.Revenue",
    "TR.DepreciationAmort",
    "TR.CapitalExpenditures",
]


def _pull_block(rics: list[str], fields: list[str], start: str, end: str, frq: str, curn: str | None) -> pd.DataFrame:
    params = {"SDate": start, "EDate": end, "Frq": frq}
    if curn:
        params["Curn"] = curn
    df = ld.get_data(rics, [f+".date" for f in fields] + fields, params)
    if df.empty:
        return df
    # reshape: wide TR.* timeseries -> tidy long per field, then merge
    inst_col = "Instrument"
    date_cols = [c for c in df.columns if c.endswith(".date")]
    val_cols = [c for c in df.columns if (c.startswith("TR.") and not c.endswith(".date"))]

    # Try to pair date/values in order of the requested fields
    melted = []
    for f in fields:
        date_col = f + ".date"
        val_col = f
        if date_col in df.columns and val_col in df.columns:
            tmp = df[[inst_col, date_col, val_col]].copy()
            tmp.columns = ["ric", "date", f.split("(")[0].replace("TR.", "").lower()]
            melted.append(tmp)
    if not melted:
        return pd.DataFrame(columns=["ric", "date"])  # nothing found
    out = melted[0]
    for m in melted[1:]:
        out = out.merge(m, on=["ric", "date"], how="outer")
    return out


def pull_fundamentals(universe: pd.DataFrame, start: str, end: str, curn: str | None = "SEK") -> pd.DataFrame:
    rics = sorted(universe["ric"].unique())
    frames_q, frames_a = [], []
    with session_scope():
        for batch in tqdm(list(chunks(rics, 50)), desc="Fundamentals Q"):
            try:
                frames_q.append(_pull_block(batch, FUND_Q_FIELDS, start, end, frq="Q", curn=curn))
            except Exception as e:
                frames_q.append(pd.DataFrame({"ric": batch, "error": str(e)}))
        for batch in tqdm(list(chunks(rics, 50)), desc="Fundamentals A"):
            try:
                frames_a.append(_pull_block(batch, FUND_A_FIELDS, start, end, frq="A", curn=curn))
            except Exception as e:
                frames_a.append(pd.DataFrame({"ric": batch, "error": str(e)}))
    fq = pd.concat(frames_q, ignore_index=True) if frames_q else pd.DataFrame()
    fa = pd.concat(frames_a, ignore_index=True) if frames_a else pd.DataFrame()

    # tag frequency and combine
    if not fq.empty:
        fq["freq"] = "Q"
    if not fa.empty:
        fa["freq"] = "A"
    fund = pd.concat([fq, fa], ignore_index=True).drop_duplicates()
    return fund
