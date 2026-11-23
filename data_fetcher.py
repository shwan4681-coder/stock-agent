"""Real-time free market data fetcher (Yahoo Finance + CNN Fear & Greed Index)."""

from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from indicators import summarize_index

CNN_FG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://edition.cnn.com/markets/fear-and-greed",
}


def _clean_yf_history(hist: pd.DataFrame) -> pd.DataFrame:
    if hist is None or hist.empty:
        return pd.DataFrame()
    df = hist.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])


@st.cache_data(ttl=60, show_spinner=False)
def fetch_index_data(symbol: str, name: str, period: str = "5y") -> dict:
    """Fetch historical + latest market data from Yahoo Finance (no API key required)."""
    ticker = yf.Ticker(symbol)
    hist = _clean_yf_history(ticker.history(period=period, interval="1d", auto_adjust=False))
    if hist.empty:
        raise RuntimeError(f"{symbol} 데이터를 불러오지 못했습니다.")

    # Overlay latest intraday quote if available for freshest real-time price
    try:
        fast = ticker.fast_info
        live_price = getattr(fast, "last_price", None)
        if live_price is None and isinstance(fast, dict):
            live_price = fast.get("lastPrice") or fast.get("last_price")
        if live_price and live_price > 0:
            last_idx = hist.index[-1]
            hist.loc[last_idx, "Close"] = float(live_price)
            if float(live_price) > float(hist.loc[last_idx, "High"]):
                hist.loc[last_idx, "High"] = float(live_price)
            if float(live_price) < float(hist.loc[last_idx, "Low"]):
                hist.loc[last_idx, "Low"] = float(live_price)
    except Exception:
        pass

    return summarize_index(hist, symbol=symbol, name=name)


@st.cache_data(ttl=120, show_spinner=False)
def fetch_vix() -> dict:
    """Fetch CBOE Volatility Index (^VIX) as auxiliary sentiment indicator."""
    try:
        ticker = yf.Ticker("^VIX")
        hist = _clean_yf_history(ticker.history(period="6mo", interval="1d"))
        if hist.empty:
            return {"price": None, "change_pct": 0.0}
        price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        chg_pct = ((price - prev) / prev * 100.0) if prev else 0.0
        return {"price": price, "change_pct": chg_pct}
    except Exception:
        return {"price": None, "change_pct": 0.0}


def rating_to_korean(rating: str) -> tuple[str, str]:
    """Map CNN rating string to (Korean label, accent hex color)."""
    r = (rating or "").strip().lower()
    if "extreme fear" in r:
        return "극단적 공포", "#ef4444"
    if "fear" in r:
        return "공포", "#f97316"
    if "extreme greed" in r:
        return "극단적 탐욕", "#10b981"
    if "greed" in r:
        return "탐욕", "#22c55e"
    return "중립", "#eab308"


def score_to_rating(score: float) -> str:
    if score < 25:
        return "extreme fear"
    if score < 45:
        return "fear"
    if score <= 55:
        return "neutral"
    if score <= 75:
        return "greed"
    return "extreme greed"


@st.cache_data(ttl=180, show_spinner=False)
def fetch_fear_and_greed() -> dict:
    """Fetch live CNN Fear & Greed Index with 1-year history (fallback to VIX estimate)."""
    try:
        resp = requests.get(CNN_FG_URL, headers=CNN_HEADERS, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        fg = payload.get("fear_and_greed", {})
        score = float(fg["score"])
        rating = fg.get("rating") or score_to_rating(score)
        kr_label, color = rating_to_korean(rating)

        hist_raw = payload.get("fear_and_greed_historical", {}).get("data", [])
        hist_rows = []
        for pt in hist_raw:
            ts_ms = pt.get("x")
            val = pt.get("y")
            if ts_ms is not None and val is not None:
                dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).replace(tzinfo=None)
                hist_rows.append({"date": dt, "score": float(val), "rating": pt.get("rating", "")})
        hist_df = pd.DataFrame(hist_rows).sort_values("date") if hist_rows else pd.DataFrame(columns=["date", "score", "rating"])

        return {
            "source": "CNN Fear & Greed Index (실시간)",
            "is_fallback": False,
            "score": score,
            "rating": rating,
            "kr_label": kr_label,
            "color": color,
            "timestamp": fg.get("timestamp", ""),
            "previous_close": float(fg.get("previous_close", score)),
            "previous_1_week": float(fg.get("previous_1_week", score)),
            "previous_1_month": float(fg.get("previous_1_month", score)),
            "previous_1_year": float(fg.get("previous_1_year", score)),
            "history": hist_df,
        }
    except Exception as exc:
        # Resilient fallback derived from VIX if CNN temporarily rate-limits
        vix = fetch_vix()
        vix_val = vix.get("price") or 20.0
        est_score = float(max(5.0, min(95.0, 100.0 - (vix_val - 10.0) * 3.0)))
        rating = score_to_rating(est_score)
        kr_label, color = rating_to_korean(rating)
        return {
            "source": f"VIX 추정치 (CNN 일시 오류: {exc})",
            "is_fallback": True,
            "score": est_score,
            "rating": rating,
            "kr_label": kr_label,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_close": est_score,
            "previous_1_week": est_score,
            "previous_1_month": est_score,
            "previous_1_year": est_score,
            "history": pd.DataFrame(columns=["date", "score", "rating"]),
        }


def load_all_market_data(nasdaq_symbol: str = "^IXIC") -> dict:
    """Load S&P 500, NASDAQ (Composite + 100), VIX, and CNN Fear & Greed Index."""
    sp500 = fetch_index_data("^GSPC", "S&P 500", period="5y")
    nasdaq_comp = fetch_index_data("^IXIC", "NASDAQ 종합", period="5y")
    nasdaq_100 = fetch_index_data("^NDX", "NASDAQ 100", period="5y")
    vix = fetch_vix()
    fg = fetch_fear_and_greed()

    selected_nasdaq = nasdaq_comp if nasdaq_symbol == "^IXIC" else nasdaq_100
    return {
        "sp500": sp500,
        "nasdaq": selected_nasdaq,
        "nasdaq_comp": nasdaq_comp,
        "nasdaq_100": nasdaq_100,
        "vix": vix,
        "fear_greed": fg,
    }
