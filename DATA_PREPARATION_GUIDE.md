# Data Preparation Guide - Unified Pipeline

## Overview

This document explains the **streamlined data preparation pipeline** for the P-Tree analysis. All data processing happens in **one unified script** that is fully documented and traceable.

---

## Quick Start

### Run the complete pipeline in ONE step:

```bash
cd src/data_preparation
python prepare_ptree_dataset.py
```

**Output:** `results/ptree_34chars/ptree_ready_data_34chars.csv` (ready for P-Tree)

**Runtime:** ~2-3 minutes

---

## What This Script Does

The `prepare_ptree_dataset.py` script performs ALL data preparation in a single, traceable pipeline:

```
RAW DATA (4 sources)
  |
  |--> Load & Merge
  |--> Calculate ALL 34 characteristics (documented)
  |--> Apply lags (prevent look-ahead bias)
  |--> Create cross-sectional ranks
  |
  v
P-TREE READY DATASET
```

---

## Input Data Sources

### 1. Stock Market Data
- **File:** `data/raw/serrano/final_dataset_with_serrano_isin.csv`
- **Content:** LSEG stock prices, returns, volume + some accounting
- **Size:** 102,823 observations (monthly, 1997-2022)
- **Key fields:** price, volume, market_cap, returns, book_value

### 2. Accounting Data
- **File:** `data/raw/serrano/serrano_nyckeltal_full.csv`
- **Content:** Swedish company financial ratios (Serrano database)
- **Note:** Already merged into base dataset via ORGNR mapping

### 3. Macro Variables
- **File:** `data/macro/macro_variables_with_dates.csv`
- **Content:** Risk-free rate (rf), market returns (rm)
- **Usage:** Calculate excess returns for Sharpe ratio

### 4. Company Mapping
- **File:** `data/raw/serrano/isin_orgnr_mapping.csv`
- **Content:** Maps stock ISINs to company registration numbers
- **Usage:** Link market data to accounting data

---

## Processing Steps (Detailed)

### STEP 1: Load and Merge Raw Sources

1. Load base stock dataset (102,823 obs)
2. Load macro variables (275 months)
3. Merge on date
4. Create P-Tree required fields:
   - `permno` - unique stock identifier
   - `xret` - excess returns (return - rf)
   - `lag_me` - lagged market cap for value-weighting

**Output:** 101,445 observations (after removing missing data)

---

### STEP 2: Calculate ALL 34 Characteristics

All characteristics are calculated and **fully documented** in the script with:
- Formula
- Data source (from base vs calculated)
- Coverage statistics
- Assumptions/limitations

#### GROUP A: Critical Characteristics (Top 6 from P-Tree paper)

