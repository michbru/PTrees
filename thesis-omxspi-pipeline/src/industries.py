from __future__ import annotations
import pandas as pd
import lseg.data as ld
from tqdm import tqdm
from .lseg_session import session_scope
from .utils import chunks


INDUSTRY_FIELDS = [
    "TR.TRBCEconomicSector",      # TRBC Economic Sector
    "TR.TRBCIndustryGroup",       # TRBC Industry Group
    # ICB alternatives (fallbacks)
    "TR.ICBIndustry",             # ICB Industry
    "TR.ICBSuperSector",          # ICB Super Sector
]


def pull_industry_codes(universe: pd.DataFrame) -> pd.DataFrame:
    """Pull industry classifications for all RICs.
    Returns: [ric, trbc_sector, trbc_industry, icb_industry?, icb_supersector?]
    """
    rics = sorted(universe["ric"].unique())

    frames = []
    with session_scope():
        for batch in tqdm(list(chunks(rics, 100)), desc="Industry codes"):
            try:
                df = ld.get_data(batch, INDUSTRY_FIELDS)
                if not df.empty and "Instrument" in df.columns:
                    # Rename columns
                    df = df.rename(columns={"Instrument": "ric"})

                    # Clean up column names
                    column_mapping = {}
                    for col in df.columns:
                        if col == "ric":
                            continue
                        elif "TRBCEconomicSector" in col:
                            column_mapping[col] = "trbc_sector"
                        elif "TRBCIndustryGroup" in col:
                            column_mapping[col] = "trbc_industry"
                        elif "ICBIndustry" in col:
                            column_mapping[col] = "icb_industry"
                        elif "ICBSuperSector" in col:
                            column_mapping[col] = "icb_supersector"

                    df = df.rename(columns=column_mapping)
                    frames.append(df)
            except Exception as e:
                print(f"Warning: Could not pull industry codes for batch: {e}")
                # Add empty frame with just RICs to maintain coverage
                frames.append(pd.DataFrame({"ric": batch}))

    industry_data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # Remove duplicates (keep first occurrence)
    if not industry_data.empty:
        industry_data = industry_data.drop_duplicates(subset=["ric"], keep="first")

    return industry_data


def attach_industry(panel: pd.DataFrame, industry_codes: pd.DataFrame = None) -> pd.DataFrame:
    """Attach industry codes to the panel.
    If industry_codes is None, will pull fresh codes from universe in panel.
    """
    if industry_codes is None:
        # Extract unique RICs and pull industry codes
        uni_df = panel[["ric"]].drop_duplicates()
        industry_codes = pull_industry_codes(uni_df)

    # Merge industry codes
    panel_with_industry = panel.merge(industry_codes, on="ric", how="left")

    return panel_with_industry


def industry_adjust_cross_section(df: pd.DataFrame, col: str, level: str = 'sector') -> pd.DataFrame:
    """Industry-adjust a characteristic by demeaning and z-scoring within industry per month.

    Args:
        df: Panel with date, ric, and the characteristic column
        col: Name of characteristic column to adjust
        level: 'sector' (use trbc_sector) or 'industry' (use trbc_industry)

    Returns:
        DataFrame with additional column: {col}_ind_adj
    """
    df = df.copy()

    # Choose industry level
    if level == 'sector':
        ind_col = 'trbc_sector'
    elif level == 'industry':
        ind_col = 'trbc_industry'
    else:
        raise ValueError("level must be 'sector' or 'industry'")

    # Check if required columns exist
    if col not in df.columns:
        print(f"Warning: Column '{col}' not found in dataframe")
        return df

    if ind_col not in df.columns:
        print(f"Warning: Industry column '{ind_col}' not found in dataframe. Skipping industry adjustment.")
        return df

    def adjust_group(group):
        """Adjust within each date-industry group"""
        if len(group) <= 1 or group[col].std() == 0:
            # If only one company in industry or no variation, return zeros
            group[f"{col}_ind_adj"] = 0.0
        else:
            # Demean and z-score within industry
            mean_val = group[col].mean()
            std_val = group[col].std()
            group[f"{col}_ind_adj"] = (group[col] - mean_val) / std_val
        return group

    # Apply industry adjustment by date and industry
    adjusted_df = df.groupby(['date', ind_col], group_keys=False).apply(adjust_group)

    return adjusted_df


def industry_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Generate summary statistics by industry."""
    if 'trbc_sector' not in panel.columns:
        print("Warning: No industry codes found in panel")
        return pd.DataFrame()

    summary = panel.groupby('trbc_sector').agg({
        'ric': 'nunique',
        'mkt_cap': ['count', 'mean', 'median'] if 'mkt_cap' in panel.columns else 'count'
    }).round(2)

    # Flatten column names
    summary.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in summary.columns]
    summary = summary.rename(columns={'ric_nunique': 'num_companies'})

    return summary.reset_index()