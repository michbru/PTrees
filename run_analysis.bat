@echo off
REM ========================================================================
REM P-Tree Analysis - Complete Replication Script (Windows)
REM
REM This script runs the entire P-Tree analysis pipeline from start to finish.
REM Prerequisites: Python 3.8+, R 4.0+, required packages installed
REM ========================================================================

setlocal enabledelayedexpansion

echo.
echo ========================================================================
echo        P-Tree Analysis - Swedish Stock Market (1997-2022)
echo ========================================================================
echo.

REM Check if we're in the right directory
if not exist "README.md" (
    echo Error: Please run this script from the PTrees project root directory
    exit /b 1
)
if not exist "data" (
    echo Error: Please run this script from the PTrees project root directory
    exit /b 1
)

REM Step 1: Data Preparation (Python)
echo ========================================================================
echo Step 1/2: Preparing data with Python...
echo ========================================================================
echo.

python src\1_prepare_data_relaxed.py

if errorlevel 1 (
    echo.
    echo Error: Data preparation failed
    exit /b 1
)

echo.
echo [OK] Data preparation complete
echo.

REM Step 2: P-Tree Analysis (R)
echo ========================================================================
echo Step 2/2: Running P-Tree analysis with R...
echo ========================================================================
echo.

Rscript src\2_run_ptree_attempt2.R

if errorlevel 1 (
    echo.
    echo Error: P-Tree analysis failed
    exit /b 1
)

echo.
echo [OK] P-Tree analysis complete
echo.

REM Success summary
echo.
echo ========================================================================
echo                    [SUCCESS] ANALYSIS COMPLETE
echo ========================================================================
echo.
echo Results saved to:
echo   - results\ptree_factors.csv        (factor returns - main result)
echo   - results\ptree_models.RData       (fitted P-Tree models)
echo   - results\ptree_ready_data_*.csv   (processed data)
echo.
echo Expected result: Sharpe Ratio = 1.20, Win Rate = 67.5%%
echo.

endlocal
