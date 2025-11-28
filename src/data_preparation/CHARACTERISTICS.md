# P-Tree Swedish Market — Characteristics & Lagging Spec

This document is the single source of truth for how each characteristic is constructed, which data it uses, and what lagging assumptions are applied. It reflects the code in `src/data_preparation` after Steps 1–6 and the final validation.

## Data & Alignment

- Daily market data: Finbas (prices, bid/ask, volume, turnover, market cap). Filtered to SEK quotes and SE ISINs. One row per (ISIN, date) with deterministic venue/liquidity preference.
- Annual accounting data: Serrano (bokslut + nyckeltal), merged vertically across 10 files each; deduplicated per (ORGNR, fiscal year) with deterministic tie‑breakers; left‑merged nyckeltal onto bokslut.
- Mapping: ISIN → ORGNR via automated LSEG (TaxID + conservative name‑match) and manual overrides.
- Step 5 merge: as‑of for each (ISIN, date) on `orgnr` where `fiscal_year_end <= date` (no reporting lag applied at this stage) with proper sorting for `merge_asof`.

## Lagging Policy (Step 6)

- Publication lag: Accounting variables use a 6‑month publication lag. For month `t` with fiscal year end `FYE`:
  - If `months_since_fye(t, FYE) >= 6`: use current FY values.
  - Else: use previous FY values.
  - These appear as `…_pub` columns in Step 6.
- Market cap for ratios/weights: 1‑month lag (`market_cap_lag1`). If raw market cap is missing, `market_cap_filled` is used for monthly aggregation and lagging where needed.
- Monthly cross‑section: last trading day of each month; returns `ret_monthly` are close‑to‑close from these month‑ends.
- Ranking: Within each month (cross‑section), map each raw characteristic to `[-1, 1]`. Missing values are set to `0` (neutral).
- Safe division: All ratios use `safe_div` (return NaN when denominator is near zero or non‑finite); ranks then neutralize missing.

## Characteristic Definitions

Notation below uses publication‑lagged accounting values (`…_pub`) and market cap lagged by 1 month (`market_cap_lag1`).

### Momentum
- `MOM1M`: previous month return `ret_monthly_{t-1}`.
- `MOM6M`: `(P_{t-2}/P_{t-6}) − 1` (skip `t−1`).
- `MOM12M`: `(P_{t-2}/P_{t-12}) − 1`.
- `MOM36M`: `(P_{t-13}/P_{t-36}) − 1`.
- `MOM60M`: `(P_{t-13}/P_{t-60}) − 1`.
- `SEAS1A`: `ret_monthly_{t-12}`.
- `CHTX`: YoY pct change of `tax_expense_pub` (12‑month diff).
- `DEPR`: `depreciation_pub / (ppe_buildings_pub + ppe_machinery_pub)`.

### Value
- `BM`: `book_equity_pub / market_cap_lag1`.
- `EP`: `net_income_pub / market_cap_lag1`.
- `SP`: `sales_pub / market_cap_lag1`.
- `CFP`: `(net_income_pub + depreciation_pub) / market_cap_lag1`.
- `CASH`: `cash_pub / total_assets_pub`.
- `CASHDEBT`: `cash_pub / (long_term_debt_pub + current_liabilities_pub)`.
- `LEV`: `(long_term_debt_pub + current_liabilities_pub) / total_assets_pub`.
- `SGR`: YoY pct change of `sales_pub`.

### Investment
- `AGR`: YoY pct change of `total_assets_pub`.
- `GMA`: `(sales_pub − (cogs_materials_pub + cogs_goods_pub)) / total_assets_pub`.
- `LGR`: YoY pct change of `long_term_debt_pub`.
- `ACC`: `(Δ working_capital − depreciation_pub) / avg_assets`, where `working_capital = current_assets_pub − current_liabilities_pub`, `avg_assets = mean(total_assets_pub_t, total_assets_pub_{t−12})`.
- `PCTACC`: `(ACC × avg_assets) / |net_income_pub|`.
- `NOA`: `(operating_assets − operating_liabilities) / total_assets_pub_{t−24}`, where `operating_assets = total_assets_pub − cash_pub`, `operating_liabilities = total_assets_pub − book_equity_pub − long_term_debt_pub`.
- `CINVEST`: `(ppe_pub − ppe_pub_{t−12}) / ppe_pub_{t−12}`, where `ppe_pub = ppe_buildings_pub + ppe_machinery_pub`.
- `GRLTNOA`: YoY pct change of `NOA`.
- `CHCSHO`: `(shares − shares_{t−12}) / shares_{t−12}`, where `shares ≈ market_cap / close`.
- `NI`: `log(shares / shares_{t−12})`.

### Profitability
- `ROA`: `net_income_pub / total_assets_pub`.
- `ROE`: `net_income_pub / book_equity_pub`.
- `ATO`: `sales_pub / avg_assets`.
- `PM`: `net_income_pub / sales_pub`.
- `OP` (operating profitability): `operating_income_pub / total_assets_pub` (distinct from GMA).
- `RNA`: `operating_income_pub / (operating_assets − operating_liabilities)`.

### Intangibles
- `HIRE`: YoY pct change of `num_employees_pub`.

### Frictions (Daily → 3‑Month Rolling → Monthly last)
All daily metrics use a 63‑trading‑day (~3 months) window and are averaged (or as noted) then sampled on the month’s last trading day.
- `ZEROTRADE`: mean(1[volume == 0]).
- `BASPREAD`: mean((ask − bid)/((ask + bid)/2)).
- `DOLVOL`: log(mean(turnover_sek) + 1).
- `ILL` (Amihud): mean(|ret| / (turnover_sek + 1) × 1e6).
- `MAXRET`: max(daily return).
- `SVAR`: var(daily return).
- `STD_DOLVOL`: std(log(turnover_sek + 1)).
- `TURN`: mean(volume / shares_out), `shares_out ≈ market_cap_filled / close`.
- `STD_TURN`: std(volume / shares_out).
- `ME`: log(market_cap) (monthly, not daily).

### Ranking & Final Dataset
- Cross‑sectional ranking: within each `year_month` to `[-1, 1]` via linear rescaling. Missing values set to 0 (neutral).
- Weighting variable: `lag_me = market_cap_{t−1}` with a first‑month fallback to current market cap.

## Known Limitations / Notes

- Beta/Idiosyncratic variance (CAPM/FF3) are currently placeholders (not computed) and excluded from ranking.
- `ZEROTRADE` may have very low coverage on this market due to non‑zero volume; it will be filtered by your coverage threshold.
- Shares outstanding are approximated via `market_cap / close` where explicit share count is unavailable.
- No winsorization is applied; extreme raw values are handled naturally by ranking and safe division.

## Validation Summary

The `src/validation/validate_pipeline.py` script verifies:
- As‑of join integrity (`fiscal_year_end <= date`, unique keys).
- Monthly aggregation correctness (last trading day, return recomputation).
- Publication‑lag logic (prev FY used within 6 months after FYE for sales/book_equity/net_income).
- Final dataset integrity (unique keys, rank bounds, `lag_me` alignment).
- Quick signal sanity (value and momentum long‑shorts vs next‑month returns).

All checks passed on the current dataset.

