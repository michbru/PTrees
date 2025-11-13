# P-Tree Analysis: Swedish Stock Market

**Implementation of "Growing the Efficient Frontier on Panel Trees"** (Cong et al., 2024, *Journal of Financial Economics*) applied to Swedish stock market data (1997-2022).

**Status:** Complete with 34 Characteristics | Out-of-Sample Sharpe Ratio: 1.40

---

## Key Results

### Enhanced 34-Characteristic Implementation

**Out-of-Sample Performance (Validated Results):**

| Scenario | Train Period | Test Period | In-Sample Sharpe | Out-of-Sample Sharpe | Degradation |
|----------|--------------|-------------|------------------|----------------------|-------------|
| **B: Time Split** | 1997-2010 | 2010-2022 | 3.31 | **1.40** | 58% |
| **C: Reverse Split** | 2010-2022 | 1997-2010 | 2.69 | 0.70 | 74% |

**Key Achievement:** Scenario B achieves an out-of-sample Sharpe ratio of **1.40** (t=12.41, highly significant) when training on the first half (1997-2010) and testing on the second half (2010-2022). While showing moderate degradation (58%), this performance is economically meaningful and statistically robust.

**Important Note:** Scenario C shows weaker out-of-sample performance (0.70 Sharpe, 74% degradation), suggesting that models trained on recent data (post-2010) do not generalize as well to earlier periods. This asymmetry indicates structural changes in Swedish equity market dynamics around 2010.

### Critical Characteristics Included

This implementation includes all 6 critical characteristics used in the original P-Tree study's top splits:

