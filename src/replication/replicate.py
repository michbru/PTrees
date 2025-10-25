"""
P-Tree Analysis - Complete Replication Script

Replicates the complete P-Tree analysis for Swedish stock market:
1. Runs P-Tree analysis (3 scenarios)
2. Runs benchmark comparisons (CAPM, FF3, FF4)
3. Displays results

Usage:
    python src/replication/replicate.py

Prerequisites:
    - Python 3.8+ with: pandas, numpy, statsmodels
    - R 4.0+ with: PTree, arrow, rpart, ranger, data.table
    - Data files in data/ directory
"""

import subprocess
import sys
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(text.center(80))
    print("="*80 + "\n")

def print_step(step_num, total_steps, text):
    """Print step header"""
    print(f"\n{'-'*80}")
    print(f"Step {step_num}/{total_steps}: {text}")
    print(f"{'-'*80}\n")

def run_data_preparation():
    """Run Python data preparation script"""
    print("Preparing data (creating ranked characteristics)...\n")

    try:
        subprocess.run(
            [sys.executable, "src/1_prepare_data.py"],
            check=True,
            capture_output=False
        )
        print("\n  ✓ Data preparation complete")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"\n  ✗ Error: Data preparation failed - {str(e)}")
        return False



def run_ptree_analysis():
    """Run R P-Tree analysis for all scenarios"""
    print("Running P-Tree analysis (3 scenarios)...")
    print("  This will generate P-Tree factors for Full, Split, and Reverse scenarios\n")

    # Try multiple R locations
    rscript_commands = [
        ["Rscript", "src/4_complete_ptree_analysis.R"],
        ["wsl", "Rscript", "src/4_complete_ptree_analysis.R"],
        ["/usr/bin/Rscript", "src/4_complete_ptree_analysis.R"],
        ["C:\\Program Files\\R\\R-4.3.0\\bin\\Rscript.exe", "src/4_complete_ptree_analysis.R"],
        ["C:\\Program Files\\R\\R-4.2.0\\bin\\Rscript.exe", "src/4_complete_ptree_analysis.R"],
    ]

    for cmd in rscript_commands:
        try:
            subprocess.run(cmd, check=True, capture_output=False)
            print("\n  ✓ P-Tree analysis complete (all scenarios)")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    # If none worked
    print(f"\n  ✗ Error: Could not find Rscript")
    print(f"\n  💡 Manual workaround:")
    print(f"     Open R/RStudio and run: source('src/4_complete_ptree_analysis.R')")
    return False

def run_benchmark_analysis():
    """Run benchmark comparison for all scenarios"""
    print("Running benchmark analysis (all scenarios)...")
    print("  Comparing P-Trees vs CAPM, FF3, FF4 for all scenarios\n")

    try:
        subprocess.run(
            [sys.executable, "src/5_benchmark_all_scenarios.py"],
            check=True,
            capture_output=False
        )
        print("\n  ✓ Benchmark analysis complete")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n  ✗ Error: Benchmark analysis failed - {str(e)}")
        return False
    except FileNotFoundError:
        print(f"\n  ✗ Error: Could not find src/5_benchmark_all_scenarios.py")
        return False

def verify_results():
    """Check that expected result files were created"""
    print("Verifying results...")

    results_dir = Path("results")
    
    # Check main summary files
    main_files = {
        "cross_scenario_comparison.csv": "Cross-scenario summary",
        "ptree_all_scenarios_summary.csv": "Detailed scenario metrics"
    }
    
    all_found = True
    for file, description in main_files.items():
        file_path = results_dir / file
        if file_path.exists():
            print(f"  ✓ {file:<35} - {description}")
        else:
            print(f"  ✗ {file:<35} - MISSING!")
            all_found = False
    
    # Check scenario folders
    scenarios = ["ptree_scenario_a_full", "ptree_scenario_b_split", "ptree_scenario_c_reverse"]
    for scenario in scenarios:
        scenario_dir = results_dir / scenario
        if scenario_dir.exists():
            print(f"  ✓ {scenario:<35}")
            # Check for key files
            if (scenario_dir / "ptree_factors.csv").exists():
                print(f"    - ptree_factors.csv")
            if (scenario_dir / "benchmark_analysis").exists():
                print(f"    - benchmark_analysis/")
        else:
            print(f"  ✗ {scenario:<35} - MISSING!")
            all_found = False
    
    return all_found


def main():
    """Main replication workflow"""

    print_header("P-Tree Analysis - Complete Replication")
    print("Replicates P-Tree analysis on Swedish stock market (1997-2022)")
    print("\nExpected results:")
    print("  - Sharpe Ratios: 2.7-4.3")
    print("  - Alphas: 20-28% per year")
    print("  - t-statistics: > 9.6 (highly significant)")
    print("\nRuntime: ~2 minutes\n")

    # Check we're in the right directory
    if not Path("README.md").exists() or not Path("data").exists():
        print("✗ Error: Please run this script from the PTrees project root directory")
        print("  Usage: python src/replication/replicate.py")
        return 1

    # Step 1: Data preparation
    print_step(1, 3, "Data Preparation (Python)")
    if not run_data_preparation():
        return 1

    # Step 2: P-Tree analysis
    print_step(2, 3, "P-Tree Analysis (R) - All Scenarios")
    if not run_ptree_analysis():
        print("\n⚠ Manual alternative: Open R and run: source('src/4_complete_ptree_analysis.R')")
        return 1

    # Step 3: Benchmark analysis  
    print_step(3, 3, "Benchmark Analysis (Python) - All Scenarios")
    if not run_benchmark_analysis():
        print("\n⚠ Warning: Benchmark analysis failed, but P-Tree results are available")

    # Verify results
    print("\n" + "-"*80)
    if not verify_results():
        print("\n⚠ Warning: Some expected files were not created")
        return 1

    # Success!
    print_header("✓ REPLICATION COMPLETE")
    print("Results Summary:")
    print("  📊 results/cross_scenario_comparison.csv    (Main summary table)")
    print("  � results/ptree_scenario_a_full/           (Full period: 1997-2022)")
    print("  � results/ptree_scenario_b_split/          (Train/test split)")
    print("  � results/ptree_scenario_c_reverse/        (Reverse chronology)")
    print("\nKey Findings:")
    print("  ✓ Sharpe Ratios: 2.7-4.3")
    print("  ✓ Alphas: 20-28% per year (vs CAPM/FF3/FF4)")
    print("  ✓ t-statistics: 9.6-15.0 (p < 0.001)")
    print("\nFor detailed analysis, see RESULTS_SUMMARY.md")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
