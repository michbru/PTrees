# P-Trees: Asset Pricing Factors for the Swedish Stock Market

**BE451 - Degree Project in Finance, Fall 2025**  
Stockholm School of Economics

## Authors

- Michael Brusis 
- Erik Jin 

**Supervisor:** [Maíra Sontag González]

---

## Abstract

This repository contains the replication files for our B.Sc. thesis applying the Portfolio Trees (P-Trees) methodology of Cong et al. (2025) to the Swedish stock market. We construct machine-learning-based pricing factors using firm characteristics and evaluate their out-of-sample performance against traditional Fama-French factors.

---

## Repository Structure

```
PTrees/
├── data/
│   ├── raw/                          # Raw input data (not tracked)
│   │   ├── finbas/                   # Finbas market data
│   │   ├── serrano/                  # Serrano accounting data
│   │   ├── macro/                    # Fama-French factors (Swedish)
│   │   └── FamaFrench2020/           # FF factors from Shof et al. (2020)
│   ├── intermediate/                 # Processed intermediate files
│   │   ├── finbas/                   # Cleaned Finbas data
│   │   └── serrano/                  # Cleaned Serrano data
│   ├── mappings/                     # ISIN-ORGNR mapping files
│   │   ├── automated/                # Automated mappings (LSEG)
│   │   └── manual/                   # Manual corrections
│   └── processed/                    # Final analysis-ready datasets
├── src/
│   ├── data_preparation/             # Python scripts for data processing
│   │   ├── 1_process_finbas.py
│   │   ├── 2_process_serrano_accounting.py
│   │   ├── 3_build_isin_orgnr_mapping_LSEG.py
│   │   ├── 4_merge_mappings.py
│   │   ├── 5_merge_datasets.py
│   │   └── 6_prepare_ptree_dataset.py
│   └── analysis/                     # R scripts for P-Tree analysis
│       ├── 01_prepare_inputs.R
│       ├── 02_train_ptree.R
│       ├── 03_evaluate_model.R
│       ├── 04_visualize_results.R
│       └── 05_validation_analysis.R
├── results/
│   ├── inputs/                       # Prepared P-Tree inputs
│   ├── models/                       # Trained model outputs
│   ├── evaluation/                   # Performance metrics
│   ├── validation/                   # Data validation outputs
│   └── thesis_visualisations/        # Tables and figures for thesis
├── notebooks/                        # Exploratory Jupyter notebooks
├── docs/                             # Documentation and references
└── archive/                          # Original PTree package source
```

---

## Data Sources

| Source | Description | Access |
|--------|-------------|--------|
| **Finbas** | Swedish stock market data (prices, returns, market cap) | Swedish House of Finance |
| **Serrano** | Accounting data for Swedish firms | Swedish House of Finance |
| **Fama-French Factors** | Swedish market factors (Rm-Rf, SMB, HML) | Shof et al. (2020) |
| **LSEG Workspace** | ISIN-ORGNR identifier mapping | SSE Library |

**Note:** Raw data files are not included in this repository due to licensing restrictions and file size. Contact the authors for data access instructions.

---

## Requirements

### Python (Data Preparation)
- Python 3.9+
- pandas >= 1.5.0
- numpy >= 1.21.0

### R (Analysis)
- R 4.0+
- data.table
- PTree (from: `devtools::install_github("bpf_ptree/PTree")`)
- ggplot2
- sandwich
- lmtest
- xtable

---

## Replication Instructions

### Step 1: Data Preparation (Python)

Run the data preparation scripts in order:

```bash
# From repository root
python src/data_preparation/1_process_finbas.py
python src/data_preparation/2_process_serrano_accounting.py
python src/data_preparation/3_build_isin_orgnr_mapping_LSEG.py
python src/data_preparation/4_merge_mappings.py
python src/data_preparation/5_merge_datasets.py
python src/data_preparation/6_prepare_ptree_dataset.py
```

**Inputs:**
- `data/raw/finbas/raw_finbas_monthly.csv`
- `data/raw/serrano/Stata_2025/*.dta`
- `data/raw/macro/raw_macro_factors.csv`

**Output:**
- `data/processed/ptree_dataset_monthly.csv`

### Step 2: P-Tree Analysis (R)

Run the R analysis scripts in order:

```bash
# From repository root
Rscript src/analysis/01_prepare_inputs.R
Rscript src/analysis/02_train_ptree.R
Rscript src/analysis/03_evaluate_model.R
Rscript src/analysis/04_visualize_results.R
Rscript src/analysis/05_validation_analysis.R
```

