
import pandas as pd
from pathlib import Path

RAW_SERRANO = Path('data/raw/serrano/Stata_2025/ftg1.dta')
RAW_FINBAS = Path('data/intermediate/finbas/finbas_daily_clean.csv')

def inspect():
    print("Inspecting Serrano FTG file...")
    try:
        ftg = pd.read_stata(RAW_SERRANO)
        print("Columns:", ftg.columns.tolist())
        print(ftg.head())
    except Exception as e:
        print(f"Error reading FTG: {e}")

    print("\nInspecting Finbas Clean file...")
    try:
        finbas = pd.read_csv(RAW_FINBAS, nrows=5)
        print("Columns:", finbas.columns.tolist())
        print(finbas[['isin', 'name']].head())
    except Exception as e:
        print(f"Error reading Finbas: {e}")

if __name__ == '__main__':
    inspect()
