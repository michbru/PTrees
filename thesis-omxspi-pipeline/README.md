# OMXSPI Survivorship-Free Panel via LSEG (Python)

This pipeline builds a clean panel of Swedish equities (Stockholm, `.ST`) with active + inactive names to avoid survivorship bias, using **OMX Stockholm All‑Share (.OMXSPI)** historical constituents as the unbiased universe backbone. It downloads prices, corporate actions, and fundamentals, and merges them for asset‑pricing tests (e.g., p‑trees). Fama–French + momentum factors from **SHoF** are loaded from CSVs you provide.

## 1) Quick start

### a) Install deps
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### b) Credentials

* **Option A (env var)**: create a `.env` with `LSEG_APP_KEY=xxxxxxxx...`
* **Option B (JSON config)**: edit `lseg-data.config.json` (Desktop session by default).
  You need an active **LSEG Workspace/Eikon** login (desktop) or a platform session entitlement.

### c) Run a small smoke test

```bash
python -m src.run_pipeline --start 2019-01-01 --end 2020-12-31 --freq M --universe omxspi
```

Outputs land in `data/processed/`.

### d) Full run (e.g., 1996–today)

```bash
python -m src.run_pipeline --start 1996-01-01 --end 2025-09-01 --freq M --universe omxspi --pull-ca --pull-fund
```

## 2) Inputs & outputs

* **Universe**: historical constituents of `.OMXSPI` at each month‑end
* **Prices**: monthly (default) or daily OHLC/Close + Volume (adjusted optional)
* **Corporate actions**: splits/adjustment factors
* **Fundamentals**: quarterly & annual (optionally currency‑converted to SEK)
* **Factors**: load SHoF CSVs you download manually
* **Outputs**: tidy parquet/CSV files in `data/processed/` suitable for p‑trees

## 3) Notes

* If you ever hit field/entitlement quirks, open LSEG **Data Item Browser** and verify field names/parameters, then adjust the field lists in `prices.py` and `fundamentals.py`.
* Universe uses historical constituents (not today’s members), so delisted & dead securities appear during their life windows.

