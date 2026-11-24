"""Real estate technical & fundamental indicators (Monthly RSI, Drawdown, Jeonse Momentum, Volume)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rsi(series: pd.Series, period: int = 12) -> pd.Series:
    """Compute Wilder's Relative Strength Index (RSI) on monthly real estate price indices."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, np.where(avg_gain > 0.0, 100.0, 50.0))
    return rsi


def lerp_score(val: float, best_val: float, worst_val: float, max_pts: int = 25) -> int:
    """Linear score (0~max_pts). Supports both lower-is-better and higher-is-better rules.

    Full max_pts is ONLY awarded when val reaches or exceeds best_val in the favorable direction.
    """
    if best_val < worst_val:
        # Lower is better (e.g., Supply-Demand <= 78, RSI <= 32, Drawdown <= -14%)
        if val <= best_val:
            return max_pts
        if val >= worst_val:
            return 0
        ratio = (worst_val - val) / (worst_val - best_val)
    else:
        # Higher is better (e.g., Jeonse Support Score >= +6)
        if val >= best_val:
            return max_pts
        if val <= worst_val:
            return 0
        ratio = (val - worst_val) / (best_val - worst_val)
    return max(0, min(max_pts - 1, int(round(ratio * (max_pts - 1)))))


def enrich_seoul_df(df: pd.DataFrame, price_col: str = "real_tx_idx") -> pd.DataFrame:
    """Attach monthly RSI(12), rolling 5Y & ATH drawdowns, Jeonse cushion, and volume ratios."""
    out = df.copy()
    px = out[price_col]

    out["RSI_12"] = compute_rsi(px, period=12)
    out["Sale_YoY"] = px.pct_change(12) * 100.0
    out["Jeonse_YoY"] = out["jeonse_idx"].pct_change(12) * 100.0
    # Positive spread = Jeonse rising faster than Sale price (classic floor-building buy signal)
    out["Jeonse_Lead_Spread"] = out["Jeonse_YoY"] - out["Sale_YoY"]

    # Relative Jeonse Ratio vs 5Y (60M) rolling average to normalize structural interest-rate shifts
    jr_ma60 = out["jeonse_ratio"].rolling(60, min_periods=12).mean()
    out["JR_Rel_5Y"] = out["jeonse_ratio"] - jr_ma60

    # Combined Jeonse Floor Support index: relative jeonse ratio + jeonse lead momentum
    # Typical range: -12 (bubble / weak floor) to +14 (strong floor / jeonse pushing sale price up)
    out["Jeonse_Support"] = (
        0.55 * out["JR_Rel_5Y"].fillna(0.0)
        + 0.45 * out["Jeonse_Lead_Spread"].clip(-18, 18).fillna(0.0)
    )

    out["MA_12"] = px.rolling(12).mean()
    out["MA_36"] = px.rolling(36).mean()

    # 5-year (60-month) rolling high drawdown & true all-time high drawdown
    out["High_5Y"] = px.rolling(60, min_periods=12).max()
    out["DD_5Y"] = (px / out["High_5Y"] - 1.0) * 100.0
    out["High_ATH"] = px.cummax()
    out["DD_ATH"] = (px / out["High_ATH"] - 1.0) * 100.0

    # Volume recovery ratio vs 36M rolling average
    vol_ma36 = out["volume"].rolling(36, min_periods=6).mean()
    out["Vol_Ratio_Pct"] = (out["volume"] / vol_ma36) * 100.0

    # 3-month mortgage rate change (rate pivot detector: negative = falling rates)
    out["Rate_Chg_3M"] = out["mortgage_rate"] - out["mortgage_rate"].shift(3)

    # Strictly causal (Out-of-Sample, zero look-ahead) rolling percentile ranks (0..100, higher = better buy)
    out["R_DD"] = rolling_percentile_rank(out["DD_5Y"], window=120, min_periods=24, lower_is_better=True)
    out["R_RSI"] = rolling_percentile_rank(out["RSI_12"], window=120, min_periods=24, lower_is_better=True)
    out["R_SD"] = rolling_percentile_rank(out["supply_demand"], window=120, min_periods=24, lower_is_better=True)
    out["R_JR"] = rolling_percentile_rank(out["jeonse_ratio"], window=120, min_periods=24, lower_is_better=False)
    out["R_JS"] = rolling_percentile_rank(out["Jeonse_Support"], window=60, min_periods=18, lower_is_better=False)
    out["R_RC"] = rolling_percentile_rank(out["Rate_Chg_3M"], window=120, min_periods=24, lower_is_better=True)
    out["R_KHAI"] = rolling_percentile_rank(out["khai"], window=120, min_periods=24, lower_is_better=True)
    out["R_SUP"] = rolling_percentile_rank(out["annual_supply"], window=120, min_periods=24, lower_is_better=True)

    return out


def rolling_percentile_rank(
    series: pd.Series,
    window: int = 120,
    min_periods: int = 24,
    lower_is_better: bool = True,
) -> pd.Series:
    """Strictly causal rolling percentile rank using ONLY past data up to month t (zero look-ahead)."""
    def _rank(arr: np.ndarray) -> float:
        cur = arr[-1]
        if np.isnan(cur):
            return np.nan
        valid = arr[~np.isnan(arr)]
        if len(valid) < 6:
            return 50.0
        if lower_is_better:
            return float((valid >= cur).mean()) * 100.0
        return float((valid <= cur).mean()) * 100.0

    return series.rolling(window=window, min_periods=min_periods).apply(_rank, raw=True)


def summarize_region_series(df: pd.DataFrame, col: str, name: str, badge: str) -> dict:
    """Summarize a Seoul regional index (Seoul Overall, Gangnam, Gangbuk, Real Tx)."""
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest
    prev_1y = df.iloc[-13] if len(df) >= 13 else df.iloc[0]

    val = float(latest[col])
    prev_val = float(prev[col])
    mom_pct = ((val / prev_val) - 1.0) * 100.0 if prev_val else 0.0
    yoy_pct = ((val / float(prev_1y[col])) - 1.0) * 100.0 if float(prev_1y[col]) else 0.0

    recent_5y = df.tail(60)
    peak_idx = recent_5y[col].idxmax()
    peak_5y = float(recent_5y.loc[peak_idx, col])
    dd_5y = ((val / peak_5y) - 1.0) * 100.0 if peak_5y else 0.0
    rec_pct = ((peak_5y / val) - 1.0) * 100.0 if val else 0.0

    ath_idx = df[col].idxmax()
    ath_val = float(df.loc[ath_idx, col])
    dd_ath = ((val / ath_val) - 1.0) * 100.0 if ath_val else 0.0

    return {
        "name": name,
        "badge": badge,
        "col": col,
        "value": val,
        "mom_pct": mom_pct,
        "yoy_pct": yoy_pct,
        "peak_5y": peak_5y,
        "peak_5y_date": peak_idx,
        "dd_5y_pct": dd_5y,
        "recovery_pct": rec_pct,
        "ath_val": ath_val,
        "ath_date": ath_idx,
        "dd_ath_pct": dd_ath,
        "last_date": df.index[-1],
    }
