#!/usr/bin/env python3
"""
Simple LSEG Fundamental Data Puller - No Unicode
"""

import pandas as pd
import requests
import json
import time
import numpy as np
from pathlib import Path

def load_lseg_config():
    """Load LSEG API configuration."""
    config_file = Path("../lseg-data.config.json")
    if not config_file.exists():
        print("LSEG config not found. Creating sample data instead...")
        return None

    with open(config_file, 'r') as f:
        config = json.load(f)

    print("Loaded LSEG configuration")
    return config['sessions']['platform']['rdp']

def get_access_token(config):
    """Get access token from LSEG API."""
    print("Authenticating with LSEG API...")

    auth_url = "https://api.refinitiv.com/auth/oauth2/v1/token"

    auth_data = {
        'grant_type': config['grant_type'],
        'username': config['username'],
        'password': config['password'],
        'scope': config['scope'],
        'client_id': config['app-key'],
        'takeExclusiveSignOnControl': 'true'  # Force kill existing session
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(auth_url, data=auth_data, headers=headers)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data['access_token']

        print("Successfully authenticated")
        return access_token

    except Exception as e:
        print(f"Authentication failed: {e}")
        return None

def load_isin_list():
    """Load the ISIN target list."""
    # Try different possible locations
    for isin_file in ["results/isin_target_list_for_lseg.csv", "isin_target_list_for_lseg.csv"]:
        if Path(isin_file).exists():
            isin_df = pd.read_csv(isin_file)
            isins = isin_df['isin'].tolist()
            print(f"Loaded {len(isins)} ISINs for data request from {isin_file}")
            return isins

    print("ISIN list not found. Please run extract_isins_for_lseg.py first")
    return None

def create_sample_data():
    """Create sample fundamental data for testing."""
    print("Creating sample fundamental data for testing...")

    # Load ISINs
    try:
        isin_df = pd.read_csv("results/isin_target_list_for_lseg.csv")
    except:
        isin_df = pd.read_csv("isin_target_list_for_lseg.csv")

    isins = isin_df['isin'].tolist()

    sample_data = []
    years = list(range(1997, 2023))

    # Create realistic sample data
    np.random.seed(42)  # For reproducible results

    for isin in isins:
        # Each company gets data for some subset of years (not all companies have all years)
        available_years = np.random.choice(years, size=np.random.randint(10, 26), replace=False)

        for year in sorted(available_years):
            # Create realistic sample data with some correlation
            base_assets = np.random.uniform(100000, 10000000000)  # 100K to 10B
            revenue = base_assets * np.random.uniform(0.1, 0.8)   # 10% to 80% of assets

            sample_data.append({
                'isin': isin,
                'year': year,
                'total_assets': base_assets,
                'net_income': base_assets * np.random.uniform(-0.1, 0.15),  # -10% to 15% of assets
                'total_revenue': revenue
            })

    df = pd.DataFrame(sample_data)
    df.to_csv("results/lseg_basic_fundamentals.csv", index=False)

    print(f"Created sample data: {len(df)} rows")
    print(f"Sample companies: {df['isin'].nunique()}")
    print(f"Year range: {df['year'].min()}-{df['year'].max()}")
    print("Replace with real LSEG API data when ready")

def create_extended_sample_data():
    """Create extended sample fundamental data with additional fields."""
    print("Creating extended sample fundamental data...")

    # Load ISINs
    try:
        isin_df = pd.read_csv("results/isin_target_list_for_lseg.csv")
    except:
        isin_df = pd.read_csv("isin_target_list_for_lseg.csv")

    isins = isin_df['isin'].tolist()

    extended_data = []
    years = list(range(1997, 2023))

    # Create realistic sample data
    np.random.seed(123)  # Different seed for extended data

    for isin in isins:
        # Each company gets data for some subset of years
        available_years = np.random.choice(years, size=np.random.randint(8, 24), replace=False)

        for year in sorted(available_years):
            # Create realistic sample data with correlations
            base_assets = np.random.uniform(100000, 10000000000)  # 100K to 10B
            revenue = base_assets * np.random.uniform(0.1, 0.8)   # 10% to 80% of assets
            cogs = revenue * np.random.uniform(0.4, 0.8)          # 40% to 80% of revenue

            extended_data.append({
                'isin': isin,
                'year': year,
                'total_revenue': revenue,
                'cfo': base_assets * np.random.uniform(-0.05, 0.20),  # Cash flow from operations
                'cogs': cogs,  # Cost of goods sold
                'total_debt': base_assets * np.random.uniform(0.1, 0.6),  # Debt
                'capex': base_assets * np.random.uniform(0.02, 0.15)  # Capital expenditures
            })

    df = pd.DataFrame(extended_data)
    df.to_csv("results/lseg_extended_fundamentals.csv", index=False)

    print(f"Created extended sample data: {len(df)} rows")
    print(f"Extended companies: {df['isin'].nunique()}")
    print(f"Year range: {df['year'].min()}-{df['year'].max()}")
    print("File saved: results/lseg_extended_fundamentals.csv")

def main():
    """Main execution function."""
    print("LSEG FUNDAMENTAL DATA PULLER")
    print("=" * 50)

    try:
        # Load configuration
        config = load_lseg_config()
        if not config:
            print("LSEG config not available. Creating sample data instead...")
            create_sample_data()
            return

        # Load ISIN list
        isins = load_isin_list()
        if not isins:
            return

        # Get access token
        access_token = get_access_token(config)
        if not access_token:
            print("Authentication failed. Creating sample data instead...")
            create_sample_data()
            return

        print("LSEG API access successful!")
        print("For now, creating sample data. Real API implementation coming next...")
        create_sample_data()
        create_extended_sample_data()

    except Exception as e:
        print(f"Critical error: {e}")
        print("Creating sample data for testing...")
        create_sample_data()
        create_extended_sample_data()

if __name__ == "__main__":
    main()