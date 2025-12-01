# P-Trees: Prediction Trees for Swedish Market Factor Construction

This repository implements the P-Tree (Prediction Tree) methodology for constructing factor portfolios in the Swedish equity market. The analysis builds on the framework introduced by Bryzgalova et al. (2023) and applies it to Swedish stocks using combined market and accounting data.

## Overview

P-Trees are decision trees that construct tradeable factors by:
1. Splitting stocks based on firm characteristics
2. Creating long-short portfolios from leaf nodes
3. Optimizing splits to maximize Sharpe ratio of resulting factors

This implementation uses 28 firm characteristics spanning momentum, value, investment, profitability, intangibles, and frictions to analyze Swedish market data from the Stockholm Stock Exchange.

## Project Structure

```
PTrees/
├── src/                              # Source code
│   ├── data_preparation/            # Data processing pipeline
│   │   ├── 1_process_finbas.py     # Process market data
│   │   ├── 2_process_serrano_accounting.py  # Process accounting data
│   │   ├── 3_build_isin_orgnr_mapping_LSEG.py  # Build ISIN-ORGNR mapping
│   │   ├── 4_merge_mappings.py     # Merge mapping sources
│   │   ├── 5_merge_datasets.py     # Merge market + accounting data
│   │   ├── 6_prepare_ptree_dataset.py  # Final dataset preparation
│   │   └── CHARACTERISTICS.md       # Complete characteristic definitions
│   ├── analysis/                    # P-Tree model training & evaluation
│   │   ├── 01_prepare_inputs.R     # Prepare inputs for P-Tree
│   │   ├── 02_train_ptree.R        # Train P-Tree models
│   │   ├── 03_evaluate_model.R     # Evaluate model performance
│   │   └── 04_visualize_results.R  # Generate visualizations
│   └── validation/                  # Pipeline validation
│       └── validate_pipeline.py     # Verify data integrity
├── data/                            # Data directory (large files gitignored)
│   ├── raw/                         # Raw data sources
│   │   ├── finbas/                 # Finbas market data
│   │   └── serrano/                # Serrano accounting data
│   ├── intermediate/                # Intermediate processing outputs
│   ├── processed/                   # Final processed datasets
│   └── mappings/                    # ISIN-ORGNR mappings
├── results/                         # Analysis results
│   ├── inputs/                      # P-Tree input matrices
│   ├── models/                      # Trained models & summaries
│   ├── evaluation/                  # Performance metrics
│   └── visualizations/              # Figures and tables
├── notebooks/                       # Jupyter notebooks for exploration
├── docs/                            # Documentation
└── archive/                         # Archived experimental work

```

## Key Results

The analysis evaluates three scenarios:

| Scenario | Description | Test Sharpe Ratio | Annualized Return |
|----------|-------------|-------------------|-------------------|
| **A: Full Sample** | Single model on entire period | 1.82 | 10.07% |
| **B: Time-Split** | Train: early, Test: late | 0.27 | 1.35% |
| **C: Reverse Split** | Train: late, Test: early | 0.24 | 2.98% |

**Key Finding:** Scenario A demonstrates strong in-sample performance, while out-of-sample scenarios (B & C) show the challenges of predicting factor performance across different time periods in the Swedish market.

## Installation

### Prerequisites

- **Python 3.11+** with packages:
  - pandas, numpy, scipy
  - jupyter (for notebooks)
- **R 4.0+** with packages:
  - data.table
  - PTree (custom package for P-Tree methodology)
- **Git** for version control

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd PTrees
```

2. Set up Python environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install pandas numpy scipy jupyter
```

3. Install R dependencies:
```R
install.packages("data.table")
# Install PTree package (instructions depend on package source)
```

## Usage

### Data Preparation Pipeline

The data preparation pipeline processes raw market and accounting data:

