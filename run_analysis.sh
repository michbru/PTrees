#!/bin/bash
############################################################################
# P-Tree Analysis - Complete Replication Script
#
# This script runs the entire P-Tree analysis pipeline from start to finish.
# Prerequisites: Python 3.8+, R 4.0+, required packages installed
############################################################################

set -e  # Exit on any error

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║        P-Tree Analysis - Swedish Stock Market (1997-2022)     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "data" ]; then
    echo "❌ Error: Please run this script from the PTrees project root directory"
    exit 1
fi

# Step 1: Data Preparation (Python)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1/2: Preparing data with Python..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python src/1_prepare_data_relaxed.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error: Data preparation failed"
    exit 1
fi

echo ""
echo "✅ Data preparation complete"
echo ""

# Step 2: P-Tree Analysis (R)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2/2: Running P-Tree analysis with R..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

Rscript src/2_run_ptree_attempt2.R

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error: P-Tree analysis failed"
    exit 1
fi

echo ""
echo "✅ P-Tree analysis complete"
echo ""

# Success summary
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    ✅ ANALYSIS COMPLETE                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Results saved to:"
echo "  📊 results/ptree_factors.csv        (factor returns - main result)"
echo "  📦 results/ptree_models.RData       (fitted P-Tree models)"
echo "  📄 results/ptree_ready_data_*.csv   (processed data)"
echo ""
echo "Expected result: Sharpe Ratio ≈ 1.20, Win Rate ≈ 67.5%"
echo ""
