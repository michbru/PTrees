# PTrees Analysis Dataset

## Overview
This project builds a comprehensive dataset of Swedish public companies (1997-2022) by combining market data from Finbas with fundamental data from LSEG (formerly Refinitiv). The final dataset contains **rich firm characteristics** including traditional factors (Size, Value, Momentum) and extended metrics (profitability ratios, financial health, growth metrics).

## Project Structure

```
analysis_dataset/
├── README.md                          # This documentation
├── run_pipeline.py                    # One-click pipeline runner
├── data/                              # Source data
│   └── finbas_market_data.csv        # Market data from Finbas
├── scripts/                          # Processing pipeline (run in order)
│   ├── 1_extract_isins_for_lseg.py   # Extract ISINs for API requests
│   ├── 2_pull_lseg_simple.py         # Pull fundamental data from LSEG API
│   ├── 3_build_final_dataset.py      # Build comprehensive dataset with all characteristics
│   ├── data_auditor.py               # Generate quality report
│   └── test_auth_simple.py           # Test LSEG API authentication
└── results/                          # Output files
    ├── ptrees_final_dataset.csv      # 🎯 MAIN RESULT: Analysis-ready dataset
    ├── isin_target_list_for_lseg.csv # List of ISINs for LSEG requests
    ├── lseg_basic_fundamentals.csv   # Basic fundamentals from LSEG
    └── lseg_extended_fundamentals.csv # Extended fundamentals from LSEG
```

## Quick Start

### Prerequisites
- Python 3.11+ with virtual environment
- LSEG API credentials (configured in `../lseg-data.config.json`)
- Required packages: `pandas`, `numpy`, `requests`

### Complete Pipeline (Recommended)
```bash
# Run the complete pipeline with one command
python run_pipeline.py
```

### Manual Step-by-Step
```bash
# 1. Extract unique ISINs from market data
python scripts/1_extract_isins_for_lseg.py

# 2. Pull fundamental data from LSEG API
python scripts/2_pull_lseg_simple.py

# 3. Build final comprehensive dataset
python scripts/3_build_final_dataset.py

# 4. Generate quality report
python scripts/data_auditor.py
```

**Final Output**: `results/ptrees_final_dataset.csv`

## Final Dataset: Rich Firm Characteristics

### Dataset Overview
- **Observations**: ~98,000 monthly observations
- **Companies**: 1,134 unique Swedish public companies
- **Period**: January 1997 - December 2022 (26 years)
- **Characteristics**: 19+ firm characteristics across 6 categories

### Characteristic Categories

#### 1. Size & Valuation (100% coverage)
- `market_cap`: Market capitalization
- `book_to_market`: Book-to-market ratio
- `price`: Stock price

#### 2. Market-Based Factors (85-99% coverage)
- `momentum_12m`: 12-month price momentum
- `volatility_12m`: 12-month price volatility
- `turnover`: Stock turnover ratio

#### 3. Profitability Ratios (69-93% coverage)
- `roa`: Return on assets
- `cfp_ratio`: Cash flow-to-price ratio
- `ep_ratio`: Earnings-to-price ratio (when available)

#### 4. Valuation Ratios (69-93% coverage)
- `sp_ratio`: Sales-to-price ratio
- `price_to_assets`: Price-to-assets ratio

#### 5. Investment & Growth (69-81% coverage)
- `sales_growth`: Year-over-year sales growth
- `asset_turnover`: Asset turnover ratio
- `capex_to_assets`: Capital expenditure intensity

#### 6. Financial Health (93% coverage)
- `debt_to_equity`: Debt-to-equity ratio
- `asset_quality`: Asset quality metric (1 - COGS/Revenue)

## API Authentication

### LSEG API Setup

⚠️ **SECURITY WARNING**: Never commit API credentials to git!

1. Create `../lseg-data.config.json` (this file is git-ignored):
```json
{
  "sessions": {
    "platform": {
      "rdp": {
        "app-key": "your-app-key",
        "username": "your-username",
        "password": "your-password",
        "grant_type": "password",
        "scope": "trapi"
      }
    }
  }
}
```

2. Test authentication:
```bash
python scripts/test_auth_simple.py
```

**Security Notes**:
- ✅ `lseg-data.config.json` is automatically git-ignored
- ✅ Scripts handle "Session quota reached" errors automatically
- ⚠️ Never share or commit API credentials
- ⚠️ Keep credentials in parent directory (outside version control)

## Data Quality Summary

### Coverage Excellence
- **13 characteristics**: Excellent coverage (≥90%)
- **3 characteristics**: Good coverage (75-89%)
- **3 characteristics**: Moderate coverage (50-74%)

### Recommended Usage
- **Primary analysis**: Use excellent coverage characteristics
- **Robustness checks**: Include good coverage characteristics
- **Subsample analysis**: Consider post-2010 for fundamental-dependent studies

## Usage for P-Tree Analysis

### Loading the Dataset
```python
import pandas as pd

# Load the final dataset
df = pd.read_csv('results/ptrees_final_dataset.csv')
df['date'] = pd.to_datetime(df['date'])

print(f"Dataset: {len(df):,} observations")
print(f"Companies: {df['isin'].nunique()}")
print(f"Characteristics: {len(df.columns)}")
```

### Feature Categories for P-Trees
```python
# Traditional factors (excellent coverage)
traditional_factors = ['market_cap', 'book_to_market', 'momentum_12m', 'volatility_12m', 'turnover']

# Profitability factors (good-excellent coverage)
profitability_factors = ['roa', 'cfp_ratio', 'sp_ratio']

# Financial health factors (excellent coverage)
financial_health = ['debt_to_equity', 'asset_quality']

# Growth factors (good coverage)
growth_factors = ['sales_growth', 'asset_turnover']

# All characteristics for rich P-Tree models
all_characteristics = traditional_factors + profitability_factors + financial_health + growth_factors
```

## Quality Report

Run the data auditor for a comprehensive quality assessment:
```bash
python scripts/data_auditor.py
```

This generates a publication-ready report showing:
- Coverage statistics by characteristic group
- Temporal coverage analysis
- Data quality checks
- Recommendations for analysis

## Troubleshooting

### Common Issues
- **LSEG "Session quota reached"**: Automatically handled by scripts
- **Missing data files**: Run `python run_pipeline.py` to rebuild everything
- **Unicode errors**: All scripts use ASCII-only output for Windows compatibility

### Dependencies
```bash
pip install pandas numpy requests
```

## Research Applications

This dataset is optimized for:
- **P-Tree modeling** with rich feature sets
- **Traditional factor models** (Fama-French, Carhart, etc.)
- **Cross-sectional asset pricing** studies
- **Corporate finance** research
- **Swedish equity market** analysis

## File Sizes
- `ptrees_final_dataset.csv`: ~50 MB (comprehensive dataset)
- `lseg_basic_fundamentals.csv`: ~2 MB
- `lseg_extended_fundamentals.csv`: ~2 MB
- `data/finbas_market_data.csv`: ~15 MB

---
**Status**: Production Ready ✅
**Last Updated**: September 2025
**Coverage**: 1997-2022 (26 years)
**Quality**: Publication-ready with comprehensive characteristics