```bash
# Step 1: Process Finbas market data
python src/data_preparation/1_process_finbas.py

# Step 2: Process Serrano accounting data
python src/data_preparation/2_process_serrano_accounting.py

# Step 3: Build ISIN-ORGNR mapping
python src/data_preparation/3_build_isin_orgnr_mapping_LSEG.py

# Step 4: Merge mappings
python src/data_preparation/4_merge_mappings.py

# Step 5: Merge datasets
python src/data_preparation/5_merge_datasets.py

# Step 6: Prepare final P-Tree dataset
python src/data_preparation/6_prepare_ptree_dataset.py

# Optional: Validate pipeline
python src/validation/validate_pipeline.py
```

### P-Tree Analysis

Run the complete P-Tree analysis pipeline:

```bash
# Step 1: Prepare inputs
Rscript src/analysis/01_prepare_inputs.R

# Step 2: Train P-Tree models (Scenarios A, B, C)
Rscript src/analysis/02_train_ptree.R

# Step 3: Evaluate model performance
Rscript src/analysis/03_evaluate_model.R

# Step 4: Generate visualizations
Rscript src/analysis/04_visualize_results.R
```

Results will be saved in the `results/` directory.

## Data Sources

1. **Finbas**: Daily market data for Swedish stocks (prices, volume, market cap)
   - Filtered to SEK-quoted stocks with SE ISINs
   - Single deterministic row per (ISIN, date)

2. **Serrano**: Annual accounting data from Swedish company reports
   - Balance sheet and income statement items
   - Financial ratios (nyckeltal)
   - Merged via ORGNR (Swedish company registration number)

3. **LSEG**: London Stock Exchange Group data for ISIN-ORGNR mapping

## Firm Characteristics

The analysis uses 44 firm characteristics across six categories:

- **Momentum** (8): MOM1M, MOM6M, MOM12M, MOM36M, MOM60M, SEAS1A, CHTX, DEPR
- **Value** (8): BM, EP, SP, CFP, CASH, CASHDEBT, LEV, SGR
- **Investment** (10): AGR, GMA, LGR, ACC, PCTACC, NOA, CINVEST, GRLTNOA, CHCSHO, NI, CHPM
- **Profitability** (6): ROA, ROE, ATO, PM, OP, RNA
- **Intangibles** (1): HIRE
- **Frictions** (11): ZEROTRADE, BASPREAD, DOLVOL, ILL, MAXRET, SVAR, STD_DOLVOL, TURN, STD_TURN, ME

Complete definitions and construction logic are documented in `src/data_preparation/CHARACTERISTICS.md`.

**Note:** BETA and RVAR_CAPM are implemented but currently excluded from the analysis as they are placeholders (not yet computed with market model regression).

## Key Features

- **Publication Lag**: 6-month lag applied to accounting variables to ensure data availability
- **As-of Joins**: Proper temporal alignment between market and accounting data
- **Cross-sectional Ranking**: Characteristics normalized to [-1, 1] within each month
- **Value Weighting**: Portfolios weighted by lagged market capitalization
- **Safe Division**: Robust handling of missing values and extreme ratios

## Validation

The pipeline includes comprehensive validation:
- As-of join integrity verification
- Monthly aggregation correctness
- Publication lag logic validation
- Final dataset integrity checks

Run validation with:
```bash
python src/validation/validate_pipeline.py
```

## Results Files

Key output files in `results/`:

- `models/all_scenarios_summary.csv`: Summary statistics for all scenarios
- `models/scenario_*_summary.csv`: Individual scenario results
- `models/scenario_*_tree.txt`: Tree structure for each model
- `models/scenario_*_factor.csv`: Factor returns over time
- `models/scenario_*_leaf_portfolios.csv`: Leaf node portfolio compositions
- `visualizations/`: Figures and tables for publication

## Known Limitations

- Beta and idiosyncratic variance (CAPM/FF3) are currently placeholders (not computed)
- ZEROTRADE has low coverage due to high trading activity in Swedish market
- Share counts approximated via market_cap/price where explicit data unavailable
- No winsorization applied; extreme values handled via ranking

## References

Bryzgalova, S., Huang, J., & Julliard, C. (2023). Bayesian solutions for the factor zoo: We just ran two quadrillion models. *Journal of Finance*, 78(1), 487-557.


**Last Updated:** December 2025
