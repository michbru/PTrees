"""
Compare P-Tree Performance: 24-Char vs Full (54-Char) Dataset

This script compares the performance of P-Trees trained on:
1. 24 matched characteristics (those that align with US study)
2. Full 54 characteristics (including Swedish-specific additions)

The comparison will show whether using only "authentic" US characteristics
improves performance or if the additional Swedish characteristics help.
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("P-TREE PERFORMANCE COMPARISON: 24-CHAR vs FULL (54-CHAR)")
print("="*80)
print()

# Load results from both analyses
print("Loading analysis results...")

# 24-char results
results_24 = pd.read_csv('../results/ptree_24chars_all_scenarios_summary.csv')
print(f"[OK] Loaded 24-char results: {len(results_24)} scenarios")

# Full results
results_full = pd.read_csv('../results/ptree_all_scenarios_summary.csv')
print(f"[OK] Loaded full results: {len(results_full)} scenarios")
print()

# Merge results
print("Comparing performance metrics...")
print()

comparison = pd.DataFrame()

for idx in range(len(results_24)):
    scenario = results_24.iloc[idx]['Scenario']
    
    # Get 24-char metrics
    char24_tree1_sharpe = results_24.iloc[idx]['Tree1_Sharpe']
    char24_tree2_sharpe = results_24.iloc[idx]['Tree2_Sharpe']
    char24_tree3_sharpe = results_24.iloc[idx]['Tree3_Sharpe']
    char24_tree1_nodes = results_24.iloc[idx]['Tree1_Nodes']
    
    # Get full metrics
    full_tree1_sharpe = results_full.iloc[idx]['Tree1_Sharpe']
    full_tree2_sharpe = results_full.iloc[idx]['Tree2_Sharpe']
    full_tree3_sharpe = results_full.iloc[idx]['Tree3_Sharpe']
    full_tree1_nodes = results_full.iloc[idx]['Tree1_Nodes']
    
    # Calculate differences
    tree1_diff = char24_tree1_sharpe - full_tree1_sharpe
    tree2_diff = char24_tree2_sharpe - full_tree2_sharpe
    tree3_diff = char24_tree3_sharpe - full_tree3_sharpe
    
    # Calculate percentage improvements
    tree1_pct = 100 * tree1_diff / abs(full_tree1_sharpe) if full_tree1_sharpe != 0 else 0
    tree2_pct = 100 * tree2_diff / abs(full_tree2_sharpe) if full_tree2_sharpe != 0 else 0
    tree3_pct = 100 * tree3_diff / abs(full_tree3_sharpe) if full_tree3_sharpe != 0 else 0
    
    row = {
        'Scenario': scenario,
        '24Char_Tree1_Sharpe': char24_tree1_sharpe,
        'Full_Tree1_Sharpe': full_tree1_sharpe,
        'Tree1_Diff': tree1_diff,
        'Tree1_Improvement_%': tree1_pct,
        '24Char_Tree2_Sharpe': char24_tree2_sharpe,
        'Full_Tree2_Sharpe': full_tree2_sharpe,
        'Tree2_Diff': tree2_diff,
        'Tree2_Improvement_%': tree2_pct,
        '24Char_Tree3_Sharpe': char24_tree3_sharpe,
        'Full_Tree3_Sharpe': full_tree3_sharpe,
        'Tree3_Diff': tree3_diff,
        'Tree3_Improvement_%': tree3_pct,
        '24Char_Nodes': char24_tree1_nodes,
        'Full_Nodes': full_tree1_nodes
    }
    
    comparison = pd.concat([comparison, pd.DataFrame([row])], ignore_index=True)

# Print comparison table
print("="*80)
print("SHARPE RATIO COMPARISON")
print("="*80)
print()

for idx, row in comparison.iterrows():
    print(f"{row['Scenario']}:")
    print(f"  Tree 1: 24-char={row['24Char_Tree1_Sharpe']:.3f}, Full={row['Full_Tree1_Sharpe']:.3f}, "
          f"Diff={row['Tree1_Diff']:+.3f} ({row['Tree1_Improvement_%']:+.1f}%)")
    print(f"  Tree 2: 24-char={row['24Char_Tree2_Sharpe']:.3f}, Full={row['Full_Tree2_Sharpe']:.3f}, "
          f"Diff={row['Tree2_Diff']:+.3f} ({row['Tree2_Improvement_%']:+.1f}%)")
    print(f"  Tree 3: 24-char={row['24Char_Tree3_Sharpe']:.3f}, Full={row['Full_Tree3_Sharpe']:.3f}, "
          f"Diff={row['Tree3_Diff']:+.3f} ({row['Tree3_Improvement_%']:+.1f}%)")
    print(f"  Nodes:  24-char={int(row['24Char_Nodes'])}, Full={int(row['Full_Nodes'])}")
    print()

# Save comparison
output_file = 'results/ptree_24_vs_full_comparison.csv'
comparison.to_csv(output_file, index=False)
print(f"Saved comparison to: {output_file}")
print()

# Summary statistics
print("="*80)
print("SUMMARY")
print("="*80)
print()

avg_improvement_tree1 = comparison['Tree1_Improvement_%'].mean()
avg_improvement_tree2 = comparison['Tree2_Improvement_%'].mean()
avg_improvement_tree3 = comparison['Tree3_Improvement_%'].mean()

print(f"Average Sharpe Ratio Improvement (24-char vs Full):")
print(f"  Tree 1: {avg_improvement_tree1:+.1f}%")
print(f"  Tree 2: {avg_improvement_tree2:+.1f}%")
print(f"  Tree 3: {avg_improvement_tree3:+.1f}%")
print()

if avg_improvement_tree1 > 0:
    print("✓ Tree 1: 24-char dataset performs BETTER on average")
else:
    print("✗ Tree 1: Full dataset performs BETTER on average")

if avg_improvement_tree2 > 0:
    print("✓ Tree 2: 24-char dataset performs BETTER on average")
else:
    print("✗ Tree 2: Full dataset performs BETTER on average")

if avg_improvement_tree3 > 0:
    print("✓ Tree 3: 24-char dataset performs BETTER on average")
else:
    print("✗ Tree 3: Full dataset performs BETTER on average")

print()
print("="*80)
print("INTERPRETATION")
print("="*80)
print()

if avg_improvement_tree1 > 0:
    print("The 24-characteristic dataset (matching US study) shows improved performance.")
    print("This suggests that using only well-validated US characteristics is beneficial")
    print("and that some of the additional Swedish characteristics may introduce noise.")
else:
    print("The full 54-characteristic dataset shows better performance.")
    print("This suggests that the additional Swedish characteristics capture important")
    print("market-specific information that improves P-Tree predictions.")

print()
print("Characteristic counts:")
print(f"  24-char dataset: 23 unique characteristics (24 US chars, 2 map to same)")
print(f"  Full dataset:    54 characteristics (24 matched + 30 Swedish-specific)")
print()
