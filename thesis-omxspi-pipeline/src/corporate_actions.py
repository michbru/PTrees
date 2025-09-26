from __future__ import annotations
import pandas as pd
import lseg.data as ld
from tqdm import tqdm
from .lseg_session import session_scope
from .utils import chunks

# Example CA fields supported by LSEG Data Library for splits/adjustments
CA_FIELDS = [
    "TR.CAEffectiveDate",
    "TR.CAAdjustmentType",
    "TR.CAAdjustmentFactor"
]


def pull_corporate_actions(rics: list[str], start: str, end: str) -> pd.DataFrame:
    frames = []
    with session_scope():
        for batch in tqdm(list(chunks(rics, 100)), desc="Corporate actions"):
            try:
                df = ld.get_data(batch, CA_FIELDS, {"SDate": start, "EDate": end})
                if not df.empty:
                    df = df.rename(columns={"Instrument": "ric"})
                    frames.append(df)
            except Exception as e:
                frames.append(pd.DataFrame({"ric": batch, "error": str(e)}))
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return out
