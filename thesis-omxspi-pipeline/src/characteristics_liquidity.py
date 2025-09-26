from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional


def compute_amihud_illiquidity(daily_data: pd.DataFrame) -> pd.DataFrame:
    """Compute Amihud (2002) illiquidity measure from daily data.

    Amihud monthly = mean( |ret_daily| / (price_daily * volume_daily) ) over days in month

    Args:
        daily_data: Daily data with [ric, date, close, volume, ret?]

    Returns:
        DataFrame with [ric, date, amihud]
    """
    df = daily_data.copy()
    df = df.sort_values(["ric", "date"])

    # Compute returns if not available
    if "ret" not in df.columns:
        df["ret"] = df.groupby("ric")["close"].pct_change()

    # Compute daily Amihud: |ret| / (price * volume)
    df["daily_amihud"] = np.where(
        (df["volume"] > 0) & (df["close"] > 0),
        np.abs(df["ret"]) / (df["close"] * df["volume"]),
        np.nan
    )

    # Aggregate to monthly: mean over days in each month
    monthly_results = []

    for ric in df["ric"].unique():
        ric_data = df[df["ric"] == ric].copy()
        ric_data["year_month"] = ric_data["date"].dt.to_period("M")

        for period, group in ric_data.groupby("year_month"):
            # Need at least 3 trading days for reliable estimate
            valid_days = group["daily_amihud"].notna().sum()
            if valid_days >= 3:
                monthly_amihud = group["daily_amihud"].mean()
                monthly_results.append({
                    "ric": ric,
                    "date": group["date"].iloc[-1],  # Last day of month
                    "amihud": monthly_amihud
                })

    if monthly_results:
        return pd.DataFrame(monthly_results)
    else:
        return pd.DataFrame(columns=["ric", "date", "amihud"])


