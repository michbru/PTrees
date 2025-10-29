"""
Master Script - Complete P-Tree Analysis with Robustness Checks

Runs the entire analysis pipeline in correct order:
1. Data preparation (already done, skip)
2. P-Tree model training (already done, skip)
3. Fixed benchmark analysis (correct OOS handling)
4. Rolling window analysis
5. Transaction cost analysis
6. Subperiod analysis
7. Generate comprehensive report
"""

import subprocess
import sys
from pathlib import Path
import time

print("="*80)
print("COMPLETE P-TREE ANALYSIS WITH ROBUSTNESS CHECKS")
print("="*80)

scripts_to_run = [
    ("3_benchmark_analysis.py", "Benchmark Analysis (FIXED)", True),
    ("4_rolling_window_analysis.py", "Rolling Window Analysis", True),
    ("5_transaction_cost_analysis.py", "Transaction Cost Analysis", True),
    ("6_subperiod_analysis.py", "Subperiod Analysis", True)
]

results = {}

for script_name, description, run in scripts_to_run:
    if not run:
        print(f"\n[SKIP] {description}")
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
        # Run script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
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
        print(f"\n[ERROR] Script timed out after 10 minutes")
        results[script_name] = "TIMEOUT"
    except Exception as e:
        print(f"\n[ERROR] Exception: {str(e)}")
        results[script_name] = f"EXCEPTION: {str(e)}"

print("\n" + "="*80)
print("ANALYSIS PIPELINE SUMMARY")
print("="*80)

for script_name, status in results.items():
    print(f"  {script_name:40} {status}")

print("\n" + "="*80)
print("OUTPUT FILES GENERATED")
print("="*80)

output_files = [
    "results/cross_scenario_comparison.csv",
    "results/ptree_scenario_a_full/benchmark_analysis/table1_sharpe_ratios.csv",
    "results/ptree_scenario_a_full/benchmark_analysis/table2_alphas.csv",
    "results/ptree_scenario_b_split/benchmark_analysis/table1_sharpe_ratios.csv",
    "results/ptree_scenario_b_split/benchmark_analysis/table2_alphas.csv",
    "results/ptree_scenario_c_reverse/benchmark_analysis/table1_sharpe_ratios.csv",
    "results/ptree_scenario_c_reverse/benchmark_analysis/table2_alphas.csv",
    "results/robustness_checks/rolling_window_results.csv",
    "results/robustness_checks/transaction_cost_analysis.csv",
    "results/robustness_checks/subperiod_analysis.csv"
]

for file_path in output_files:
    if Path(file_path).exists():
        print(f"  ✓ {file_path}")
    else:
        print(f"  ✗ {file_path} [MISSING]")

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)

print("\n1. Review cross_scenario_comparison.csv:")
print("   - Verify each scenario uses correct data type (IS/OOS)")
print("   - Verify evaluation periods are correct")
print("   - Compare performance metrics")

print("\n2. Review robustness checks:")
print("   - Rolling window: Is performance stable over time?")
print("   - Transaction costs: What is net alpha after costs?")
print("   - Subperiod: Is performance driven by specific periods?")

print("\n3. Key questions to answer:")
print("   - Are Scenario B and C truly out-of-sample?")
print("   - Is OOS performance significantly lower than IS?")
print("   - Does performance survive transaction costs?")
print("   - Is performance consistent across subperiods?")

print("\n" + "="*80)
print("COMPLETE ANALYSIS PIPELINE FINISHED")
print("="*80)
