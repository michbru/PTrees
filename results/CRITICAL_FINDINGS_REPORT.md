# CRITICAL FINDINGS REPORT
## P-Tree Analysis - Swedish Stock Market
## Date: 2025-10-29

---

## EXECUTIVE SUMMARY

**CRITICAL ISSUE IDENTIFIED:** Your paper reported incorrect results for Scenario B. The TRUE out-of-sample performance is significantly different from what was reported.

**Key Finding:** The model shows **strong asymmetric performance** - it works exceptionally well when trained on recent data and tested on old data (Scenario C), but performs modestly when trained on old data and tested on recent data (Scenario B).

---

## 1. CORRECTED RESULTS (TRUE OOS Performance)

### Scenario A: Full Sample (IN-SAMPLE)
- **Period:** 1997-09 to 2020-07 (275 months)
- **Data Type:** IN-SAMPLE
- **Sharpe Ratio:** 2.74
- **CAPM Alpha:** 21.84% per year (t-stat: 9.92)
- **FF3 Alpha:** 21.78% per year (t-stat: 9.82)

**Assessment:** Strong in-sample performance, as expected.

---

### Scenario B: Time Split (OUT-OF-SAMPLE)
**Training:** 1997-2009 | **Testing:** 2010-2020

#### What Your Paper Claimed:
- Sharpe Ratio: 4.21
- CAPM Alpha: 21.70% (t-stat: 11.29)

#### TRUE OOS Results:
- **Period:** 2010-01 to 2020-07 (127 months)
- **Data Type:** OUT-OF-SAMPLE ✓
- **Sharpe Ratio: 1.69** (61% LOWER than claimed!)
- **CAPM Alpha: 6.63%** (69% LOWER than claimed!)
- **t-statistic: 4.65** (59% LOWER than claimed!)

**CRITICAL:** Your paper was reporting results from the WRONG file or period!

#### Transaction Cost Adjusted Performance:
- **Gross Return:** 7.81% per year
- **Net Return (Medium TC):** -1.19% per year
- **Net Sharpe:** -0.28

**VERDICT:** **Strategy becomes UNPROFITABLE after transaction costs!**

---

### Scenario C: Reverse Split (OUT-OF-SAMPLE)
**Training:** 2010-2022 | **Testing:** 1997-2010

#### What Your Paper Claimed:
- Sharpe Ratio: 4.27
- CAPM Alpha: 26.58% (t-stat: 15.00)

#### TRUE OOS Results:
- **Period:** 1997-09 to 2009-12 (148 months)
- **Data Type:** OUT-OF-SAMPLE ✓
- **Sharpe Ratio: 3.11** (27% LOWER than claimed)
- **CAPM Alpha: 40.84%** (54% HIGHER than claimed!)
- **t-statistic: 8.82** (41% LOWER than claimed)

#### Transaction Cost Adjusted Performance:
- **Gross Return:** 38.69% per year
- **Net Return (Medium TC):** 29.69% per year
- **Net Sharpe:** 2.26

**VERDICT:** Exceptionally strong performance, even after costs!

---

## 2. KEY FINDINGS

### Finding 1: Asymmetric Temporal Performance

The model shows **dramatically different** performance depending on training/test direction:

| Scenario | Train Period | Test Period | OOS Alpha | OOS Sharpe |
|----------|-------------|-------------|-----------|------------|
| **B: Forward** | 1997-2009 | 2010-2020 | **6.6%** | **1.69** |
| **C: Reverse** | 2010-2022 | 1997-2010 | **40.8%** | **3.11** |

**Interpretation:**
- Model trained on **old data** doesn't work well on **new data** (6.6% alpha)
- Model trained on **new data** works VERY well on **old data** (40.8% alpha)

**Possible Explanations:**
1. **Market regime change:** Market structure changed significantly post-2010
2. **Data quality:** Early period (1997-2010) may have higher quality signals
3. **Volatility:** Early period includes dot-com crash (2001-2003) and financial crisis (2008-2009), which may be easier to predict
4. **Overfitting:** Model may be overfit to crisis periods

---

### Finding 2: Transaction Costs ELIMINATE Scenario B Profits

#### Scenario B (Forward Test) - Net Returns After Costs:

| Cost Scenario | Turnover | Annual Cost | Net Return | Net Sharpe |
|---------------|----------|-------------|------------|------------|
| Low TC | 50% | -6.0% | +1.8% | 0.42 |
| **Medium TC** | **100%** | **-9.0%** | **-1.2%** | **-0.28** |
| High TC | 150% | -12.0% | -4.2% | -0.98 |

