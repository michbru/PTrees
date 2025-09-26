from __future__ import annotations
import pandas as pd
import lseg.data as ld
from tqdm import tqdm
import time
from .lseg_session import session_scope
from .utils import chunks, backoff_retry

# Core fields that should always work
FUND_CORE_FIELDS = [
    "TR.TotalAssetsActual",            # Balance sheet
    "TR.ShareholdersEquity",
    "TR.CommonSharesOutstanding",
    "TR.NetIncome",                    # Income statement
    "TR.OperatingIncome",
    "TR.Revenue",
]

# Extended fields to try (may require entitlements)
FUND_EXTENDED_FIELDS = [
    # Earnings & cash flows
    "TR.EPSNormalized",
    "TR.EPSReported",           # fallback if Normalized not entitled
    "TR.CashFromOperations",
    # Profitability & margins
    "TR.GrossProfit",
    "TR.GrossMargin",
    "TR.OperatingMargin",
    # Investment & leverage
    "TR.TotalDebt",
    "TR.LongTermDebt",
    "TR.DebtToAssets",
    "TR.CurrentAssets",
    "TR.CurrentLiabilities",
    # R&D / Advertising (skip gracefully if not entitled)
    "TR.RDExpense",
    "TR.AdvertisingExpense",
]

# Use core fields by default, with fallback strategy
FUND_Q_FIELDS = FUND_CORE_FIELDS + FUND_EXTENDED_FIELDS

FUND_A_FIELDS = FUND_CORE_FIELDS + FUND_EXTENDED_FIELDS


def _build_exprs(fields: list[str], start: str, end: str, frq: str, curn: str | None) -> list[str]:
    """Build per-field inline expressions with parameters to avoid parser issues."""
    exprs = []
    curn_part = f",Curn={curn}" if curn else ""
    for f in fields:
        base = f.split("(")[0]
        exprs.append(f"{base}(SDate={start},EDate={end},Frq={frq}{curn_part}).date")
        exprs.append(f"{base}(SDate={start},EDate={end},Frq={frq}{curn_part})")
    return exprs


@backoff_retry
def _get_data(universe, fields):
    return ld.get_data(universe, fields)


def _pull_block(rics: list[str], fields: list[str], start: str, end: str, frq: str, curn: str | None) -> pd.DataFrame:
    """Pull a set of fields for rics with robust chunking to avoid parser/timeouts.

    Strategy:
      - Split fields into small groups (5-6 per request)
      - For each group, try fetching all expressions; if fails, split further
      - Parse group result into tidy [ric,date,<fields>] and outer-merge
    """
    inst_col = "Instrument"

    def parse_group_df(group_df: pd.DataFrame, group_fields: list[str]) -> pd.DataFrame:
        if group_df.empty:
            return pd.DataFrame(columns=["ric", "date"])
        # Generic Date shape
        if "Date" in group_df.columns and inst_col in group_df.columns:
            out = group_df.rename(columns={inst_col: "ric", "Date": "date"}).copy()
            col_map = {}
            for c in out.columns:
                if c.startswith("TR."):
                    base = c.split("(")[0]
                    name = base.replace("TR.", "").lower()
                    name = name.replace("totalassetsactual", "totalassets")
                    col_map[c] = name
            if col_map:
                out = out.rename(columns=col_map)
            keep_cols = ["ric", "date"] + list(col_map.values())
            keep_cols = [c for c in keep_cols if c in out.columns]
            return out[keep_cols].dropna(subset=["date"]) if keep_cols else pd.DataFrame(columns=["ric", "date"])

        # .date/value pairs
        date_cols = [c for c in group_df.columns if c.endswith(".date")]
        melted = []
        for f in group_fields:
            base = f.split("(")[0]
            # Find matching cols
            date_cands = [c for c in date_cols if c.startswith(base + "(")]
            val_cands = [c for c in group_df.columns if c.startswith(base + "(") and not c.endswith('.date')]
            if date_cands and val_cands and inst_col in group_df.columns:
                tmp = group_df[[inst_col, date_cands[0], val_cands[0]]].copy()
                fname = base.replace('TR.', '').lower().replace('totalassetsactual', 'totalassets')
                tmp.columns = ['ric', 'date', fname]
                melted.append(tmp)
        if not melted:
            return pd.DataFrame(columns=["ric", "date"])  # nothing
        out = melted[0]
        for m in melted[1:]:
            out = out.merge(m, on=["ric", "date"], how="outer")
        return out

    def fetch_group(group_fields: list[str]) -> pd.DataFrame:
        exprs = _build_exprs(group_fields, start, end, frq, curn)
        try:
            df = _get_data(rics, exprs)
            return parse_group_df(df, group_fields)
        except Exception:
            return pd.DataFrame(columns=["ric", "date"])  # let caller try splitting

    # Split fields into small groups to avoid parser issues
    group_size = 6
    groups = [fields[i:i+group_size] for i in range(0, len(fields), group_size)]

    group_results: list[pd.DataFrame] = []
    for g in groups:
        res = fetch_group(g)
        if res.empty and len(g) > 1:
            # Split group in half and try again
            mid = len(g)//2
            left = fetch_group(g[:mid])
            right = fetch_group(g[mid:])
            # If still empty, go per-field to salvage whatever is available
            if left.empty and right.empty:
                for f in g:
                    single = fetch_group([f])
                    if not single.empty:
                        group_results.append(single)
            else:
                if not left.empty:
                    group_results.append(left)
                if not right.empty:
                    group_results.append(right)
        elif not res.empty:
            group_results.append(res)

        # Gentle pacing to reduce rate limiting
        time.sleep(0.2)

    if not group_results:
        return pd.DataFrame()

    out = group_results[0]
    for part in group_results[1:]:
        out = out.merge(part, on=["ric", "date"], how="outer")
    return out


