import pandas as pd

panel = pd.read_parquet("data/processed/panel_m.parquet")

# Size (market cap)
panel = panel.sort_values(["ric","date"])
# already mkt_cap in merge_panel; if not:
# panel["mkt_cap"] = panel["commonsharesoutstanding"] * panel["adj_close"].fillna(panel["close"])

# Book-to-market
if {"shareholdersequity","mkt_cap"}.issubset(panel.columns):
    panel["bm"] = panel["shareholdersequity"] / panel["mkt_cap"]

# Momentum (12-1)
panel["ret_mom"] = (
    panel.groupby("ric")["ret"].rolling(12).apply(lambda x: (1+x).prod()-1, raw=False).reset_index(level=0, drop=True)
)
panel["ret_mom_excl_1m"] = (
    panel.groupby("ric")["ret"].shift(1).rolling(11).apply(lambda x: (1+x).prod()-1, raw=False)
)
