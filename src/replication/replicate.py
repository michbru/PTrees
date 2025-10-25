"""
P-Tree Analysis - Complete Replication Script

This script replicates the entire P-Tree analysis pipeline:
1. Cleans previous results
2. Runs data preparation (Python)
3. Runs P-Tree analysis (R)
4. Displays results

Usage:
    python src/replication/replicate.py

Prerequisites:
    - Python 3.8+ with packages: pandas, numpy, pyarrow
    - R 4.0+ with packages: PTree, arrow, rpart, ranger, data.table
"""

import subprocess
import sys
from pathlib import Path
import shutil

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(text.center(70))
    print("="*70 + "\n")

def print_step(step_num, total_steps, text):
    """Print step header"""
    print(f"\n{'─'*70}")
    print(f"Step {step_num}/{total_steps}: {text}")
    print(f"{'─'*70}\n")

def clean_results():
    """Remove previous results to ensure fresh replication"""
    print("Cleaning previous results...")

    results_dir = Path("results")

    # List of result files to remove
    result_files = [
        "ptree_factors.csv",
        "ptree_models.RData",
        "ptree_ready_data.feather",
        "ptree_ready_data_full.csv",
        "ptree_ready_data_sample.csv"
    ]

    removed_count = 0
    for file in result_files:
        file_path = results_dir / file
        if file_path.exists():
            file_path.unlink()
            print(f"  ✓ Removed {file}")
            removed_count += 1

    if removed_count == 0:
        print("  ✓ No previous results found (clean state)")
    else:
        print(f"\n  ✓ Cleaned {removed_count} result file(s)")

    return True

def run_data_preparation():
    """Run Python data preparation script"""
    print("Running data preparation...")
    print("  (This will create ranked characteristics and handle missing data)\n")

    try:
        # Try with current Python executable first
        result = subprocess.run(
            [sys.executable, "src/1_prepare_data_relaxed.py"],
            check=True,
            capture_output=False
        )
        print("\n  ✓ Data preparation complete")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n  ✗ Error: Data preparation failed")
        print(f"     {str(e)}")
        return False
    except FileNotFoundError:
        print(f"\n  ✗ Error: Could not find src/1_prepare_data_relaxed.py")
        return False
    except Exception as e:
        print(f"\n  ✗ Error: {str(e)}")
        return False

def run_ptree_analysis():
    """Run R P-Tree analysis"""
    print("Running P-Tree analysis...")
    print("  (This will fit P-Tree models and generate factor returns)\n")

    # Try multiple common R locations
    rscript_paths = [
        "Rscript",  # In PATH
        "/usr/bin/Rscript",  # WSL/Linux
        "wsl Rscript",  # Call WSL R from Windows
        "C:\\Program Files\\R\\R-4.3.0\\bin\\Rscript.exe",  # Common Windows location
        "C:\\Program Files\\R\\R-4.2.0\\bin\\Rscript.exe",
        "C:\\Program Files\\R\\R-4.1.0\\bin\\Rscript.exe",
    ]

    for rscript_path in rscript_paths:
        try:
            result = subprocess.run(
                [rscript_path, "src/2_run_ptree_attempt2.R"],
                check=True,
                capture_output=False
            )
            print("\n  ✓ P-Tree analysis complete")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    # If we get here, none worked
    print(f"\n  ✗ Error: Could not find Rscript")
    print(f"     Tried: {', '.join(rscript_paths)}")
    print(f"\n  💡 Manual workaround:")
    print(f"     Open R/RStudio and run: source('src/2_run_ptree_attempt2.R')")
    return False

def verify_results():
    """Check that expected result files were created"""
    print("Verifying results...")

    results_dir = Path("results")
    expected_files = {
        "ptree_factors.csv": "Factor returns (main result)",
        "ptree_models.RData": "Fitted P-Tree models",
        "ptree_ready_data_full.csv": "Processed dataset"
    }

    all_found = True
    for file, description in expected_files.items():
        file_path = results_dir / file
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  ✓ {file:<30} ({size_mb:.1f} MB) - {description}")
        else:
            print(f"  ✗ {file:<30} - MISSING!")
            all_found = False

    return all_found

def main():
    """Main replication workflow"""

    print_header("P-Tree Analysis - Complete Replication")
    print("This script will replicate the entire P-Tree analysis pipeline.")
    print("\nExpected result: Sharpe Ratio ≈ 1.20, Win Rate ≈ 67.5%")
    print("Runtime: ~3-5 minutes\n")

    # Check we're in the right directory
    if not Path("README.md").exists() or not Path("data").exists():
        print("✗ Error: Please run this script from the PTrees project root directory")
        print("  Usage: python src/replication/replicate.py")
        return 1

    # Step 1: Clean previous results
    print_step(1, 4, "Cleaning Previous Results")
    if not clean_results():
        return 1

    # Step 2: Data preparation
    print_step(2, 4, "Data Preparation (Python)")
    if not run_data_preparation():
        return 1

    # Step 3: P-Tree analysis
    print_step(3, 4, "P-Tree Analysis (R)")
    if not run_ptree_analysis():
        return 1

    # Step 4: Verify results
    print_step(4, 4, "Verifying Results")
    if not verify_results():
        print("\n✗ Warning: Some expected files were not created")
        return 1

    # Success!
    print_header("✓ REPLICATION COMPLETE")
    print("Results saved to:")
    print("  📊 results/ptree_factors.csv        (factor returns - main result)")
    print("  📦 results/ptree_models.RData       (fitted P-Tree models)")
    print("  📄 results/ptree_ready_data_*.csv   (processed data)")
    print("\nExpected result: Sharpe Ratio ≈ 1.20, Win Rate ≈ 67.5%\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
