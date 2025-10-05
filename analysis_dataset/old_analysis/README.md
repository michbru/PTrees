# Old Analysis (DO NOT USE)

## ⚠️ This folder contains superseded analysis with wrong parameters

**Use `../final_ptree_analysis/` instead!**

---

## Why This is Old

### Problems with this analysis:
1. **Overfitting:** min_leaf_size=3 (too aggressive for 300 stocks/month)
2. **Wrong parameters:** equal_weight=TRUE, num_cutpoints=10 (doesn't match paper)
3. **Look-ahead bias:** Earlier versions used current return to predict itself
4. **Unrealistic results:** Sharpe 2.53 (too good to be true)

### What superseded it:
→ `../final_ptree_analysis/` with Sharpe 1.20 (realistic, correct parameters)

---

## Contents

```
old_analysis/
├── data/                        # Raw Finbas data
├── scripts/                     # Data collection pipeline
│   ├── 1_extract_isins_for_lseg.py
│   ├── 2_pull_lseg_simple.py
│   └── 3_build_final_dataset.py
├── results/                     # Intermediate data
│   ├── ptrees_final_dataset.csv         (still used as input!)
│   ├── ptree_outputs/                   (WRONG - overfitted)
│   └── other intermediate files
└── run_pipeline.py              # Old pipeline script
```

---

## What to Use from Here

**Only ONE file is still used:**
✅ `results/ptrees_final_dataset.csv` - Input for final analysis
   - This is the merged dataset (Finbas + LSEG)
   - Used by `../final_ptree_analysis/scripts/1_prepare_data_relaxed.py`

**Everything else is superseded!**

---

## For Reference Only

This folder is kept for:
- Understanding project evolution
- Seeing what didn't work (overfitting)
- Data collection scripts (may be reused if pulling fresh data)

**Do NOT use results from here for publication or analysis!**

---

## Correct Analysis Location

→ `../final_ptree_analysis/`
→ See `../README.md` for overview
→ See `../docs/FINAL_ANALYSIS_SUMMARY.md` for findings