**CRITICAL:** Under realistic assumptions (75 bps TC, 100% monthly turnover), the strategy is **UNPROFITABLE**.

#### Scenario C (Reverse Test) - Net Returns After Costs:

| Cost Scenario | Turnover | Annual Cost | Net Return | Net Sharpe |
|---------------|----------|-------------|------------|------------|
| Low TC | 50% | -6.0% | +32.7% | 2.49 |
| **Medium TC** | **100%** | **-9.0%** | **+29.7%** | **2.26** |
| High TC | 150% | -12.0% | +26.7% | 2.03 |

**Still highly profitable after costs.**

---

### Finding 3: Subperiod Analysis Shows High Variability

#### Scenario A (Full Sample) - Performance by Period:

| Period | Label | Sharpe | Alpha | t-stat |
|--------|-------|--------|-------|--------|
| 1997-2000 | Dot-com Boom | 3.33 | 27.5% | 6.09 |
| 2001-2003 | Dot-com Bust | **3.87** | **43.7%** | 7.05 |
| 2004-2007 | Pre-Crisis | 3.34 | 20.5% | 4.20 |
| 2008-2009 | **Financial Crisis** | **1.88** | 23.2% | 2.45 |
| 2010-2014 | Post-Crisis | 2.89 | 13.6% | 5.01 |
| 2015-2020 | Late Expansion | 2.60 | 12.9% | 6.23 |

**Observations:**
- **BEST** performance: 2001-2003 (Dot-com Bust) - 43.7% alpha
- **WORST** performance: 2008-2009 (Financial Crisis) - Still positive but lowest Sharpe (1.88)
- Performance **DECLINES OVER TIME**: 43.7% (2001-2003) → 12.9% (2015-2020)

#### Scenario B (OOS: 2010-2020) - Performance by Period:

| Period | Label | Sharpe | Alpha | t-stat |
|--------|-------|--------|-------|--------|
| 2010-2014 | Post-Crisis | 1.54 | 5.7% | 2.76 |
| 2015-2020 | Late Expansion | 2.05 | 7.5% | 4.13 |

**Observation:** Modest but consistent performance in both subperiods.

#### Scenario C (OOS: 1997-2010) - Performance by Period:

| Period | Label | Sharpe | Alpha | t-stat |
|--------|-------|--------|-------|--------|
| 1997-2000 | Dot-com Boom | 2.69 | 39.7% | 4.76 |
| 2001-2003 | **Dot-com Bust** | **3.35** | **63.2%** | 6.02 |
| 2004-2007 | Pre-Crisis | **4.51** | 28.4% | 8.53 |
| 2008-2009 | Financial Crisis | 2.78 | 32.4% | 3.05 |

**Observation:** Exceptional performance across ALL pre-2010 subperiods.

---

## 3. CRITICAL INTERPRETATION

### Why is Scenario C (Reverse) SO Much Better Than Scenario B (Forward)?

#### Hypothesis 1: Market Regime Change (Most Likely)
Post-2010 market is fundamentally different from pre-2010:
- Lower volatility
- Different cross-sectional return patterns
- Different factor exposures
- Models trained on pre-2010 data don't generalize to post-2010

#### Hypothesis 2: Crisis Period Predictability
Pre-2010 period includes TWO major crises (Dot-com 2001-2003, Financial Crisis 2008-2009):
- Scenario C captures 63% alpha during 2001-2003 crash
- Crises may have more predictable cross-sectional patterns
- P-Trees may be particularly good at identifying crisis winners/losers

#### Hypothesis 3: Data Quality
Early period may have:
- Less efficient market (easier to exploit)
- Fewer competitors using similar strategies
- Different liquidity profile

---

## 4. STATISTICAL CONCERNS

### Concern 1: Multiple Testing
You're testing 3 scenarios, each with 3 factors, across different periods.
- Total effective tests: ~50-100
- Need to adjust significance levels (Bonferroni correction)
- True significance threshold: p < 0.001 instead of p < 0.05

**Assessment:** Your t-stats (4.65, 8.82) are still significant even after adjustment.

### Concern 2: Sample Size
- Scenario B: Only 127 months OOS
- Scenario C: Only 148 months OOS
- For monthly data, this is borderline small

**Recommendation:** Report confidence intervals, not just point estimates.

### Concern 3: Regime-Dependent Performance
Scenario C's exceptional performance is driven by **crisis periods**:
- 63% alpha during 2001-2003 crash
- 32% alpha during 2008-2009 crisis

