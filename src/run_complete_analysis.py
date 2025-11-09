"""
Master Script - Complete P-Tree Analysis with Robustness Checks

Runs the entire analysis pipeline in correct order:
1. Data preparation (1_prepare_data.py) - Optional if already run
2. P-Tree model training (2_ptree_analysis.R) - Optional if already run
3. Benchmark analysis (3_benchmark_analysis.py)
4. Transaction cost analysis (5_transaction_cost_analysis.py)
5. Subperiod analysis (6_subperiod_analysis.py)
6. Rolling window P-Tree analysis (7_rolling_window_ptree.R) - Most robust test
7. Visualize rolling window results (8_visualize_rolling_window.py)

Note: Scripts 1 and 2 are optional because they take time and only need to be run once.
"""

import subprocess
import sys
from pathlib import Path
import time

print("="*80)
print("COMPLETE P-TREE ANALYSIS WITH ROBUSTNESS CHECKS")
print("="*80)

# Define all scripts in execution order
# Format: (script_name, description, run_by_default, script_type)
scripts_to_run = [
    ("1_prepare_data.py", "Data Preparation", False, "python"),
    ("2_ptree_analysis.R", "P-Tree Model Training (3 scenarios)", False, "r"),
    ("3_benchmark_analysis.py", "Benchmark Analysis (CAPM/FF3/FF4)", True, "python"),
    ("4_transaction_cost_analysis.py", "Transaction Cost Analysis", True, "python"),
    ("5_subperiod_analysis.py", "Subperiod Analysis", True, "python"),
    ("6_rolling_window_ptree.R", "Rolling Window P-Trees (Most Robust)", True, "r"),
    ("7_visualize_rolling_window.py", "Visualize Rolling Window Results", True, "python")
]

print("\nAnalysis Pipeline:")
for i, (script_name, description, will_run, _) in enumerate(scripts_to_run, 1):
    status = "✓ WILL RUN" if will_run else "○ SKIP (already done)"
    print(f"  {i}. {description:50} {status}")

print("\nNote: Scripts 1 & 2 are skipped by default (run once, outputs cached).")
print("      To run them, edit run_complete_analysis.py and set run=True.\n")

results = {}

for script_name, description, run, script_type in scripts_to_run:
    if not run:
        print(f"\n[SKIP] {description}")
        results[script_name] = "SKIPPED"
        continue

    print("\n" + "="*80)
    print(f"RUNNING: {description}")
    print(f"Script: {script_name}")
    print("="*80)

    script_path = Path("src") / script_name

    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        results[script_name] = "ERROR - File not found"
        continue

    start_time = time.time()

    try:
        # Determine command based on script type
        if script_type == "python":
            cmd = [sys.executable, str(script_path)]
        elif script_type == "r":
            cmd = ["Rscript", str(script_path)]
        else:
            print(f"[ERROR] Unknown script type: {script_type}")
            results[script_name] = "ERROR - Unknown type"
            continue

        # Run script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1200  # 20 minute timeout (rolling window can be slow)
        )

        elapsed = time.time() - start_time

        print(result.stdout)

        if result.returncode == 0:
            print(f"\n[SUCCESS] Completed in {elapsed:.1f} seconds")
            results[script_name] = f"SUCCESS ({elapsed:.1f}s)"
        else:
            print(f"\n[ERROR] Script failed with return code {result.returncode}")
            print("STDERR:", result.stderr)
            results[script_name] = f"FAILED (code {result.returncode})"

    except subprocess.TimeoutExpired:
        print(f"\n[ERROR] Script timed out after 20 minutes")
        results[script_name] = "TIMEOUT"
    except FileNotFoundError as e:
        print(f"\n[ERROR] Command not found: {str(e)}")
        print("Make sure Python and R are installed and in PATH")
        results[script_name] = f"ERROR - Command not found"
    except Exception as e:
        print(f"\n[ERROR] Exception: {str(e)}")
        results[script_name] = f"EXCEPTION: {str(e)}"

print("\n" + "="*80)
print("ANALYSIS PIPELINE SUMMARY")
print("="*80)

for script_name, status in results.items():
    status_symbol = "✓" if "SUCCESS" in status else ("○" if status == "SKIPPED" else "✗")
    print(f"  {status_symbol} {script_name:45} {status}")

print("\n" + "="*80)
print("OUTPUT FILES GENERATED")
print("="*80)

output_files = [
    ("results/ptree_ready_data_full.csv", "Prepared data for P-Tree"),
    ("results/ptree_scenario_a_full/ptree_factors.csv", "P-Tree factors (Scenario A)"),
    ("results/ptree_scenario_b_split/ptree_factors_oos.csv", "P-Tree factors (Scenario B OOS)"),
    ("results/ptree_scenario_c_reverse/ptree_factors_oos.csv", "P-Tree factors (Scenario C OOS)"),
    ("results/cross_scenario_comparison.csv", "Main results comparison"),
    ("results/ptree_scenario_a_full/benchmark_analysis/table2_alphas.csv", "Alphas (Scenario A)"),
    ("results/ptree_scenario_b_split/benchmark_analysis/table2_alphas.csv", "Alphas (Scenario B)"),
    ("results/ptree_scenario_c_reverse/benchmark_analysis/table2_alphas.csv", "Alphas (Scenario C)"),
    ("results/robustness_checks/transaction_cost_analysis.csv", "Transaction cost analysis"),
    ("results/robustness_checks/subperiod_analysis.csv", "Subperiod analysis"),
    ("results/robustness_checks/rolling_window_ptree_results.csv", "Rolling window results"),
    ("results/robustness_checks/plots/rolling_sharpe_ratios.png", "Rolling window plots")
]

print()
for file_path, description in output_files:
    if Path(file_path).exists():
        print(f"  ✓ {description:50} {file_path}")
    else:
        print(f"  ✗ {description:50} {file_path} [MISSING]")

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)

print("\n1. Review main results (results/cross_scenario_comparison.csv):")
print("   - Scenario A (IS): Baseline performance")
print("   - Scenario B (OOS Forward): Realistic forward prediction")
print("   - Scenario C (OOS Reverse): Academic robustness check")

print("\n2. Review robustness checks:")
print("   - Rolling window: Most robust OOS test (Sharpe 4.60 expected)")
print("   - Transaction costs: Net returns after realistic trading costs")
print("   - Subperiod: Performance by market regime")

print("\n3. Key metrics to check:")
print("   - Scenario B OOS: Sharpe 1.69, Alpha 6.63%")
print("   - Rolling window: Sharpe 4.60, Alpha 36.77%")
print("   - All t-statistics should be > 4.0 (highly significant)")

print("\n4. Visualizations:")
print("   - Check plots in results/robustness_checks/plots/")
print("   - Rolling Sharpe ratios over time")
print("   - Cumulative returns")

print("\n" + "="*80)
print("COMPLETE ANALYSIS PIPELINE FINISHED")
print("="*80)

# Count successes
successes = sum(1 for status in results.values() if "SUCCESS" in status)
total_run = sum(1 for status in results.values() if status != "SKIPPED")

if total_run > 0:
    print(f"\nSuccess rate: {successes}/{total_run} scripts completed successfully")
    if successes == total_run:
        print("🎉 All scripts completed successfully!")
    elif successes > 0:
        print("⚠️  Some scripts had issues. Review the errors above.")
    else:
        print("❌ No scripts completed successfully. Check errors above.")
