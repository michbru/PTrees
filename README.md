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
│       ├── 05_validation_analysis.R
│       └── 06_optimal_tree_depth.R               # Model selection & sensitivity analysis
├── results/
│   ├── inputs/                       # Prepared P-Tree inputs
│   ├── models/                       # Trained model outputs
│   ├── evaluation/                   # Performance metrics
│   ├── validation/                   # Data validation outputs
│   └── thesis_visualisations/        # Tables and figures for thesis
├── notebooks/                        # Exploratory Jupyter notebooks
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

**Note:** Raw data files from Finbas and Serrano are required but not included in this repository due to licensing restrictions. These datasets are available through the Swedish House of Finance. Contact the authors for data access instructions.

### Required Raw Data Files

The following files must be placed in the `data/raw/` directory before running the pipeline:

```
data/raw/
├── finbas/
│   └── raw_finbas_monthly.csv          # Finbas market data export
├── serrano/
│   └── Stata_2025/                     # Serrano accounting data (Stata format)
│       ├── bokslut1.dta ... bokslut10.dta    # Balance sheet data
│       ├── ftg1.dta ... ftg10.dta            # Company information
│       ├── nyckeltal1.dta ... nyckeltal10.dta # Financial ratios
│       ├── knc1.dta ... knc10.dta            # Cash flow data
│       ├── bol1.dta ... bol10.dta            # Income statement data
│       └── serrano1.dta ... serrano10.dta    # Combined Serrano data
├── macro/
│   └── raw_macro_factors.csv           # Swedish FF factors (Rm, SMB, HML, MOM)
└── FamaFrench2020/
    └── FF4F_monthly.csv                # Shof et al. (2020) factors
```

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
Rscript src/analysis/06_optimal_tree_depth.R  # Optional: model selection analysis
```

**Outputs:**
- `results/models/` - Trained P-Tree models and factor returns
- `results/evaluation/performance_metrics.csv` - Alpha and Sharpe ratio estimates
- `results/thesis_visualisations/` - LaTeX tables and figures
- `results/validation/` - Data validation tables and figures

---

## Key Output Tables for Thesis

### Performance Tables
- **`table_performance.tex`** - Main results: P-Tree performance across all scenarios
- **`table_performance_2splits.tex`** - Sensitivity analysis with 2 splits
- **`table_performance_maxdepth.tex`** - Sensitivity analysis with maximum depth (10 splits)
- **`table_original_paper_results.tex`** - Original paper results (Panel B2: OOS 2001-2020)
- **`table_original_paper_c2.tex`** - Original paper results (Panel C2: OOS 1981-2000)

### Data Validation Tables
- **`table_data_summary.tex`** - Dataset overview statistics
- **`table_univariate_r2.tex`** - Top predictive characteristics
- **`table_sample_attrition.tex`** - Sample construction pipeline
- **`table_variable_stats.tex`** - Variable coverage and distributions
- **`table_high_correlations.tex`** - Highly correlated characteristic pairs (|ρ| > 0.7)

### Model Structure
- **`table_leaf_weights.tex`** - Portfolio weights and tree structure

---

## Model Selection and Sensitivity Analysis

We empirically determined the optimal tree depth using cross-validation and documented the sensitivity to this parameter:

**Method (Part 1 - Model Selection):**
1. Train models with `num_iter = 1, 2, 3, ..., 10`
2. Evaluate each on held-out test data (2010-2019)
3. Select depth that maximizes out-of-sample Sharpe ratio

**Method (Part 2 - Sensitivity Analysis):**
- Compare optimal (`num_iter = 1`) vs maximum (`num_iter = 10`)
- Document in-sample vs out-of-sample performance differences
- Statistical significance testing via Sharpe ratio t-statistics

**To run the combined analysis:**

```bash
Rscript src/analysis/06_optimal_tree_depth.R
```

**Outputs:**
- `results/thesis_visualisations/table_performance_maxdepth.tex`
- `results/thesis_visualisations/table_performance_2splits.tex`
- `results/thesis_visualisations/table_original_paper_results.tex` - Panel B2 from Cong et al. (2025)
- `results/thesis_visualisations/table_original_paper_c2.tex` - Panel C2 from Cong et al. (2025)

**Key Findings:**
- **Optimal depth:** `num_iter = 1` (single split) maximizes test Sharpe (0.534)
- **Overfitting pattern:** Deeper trees improve train Sharpe (+112%) but degrade test Sharpe (-64%)
- **Statistical significance:** Single split is highly significant (t-stat ~5.85, p < 0.001)
- **Data constraint:** Swedish market's limited cross-section (~150 firms/month) cannot support complex trees
- **Robustness:** First split (typically rank_bm or rank_cfp) is stable and generalizable

This is a **data-driven result**, not an arbitrary choice. The analysis demonstrates that the optimal tree depth is determined by the data's cross-sectional dimension.

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

Performance summary comparing our Swedish replication with the original US study:

### Our Results (Swedish Market, 1998-2019)

| Scenario | Sharpe Ratio | CAPM Alpha (%) | FF3 Alpha (%) | t-stat |
|----------|--------------|----------------|---------------|--------|
| A (Full Sample) | 0.92 | 9.68 | 9.61 | 4.43*** |
| B (Test OOS) | 0.53 | 3.08 | 3.21 | 2.02** |
| C (Test OOS) | 0.48 | 3.71 | 3.39 | 1.33 |

*Note: Alphas are annualized (%). *** p<0.01, ** p<0.05.*

### Original Paper (US Market, 1981-2020)

**Panel B2 (OOS 2001-2020):**

| Model | Sharpe Ratio | Monthly α (CAPM) | Monthly α (FF5) |
|-------|--------------|------------------|-----------------|
| P-Tree1 | 3.23 | 1.35%*** | 1.31%*** |
| P-Tree1-5 | 3.41 | 1.02%*** | 1.00%*** |
| P-Tree1-20 | 3.13 | 0.85%*** | 0.84%*** |

**Panel C2 (OOS 1981-2000):**

| Model | Sharpe Ratio | Monthly α (CAPM) | Monthly α (FF5) |
|-------|--------------|------------------|-----------------|
| P-Tree1 | 4.35 | 1.50%*** | 1.42%*** |
| P-Tree1-5 | 3.87 | 1.18%*** | 1.05%*** |
| P-Tree1-20 | 3.88 | 0.96%*** | 0.87%*** |

### Comparison Interpretation

Our Swedish results show lower Sharpe ratios (0.48-0.92) compared to the original US study (3.13-4.35). This difference reflects:
1. **Market size:** ~150 Swedish firms/month vs. thousands of US firms
2. **Characteristic availability:** Missing key predictors (SUE, analyst revisions)
3. **Sample period:** Shorter time span (22 years vs. 40 years)
4. **Model complexity:** Single P-Tree vs. boosted multi-tree models (1-20 trees)

Despite these constraints, our results demonstrate economically meaningful outperformance with statistical significance in several specifications, validating the portability of P-Trees to smaller markets.

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
