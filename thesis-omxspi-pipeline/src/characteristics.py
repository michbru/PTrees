from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List, Optional
import warnings


def compute_core_characteristics(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute core characteristics that must be present.

    Core characteristics:
    - size: log(mkt_cap)
    - bm: book-to-market ratio
    - mom_12_1: 12-month momentum excluding last month
    - op_prof: operating profitability
    - assets_growth: asset growth
    - turnover: share turnover
    - dolvol: dollar volume
    - zerotrade: zero trading indicator
    - roe: return on equity
    """
    df = panel.copy()
    df = df.sort_values(["ric", "date"])

    # Ensure we have the price column (adj_close or close)
    price_col = "adj_close" if "adj_close" in df.columns else "close"
    if price_col not in df.columns:
        raise ValueError("No price column (adj_close or close) found in panel")

    # Market cap (if not already computed)
    if "mkt_cap" not in df.columns:
        if "commonsharesoutstanding" in df.columns:
            df["mkt_cap"] = df["commonsharesoutstanding"] * df[price_col]
        else:
            raise ValueError("Cannot compute market cap: missing shares outstanding")

    # 1. Size (log market cap)
    df["size"] = np.log(df["mkt_cap"])

    # 2. Book-to-market
    if "shareholdersequity" in df.columns:
        df["bm"] = df["shareholdersequity"] / df["mkt_cap"]
    else:
        print("Warning: Cannot compute book-to-market (missing shareholdersequity)")
        df["bm"] = np.nan

    # 3. Momentum 12-1 (12 months excluding last month)
    if "ret" in df.columns:
        # 12-month momentum excluding last month
        df["mom_12_1"] = (
            df.groupby("ric")["ret"]
            .shift(1)  # Start from t-1
            .rolling(11)  # Take 11 months (t-12 to t-2)
            .apply(lambda x: (1 + x).prod() - 1 if len(x.dropna()) >= 6 else np.nan)
            .values
        )
    else:
        print("Warning: Cannot compute momentum (missing ret column)")
        df["mom_12_1"] = np.nan

    # 4. Operating profitability
    if "operatingincome" in df.columns:
        if "totalassets" in df.columns:
            df["op_prof"] = df["operatingincome"] / df["totalassets"]
        elif "shareholdersequity" in df.columns:
            df["op_prof"] = df["operatingincome"] / df["shareholdersequity"]
            print("Warning: Using equity instead of assets for operating profitability")
        else:
            print("Warning: Cannot compute operating profitability (missing denominator)")
            df["op_prof"] = np.nan
    else:
        print("Warning: Cannot compute operating profitability (missing operatingincome)")
        df["op_prof"] = np.nan

    # 5. Asset growth
    if "totalassets" in df.columns:
        df["assets_growth"] = df.groupby("ric")["totalassets"].pct_change()
    else:
        print("Warning: Cannot compute asset growth (missing totalassets)")
        df["assets_growth"] = np.nan

    # 6. Turnover
    if "volume" in df.columns and "commonsharesoutstanding" in df.columns:
        df["turnover"] = df["volume"] / df["commonsharesoutstanding"]
    else:
        print("Warning: Cannot compute turnover (missing volume or shares outstanding)")
        df["turnover"] = np.nan

    # 7. Dollar volume
    if "volume" in df.columns:
        df["dolvol"] = df["volume"] * df[price_col]
    else:
        print("Warning: Cannot compute dollar volume (missing volume)")
        df["dolvol"] = np.nan

    # 8. Zero trading indicator
    if "volume" in df.columns:
        df["zerotrade"] = (df["volume"] == 0).astype(int)
    else:
        print("Warning: Cannot compute zero trade indicator (missing volume)")
        df["zerotrade"] = np.nan

    # 9. Return on equity
    if "netincome" in df.columns and "shareholdersequity" in df.columns:
        df["roe"] = df["netincome"] / df["shareholdersequity"]
    else:
        print("Warning: Cannot compute ROE (missing netincome or shareholdersequity)")
        df["roe"] = np.nan

    return df


def compute_extended_characteristics(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute extended characteristics where inputs exist.

    Extended characteristics include:
    - Valuation: ep, cfp, sp, sgr
    - Profitability/quality: pm, gma
    - Investment/leverage: leverage, noa (approximate)
    - Liquidity variability: std_turn_3m, std_dolvol_3m
    - Volatility: rvar_3m
    - Momentum extensions: mom_6m, mom_36m
    """
    df = panel.copy()
    df = df.sort_values(["ric", "date"])

    price_col = "adj_close" if "adj_close" in df.columns else "close"

    # Add derived raw inputs if missing (margins, leverage ratios)
    # Gross margin = GrossProfit / Revenue
    if "grossmargin" not in df.columns and {"grossprofit", "revenue"}.issubset(df.columns):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            denom = df["revenue"]
            df["grossmargin"] = np.where(denom != 0, df["grossprofit"] / denom, np.nan)

    # Operating margin = OperatingIncome / Revenue
    if "operatingmargin" not in df.columns and {"operatingincome", "revenue"}.issubset(df.columns):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            denom = df["revenue"]
            df["operatingmargin"] = np.where(denom != 0, df["operatingincome"] / denom, np.nan)

    # Debt to assets = TotalDebt / TotalAssets
    if "debttoassets" not in df.columns and {"totaldebt", "totalassets"}.issubset(df.columns):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            denom = df["totalassets"]
            df["debttoassets"] = np.where(denom != 0, df["totaldebt"] / denom, np.nan)

    # Valuation characteristics
    # 1. Earnings-to-price ratio
    eps_col = None
    if "epsnormalized" in df.columns:
        eps_col = "epsnormalized"
    elif "epsreported" in df.columns:
        eps_col = "epsreported"

    if eps_col and "commonsharesoutstanding" in df.columns and "mkt_cap" in df.columns:
        df["ep"] = (df[eps_col] * df["commonsharesoutstanding"]) / df["mkt_cap"]
    elif "netincome" in df.columns and "mkt_cap" in df.columns:
        df["ep"] = df["netincome"] / df["mkt_cap"]
        print("Info: Using net income for E/P ratio (EPS not available)")
    else:
        print("Warning: Cannot compute E/P ratio")
        df["ep"] = np.nan

    # 2. Cash flow to price
    if "cashfromoperations" in df.columns and "mkt_cap" in df.columns:
        df["cfp"] = df["cashfromoperations"] / df["mkt_cap"]
    else:
        print("Warning: Cannot compute CF/P ratio (missing cash from operations)")
        df["cfp"] = np.nan

    # 3. Sales to price
    if "revenue" in df.columns and "mkt_cap" in df.columns:
        df["sp"] = df["revenue"] / df["mkt_cap"]
    else:
        print("Warning: Cannot compute S/P ratio (missing revenue)")
        df["sp"] = np.nan

    # 4. Sales growth
    if "revenue" in df.columns:
        df["sgr"] = df.groupby("ric")["revenue"].pct_change()
    else:
        print("Warning: Cannot compute sales growth (missing revenue)")
        df["sgr"] = np.nan

    # Profitability/quality characteristics
    # 5. Profit margin
    if "netincome" in df.columns and "revenue" in df.columns:
        # Guard against division by zero
        df["pm"] = np.where(df["revenue"] != 0, df["netincome"] / df["revenue"], np.nan)
    else:
        print("Warning: Cannot compute profit margin")
        df["pm"] = np.nan

    # 6. Gross margin to assets
    if "grossprofit" in df.columns:
        if "totalassets" in df.columns:
            df["gma"] = df["grossprofit"] / df["totalassets"]
        elif "shareholdersequity" in df.columns:
            df["gma"] = df["grossprofit"] / df["shareholdersequity"]
            print("Info: Using equity instead of assets for GMA")
        else:
            print("Warning: Cannot compute gross margin to assets")
            df["gma"] = np.nan
    else:
        print("Warning: Cannot compute gross margin to assets (missing gross profit)")
        df["gma"] = np.nan

    # Investment/leverage characteristics
    # 7. Leverage
    debt_col = None
    if "totaldebt" in df.columns:
        debt_col = "totaldebt"
    elif "longtermdebt" in df.columns:
        debt_col = "longtermdebt"
        print("Info: Using long-term debt for leverage ratio")

    if debt_col and "totalassets" in df.columns:
        df["leverage"] = df[debt_col] / df["totalassets"]
    else:
        print("Warning: Cannot compute leverage ratio")
        df["leverage"] = np.nan

    # 8. Net operating assets (approximate)
    if all(col in df.columns for col in ["totalassets", "currentliabilities"]):
        # Approximate NOA = Total Assets - Current Liabilities - Cash
        # If no cash field, use Current Assets as proxy for cash position
        if "currentassets" in df.columns:
            # Very rough approximation
            df["noa"] = df["totalassets"] - df["currentliabilities"] - (df["currentassets"] * 0.1)  # Assume 10% of CA is cash
        else:
            df["noa"] = df["totalassets"] - df["currentliabilities"]
            print("Info: Approximate NOA without cash adjustment")
    else:
        print("Warning: Cannot compute NOA (missing required fields)")
        df["noa"] = np.nan

    # Liquidity variability characteristics
    # 9. Turnover volatility (3-month)
    if "turnover" in df.columns:
        df["std_turn_3m"] = df.groupby("ric")["turnover"].rolling(3, min_periods=2).std().values
    else:
        print("Warning: Cannot compute turnover volatility (missing turnover)")
        df["std_turn_3m"] = np.nan

    # 10. Dollar volume volatility (3-month)
    if "dolvol" in df.columns:
        df["std_dolvol_3m"] = df.groupby("ric")["dolvol"].rolling(3, min_periods=2).std().values
    else:
        print("Warning: Cannot compute dollar volume volatility (missing dolvol)")
        df["std_dolvol_3m"] = np.nan

    # Volatility characteristics
    # 11. Return variance (3-month)
    if "ret" in df.columns:
        df["rvar_3m"] = df.groupby("ric")["ret"].rolling(3, min_periods=2).var().values
    else:
        print("Warning: Cannot compute return variance (missing returns)")
        df["rvar_3m"] = np.nan

    # Momentum extensions
    # 12. 6-month momentum (excluding last month)
    if "ret" in df.columns:
        df["mom_6m"] = (
            df.groupby("ric")["ret"]
            .shift(1)  # Start from t-1
            .rolling(5)  # Take 5 months (t-6 to t-2)
            .apply(lambda x: (1 + x).prod() - 1 if len(x.dropna()) >= 3 else np.nan)
            .values
        )
    else:
        df["mom_6m"] = np.nan

    # 13. 36-month momentum (excluding last month)
    if "ret" in df.columns:
        df["mom_36m"] = (
            df.groupby("ric")["ret"]
            .shift(1)  # Start from t-1
            .rolling(35)  # Take 35 months (t-36 to t-2)
            .apply(lambda x: (1 + x).prod() - 1 if len(x.dropna()) >= 24 else np.nan)
            .values
        )
    else:
        df["mom_36m"] = np.nan

    return df


def winsorize_by_month(df: pd.DataFrame, cols: List[str], lower: float = 0.01, upper: float = 0.99) -> pd.DataFrame:
    """Winsorize characteristics by month at specified percentiles."""
    df = df.copy()

    def winsorize_group(group):
        for col in cols:
            if col in group.columns and not group[col].isna().all():
                q_low = group[col].quantile(lower)
                q_high = group[col].quantile(upper)
                group[col] = group[col].clip(lower=q_low, upper=q_high)
        return group

    # Winsorize by date
    df = df.groupby('date', group_keys=False).apply(winsorize_group)
    return df


def standardize_to_unit(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Standardize characteristics to [-1, 1] range per month using min-max scaling."""
    df = df.copy()

    def standardize_group(group):
        for col in cols:
            if col in group.columns and not group[col].isna().all():
                min_val = group[col].min()
                max_val = group[col].max()
                if min_val == max_val:
                    # If constant, set to zero
                    group[col] = 0.0
                else:
                    # Min-max scale to [-1, 1]
                    group[col] = 2 * (group[col] - min_val) / (max_val - min_val) - 1
        return group

    # Standardize by date
    df = df.groupby('date', group_keys=False).apply(standardize_group)
    return df


def compute_industry_adjusted_characteristics(panel: pd.DataFrame,
                                            characteristics_to_adjust: Optional[List[str]] = None) -> pd.DataFrame:
    """Compute industry-adjusted versions of key characteristics.

    Industry adjustment: demean within industry each month, then global standardization
    still maps to [-1,1]. Suffix names with _ia (e.g., bm_ia, size_ia).

    Args:
        panel: Panel with characteristics and industry codes
        characteristics_to_adjust: List of characteristic names to adjust. If None, uses default set.

    Returns:
        Panel with additional industry-adjusted characteristics
    """
    df = panel.copy()

    # Default characteristics to industry-adjust
    if characteristics_to_adjust is None:
        characteristics_to_adjust = ['size', 'bm', 'op_prof', 'pm', 'roe', 'leverage', 'turnover']

    # Check if industry codes are available
    industry_col = None
    if 'trbc_sector' in df.columns:
        industry_col = 'trbc_sector'
    elif 'trbc_industry' in df.columns:
        industry_col = 'trbc_industry'
    elif 'icb_industry' in df.columns:
        industry_col = 'icb_industry'
    elif 'icb_supersector' in df.columns:
        industry_col = 'icb_supersector'

    if industry_col is None:
        print("Warning: No industry classification found, skipping industry adjustments")
        return df

    print(f"Computing industry-adjusted characteristics using {industry_col}")

    def industry_adjust_by_month(group):
        """Adjust characteristics within each date-industry group"""
        for char in characteristics_to_adjust:
            if char in group.columns and char in df.columns:
                # Create industry-adjusted version
                ia_char = f"{char}_ia"

                if industry_col in group.columns:
                    # Group by industry within this month
                    for industry, ind_group in group.groupby(industry_col):
                        if len(ind_group) > 1 and not ind_group[char].isna().all():
                            # Demean within industry
                            industry_mean = ind_group[char].mean()
                            mask = (group[industry_col] == industry)
                            group.loc[mask, ia_char] = group.loc[mask, char] - industry_mean
                        else:
                            # If only one company in industry, set to zero (no adjustment needed)
                            mask = (group[industry_col] == industry)
                            group.loc[mask, ia_char] = 0.0
                else:
                    # Fallback: no industry adjustment possible
                    group[ia_char] = group[char]

        return group

    # Apply industry adjustment by date
    adjusted_chars = []
    try:
        df = df.groupby('date', group_keys=False).apply(industry_adjust_by_month)

        # Track which characteristics were adjusted
        for char in characteristics_to_adjust:
            ia_char = f"{char}_ia"
            if ia_char in df.columns:
                adjusted_chars.append(ia_char)

        if adjusted_chars:
            print(f"   Added {len(adjusted_chars)} industry-adjusted characteristics: {adjusted_chars}")
        else:
            print("   No industry-adjusted characteristics added")

    except Exception as e:
        print(f"Warning: Could not compute industry-adjusted characteristics: {e}")

    return df


def finalize_characteristics(panel: pd.DataFrame, daily_aux: Optional[pd.DataFrame] = None,
                           include_industry_adjusted: bool = False) -> pd.DataFrame:
    """Main function to compute all characteristics, apply preprocessing, and return final dataset.

    Args:
        panel: Main monthly panel with prices, fundamentals, etc.
        daily_aux: Optional daily price/volume data for enhanced calculations
        include_industry_adjusted: Whether to compute industry-adjusted variants

    Returns:
        Final characteristics dataframe ready for P-Trees
    """
    print("Computing core characteristics...")
    df = compute_core_characteristics(panel)

    print("Computing extended characteristics...")
    df = compute_extended_characteristics(df)

    # Add industry-adjusted variants if requested
    if include_industry_adjusted:
        print("Computing industry-adjusted characteristics...")
        df = compute_industry_adjusted_characteristics(df)

    # Note: Enhanced liquidity/volatility measures are added separately in run_pipeline
    # This keeps the characteristics module focused on core computations

    # Identify all characteristic columns (exclude basic identifiers and raw data)
    exclude_cols = {
        'ric', 'date', 'ret', 'mkt_cap', 'close', 'adj_close', 'volume',
        'totalassets', 'shareholdersequity', 'netincome', 'operatingincome',
        'revenue', 'commonsharesoutstanding', 'epsnormalized', 'epsreported',
        'cashfromoperations', 'grossprofit', 'totaldebt', 'longtermdebt',
        'currentassets', 'currentliabilities', 'freq', 'trbc_sector',
        'trbc_industry', 'icb_industry', 'icb_supersector'
    }

    char_cols = [col for col in df.columns if col not in exclude_cols and not col.endswith('_error')]

    # Remove rows with no characteristics computed
    if char_cols:
        has_any_char = df[char_cols].notna().any(axis=1)
        df = df[has_any_char].copy()

    if df.empty:
        print("Warning: No valid characteristics computed!")
        return df

    # Don't apply preprocessing here - that's done in ptree_prep.py
    # Just return the raw characteristics

    # Select final columns for output
    output_cols = ['ric', 'date', 'ret', 'mkt_cap'] + char_cols

    # Only include columns that exist
    output_cols = [col for col in output_cols if col in df.columns]

    final_df = df[output_cols].copy()

    print(f"Computed {len(char_cols)} characteristics for {len(final_df)} observations")
    print(f"Characteristics: {char_cols}")

    return final_df
