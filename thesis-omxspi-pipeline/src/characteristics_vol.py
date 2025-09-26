from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional

try:
    from sklearn.linear_model import LinearRegression
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def compute_total_volatility(data: pd.DataFrame, windows: list = [3, 6, 12, 36]) -> pd.DataFrame:
    """Compute total return volatility over multiple horizons.

    Args:
        data: DataFrame with [ric, date, ret]
        windows: List of window lengths in months/periods

    Returns:
        DataFrame with volatility measures
    """
    df = data.copy()
    df = df.sort_values(["ric", "date"])

    if "ret" not in df.columns:
        print("Warning: No return column found for volatility calculation")
        return df

    for window in windows:
        col_name = f"vol_{window}m"
        df[col_name] = (
            df.groupby("ric")["ret"]
            .rolling(window, min_periods=max(1, window // 2))
            .std()
            .values
        )

        # Annualize if needed (assuming monthly data)
        df[col_name] = df[col_name] * np.sqrt(12)

    return df


def compute_idiosyncratic_volatility(panel: pd.DataFrame, market_ret: Optional[pd.Series] = None,
                                   windows: list = [3, 6, 12]) -> pd.DataFrame:
    """Compute idiosyncratic volatility using market model residuals.

    Args:
        panel: Panel with returns
        market_ret: Market return series (date, return). If None, use equal-weighted average
        windows: Rolling windows for calculation

    Returns:
        DataFrame with idiosyncratic volatility measures
    """
    df = panel.copy()
    df = df.sort_values(["ric", "date"])

    if "ret" not in df.columns:
        print("Warning: No return column found for idiosyncratic volatility")
        return df

    # Create market return if not provided
    if market_ret is None:
        print("Computing equal-weighted market return as benchmark")
        market_ret = (
            df.groupby("date")["ret"]
            .mean()
            .reset_index()
            .rename(columns={"ret": "mkt_ret"})
        )
    elif isinstance(market_ret, pd.Series):
        market_ret = market_ret.reset_index()
        market_ret.columns = ["date", "mkt_ret"]

    # Merge market return
    df = df.merge(market_ret, on="date", how="left")

    def compute_idio_vol(group, window):
        """Compute idiosyncratic volatility for one stock"""
        if len(group) < window or group["ret"].isna().all():
            return pd.Series([np.nan] * len(group), index=group.index)

        idio_vols = []
        for i in range(len(group)):
            end_idx = i + 1
            start_idx = max(0, end_idx - window)
            window_data = group.iloc[start_idx:end_idx]

            if len(window_data) < max(3, window // 2):
                idio_vols.append(np.nan)
                continue

            # Remove NaN values
            valid_data = window_data[["ret", "mkt_ret"]].dropna()
            if len(valid_data) < 3:
                idio_vols.append(np.nan)
                continue

            try:
                # Run market model regression: ret = alpha + beta * mkt_ret + error
                X = valid_data["mkt_ret"].values.reshape(-1, 1)
                y = valid_data["ret"].values

                if np.std(X) == 0:  # No variation in market returns
                    # Use total volatility as proxy
                    idio_vol = np.std(y)
                elif HAS_SKLEARN:
                    reg = LinearRegression().fit(X, y)
                    residuals = y - reg.predict(X)
                    idio_vol = np.std(residuals)
                else:
                    # Simple fallback: use correlation-based approach
                    corr = np.corrcoef(X.flatten(), y)[0, 1]
                    if not np.isnan(corr):
                        idio_vol = np.std(y) * np.sqrt(1 - corr**2)
                    else:
                        idio_vol = np.std(y)

                # Annualize (assuming monthly data)
                idio_vol = idio_vol * np.sqrt(12)
                idio_vols.append(idio_vol)

            except Exception:
                idio_vols.append(np.nan)

        return pd.Series(idio_vols, index=group.index)

    # Compute idiosyncratic volatility for each window
    for window in windows:
        col_name = f"ivol_{window}m"
        df[col_name] = df.groupby("ric", group_keys=False).apply(
            lambda g: compute_idio_vol(g, window)
        ).values

    return df


def compute_volatility_of_volatility(data: pd.DataFrame, vol_windows: list = [12],
                                   volvol_window: int = 12) -> pd.DataFrame:
    """Compute volatility of volatility (vol-of-vol).

    Args:
        data: DataFrame with return volatility measures
        vol_windows: Which volatility windows to use as base
        volvol_window: Window for computing vol-of-vol

    Returns:
        DataFrame with vol-of-vol measures
    """
    df = data.copy()

    for vol_win in vol_windows:
        vol_col = f"vol_{vol_win}m"
        if vol_col not in df.columns:
            continue

        volvol_col = f"volvol_{vol_win}m_{volvol_window}m"

        df[volvol_col] = (
            df.groupby("ric")[vol_col]
            .rolling(volvol_window, min_periods=max(1, volvol_window // 2))
            .std()
            .values
        )

    return df


def compute_downside_volatility(data: pd.DataFrame, threshold: float = 0,
                              windows: list = [3, 6, 12]) -> pd.DataFrame:
    """Compute downside volatility (volatility of negative returns).

    Args:
        data: DataFrame with returns
        threshold: Threshold for defining downside (default 0)
        windows: Rolling windows

    Returns:
        DataFrame with downside volatility measures
    """
    df = data.copy()

    if "ret" not in df.columns:
        print("Warning: No return column for downside volatility")
        return df

    def downside_vol(returns, thresh=threshold):
        """Calculate downside volatility"""
        downside_returns = returns[returns < thresh]
        if len(downside_returns) < 2:
            return np.nan
        return np.std(downside_returns) * np.sqrt(12)  # Annualize

    for window in windows:
        col_name = f"dvol_{window}m"
        df[col_name] = (
            df.groupby("ric")["ret"]
            .rolling(window, min_periods=max(1, window // 2))
            .apply(downside_vol)
            .values
        )

    return df


def compute_skewness_kurtosis(data: pd.DataFrame, windows: list = [12, 36]) -> pd.DataFrame:
    """Compute return skewness and kurtosis.

    Args:
        data: DataFrame with returns
        windows: Rolling windows

    Returns:
        DataFrame with skewness and kurtosis measures
    """
    df = data.copy()

    if "ret" not in df.columns:
        print("Warning: No return column for skewness/kurtosis")
        return df

    try:
        from scipy.stats import skew, kurtosis
        HAS_SCIPY = True
    except ImportError:
        HAS_SCIPY = False

    def safe_skew(x):
        try:
            if HAS_SCIPY and len(x.dropna()) >= 3:
                return skew(x.dropna())
            else:
                # Simple skewness approximation
                clean_x = x.dropna()
                if len(clean_x) >= 3:
                    mean = clean_x.mean()
                    std = clean_x.std()
                    if std > 0:
                        return ((clean_x - mean) ** 3).mean() / (std ** 3)
                return np.nan
        except:
            return np.nan

    def safe_kurtosis(x):
        try:
            if HAS_SCIPY and len(x.dropna()) >= 4:
                return kurtosis(x.dropna())
            else:
                # Simple kurtosis approximation
                clean_x = x.dropna()
                if len(clean_x) >= 4:
                    mean = clean_x.mean()
                    std = clean_x.std()
                    if std > 0:
                        return ((clean_x - mean) ** 4).mean() / (std ** 4) - 3
                return np.nan
        except:
            return np.nan

    for window in windows:
        # Skewness
        df[f"skew_{window}m"] = (
            df.groupby("ric")["ret"]
            .rolling(window, min_periods=max(3, window // 2))
            .apply(safe_skew)
            .values
        )

        # Kurtosis
        df[f"kurt_{window}m"] = (
            df.groupby("ric")["ret"]
            .rolling(window, min_periods=max(4, window // 2))
            .apply(safe_kurtosis)
            .values
        )

    return df


def compute_daily_volatility_metrics(daily_data: pd.DataFrame) -> pd.DataFrame:
    """Compute enhanced volatility metrics from daily data.

    Key metrics:
    - rvar_1m_d: monthly variance of daily returns
    - maxret_d: maximum daily return this month (optional)

    Args:
        daily_data: Daily price/return data

    Returns:
        DataFrame with daily-based volatility metrics aggregated to monthly
    """
    df = daily_data.copy()
    df = df.sort_values(["ric", "date"])

    # Compute daily returns if not available
    if "ret" not in df.columns and "close" in df.columns:
        df["ret"] = df.groupby("ric")["close"].pct_change()

    if "ret" not in df.columns:
        print("Warning: Cannot compute daily volatility metrics without returns")
        return pd.DataFrame(columns=["ric", "date"])

    # Aggregate to monthly
    monthly_metrics = []

    for ric in df["ric"].unique():
        ric_data = df[df["ric"] == ric].copy()
        ric_data["year_month"] = ric_data["date"].dt.to_period("M")

        for period, group in ric_data.groupby("year_month"):
            valid_returns = group["ret"].dropna()
            if len(valid_returns) < 5:  # Need at least 5 daily observations
                continue

            # Core metrics requested
            metrics = {
                "ric": ric,
                "date": group["date"].iloc[-1],  # Last day of month
                "rvar_1m_d": np.var(valid_returns),  # Monthly variance of daily returns
                "maxret_d": valid_returns.max(),     # Maximum daily return this month
            }

            # Additional useful metrics
            metrics.update({
                "minret_d": valid_returns.min(),     # Minimum daily return
                "daily_vol_realized": np.std(valid_returns) * np.sqrt(252),  # Annualized daily vol
                "ret_range": valid_returns.max() - valid_returns.min(),
                "trading_days": len(valid_returns),
            })

            monthly_metrics.append(metrics)

    if monthly_metrics:
        return pd.DataFrame(monthly_metrics)
    else:
        return pd.DataFrame(columns=["ric", "date", "rvar_1m_d", "maxret_d"])


def add_volatility_characteristics(panel: pd.DataFrame, daily_aux: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Add comprehensive volatility characteristics to the panel.

    If daily data available: compute rvar_1m_d (monthly variance of daily returns)
    If only monthly: keep rvar_3m from monthly returns

    Args:
        panel: Monthly panel with returns
        daily_aux: Optional daily data for enhanced calculations

    Returns:
        Panel with additional volatility characteristics
    """
    df = panel.copy()

    print("Computing volatility characteristics...")

    # Enhanced metrics from daily data (priority)
    daily_available = False
    if daily_aux is not None and not daily_aux.empty:
        print("Computing enhanced volatility metrics from daily data...")
        try:
            daily_vol_metrics = compute_daily_volatility_metrics(daily_aux)
            if not daily_vol_metrics.empty:
                df = df.merge(daily_vol_metrics, on=["ric", "date"], how="left")
                daily_available = True
                print(f"   Added daily volatility metrics for {len(daily_vol_metrics)} observations")
                print(f"   Includes: rvar_1m_d, maxret_d, daily_vol_realized")
        except Exception as e:
            print(f"Warning: Could not compute daily volatility metrics: {e}")

    # Monthly volatility metrics (fallback or complementary)
    if not daily_available:
        print("Using monthly volatility calculations...")
        # Basic total volatility (includes rvar_3m)
        df = compute_total_volatility(df, windows=[3, 12])  # Focus on 3m and 12m
    else:
        print("Adding complementary monthly volatility metrics...")
        # Still add some monthly metrics for comparison
        df = compute_total_volatility(df, windows=[3, 12])

    # Additional volatility characteristics (always compute)
    try:
        # Idiosyncratic volatility
        df = compute_idiosyncratic_volatility(df, windows=[3, 12])

        # Downside volatility
        df = compute_downside_volatility(df, windows=[3, 12])

        # Higher moments
        try:
            df = compute_skewness_kurtosis(df, windows=[12])
        except ImportError:
            print("Warning: scipy not available, skipping skewness/kurtosis")

    except Exception as e:
        print(f"Warning: Could not compute additional volatility metrics: {e}")

    return df