**Outputs:**
- `results/models/` - Trained P-Tree models and factor returns
- `results/evaluation/performance_metrics.csv` - Alpha and Sharpe ratio estimates
- `results/thesis_visualisations/` - LaTeX tables and figures

---

## Methodology

### Scenarios

| Scenario | Training Period | Test Period | Purpose |
|----------|-----------------|-------------|---------|
| A | 1998-2019 | - | Full-sample (in-sample) |
| B | 1998-2009 | 2010-2019 | Out-of-sample forward |
| C | 2010-2019 | 1998-2009 | Out-of-sample reverse |

### P-Tree Hyperparameters

Following Cong et al. (2025):

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_depth` | 10 | Maximum tree depth |
| `min_leaf_size` | 3 | Minimum stocks per leaf |
| `num_cutpoints` | 4 | Split thresholds (quintiles) |
| `gamma` | 1e-4 | Covariance shrinkage |
| `lambda` | 1e-5 | Factor covariance shrinkage |
| `equal_weight` | FALSE | Value-weighted portfolios |

### Firm Characteristics (33 variables)

The model uses cross-sectionally ranked firm characteristics including:

**Momentum-based:**
- MOM1M, MOM6M, MOM12M, MOM36M, MOM60M (various momentum horizons)
- SEAS1A (seasonal momentum)

**Value-based:**
- BM (book-to-market), EP (earnings-to-price), SP (sales-to-price), CFP (cash-flow-to-price)

**Profitability:**
- ROE, ROA, GMA (gross profitability), ATO (asset turnover), PM (profit margin)
- OP (operating profitability)

**Investment/Growth:**
- AGR (asset growth), CHCSHO (share issuance), HIRE (employee growth)
- LGR (debt growth), SGR (sales growth)

**Financial Health:**
- LEV (leverage), CASHDEBT (cash to debt), CASH (cash to assets)
- QUICK (quick ratio)

**Size:**
- ME (market equity)

Characteristics are lagged appropriately:
- Accounting data: 6-month publication lag
- Market data: 1-month lag (predicting t+1 returns)

---

## Output Files

### Tables (LaTeX)

| File | Description |
|------|-------------|
| `table_data_summary.tex` | Dataset summary statistics |
| `table_performance_metrics.tex` | Model performance (Sharpe, Alpha) |
| `table_univariate_r2.tex` | Characteristic predictive power |
| `table_sample_attrition.tex` | Sample construction pipeline |

### Model Outputs

| File | Description |
|------|-------------|
| `scenario_X_1_factor.csv` | Monthly factor returns (training) |
| `scenario_X_test_1_factor.csv` | Monthly factor returns (test) |
| `scenario_X_model.rds` | Trained P-Tree model object |
| `scenario_X_summary.csv` | Performance summary |
| `scenario_X_trees.txt` | Tree structure |

---

## Key Results

Performance summary from `results/evaluation/performance_metrics.csv`:

| Scenario | Sharpe Ratio | CAPM Alpha (Monthly) | FF3 Alpha (Monthly) | t-stat |
|----------|--------------|----------------------|---------------------|--------|
| A (Full) | 0.92 | 0.81% | 0.80% | 4.43*** |
| B (Train) | 0.90 | 0.85% | 0.84% | 3.43*** |
| B (Test) | 0.53 | 0.26% | 0.27% | 2.02** |
| C (Train) | 1.43 | 0.80% | 0.80% | 5.35*** |
| C (Test) | 0.48 | 0.31% | 0.28% | 1.21 |

*Note: *** p<0.01, ** p<0.05. T-statistics use Newey-West standard errors (12 lags).*

**Key Finding:** The P-Tree model generates statistically significant alphas in-sample (Scenarios A, B-Train, C-Train), but out-of-sample performance (B-Test, C-Test) is more modest, consistent with the limited cross-section of Swedish stocks compared to the US market studied in Cong et al. (2025).

---

## References

Cong, L. W., Feng, G., He, J., & He, X. (2025). Growing the efficient frontier on panel trees. *Journal of Financial Economics*, 167, 104024.

Shof, S., et al. (2020). Swedish Fama-French Factors. Working Paper.

---

## AI Disclosure

The following AI tools were used in this project:
- **GitHub Copilot / Claude**: Code assistance, debugging, and documentation formatting
- **Usage**: Grammar checking, code refactoring suggestions, and LaTeX table generation

All analytical decisions, methodology choices, and interpretations are the authors' own work.

---

## License

This project is for academic purposes only. Data sources are subject to their respective licensing terms.

---

## Contact

For questions about this replication package, please contact:
- Michael Brusis: [25895@student.hhs.se]
- Erik Jin: [26057@student.hhs.se]