1. **SUE** - Standardized Unexpected Earnings (Split #1 in original paper)
2. **DOLVOL** - Dollar Trading Volume (Splits #2, #3)
3. **BM_IA** - Industry-adjusted Book-to-Market (Splits #4, #5)
4. **ME_IA** - Industry-adjusted Market Equity (Split #7)
5. **ROE** - Return on Equity (Split #5)
6. **ZEROTRADE** - Zero Trading Days indicator (Split #6)

**Plus 28 additional characteristics** covering momentum, profitability, investment, and friction categories.

---

## Quick Start

### Prerequisites

- **Python 3.8+** with pandas, numpy, pathlib
- **R 4.0+** with PTree package installed
- **Data:** Swedish stock market data in `data/` folder

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd PTrees

# Install Python dependencies
pip install -r requirements.txt  # or use .venv

# Install R PTree package
# See archive/PTree-2501/ for package source if needed
```

### Run Complete Analysis

Run the analysis pipeline step by step:

```bash
# Step 1: Prepare data (from project root)
cd src/data_preparation
python3 1_add_missing_characteristics.py
python3 2_prepare_data.py

# Step 2: Run P-Tree analysis (MAIN STEP)
cd ../analysis
Rscript 3_ptree_analysis.R

# Step 3: Validate results
cd ../..
python3 validate_results.py
```

**Expected runtime:** 30-60 minutes

---

## Project Structure

```
PTrees/
├── README.md                          # This file
│
├── data/
│   ├── raw/serrano/                   # Raw Serrano database (42 GB)
│   ├── processed/                     # Processed datasets
│   │   ├── ptrees_final_dataset.csv
│   │   └── ptrees_enhanced_dataset.csv (34 characteristics)
│   └── macro/                         # Macro variables (risk-free rate, market returns)
│
├── src/
│   ├── data_preparation/              # Data processing scripts
│   │   ├── 1_add_missing_characteristics.py
│   │   └── 2_prepare_data.py
│   └── analysis/                      # P-Tree analysis scripts
│       ├── 3_ptree_analysis.R         # Main P-Tree training (REQUIRED)
│       ├── 4_benchmark_analysis.py    # Fama-French comparison (optional)
│       ├── 5_transaction_cost_analysis.py  # Transaction costs (optional)
│       └── 6_subperiod_analysis.py    # Robustness checks (optional)
│
├── results/
│   └── ptree_34chars/                 # Analysis results (34-char implementation)
│       ├── scenario_a_full/           # Full sample results
│       ├── scenario_b_split/          # Time split results
│       ├── scenario_c_reverse/        # Reverse split results
│       └── all_scenarios_summary.csv  # Summary statistics
│
├── docs/
│   └── pdfs/trees.pdf                 # Original paper
│
├── notebooks/                          # Jupyter notebooks for exploration
│   └── data_preprocessing.ipynb
│
├── validate_results.py                 # Validation script for OOS results
│
└── archive/
    ├── 19_char_implementation/         # Original implementation (superseded)
    └── PTree-2501/                     # R package source (reference)
```

---

## Methodology

### Data Processing Pipeline

**Step 1: Create Enhanced Dataset**
```bash
cd src/data_preparation
python3 1_add_missing_characteristics.py
```
- Calculates 15 additional characteristics from existing data
- Output: `data/processed/ptrees_enhanced_dataset.csv` (34 total characteristics)

**Step 2: Prepare for P-Tree**
```bash
python3 2_prepare_data.py
```
- Merges with macro variables (risk-free rate)
- Lags characteristics by 1-3 months (avoid look-ahead bias)
- Ranks characteristics cross-sectionally within each month
- Output: `results/ptree_34chars/ptree_ready_data_34chars.csv`

**Step 3: Train P-Tree Models** (MAIN ANALYSIS)
```bash
cd ../analysis
Rscript 3_ptree_analysis.R
```
- Trains 3 trees per scenario using boosting approach
- Three scenarios: Full sample, Time split, Reverse split
- Output: Models, factors, and summary statistics

### P-Tree Parameters

```r
min_leaf_size = 5         # Min observations per leaf (conservative for smaller market)
max_depth = 8             # Max tree depth (prevents overfitting)
lambda_cov = 5e-4         # Covariance regularization (increased from 1e-4)
equal_weight = FALSE      # Value-weighted portfolios
num_iter = 6              # Number of boosting iterations
```

Parameters are conservative to prevent overfitting in the smaller Swedish market (~300 stocks vs ~2,500 in US study).

---

## Results Analysis

### Performance Comparison

| Metric | US Study (Original) | Swedish (34-char) |
|--------|---------------------|-------------------|
| **Market size** | ~2,500 stocks | ~300 stocks |
| **Characteristics** | 61 | 34 (56% coverage) |
| **Data frequency** | Daily | Monthly |
| **Best OOS Sharpe** | ~1.5-2.0 (est.) | 1.31 |

**Interpretation:** Despite significantly smaller market size and fewer characteristics, the Swedish implementation achieves economically meaningful out-of-sample performance with proper validation.

### Detailed Performance by Scenario

**Scenario A: Full Sample (1997-2022)**
- Training on all data (in-sample only)
- Tree 1 Sharpe: 1.19
- 5 tree nodes

**Scenario B: Time Split (Forward Test)** ⭐ **Primary Result**
- Train: 1997-2010 (154 months) | Test: 2010-2022 (156 months)
- In-Sample Sharpe: 3.31 (Tree 1)
- **Out-of-Sample Sharpe: 1.40** (t=12.41, highly significant)
- Degradation: 58% (moderate overfitting, but OOS remains strong)

**Scenario C: Reverse Split (Backward Test)**
- Train: 2010-2022 (156 months) | Test: 1997-2010 (154 months)
- In-Sample Sharpe: 2.69 (Tree 1)
- **Out-of-Sample Sharpe: 0.70** (t=7.75, significant)
- Degradation: 74% (substantial degradation)

**Key Finding:** Forward testing (Scenario B) shows better out-of-sample performance than reverse testing (Scenario C), suggesting that pre-2010 data contains patterns that generalize to post-2010 periods better than vice versa. Both tests remain statistically significant, demonstrating real predictive power despite degradation.

---

## Characteristics Coverage

### Categories

| Category | Count | Key Characteristics |
|----------|-------|-------------------|
| **Momentum** | 7/9 | SUE, MOM1M, MOM6M, MOM12M, MOM36M |
| **Value & Size** | 8/12 | BM, BM_IA, ME, ME_IA, EP, CFP, SP |
| **Profitability** | 7/7 | ROA, ROE, OP, PM, GP, ATO |
| **Frictions** | 8/15 | DOLVOL, TURN, ME, SVAR, ZEROTRADE |
| **Investment** | 4/12 | AGR, CAPEX, NI, SALES_GR |

**Total:** 34 characteristics (56% coverage of original 61)

### Data Quality

- **High quality (>90% coverage):** Trading metrics, size/value, industry-adjusted metrics
- **Medium quality (50-90%):** SUE (58%), MOM36M (81%)
- **Low quality (<50%):** ROE (14%), OP (4%)

P-Tree automatically down-weights low-quality characteristics if not informative.

---

## Limitations

### Swedish Market Constraints

1. **Smaller market:** ~300 stocks vs ~2,500 in US
2. **Data availability:** 34/61 characteristics (56% coverage)
3. **Monthly frequency:** Less precise than daily data
4. **Approximations:**
   - SUE calculated from historical earnings (not analyst consensus)
   - ZEROTRADE proxied by low turnover indicator
   - Industry adjustments based on coarse market segments

### Methodological Strengths

Despite these constraints, the implementation has important strengths:

- All 6 critical characteristics from P-Tree top splits included
- Proper methodology following paper specifications
- **Conservative parameters** to prevent overfitting (min_leaf_size=5, max_depth=8)
- **3-month lag** for accounting data (prevents look-ahead bias)
- **True out-of-sample testing** with no data leakage
- Meaningful OOS performance (Sharpe 1.31, t=16.21) in primary test

---

## Documentation

### Key Files

- **`docs/pdfs/trees.pdf`** - Original P-Tree paper (Cong et al., 2024)
- **`results/ptree_34chars/validation_summary.csv`** - OOS performance validation
- **`validate_results.py`** - Script to verify out-of-sample results

### Analysis Scripts

**Core Pipeline (Required):**
1. `src/data_preparation/1_add_missing_characteristics.py` - Create 34 characteristics
2. `src/data_preparation/2_prepare_data.py` - Prepare and lag data
3. `src/analysis/3_ptree_analysis.R` - **Train P-Tree models** (main analysis)

**Optional Analyses:**
4. `src/analysis/4_benchmark_analysis.py` - Fama-French factor comparisons
5. `src/analysis/5_transaction_cost_analysis.py` - Transaction cost sensitivity
6. `src/analysis/6_subperiod_analysis.py` - Temporal stability checks

---

## Running Optional Analyses

**Note:** These are supplementary analyses for robustness checks. The core results come from step 3 (P-Tree analysis).

### Benchmark Comparisons
```bash
cd src/analysis
python3 4_benchmark_analysis.py
```
Compare P-Tree performance against CAPM and Fama-French factor models.

### Transaction Cost Analysis
```bash
python3 5_transaction_cost_analysis.py
```
Evaluate net returns after realistic transaction costs.

### Subperiod Analysis
```bash
python3 6_subperiod_analysis.py
```
Test performance stability across different time periods.

---

## Citation

### Original Paper

```bibtex
@article{cong2024growing,
  title={Growing the Efficient Frontier on Panel Trees},
  author={Cong, Lin William and Feng, Guanhao and He, Jingyu and He, Xiang},
  journal={Journal of Financial Economics},
  year={2024},
  publisher={Elsevier}
}
```

### This Implementation

If you use this Swedish market implementation, please cite:
- Original paper (above)
- This repository
- Serrano database (data source)

---

## Troubleshooting

### Common Issues

**Issue:** `PTree` package not found
- **Solution:** Install from CRAN: `install.packages("PTree")` or use archive/PTree-2501/

**Issue:** File path errors
- **Solution:** Run scripts from project root or use provided `scripts/RUN_ANALYSIS.sh`

**Issue:** Memory errors during P-Tree training
- **Solution:** Reduce `min_leaf_size` or train on subset of data

**Issue:** Missing macro variables
- **Solution:** Ensure `data/macro/macro_variables_with_dates.csv` exists

---

## Contributing

This is a research project for a Bachelor thesis. Suggestions and improvements are welcome:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

---

## License

[Specify your license]

---

## Contact

[Your contact information]

---

## Acknowledgments

- **Original Authors:** Cong, Feng, He, He (2024) for the P-Tree methodology
- **Data Source:** Serrano Database (Swedish House of Finance)
- **Supervisor:** [Your supervisor]
- **Institution:** [Your institution]

---

**Last Updated:** January 12, 2025
**Version:** 2.0 (Enhanced 34-Characteristic Implementation)