def compute_amihud_monthly_fallback(monthly_data: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly Amihud fallback when daily data not available.

    Monthly fallback: amihud_m = |ret_monthly| / dolvol_monthly

    Args:
        monthly_data: Monthly data with [ric, date, ret, dolvol]

    Returns:
        DataFrame with [ric, date, amihud_m]
    """
    df = monthly_data.copy()

    # Check required columns
    if not all(col in df.columns for col in ["ret", "dolvol"]):
        print("Warning: Missing required columns (ret, dolvol) for monthly Amihud fallback")
        return pd.DataFrame(columns=["ric", "date", "amihud_m"])

    # Compute monthly Amihud fallback
    df["amihud_m"] = np.where(
        df["dolvol"] > 0,
        np.abs(df["ret"]) / df["dolvol"],
        np.nan
    )

    return df[["ric", "date", "amihud_m"]].dropna()


def compute_bid_ask_spread(daily_data: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    """Compute bid-ask spread measures if bid/ask data available.

    Args:
        daily_data: Daily data with [ric, date, close, bid?, ask?]
        window: Rolling window for averaging

    Returns:
        DataFrame with [ric, date, ba_spread, effective_spread?]
    """
    if "bid" not in daily_data.columns or "ask" not in daily_data.columns:
        print("Warning: Bid/ask data not available for spread calculation")
        return pd.DataFrame(columns=["ric", "date", "ba_spread"])

    df = daily_data.copy()
    df = df.sort_values(["ric", "date"])

    # Compute quoted spread
    df["ba_spread"] = np.where(
        (df["bid"] > 0) & (df["ask"] > 0) & (df["ask"] > df["bid"]),
        2 * (df["ask"] - df["bid"]) / (df["ask"] + df["bid"]),
        np.nan
    )

    # Compute effective spread (using close as transaction price proxy)
    if "close" in df.columns:
        midpoint = (df["bid"] + df["ask"]) / 2
        df["effective_spread"] = np.where(
            midpoint > 0,
            2 * np.abs(df["close"] - midpoint) / midpoint,
            np.nan
        )

    # Rolling averages
    spread_cols = ["ba_spread"]
    if "effective_spread" in df.columns:
        spread_cols.append("effective_spread")

    for col in spread_cols:
        df[f"{col}_avg"] = (
            df.groupby("ric")[col]
            .rolling(window, min_periods=max(1, window // 2))
            .mean()
            .values
        )

    # Aggregate to monthly
    agg_dict = {f"{col}_avg": "last" for col in spread_cols}
    agg_dict["date"] = "last"

    monthly = (
        df.groupby(["ric", df["date"].dt.to_period("M")])
        .agg(agg_dict)
        .reset_index(drop=True)
    )

    # Rename columns
    rename_dict = {f"{col}_avg": col for col in spread_cols}
    monthly = monthly.rename(columns=rename_dict)

    return monthly.dropna()


def compute_turnover_metrics(panel: pd.DataFrame, daily_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Compute various turnover-based liquidity metrics.

    Args:
        panel: Monthly panel data
        daily_data: Optional daily data for more precise calculations

    Returns:
        DataFrame with additional turnover metrics
    """
    df = panel.copy()

    if daily_data is not None:
        # Use daily data for more accurate calculations
        daily_df = daily_data.copy()
        daily_df = daily_df.sort_values(["ric", "date"])

        # Compute daily turnover
        if "turnover" not in daily_df.columns and "volume" in daily_df.columns:
            # Merge shares outstanding from monthly panel
            shares_data = panel[["ric", "date", "commonsharesoutstanding"]].dropna()
            daily_df = pd.merge_asof(
                daily_df.sort_values(["ric", "date"]),
                shares_data.sort_values(["ric", "date"]),
                by="ric",
                on="date",
                direction="backward"
            )
            daily_df["turnover"] = daily_df["volume"] / daily_df["commonsharesoutstanding"]

        # Compute turnover metrics from daily data
        monthly_metrics = []
        for ric in daily_df["ric"].unique():
            ric_data = daily_df[daily_df["ric"] == ric].copy()

            # Group by month
            ric_data["year_month"] = ric_data["date"].dt.to_period("M")
            for period, group in ric_data.groupby("year_month"):
                if len(group) >= 5:  # Require at least 5 days
                    metrics = {
                        "ric": ric,
                        "date": group["date"].iloc[-1],  # Last day of month
                        "turnover_mean": group["turnover"].mean(),
                        "turnover_std": group["turnover"].std(),
                        "turnover_median": group["turnover"].median(),
                        "zero_volume_days": (group["volume"] == 0).sum(),
                        "total_days": len(group),
                    }
                    metrics["zero_volume_pct"] = metrics["zero_volume_days"] / metrics["total_days"]
                    monthly_metrics.append(metrics)

        if monthly_metrics:
            turnover_df = pd.DataFrame(monthly_metrics)
            # Merge back to main panel
            df = df.merge(turnover_df, on=["ric", "date"], how="left", suffixes=("", "_daily"))

    # Fallback: compute from monthly data
    if "turnover" in df.columns:
        # Rolling turnover statistics
        df = df.sort_values(["ric", "date"])

        # 3-month rolling statistics
        df["turnover_3m_mean"] = (
            df.groupby("ric")["turnover"]
            .rolling(3, min_periods=1)
            .mean()
            .values
        )

        df["turnover_3m_std"] = (
            df.groupby("ric")["turnover"]
            .rolling(3, min_periods=2)
            .std()
            .values
        )

        # 12-month rolling statistics
        df["turnover_12m_mean"] = (
            df.groupby("ric")["turnover"]
            .rolling(12, min_periods=6)
            .mean()
            .values
        )

        df["turnover_12m_std"] = (
            df.groupby("ric")["turnover"]
            .rolling(12, min_periods=6)
            .std()
            .values
        )

        # Turnover consistency (inverse of coefficient of variation)
        df["turnover_consistency"] = np.where(
            df["turnover_12m_std"] > 0,
            df["turnover_12m_mean"] / df["turnover_12m_std"],
            np.nan
        )

    return df


def compute_price_impact_proxy(daily_data: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    """Compute price impact proxy using return reversal after high volume.

    Args:
        daily_data: Daily data with returns and volume
        window: Window for impact calculation

    Returns:
        DataFrame with price impact measure
    """
    df = daily_data.copy()
    df = df.sort_values(["ric", "date"])

    # Compute returns if not available
    if "ret" not in df.columns:
        df["ret"] = df.groupby("ric")["close"].pct_change()

    # Volume relative to recent average
    df["volume_rel"] = (
        df["volume"] / df.groupby("ric")["volume"]
        .rolling(window, min_periods=max(1, window // 2))
        .mean()
        .values
    )

    # Price impact proxy: correlation between volume and subsequent return reversal
    def compute_impact(group):
        if len(group) < window:
            return pd.Series([np.nan] * len(group))

        impact = []
        for i in range(len(group)):
            if i < 5:  # Need some history
                impact.append(np.nan)
                continue

            # Look at last 5 days
            recent_vol = group["volume_rel"].iloc[max(0, i-4):i+1]
            recent_ret = group["ret"].iloc[max(0, i-4):i+1]

            # Price impact proxy: negative correlation between volume and next-day return
            if len(recent_vol) >= 3 and recent_vol.std() > 0 and recent_ret.std() > 0:
                # Simplified proxy: high volume days followed by return reversal
                high_vol_days = recent_vol > recent_vol.median()
                if high_vol_days.sum() > 0:
                    avg_ret_after_high_vol = recent_ret[high_vol_days.shift(1, fill_value=False)].mean()
                    avg_ret_after_low_vol = recent_ret[~high_vol_days.shift(1, fill_value=False)].mean()
                    impact_measure = avg_ret_after_low_vol - avg_ret_after_high_vol  # Positive = more impact
                    impact.append(impact_measure)
                else:
                    impact.append(np.nan)
            else:
                impact.append(np.nan)

        return pd.Series(impact, index=group.index)

    df["price_impact"] = df.groupby("ric", group_keys=False).apply(compute_impact).values

    # Aggregate to monthly
    monthly = (
        df.groupby(["ric", df["date"].dt.to_period("M")])
        .agg({"price_impact": "mean", "date": "last"})
        .reset_index(drop=True)
    )

    return monthly[["ric", "date", "price_impact"]].dropna()


def add_liquidity_characteristics(panel: pd.DataFrame, daily_aux: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Add comprehensive liquidity characteristics to the panel.

    Args:
        panel: Monthly panel with basic data
        daily_aux: Optional daily auxiliary data for enhanced calculations

    Returns:
        Panel with additional liquidity characteristics
    """
    df = panel.copy()

    print("Computing liquidity characteristics...")

    # Basic turnover metrics (always available)
    df = compute_turnover_metrics(df, daily_aux)

    # Enhanced metrics from daily data
    if daily_aux is not None and not daily_aux.empty:
        print("Computing Amihud illiquidity from daily data...")
        try:
            amihud_data = compute_amihud_illiquidity(daily_aux)
            if not amihud_data.empty:
                df = df.merge(amihud_data, on=["ric", "date"], how="left")
                print(f"   Added Amihud for {len(amihud_data)} observations")
            else:
                print("   No valid Amihud data computed, trying monthly fallback...")
                amihud_fallback = compute_amihud_monthly_fallback(df)
                if not amihud_fallback.empty:
                    df = df.merge(amihud_fallback, on=["ric", "date"], how="left")
                    print(f"   Added monthly Amihud fallback for {len(amihud_fallback)} observations")
        except Exception as e:
            print(f"Warning: Could not compute Amihud measure from daily data: {e}")
            print("   Trying monthly fallback...")
            try:
                amihud_fallback = compute_amihud_monthly_fallback(df)
                if not amihud_fallback.empty:
                    df = df.merge(amihud_fallback, on=["ric", "date"], how="left")
                    print(f"   Added monthly Amihud fallback for {len(amihud_fallback)} observations")
            except Exception as e2:
                print(f"Warning: Monthly Amihud fallback also failed: {e2}")

        print("Computing bid-ask spreads...")
        try:
            spread_data = compute_bid_ask_spread(daily_aux)
            if not spread_data.empty:
                df = df.merge(spread_data, on=["ric", "date"], how="left")
                print(f"   Added bid-ask spreads for {len(spread_data)} observations")
        except Exception as e:
            print(f"Warning: Could not compute bid-ask spreads: {e}")

        print("Computing price impact proxy...")
        try:
            impact_data = compute_price_impact_proxy(daily_aux)
            if not impact_data.empty:
                df = df.merge(impact_data, on=["ric", "date"], how="left")
                print(f"   Added price impact for {len(impact_data)} observations")
        except Exception as e:
            print(f"Warning: Could not compute price impact: {e}")

    else:
        print("No daily auxiliary data provided, using monthly approximations only")
        # Compute monthly Amihud fallback
        try:
            amihud_fallback = compute_amihud_monthly_fallback(df)
            if not amihud_fallback.empty:
                df = df.merge(amihud_fallback, on=["ric", "date"], how="left")
                print(f"   Added monthly Amihud fallback for {len(amihud_fallback)} observations")
        except Exception as e:
            print(f"Warning: Could not compute monthly Amihud fallback: {e}")

    return df