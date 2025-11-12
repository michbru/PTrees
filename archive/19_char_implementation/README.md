# Archived: 19-Characteristic P-Tree Implementation

**Status:** Archived - Superseded by 34-characteristic implementation

## Why Archived?

This was the original P-Tree implementation using only 19 characteristics from the Swedish dataset. It has been superseded by the enhanced 34-characteristic implementation which:
- Includes all 6 critical characteristics from the original P-Tree paper
- Achieves 134% better out-of-sample performance (Sharpe 2.69 vs 1.15)
- Has 56% coverage of original study (vs 31%)

## Performance (for reference)

| Scenario | Sharpe Ratio |
|----------|--------------|
| Full Sample | 1.27 |
| Time Split (Train) | 2.84 |
| Reverse Split (OOS) | 1.15 |

## Contents

- **src/** - Original analysis scripts
- **results/** - Original analysis results

## Current Implementation

See the main project folder for the active 34-characteristic implementation.

---

**Archived Date:** January 12, 2025
