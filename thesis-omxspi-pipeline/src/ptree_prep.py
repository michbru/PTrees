from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List, Optional
from pathlib import Path


def validate_panel_structure(panel: pd.DataFrame) -> bool:
    """Validate that panel has required structure for P-Trees preprocessing.

    Args:
        panel: Input panel dataframe

    Returns:
        True if valid, False otherwise
    """
    required_cols = {"ric", "date"}

    if not required_cols.issubset(panel.columns):
        print(f"Error: Panel missing required columns: {required_cols - set(panel.columns)}")
        return False

    if panel.empty:
        print("Error: Panel is empty")
        return False

    # Check for duplicate ric-date pairs
    duplicates = panel.duplicated(subset=["ric", "date"]).sum()
    if duplicates > 0:
        print(f"Warning: Found {duplicates} duplicate ric-date pairs")

    return True


def identify_characteristics(panel: pd.DataFrame) -> List[str]:
    """Identify characteristic columns in the panel.

    Args:
        panel: Input panel with characteristics

    Returns:
        List of characteristic column names
    """
    # Basic columns that are not characteristics
    non_char_cols = {
        'ric', 'date', 'ret', 'mkt_cap', 'close', 'adj_close', 'volume',
        'price', 'shares_outstanding', 'market_cap', 'freq',
        # Raw fundamental data
        'totalassets', 'shareholdersequity', 'netincome', 'operatingincome',
        'revenue', 'commonsharesoutstanding', 'epsnormalized', 'epsreported',
        'cashfromoperations', 'grossprofit', 'totaldebt', 'longtermdebt',
        'currentassets', 'currentliabilities', 'grossmargin', 'operatingmargin',
        'debttoassets', 'rdexpense', 'advertisingexpense',
        # Industry codes
        'trbc_sector', 'trbc_industry', 'icb_industry', 'icb_supersector',
        # Error columns
    }

    # Also exclude any columns ending with '_error' or containing 'error'
    error_cols = {col for col in panel.columns if 'error' in col.lower()}
    non_char_cols.update(error_cols)

    # Identify characteristics as remaining numeric columns
    char_cols = []
    for col in panel.columns:
        if col not in non_char_cols and pd.api.types.is_numeric_dtype(panel[col]):
            char_cols.append(col)

    return char_cols


def winsorize_characteristics(panel: pd.DataFrame, char_cols: List[str],
                            lower_pct: float = 0.01, upper_pct: float = 0.99) -> pd.DataFrame:
    """Winsorize characteristics at specified percentiles by month.

    Args:
        panel: Panel with characteristics
        char_cols: List of characteristic columns to winsorize
        lower_pct: Lower percentile (default 1%)
        upper_pct: Upper percentile (default 99%)

    Returns:
        Panel with winsorized characteristics
    """
    df = panel.copy()

    print(f"Winsorizing {len(char_cols)} characteristics at {lower_pct:.1%}/{upper_pct:.1%} by month")

    def winsorize_month(group):
        """Winsorize within each month"""
        for col in char_cols:
            if col in group.columns and not group[col].isna().all():
                # Only winsorize if we have enough observations
                valid_obs = group[col].notna().sum()
                if valid_obs >= 5:  # Need at least 5 observations
                    lower_val = group[col].quantile(lower_pct)
                    upper_val = group[col].quantile(upper_pct)

                    # Clip values
                    group[col] = group[col].clip(lower=lower_val, upper=upper_val)

        return group

    # Apply winsorization by month
    df = df.groupby('date', group_keys=False).apply(winsorize_month)

    return df


def standardize_characteristics(panel: pd.DataFrame, char_cols: List[str],
                              method: str = 'minmax') -> pd.DataFrame:
    """Standardize characteristics to [-1, 1] range by month.

    Args:
        panel: Panel with characteristics
        char_cols: List of characteristic columns
        method: 'minmax' for [-1,1] scaling, 'zscore' for z-score normalization

    Returns:
        Panel with standardized characteristics
    """
    df = panel.copy()

    print(f"Standardizing {len(char_cols)} characteristics using {method} method")

    def standardize_month(group):
        """Standardize within each month"""
        for col in char_cols:
            if col in group.columns and not group[col].isna().all():
                valid_data = group[col].dropna()

                if len(valid_data) < 2:  # Need at least 2 observations
                    continue

                if method == 'minmax':
                    # Min-max scaling to [-1, 1]
                    min_val = valid_data.min()
                    max_val = valid_data.max()

                    if min_val == max_val:
                        # If constant, set to zero (neutral)
                        group[col] = 0.0
                    else:
                        # Scale to [-1, 1]
                        group[col] = 2 * (group[col] - min_val) / (max_val - min_val) - 1

                elif method == 'zscore':
                    # Z-score normalization
                    mean_val = valid_data.mean()
                    std_val = valid_data.std()

                    if std_val > 0:
                        group[col] = (group[col] - mean_val) / std_val
                    else:
                        group[col] = 0.0

        return group

    # Apply standardization by month
    df = df.groupby('date', group_keys=False).apply(standardize_month)

    return df


