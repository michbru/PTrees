import pandas as pd
import numpy as np

# Load P-Tree factors
factors = pd.read_csv('results/ptree_34chars/boosted_trees/all_factors.csv')
factors['date'] = pd.to_datetime(factors['date'])

# Load original data to understand what xret represents
data = pd.read_csv('results/ptree_34chars/ptree_ready_data_34chars.csv', nrows=10000)

print("="*80)
print("WHAT DO P-TREE FACTORS REPRESENT?")
print("="*80)
print()

print("Sample xret (excess returns) statistics:")
print(f"  Mean: {data['xret'].mean():.6f}")
print(f"  Std: {data['xret'].std():.6f}")
print(f"  Min: {data['xret'].min():.6f}")
print(f"  Max: {data['xret'].max():.6f}")
print()

print("P-Tree Factor Statistics (monthly):")
print(f"  Mean: {factors['tree_1'].mean():.6f}")
print(f"  Std: {factors['tree_1'].std():.6f}")
print(f"  Min: {factors['tree_1'].min():.6f}")
print(f"  Max: {factors['tree_1'].max():.6f}")
print()

print("Annualized Factor Performance:")
ann_return = factors['tree_1'].mean() * 12
ann_vol = factors['tree_1'].std() * np.sqrt(12)
sharpe = (factors['tree_1'].mean() / factors['tree_1'].std()) * np.sqrt(12)
print(f"  Return: {ann_return:.2%}")
print(f"  Volatility: {ann_vol:.2%}")
print(f"  Sharpe: {sharpe:.3f}")
print()

print("="*80)
print("INTERPRETATION:")
print("="*80)
print()
print("P-Tree factors are VALUE-WEIGHTED PORTFOLIO RETURNS formed by:")
print("  1. Splitting stocks into groups based on characteristics")
print("  2. Weighting stocks by market cap within each leaf")
print("  3. Computing the return of this portfolio")
print()
print("This is NOT 'beating the market' - it's a LONG-ONLY factor strategy")
print("that captures cross-sectional return patterns.")
print()
print("Sharpe 1.14 means: For every 1% volatility, you get 1.14% excess return")
print()

# Check if we have market data
try:
    macro = pd.read_csv('data/raw/macro/macro_variables_with_dates.csv')
    print("Market benchmark data found - would need to compare properly")
except:
    print("No market benchmark loaded for direct comparison")