def pull_fundamentals(universe: pd.DataFrame, start: str, end: str, curn: str | None = "SEK") -> pd.DataFrame:
    rics = sorted(universe["ric"].unique())
    frames_q, frames_a = [], []

    with session_scope():
        for batch in tqdm(list(chunks(rics, 25)), desc="Fundamentals Q"):
            try:
                # Try full field set first
                result = _pull_block(batch, FUND_Q_FIELDS, start, end, frq="Q", curn=curn)
                if not result.empty and "date" in result.columns:
                    frames_q.append(result)
                else:
                    # Fallback to core fields only
                    print(f"   Trying core fields only for batch...")
                    result = _pull_block(batch, FUND_CORE_FIELDS, start, end, frq="Q", curn=curn)
                    if not result.empty:
                        frames_q.append(result)
                    else:
                        frames_q.append(pd.DataFrame({"ric": batch, "error": "No data returned"}))
            except Exception as e:
                print(f"   Error in fundamentals batch: {e}")
                frames_q.append(pd.DataFrame({"ric": batch, "error": str(e)}))

        for batch in tqdm(list(chunks(rics, 25)), desc="Fundamentals A"):
            try:
                # Try full field set first (use 'Y' for yearly)
                result = _pull_block(batch, FUND_A_FIELDS, start, end, frq="Y", curn=curn)
                if not result.empty and "date" in result.columns:
                    frames_a.append(result)
                else:
                    # Fallback to core fields only
                    # Use 'Y' again for yearly fallback (some endpoints don't accept 'A')
                    result = _pull_block(batch, FUND_CORE_FIELDS, start, end, frq="Y", curn=curn)
                    if not result.empty:
                        frames_a.append(result)
                    else:
                        frames_a.append(pd.DataFrame({"ric": batch, "error": "No data returned"}))
            except Exception as e:
                print(f"   Error in fundamentals batch: {e}")
                frames_a.append(pd.DataFrame({"ric": batch, "error": str(e)}))

    fq = pd.concat(frames_q, ignore_index=True) if frames_q else pd.DataFrame()
    fa = pd.concat(frames_a, ignore_index=True) if frames_a else pd.DataFrame()

    # tag frequency and combine (only for valid data)
    if not fq.empty and "date" in fq.columns:
        fq["freq"] = "Q"
    if not fa.empty and "date" in fa.columns:
        fa["freq"] = "A"

    # Only combine frames that have actual data (not just error frames)
    valid_frames = []
    if not fq.empty and "date" in fq.columns:
        valid_frames.append(fq)
    if not fa.empty and "date" in fa.columns:
        valid_frames.append(fa)

    if valid_frames:
        fund = pd.concat(valid_frames, ignore_index=True).drop_duplicates()
        print(f"   Successfully pulled {len(fund)} fundamental records")
    else:
        print("   Warning: No valid fundamental data retrieved")
        fund = pd.DataFrame()

    return fund