def fill_missing_values(panel: pd.DataFrame, char_cols: List[str],
                       fill_value: float = 0.0) -> pd.DataFrame:
    """Fill missing characteristic values.

    Args:
        panel: Panel with characteristics
        char_cols: List of characteristic columns
        fill_value: Value to fill missing with (default 0 = neutral)

    Returns:
        Panel with missing values filled
    """
    df = panel.copy()

    print(f"Filling missing values with {fill_value} for {len(char_cols)} characteristics")

    # Fill missing values
    for col in char_cols:
        if col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                print(f"  {col}: {missing_count} missing values filled")
                df[col] = df[col].fillna(fill_value).infer_objects(copy=False)

    return df


def load_risk_factors(factors_path: Path) -> Optional[pd.DataFrame]:
    """Load risk factors from CSV file (e.g., Fama-French factors).

    Expected format: [date, mkt_rf, smb, hml, mom, rf] or similar

    Args:
        factors_path: Path to factors CSV file

    Returns:
        DataFrame with risk factors or None if not found
    """
    try:
        if not factors_path.exists():
            print(f"Warning: Factors file not found: {factors_path}")
            return None

        factors = pd.read_csv(factors_path)

        # Standardize date column
        if 'date' in factors.columns:
            factors['date'] = pd.to_datetime(factors['date'])
        elif 'Date' in factors.columns:
            factors['Date'] = pd.to_datetime(factors['Date'])
            factors = factors.rename(columns={'Date': 'date'})
        else:
            print("Warning: No date column found in factors file")
            return None

        # Ensure monthly data (convert to month-end if needed)
        factors['date'] = factors['date'].dt.to_period('M').dt.to_timestamp('M')

        print(f"Loaded {len(factors)} factor observations from {factors_path}")
        return factors

    except Exception as e:
        print(f"Warning: Could not load factors from {factors_path}: {e}")
        return None


