#!/usr/bin/env python3
"""
PTrees Dataset Pipeline Runner

This script runs the complete pipeline to build the PTrees analysis dataset.
Run this script to execute all steps in the correct order.
"""

import subprocess
import sys
from pathlib import Path

def run_script(script_path, description):
    """Run a Python script and handle errors."""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"Script: {script_path}")
    print(f"{'='*60}")

    try:
        # Use the same Python executable and venv
        result = subprocess.run([
            sys.executable,
            str(script_path)
        ], check=True, capture_output=True, text=True)

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        print(f"SUCCESS: {description}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"FAILED: {description}")
        print(f"Error code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def main():
    """Run the complete PTrees dataset pipeline."""
    print("PTREES DATASET PIPELINE")
    print("This will run all 3 steps to build the complete dataset")
    print("Estimated time: 2-5 minutes")

    # Define the pipeline steps
    steps = [
        ("scripts/1_extract_isins_for_lseg.py", "Step 1: Extract ISINs"),
        ("scripts/2_pull_lseg_simple.py", "Step 2: Pull LSEG Fundamental Data"),
        ("scripts/3_build_final_dataset.py", "Step 3: Build Final Dataset with Rich Characteristics")
    ]

    # Run each step
    for script_path, description in steps:
        success = run_script(script_path, description)
        if not success:
            print(f"\nPIPELINE FAILED at {description}")
            print("Please check the error messages above and fix any issues.")
            return False

    # Pipeline completed successfully
    print(f"\nPIPELINE COMPLETED SUCCESSFULLY!")
    print(f"{'='*60}")
    print(f"Final dataset: results/ptrees_final_dataset.csv")
    print(f"Ready for analysis!")
    print(f"See README.md for usage instructions")

    return True

if __name__ == "__main__":
    main()