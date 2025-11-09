# Notebooks

This folder contains Jupyter notebooks used for data exploration and preprocessing.

## Contents

### `data_preprocessing.ipynb`

**Purpose:** Data preprocessing and macro variable construction

**What it does:**
1. Loads Fama-French 4-factor data (from `data/FamaFrench2020/`)
2. Calculates rolling volatility metrics
3. Merges with inflation data (CPIF - Swedish Consumer Price Index)
4. Creates `macro_variables.csv` with date index
5. Basic exploratory analysis of stock data

**Output:**
- Previously generated `macro_variables.csv` (now deprecated)
- The active file used by all scripts is `data/macro_variables_with_dates.csv`

**Note:** This notebook was used during initial data preparation. The final macro variables file used by all analysis scripts is located at `data/macro_variables_with_dates.csv`.

---

## Usage

To run the notebook:
```bash
jupyter notebook notebooks/data_preprocessing.ipynb
```

Or use VS Code, JupyterLab, or any other notebook environment.

---

**Last Updated:** 2025-11-09
