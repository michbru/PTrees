# P-Tree Analysis - Swedish Stock Market

---

## Structure

```
analysis_dataset/
│
├── final_ptree_analysis/        ✅ FINAL ANALYSIS (USE THIS)
│   ├── README.md                    Complete documentation
│   ├── data/                        Input data
│   ├── scripts/                     Analysis scripts
│   ├── results/                     Final results ⭐
│   ├── FINAL_ANALYSIS_SUMMARY.md    Detailed findings
│   └── INVESTIGATION_FINDINGS.md    Bug investigation
│
└── old_analysis/                ❌ OLD (Ignore - overfitted)
    ├── README.md                    Why to ignore this
    ├── data/                        Raw data
    ├── scripts/                     Data pipeline
    └── results/                     Old results
```

---

## Results

**Location:** `final_ptree_analysis/results/ptree_factors.csv`

**Performance:**
- Sharpe Ratio: 1.20
- Win Rate: 67.5%
- Period: 1997-2022 (311 months)

---

## Quick Start

### 1. See Results
```bash
cd final_ptree_analysis/results
# Open ptree_factors.csv
```

### 2. Understand Analysis
```bash
cd final_ptree_analysis
# Read README.md
# Read FINAL_ANALYSIS_SUMMARY.md
```

### 3. Replicate
```bash
cd final_ptree_analysis/scripts
python 1_prepare_data_relaxed.py
Rscript 2_run_ptree_attempt2.R
```

---

## What's What?

### ✅ final_ptree_analysis/
**CURRENT WORK** - Everything you need
- Self-contained (all data, scripts, results, docs)
- Correct parameters (min_leaf_size=10, value-weighted)
- Sharpe 1.20 (realistic)
- **Read its README for full details**

### ❌ old_analysis/
**ARCHIVE** - Don't use
- Overfitted results (Sharpe 2.53)
- Wrong parameters
- Look-ahead bias in early versions
- Kept for reference only

---

## Key Finding

P-Trees achieved Sharpe 1.20 on Swedish data, representing the market portfolio (no splits found).

**Why no splits?**
- Small market: ~300 stocks/month
- Few features: 19 characteristics
- Tree defaults to market portfolio

**This is realistic** for small markets with limited characteristics.

---

## Documentation

Everything is in `final_ptree_analysis/`:
- **README.md** - Technical documentation
- **FINAL_ANALYSIS_SUMMARY.md** - Complete findings
- **INVESTIGATION_FINDINGS.md** - Bug investigation

---

## Summary

✅ **Use:** `final_ptree_analysis/`
❌ **Ignore:** `old_analysis/`
📊 **Results:** `final_ptree_analysis/results/ptree_factors.csv`
