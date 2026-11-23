"""Technical indicators & drawdown calculations for the Stock Agent."""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Compute Wilder's Relative Strength Index (RSI)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss == 0 and avg_gain > 0, RSI is 100; when both are 0, RSI is 50
    rsi = rsi.where(avg_loss != 0.0, np.where(avg_gain > 0.0, 100.0, 50.0))
    return rsi


def compute_mfi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Compute Money Flow Index (MFI) using typical price and volume."""
    typical_price = (high + low + close) / 3.0
    raw_money_flow = typical_price * volume.fillna(0.0)
    tp_diff = typical_price.diff()

    pos_flow = pd.Series(
        np.where(tp_diff > 0.0, raw_money_flow, 0.0), index=close.index
    )
    neg_flow = pd.Series(
        np.where(tp_diff < 0.0, raw_money_flow, 0.0), index=close.index
    )

    pos_mf = pos_flow.rolling(window=period, min_periods=period).sum()
    neg_mf = neg_flow.rolling(window=period, min_periods=period).sum()

    mfr = pos_mf / neg_mf.replace(0.0, np.nan)
    mfi = 100.0 - (100.0 / (1.0 + mfr))
    mfi = mfi.where(neg_mf != 0.0, np.where(pos_mf > 0.0, 100.0, 50.0))
    return mfi


def enrich_market_df(df: pd.DataFrame) -> pd.DataFrame:
    """Attach RSI(14), MFI(14), moving averages, and running drawdown columns."""
    out = df.copy()
    out["RSI_14"] = compute_rsi(out["Close"], period=14)
    out["MFI_14"] = compute_mfi(
        out["High"], out["Low"], out["Close"], out["Volume"], period=14
    )
    out["MA_20"] = out["Close"].rolling(20).mean()
    out["MA_50"] = out["Close"].rolling(50).mean()
    out["MA_200"] = out["Close"].rolling(200).mean()
    out["Running_High"] = out["High"].cummax()
    out["Drawdown_Pct"] = (out["Close"] / out["Running_High"] - 1.0) * 100.0
    return out


def summarize_index(df: pd.DataFrame, symbol: str, name: str) -> dict:
    """Build a rich summary dictionary for a market index DataFrame."""
    enriched = enrich_market_df(df)
    latest = enriched.iloc[-1]
    prev = enriched.iloc[-2] if len(enriched) >= 2 else latest

    price = float(latest["Close"])
    prev_close = float(prev["Close"])
    change = price - prev_close
    change_pct = (change / prev_close * 100.0) if prev_close else 0.0

    # All-time / 5Y peak
    ath_idx = enriched["High"].idxmax()
    ath_price = float(enriched.loc[ath_idx, "High"])
    dd_ath_pct = (price / ath_price - 1.0) * 100.0
    recovery_ath_pct = ((ath_price / price) - 1.0) * 100.0 if price > 0 else 0.0

    # 52-week peak (~252 trading days)
    recent_52w = enriched.tail(252)
    h52_idx = recent_52w["High"].idxmax()
    high_52w = float(recent_52w.loc[h52_idx, "High"])
    low_52w = float(recent_52w["Low"].min())
    dd_52w_pct = (price / high_52w - 1.0) * 100.0

    rsi_now = float(latest["RSI_14"]) if pd.notna(latest["RSI_14"]) else None
    rsi_prev = float(prev["RSI_14"]) if pd.notna(prev["RSI_14"]) else None
    mfi_now = float(latest["MFI_14"]) if pd.notna(latest["MFI_14"]) else None
    mfi_prev = float(prev["MFI_14"]) if pd.notna(prev["MFI_14"]) else None

    ma20 = float(latest["MA_20"]) if pd.notna(latest["MA_20"]) else None
    ma50 = float(latest["MA_50"]) if pd.notna(latest["MA_50"]) else None
    ma200 = float(latest["MA_200"]) if pd.notna(latest["MA_200"]) else None

    return {
        "symbol": symbol,
        "name": name,
        "df": enriched,
        "price": price,
        "prev_close": prev_close,
        "change": change,
        "change_pct": change_pct,
        "last_date": enriched.index[-1],
        "ath_price": ath_price,
        "ath_date": ath_idx,
        "dd_ath_pct": dd_ath_pct,
        "recovery_ath_pct": recovery_ath_pct,
        "high_52w": high_52w,
        "high_52w_date": h52_idx,
        "low_52w": low_52w,
        "dd_52w_pct": dd_52w_pct,
        "rsi": rsi_now,
        "rsi_delta": (rsi_now - rsi_prev) if (rsi_now is not None and rsi_prev is not None) else 0.0,
        "mfi": mfi_now,
        "mfi_delta": (mfi_now - mfi_prev) if (mfi_now is not None and mfi_prev is not None) else 0.0,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
    }
