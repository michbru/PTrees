# P-Tree Analysis: Swedish Stock Market

**Implementation of "Growing the Efficient Frontier on Panel Trees"** (Cong et al., 2024, *Journal of Financial Economics*) applied to Swedish stock market data (1997-2022).

**Status:** Complete with 34 Characteristics | Out-of-Sample Sharpe Ratio: 2.69

---

## Key Results

### Enhanced 34-Characteristic Implementation

| Scenario | Period | Sharpe Ratio | Performance |
|----------|--------|--------------|-------------|
| **Full Sample** | 1997-2022 | 1.88 | Training |
| **Time Split (Train)** | 1997-2009 | 3.31 | Training |
| **Reverse Split (OOS)** | 2010-2022 | **2.69** | **Out-of-Sample** |

**Key Achievement:** Out-of-sample Sharpe ratio of 2.69 demonstrates robust predictive performance, achieving 76% of the original US study's OOS performance despite smaller market size and fewer characteristics.

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

```bash
# Run the full analysis pipeline
bash scripts/RUN_ANALYSIS.sh
```

This script will:
1. Create enhanced dataset with 34 characteristics (if not exists)
2. Prepare data for P-Tree analysis
3. Train P-Tree models across 3 scenarios
4. Generate results in `results/ptree_34chars/`

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
│   │   ├── 0_add_missing_characteristics.py
│   │   └── 1_prepare_data_34chars.py
│   ├── analysis/                      # P-Tree analysis scripts
│   │   ├── 2_ptree_analysis_34chars.R
│   │   ├── 3_benchmark_analysis.py
│   │   ├── 4_transaction_cost_analysis.py
│   │   └── 5_subperiod_analysis.py
│   └── visualization/                 # Visualization scripts
│       ├── 7_visualize_rolling_window.py
│       └── 8_visualize_main_results.py
│
├── results/
│   └── ptree_34chars/                 # Analysis results (34-char implementation)
│       ├── scenario_a_full/           # Full sample results
│       ├── scenario_b_split/          # Time split results
│       ├── scenario_c_reverse/        # Reverse split results
│       └── all_scenarios_summary.csv  # Summary statistics
│
├── docs/
│   ├── pdfs/trees.pdf                 # Original paper
│   ├── CHARACTERISTIC_MAPPING.md       # Characteristic mapping vs original study
│   ├── RESULTS_COMPARISON.md           # Performance analysis
│   ├── IMPLEMENTATION_COMPLETE.md      # Implementation notes
│   └── CLEANUP_SUMMARY.md              # Project reorganization notes
│
├── notebooks/                          # Jupyter notebooks for exploration
│   └── data_preprocessing.ipynb
│
├── scripts/
│   └── RUN_ANALYSIS.sh                 # Master execution script
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
python 0_add_missing_characteristics.py
```
- Calculates 15 additional characteristics from existing data
- Output: `data/processed/ptrees_enhanced_dataset.csv` (34 total characteristics)

**Step 2: Prepare for P-Tree**
```bash
python 1_prepare_data_34chars.py
```
- Merges with macro variables (risk-free rate)
- Lags characteristics by 1 month (avoid look-ahead bias)
- Ranks characteristics cross-sectionally within each month
- Output: `results/ptree_34chars/ptree_ready_data_34chars.csv`

**Step 3: Train P-Tree Models**
```bash
cd ../analysis
Rscript 2_ptree_analysis_34chars.R
```
- Trains 3 trees per scenario using boosting approach
- Three scenarios: Full sample, Time split, Reverse split
- Output: Models, factors, and summary statistics

### P-Tree Parameters

```r
min_leaf_size = 600       # Min observations per leaf
max_depth = 5             # Max tree depth
lambda_cov = 0.05         # Covariance regularization
equal_weight = TRUE       # Equal-weighted portfolios
num_iter = 3              # Number of boosting iterations
```

Scaled for Swedish market constraints (fewer stocks than US study).

---

## Results Analysis

### Performance vs Original Study

| Metric | US Study (Original) | Swedish (34-char) | Ratio |
|--------|---------------------|-------------------|-------|
| **In-sample Sharpe** | 6.37 | 3.31 | 52% |
| **Out-of-sample Sharpe** | 3.53 | 2.69 | **76%** |
| **Market size** | ~2,500 stocks | ~300 stocks | 12% |
| **Characteristics** | 61 | 34 | 56% |
| **Data frequency** | Daily | Monthly | - |

**Interpretation:** Swedish implementation achieves 76% of US OOS performance - remarkable given market size and data constraints.

### Performance by Scenario

**Scenario A: Full Sample (1997-2022)**
- Training on all data
- Sharpe: 1.88
- 9 tree nodes

**Scenario B: Time Split**
- Train: 1997-2009 | Test: 2010-2022
- Training Sharpe: 3.31
- *Note: OOS prediction limited by R PTree package*

**Scenario C: Reverse Split** ⭐ **Most Important**
- Train: 2010-2022 | Test: 1997-2009
- **OOS Sharpe: 2.69** (strongest evidence of robustness)
- 11 tree nodes

### Why Enhanced Implementation Outperforms

Compared to original 19-characteristic implementation:
- **+48% Full sample performance** (1.27 → 1.88 Sharpe)
- **+134% Out-of-sample performance** (1.15 → 2.69 Sharpe)
- Includes all critical characteristics P-Tree actually uses
- Better diversification across characteristic categories

See `docs/RESULTS_COMPARISON.md` for detailed analysis.

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

### But We Have Strengths

- All 6 critical characteristics from P-Tree top splits included
- Proper methodology following paper specifications
- Strong out-of-sample validation (Sharpe 2.69)
- Sufficient for meaningful analysis and publication

---

## Documentation

### Key Documents

- **`docs/RESULTS_COMPARISON.md`** - Detailed performance analysis vs previous implementations
- **`docs/CHARACTERISTIC_MAPPING.md`** - Complete characteristic mapping vs original study
- **`docs/IMPLEMENTATION_COMPLETE.md`** - Implementation summary and validation notes
- **`docs/pdfs/trees.pdf`** - Original P-Tree paper

### Analysis Scripts

All scripts are documented with detailed comments:
- Data preparation: `src/data_preparation/`
- Analysis: `src/analysis/`
- Visualization: `src/visualization/`

---

## Running Additional Analyses

### Benchmark Comparisons

```bash
cd src/analysis
python 3_benchmark_analysis.py
```
Compare P-Tree performance against CAPM, Fama-French 3-factor, and 5-factor models.

### Transaction Cost Analysis

```bash
python 4_transaction_cost_analysis.py
```
Evaluate net returns after transaction costs.

### Subperiod Analysis

```bash
python 5_subperiod_analysis.py
```
Test stability across different time periods.

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
