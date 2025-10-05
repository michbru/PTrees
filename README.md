# P-Tree Analysis on Swedish Stock Market

**A project applying the P-Tree methodology from Cong et al. (2024) to Swedish stock market data.**

---

## 🚀 Quick Start

**New to this project? Start here:**
1. Read **`PROJECT_STATE.md`** ← Complete project overview, workflow, and current status
2. Check **`PTREE_ANALYSIS_SUMMARY.md`** ← Summary of the 100% win rate issue
3. Review **`analysis_dataset/README.md`** ← Dataset documentation

## 📁 Key Files

| File | Purpose |
|------|---------|
| **`PROJECT_STATE.md`** | **Main entry point** - Full project state, numbered workflow, current issues |
| `PTREE_ANALYSIS_GUIDE.md` | Original analysis guide (now superseded by PROJECT_STATE.md) |
| `PTREE_ANALYSIS_SUMMARY.md` | Summary of invalid results issue |
| `analysis_dataset/README.md` | Dataset documentation and pipeline |

## 🔄 Workflow Overview

```
1. Data Collection      → scripts/1_extract_isins_for_lseg.py
                        → scripts/2_pull_lseg_simple.py
                        → scripts/3_build_final_dataset.py

2. P-Tree Attempt 1     → scripts/4_prepare_ptree_data.py
   (Strict NA)          → scripts/5_run_ptree_swedish.R
                        → ⚠️ ISSUE: Factors only 2011-2022

3. P-Tree Attempt 2     → ptree_attempt2/scripts/1_prepare_data_relaxed.py
   (Relaxed NA)         → ptree_attempt2/scripts/2_run_ptree_attempt2.R
                        → ⚠️ ISSUE: 100% win rate (invalid results)
```

See **`PROJECT_STATE.md`** for detailed step-by-step workflow.

## ✅ Current Status

**ROOT CAUSE IDENTIFIED:** Look-ahead bias in `return_1m` characteristic
- Using current month's return to predict itself → 100% win rate
- **Solution:** Remove or properly lag `return_1m` characteristic
- **See:** `INVESTIGATION_FINDINGS.md` for detailed analysis
- **Next:** Implement fix and re-run analysis

## 📊 Dataset

- **Source:** Swedish stock market (Finbas + LSEG)
- **Period:** 1997-2022 (26 years)
- **Size:** 102,823 observations from 1,177 stocks
- **Characteristics:** 19 factors (Size, Value, Momentum, Profitability, etc.)

## 🛠️ Setup

```bash
# 1. Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 2. Install Python dependencies (if needed)
pip install pandas numpy pyarrow matplotlib seaborn

# 3. Install R packages (in R)
install.packages(c("arrow", "rpart", "ranger"))

# 4. Install P-Tree package (in R)
install.packages("PTree-2501/PTree", repos = NULL, type = "source")
```

## 📈 Results & Diagnostics

```bash
# Visualize latest results
python analysis_dataset/scripts/6_visualize_results.py

# Run diagnostics
python analysis_dataset/scripts/7_diagnostic_analysis.py
```

## 📚 References

- **Paper:** Cong, Feng, He & He (2024). "Growing the efficient frontier on panel trees." *Journal of Financial Economics*.
- **Package:** `PTree-2501/PTree/` (R implementation)
- **Data:** Finbas (market) + LSEG/Refinitiv (fundamentals)

---

**For full context and next steps, read `PROJECT_STATE.md`** 📖