def compute_excess_returns(panel: pd.DataFrame, factors: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Compute excess returns using risk-free rate from factors.

    Args:
        panel: Panel with returns
        factors: Risk factors with 'rf' column

    Returns:
        Panel with excess_ret column added
    """
    df = panel.copy()

    if factors is None or 'rf' not in factors.columns:
        print("Warning: No risk-free rate available, using raw returns")
        if 'ret' in df.columns:
            df['excess_ret'] = df['ret']
        return df

    # Merge risk-free rate
    rf_data = factors[['date', 'rf']].copy()
    df = df.merge(rf_data, on='date', how='left')

    # Compute excess returns
    if 'ret' in df.columns:
        df['excess_ret'] = df['ret'] - df['rf'].fillna(0).infer_objects(copy=False)
    else:
        print("Warning: No return column found for excess return calculation")

    # Clean up
    df = df.drop(columns=['rf'], errors='ignore')

    return df


def build_tree_ready(panel: pd.DataFrame, factors: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Build tree-ready dataset with excess returns if factors present.

    Args:
        panel: Panel with characteristics
        factors: Optional risk factors

    Returns:
        Tree-ready panel with excess_ret if factors available
    """
    df = panel.copy()

    # Add excess returns if factors available
    if factors is not None:
        print("Computing excess returns using risk factors...")
        df = compute_excess_returns(df, factors)

    # Ensure proper date formatting
    df['date'] = pd.to_datetime(df['date'])

    return df


def prepare_tree_input(panel: pd.DataFrame, output_path: Optional[Path] = None,
                      factors: Optional[pd.DataFrame] = None,
                      winsorize_pcts: tuple = (0.01, 0.99),
                      standardization: str = 'minmax',
                      fill_missing: float = 0.0) -> pd.DataFrame:
    """Main function to prepare panel data for P-Trees input.

    Steps:
    1. Build tree-ready data (add excess returns if factors present)
    2. Validate panel structure
    3. Identify characteristics
    4. Winsorize at 1%/99% per month
    5. Standardize to [-1,1] per month (min-max)
    6. Fill missing values with 0 (neutral)
    7. Export to parquet and CSV

    Args:
        panel: Input panel with characteristics
        output_path: Optional output directory path
        factors: Optional risk factors for excess return calculation
        winsorize_pcts: Tuple of (lower, upper) percentiles for winsorization
        standardization: 'minmax' or 'zscore'
        fill_missing: Value to fill missing with

    Returns:
        Final processed dataframe
    """
    print("=" * 60)
    print("P-TREES PREPROCESSING PIPELINE")
    print("=" * 60)

    # 1. Build tree-ready data with excess returns
    print("\n1. Building tree-ready dataset...")
    df = build_tree_ready(panel, factors)

    # 2. Validate structure
    print("\n2. Validating panel structure...")
    if not validate_panel_structure(df):
        raise ValueError("Panel validation failed")

    print(f"   Panel shape: {df.shape}")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   Unique RICs: {df['ric'].nunique()}")

    # 3. Identify characteristics
    print("\n3. Identifying characteristics...")
    char_cols = identify_characteristics(df)

    if not char_cols:
        raise ValueError("No characteristic columns found in panel")

    print(f"   Found {len(char_cols)} characteristics:")
    for col in sorted(char_cols):
        non_na = df[col].notna().sum()
        print(f"   - {col}: {non_na:,} non-missing values")

    # 4. Winsorize
    print("\n4. Winsorizing characteristics...")
    df = winsorize_characteristics(df, char_cols, winsorize_pcts[0], winsorize_pcts[1])

    # 5. Standardize
    print("\n5. Standardizing characteristics...")
    df = standardize_characteristics(df, char_cols, method=standardization)

    # 6. Fill missing values
    print("\n6. Filling missing values...")
    df = fill_missing_values(df, char_cols, fill_missing)

    # 7. Final data quality checks
    print("\n7. Final data quality checks...")

    # Check for any remaining issues
    total_obs = len(df)
    complete_obs = df[['ric', 'date'] + char_cols].dropna().shape[0]

    print(f"   Total observations: {total_obs:,}")
    print(f"   Complete observations: {complete_obs:,} ({complete_obs/total_obs:.1%})")

    # Summary statistics for key characteristics
    key_chars = [col for col in ['size', 'bm', 'mom_12_1', 'op_prof', 'turnover'] if col in char_cols]
    if key_chars:
        print("\n   Summary of key characteristics (post-processing):")
        summary = df[key_chars].describe()
        print(summary.round(3))

    # 8. Export if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"\n8. Exporting to {output_path}...")

        # Select final columns for export (include excess_ret if available)
        export_cols = ['ric', 'date', 'ret', 'mkt_cap']
        if 'excess_ret' in df.columns:
            export_cols.append('excess_ret')
        export_cols.extend(char_cols)
        export_cols = [col for col in export_cols if col in df.columns]

        export_df = df[export_cols].copy()

        # Export to parquet (primary format)
        parquet_path = output_path / "tree_input.parquet"
        export_df.to_parquet(parquet_path, index=False)
        print(f"   Saved parquet: {parquet_path} ({parquet_path.stat().st_size / 1024 / 1024:.1f} MB)")

        # Export to CSV (for compatibility)
        csv_path = output_path / "tree_input.csv"
        export_df.to_csv(csv_path, index=False)
        print(f"   Saved CSV: {csv_path} ({csv_path.stat().st_size / 1024 / 1024:.1f} MB)")

        # Export metadata
        metadata = {
            'processing_date': pd.Timestamp.now().isoformat(),
            'total_observations': len(export_df),
            'unique_rics': export_df['ric'].nunique(),
            'date_range': [export_df['date'].min().isoformat(), export_df['date'].max().isoformat()],
            'characteristics': char_cols,
            'has_excess_returns': 'excess_ret' in df.columns,
            'winsorize_percentiles': winsorize_pcts,
            'standardization_method': standardization,
            'missing_fill_value': fill_missing,
        }

        metadata_path = output_path / "tree_input_metadata.json"
        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        print(f"   Saved metadata: {metadata_path}")

    print("\n" + "=" * 60)
    print("P-TREES PREPROCESSING COMPLETED SUCCESSFULLY")
    print("=" * 60)

    return df


def quick_summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Generate quick summary statistics for the processed data.

    Args:
        df: Processed dataframe

    Returns:
        Summary statistics dataframe
    """
    char_cols = identify_characteristics(df)

    if not char_cols:
        return pd.DataFrame()

    summary = df[char_cols].describe().round(4)

    # Add additional statistics
    extra_stats = pd.DataFrame(index=['missing_pct', 'zeros_pct'])

    for col in char_cols:
        missing_pct = df[col].isna().mean() * 100
        zeros_pct = (df[col] == 0).mean() * 100

        extra_stats.loc['missing_pct', col] = missing_pct
        extra_stats.loc['zeros_pct', col] = zeros_pct

    summary = pd.concat([summary, extra_stats])

    return summary