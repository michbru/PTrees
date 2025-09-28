# PTrees Dataset Setup Instructions

## Quick Setup for New Users

### 1. Clone the Repository
```bash
git clone [repository-url]
cd PTrees/analysis_dataset
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install pandas numpy requests
```

### 3. Configure LSEG API Credentials

⚠️ **CRITICAL SECURITY STEP**

Create the file `../lseg-data.config.json` (in the PTrees root directory) with your LSEG credentials:

```json
{
  "sessions": {
    "platform": {
      "rdp": {
        "app-key": "YOUR_APP_KEY_HERE",
        "username": "YOUR_USERNAME_HERE",
        "password": "YOUR_PASSWORD_HERE",
        "grant_type": "password",
        "scope": "trapi"
      }
    }
  }
}
```

**IMPORTANT**:
- ✅ This file is automatically git-ignored
- ✅ Keep it in the parent directory (outside analysis_dataset/)
- ❌ NEVER commit API credentials to git
- ❌ NEVER share this file publicly

### 4. Test Your Setup
```bash
# Test LSEG API connection
python scripts/test_auth_simple.py

# If successful, run the complete pipeline
python run_pipeline.py
```

### 5. Expected Output
```
analysis_dataset/
└── results/
    ├── ptrees_final_dataset.csv      # 🎯 Your final dataset
    ├── isin_target_list_for_lseg.csv
    ├── lseg_basic_fundamentals.csv
    └── lseg_extended_fundamentals.csv
```

## Troubleshooting

### Common Issues

**"Session quota reached"**
- Solution: Scripts automatically handle this with `takeExclusiveSignOnControl`

**"Config file not found"**
- Check: `../lseg-data.config.json` exists in parent directory
- Check: File contains valid JSON with your credentials

**"Module not found"**
- Solution: Activate virtual environment and install dependencies

**Unicode errors (Windows)**
- Solution: All scripts use ASCII-only output for compatibility

### Getting Help

1. Check the main [README.md](README.md) for detailed documentation
2. Run `python scripts/data_auditor.py` for dataset quality report
3. Verify your file structure matches the expected layout

## Data Sources Required

- `data/finbas_market_data.csv`: Market data from Finbas (semicolon-separated)
- LSEG API access with valid credentials

---
**Ready to start? Run `python run_pipeline.py`** 🚀