**Question:** Is this a genuine signal or data mining?

---

## 5. REALISTIC EXPECTATIONS

### What Should You Report in Your Thesis?

#### Scenario A (Full Sample, IS):
- Report as IS baseline
- **Realistic interpretation:** "In-sample Sharpe of 2.74, but likely optimistic"

#### Scenario B (Forward Test, OOS):
- **Gross OOS Performance:** Sharpe 1.69, Alpha 6.6%
- **Net OOS Performance (after costs):** Sharpe -0.28, Alpha -1.2%
- **Realistic interpretation:** "Forward OOS test shows modest gross alpha (6.6%) that disappears after transaction costs"

#### Scenario C (Reverse Test, OOS):
- **Gross OOS Performance:** Sharpe 3.11, Alpha 40.8%
- **Net OOS Performance (after costs):** Sharpe 2.26, Alpha 29.7%
- **Realistic interpretation:** "Reverse OOS test shows exceptional performance (40.8% gross, 29.7% net), but driven by pre-2010 market conditions and crisis periods"

---

## 6. RECOMMENDATIONS FOR YOUR THESIS

### Immediate Actions:

1. **CORRECT Table 1 in your paper:**
   - Scenario B: Sharpe 1.69 (not 4.21), Alpha 6.6% (not 21.7%)
   - Scenario C: Keep as-is or update to 3.11/40.8%

2. **Add transaction cost analysis:**
   - Show that Scenario B becomes unprofitable after costs
   - Show that Scenario C remains profitable after costs

3. **Add subperiod analysis:**
   - Show performance by time period
   - Discuss regime dependence

4. **Temper your conclusions:**
   - Don't claim "P-Trees work well on small markets" based on Scenario C alone
   - Acknowledge asymmetric temporal performance
   - Discuss forward-test limitations

### Honest Thesis Conclusion:

> "We find mixed evidence for P-Tree performance in the Swedish market. While in-sample (Scenario A) and reverse out-of-sample (Scenario C) results show strong performance, the forward out-of-sample test (Scenario B) shows only modest gross alpha (6.6%) that disappears after transaction costs. The asymmetric performance suggests that P-Trees trained on pre-2010 data do not generalize well to post-2010 market conditions, potentially due to regime changes or reduced market inefficiency. The exceptional Scenario C performance appears driven by crisis periods (2001-2003, 2008-2009), raising questions about practical implementability."

---

## 7. COMPARISON TO ORIGINAL US PAPER

### US Paper (Cong et al. 2024):
- Market: US, ~2500 stocks, 61 characteristics
- In-sample Sharpe: ~6.37
- OOS Sharpe: ~3-4 (estimated)

### Your Results (Swedish Market):
- Market: Sweden, ~300 stocks, 19 characteristics
- In-sample Sharpe: 2.74
- Forward OOS Sharpe: 1.69
- Reverse OOS Sharpe: 3.11

**Verdict:** Your forward OOS results (1.69) are LOWER than expected given the US results. This is realistic given the smaller market and less data.

---

## 8. FINAL VERDICT

### Is Your Analysis Correct Now?
**YES** - After fixing the benchmark analysis script, your methodology is sound.

### Are You Overfitting?
**PARTIALLY** - Scenario C shows suspiciously high performance that may be regime-specific.

### What Should You Conclude?
**MIXED RESULTS:**
- Forward test (Scenario B): Weak, unprofitable after costs
- Reverse test (Scenario C): Strong, but regime-dependent
- Overall: P-Trees show limited forward predictability in Swedish market

### What Makes a Strong Thesis?
**HONESTY ABOUT LIMITATIONS:**
- Report true OOS results (both forward and reverse)
- Acknowledge transaction cost impact
- Discuss regime dependence
- Compare to US results
- Be transparent about what worked and what didn't

**Your thesis will be STRONGER** if you honestly report mixed results and discuss why, rather than claiming universal success.

---

## APPENDIX: Data Quality Checklist

- [x] **Correct OOS files used:** Yes, after fix
- [x] **Correct evaluation periods:** Yes, after fix
- [x] **No look-ahead bias:** Yes, lagged variables used
- [x] **Transaction costs included:** Yes, in analysis
- [x] **Subperiod analysis:** Yes, completed
- [x] **Statistical significance:** Yes, t-stats > 4.5
- [ ] **Rolling window validation:** Partially (simplified version)
- [?] **Survivor bias check:** Unknown - does data include delisted firms?

---

**Report Generated:** 2025-10-29
**Status:** ANALYSIS COMPLETE - READY FOR THESIS REVISION