**A1. SUE - Standardized Unexpected Earnings** (Split #1)
```python
earnings_surprise = net_income_t - net_income_{t-4}
sue = earnings_surprise / std(earnings_surprise, 8 months)
```
- Coverage: 57.9%
- Assumption: 4-month lag approximates quarterly comparison
- Limitation: Uses historical earnings, not analyst consensus

**A2. DOLVOL - Dollar Trading Volume** (Splits #2, #3)
```python
dolvol = price × volume
```
- Coverage: 99.9%
- No approximations

**A3. BM_IA - Industry-Adjusted Book-to-Market** (Splits #4, #5)
```python
bm_ia = log(book_to_market / industry_median_BM)
```
- Coverage: 98.2%
- **IMPORTANT:** "Industry" = market segment (SSE, SSEFN, etc.), NOT true industry
- Limitation: Ericsson (tech) compared to Volvo (auto) if both on SSE

**A4. ME_IA - Industry-Adjusted Market Equity** (Split #7)
```python
me_ia = log(market_cap / industry_median_MC)
```
- Coverage: 100.0%
- Same industry proxy as BM_IA

**A5. ROE - Return on Equity** (Split #5)
```python
roe = net_income / book_value
```
- Coverage: 13.7%
- Limitation: Low coverage due to limited accounting data

**A6. ZEROTRADE - Zero Trading Days Proxy** (Split #6)
```python
zerotrade = 1 if monthly_turnover < 0.01 else 0
```
- Coverage: 100.0%
- **Approximation:** Binary flag vs count (monthly data limitation)
- Justification: Captures illiquidity (core concept)

#### GROUP B: Momentum (4 characteristics)
- MOM1M (return_1m) - 1-month return
- MOM6M - 6-month compound return
- MOM12M (momentum_12m) - 12-month return
- MOM36M - 36-month compound return

#### GROUP C: Value & Size (6 characteristics)
- MARKET_CAP, ME (log size), BM, EP, CFP, SP

#### GROUP D: Profitability (4 characteristics)
- ROA, GP (gross_profitability), OP, PM

#### GROUP E: Investment & Growth (4 characteristics)
- AGR (asset_growth), SALES_GR, CAPEX, NI

#### GROUP F: Frictions (4 characteristics)
- TURN (turnover), SVAR (variance), STD_TURN, STD_DOLVOL

#### GROUP G: Other (5 characteristics)
- ATO (asset_turnover), DE (debt_to_equity), AQ (asset_quality), CFOA, PA

**Total: 34 characteristics** (56% of US study's 61)

---

### STEP 3: Apply Lags (Prevent Look-Ahead Bias)

**CRITICAL:** Cannot use current month's data to predict current returns!

```python
# Market characteristics: 1-month lag
for char in [momentum, volume, turnover, ...]:
    lag_char = char.shift(1)

# Accounting characteristics: 3-month lag (reporting delay)
for char in [roe, roa, earnings, margins, ...]:
    lag_char = char.shift(3)
```

**Why 3-month lag for accounting?**
- Companies report quarterly earnings ~2 months after quarter end
- Data becomes public with additional delay
- 3-month lag ensures no look-ahead bias

---

### STEP 4: Create Cross-Sectional Ranks

P-Tree works better with percentile ranks [0, 1] than raw values.

```python
# For each month, rank all stocks by each characteristic
rank_sue = percentile_rank(lag_sue, by_month)

# Example for month 2010-01:
# Stock A: sue = 2.5 → rank_sue = 0.95 (top 5%)
# Stock B: sue = -1.2 → rank_sue = 0.15 (bottom 15%)
```

**Why rank?**
- Makes characteristics comparable
- Reduces impact of outliers
- P-Tree algorithm works better with bounded [0, 1] values

**Handling missing values:**
```python
# Fill missing ranks with 0.5 (neutral) instead of dropping
rank_char = rank_char.fillna(0.5)
```
- Preserves all observations (97.8% retention)
- P-Tree learns to ignore characteristics with low coverage

---

### STEP 5: Final Validation and Save

**Verification checks:**
- No NaN in core columns (xret, permno, lag_me)
- No NaN in ranked characteristics
- All characteristics properly lagged

**Final output:**
- 100,562 observations
- 310 months (1997-03 to 2022-12)
- 33-34 ranked characteristics
- Ready for P-Tree training

---

## Output Structure

The final dataset `ptree_ready_data_34chars.csv` contains:

### Core Columns (Required by P-Tree)
- `xret` - excess returns (target variable)
- `permno` - stock identifier
- `lag_me` - lagged market cap (for value-weighting)
- `date` - month

### Ranked Characteristics (Features for P-Tree)
- `rank_sue`, `rank_dolvol`, `rank_bm_ia`, ... (34 total)
- All values in [0, 1] range (percentiles)
- All properly lagged (1 or 3 months)
- Missing values filled with 0.5 (neutral)

### Metadata Columns
- `ticker`, `name` - stock identifiers
- `industry` - market segment
- Original characteristic values (for reference)

---

## Key Assumptions & Limitations

### Valid Assumptions
1. **Monthly data approximates quarterly patterns** - SUE using 4-month lags
2. **Lagging prevents look-ahead bias** - 1-month for market, 3-month for accounting
3. **Ranking improves robustness** - Reduces outlier impact
4. **Value-weighting is standard** - Uses lagged market cap

### Important Limitations (Acknowledge in Thesis)

1. **Industry = Market Segment**
   - ME_IA/BM_IA compare stocks on same exchange, not same industry
   - Missing true industry peers comparison
   - Still captures size/liquidity effects

2. **SUE Approximation**
   - Uses historical earnings, not analyst consensus
   - 4-month lag is proxy for quarterly comparison
   - Coverage: 57.9%

3. **ZEROTRADE Approximation**
   - Binary flag vs count of zero days
   - Arbitrary 1% threshold
   - Captures illiquidity concept

4. **Monthly vs Daily Data**
   - Less precise for trading-based metrics
   - Cannot calculate true daily zero-trading days
   - Momentum/volatility less granular

5. **Data Coverage**
   - 34/61 characteristics (56% of US study)
   - Some low coverage (roe 13.7%, op 3.6%)
   - P-Tree handles this via regularization

---

## Comparison: Old vs New Pipeline

### Old "Frankenstein" Approach
```
??? (unknown origin)
  |
  v
final_dataset_with_serrano_isin.csv (19 chars)
  |
  v
1_add_missing_characteristics.py (+15 chars)
  |
  v
2_prepare_data.py (ranking, lagging)
  |
  v
ptree_ready_data_34chars.csv
```

**Problems:**
- Unclear data origin
- Two-step process
- Hard to trace characteristic calculations
- Split between "base" and "calculated" characteristics

### New Unified Approach ✓
```
RAW DATA (4 clearly defined sources)
  |
  v
prepare_ptree_dataset.py
  - Documents ALL 34 characteristics
  - Single traceable pipeline
  - Fully commented formulas
  - Assumptions clearly stated
  |
  v
ptree_ready_data_34chars.csv
```

**Benefits:**
- Clear data lineage
- One script does everything
- Fully documented
- Easy to modify/extend
- Better for thesis defense

---

## Next Steps

After running the unified pipeline:

```bash
# Step 1: Prepare data
cd src/data_preparation
python prepare_ptree_dataset.py

# Step 2: Run P-Tree analysis
cd src/analysis
Rscript 3_ptree_analysis.R

# Step 3: Validate results
python 7_validate_results.py
```

---

## Troubleshooting

**Issue:** File not found errors
- **Solution:** Run from project root directory

**Issue:** Encoding errors (Windows)
- **Solution:** Script now uses ASCII-safe characters

**Issue:** Memory errors
- **Solution:** Script processes data efficiently, should work on 8GB+ RAM

**Issue:** Missing macro variables
- **Solution:** Ensure `data/macro/macro_variables_with_dates.csv` exists

---

## For Thesis Defense

When asked about data preparation, you can confidently explain:

1. **Data sources:** 4 clearly defined raw inputs
2. **Processing:** Single unified pipeline (prepare_ptree_dataset.py)
3. **All 34 characteristics:** Documented with formulas, assumptions, limitations
4. **Look-ahead bias prevention:** Proper lagging (1-month market, 3-month accounting)
5. **Robustness:** Cross-sectional ranking, missing value handling
6. **Transparency:** Every calculation is traceable and documented

The unified script serves as **living documentation** of your entire data pipeline.

---

Last updated: 2025-01-23
Version: 2.0 (Unified Pipeline)
