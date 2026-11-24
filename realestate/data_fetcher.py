"""Hybrid Seoul Real Estate Data Fetcher.

- Always works out-of-the-box with zero API keys using calibrated 40-year Seoul statistics + live Yahoo Finance macro.
- When optional free public API keys are provided (data.go.kr MOLIT Real Transaction API / BOK ECOS API),
  automatically fetches LIVE Seoul apartment trades, jeonse prices, and Korean macro rates.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from urllib.parse import unquote
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st

from realestate.indicators import enrich_seoul_df, summarize_region_series
from realestate.real_data_loader import (
    fetch_ecos_monthly_history,
    fetch_reb_monthly_history,
    load_local_raw_file_if_present,
    overlay_raw_series,
    parse_kb_or_custom_file,
)
from realestate.seoul_history_data import load_seoul_40y_history


# All 25 Seoul autonomous districts with official 5-digit legal district codes (LAWD_CD)
SEOUL_DISTRICTS: dict[str, dict] = {
    "강남구": {"code": "11680", "zone": "강남3구·용산", "tier": "최상급지"},
    "서초구": {"code": "11650", "zone": "강남3구·용산", "tier": "최상급지"},
    "송파구": {"code": "11710", "zone": "강남3구·용산", "tier": "최상급지"},
    "용산구": {"code": "11170", "zone": "강남3구·용산", "tier": "최상급지"},
    "성동구": {"code": "11200", "zone": "마용성·한강벨트", "tier": "상급지"},
    "마포구": {"code": "11440", "zone": "마용성·한강벨트", "tier": "상급지"},
    "양천구": {"code": "11470", "zone": "서남·학군핵심", "tier": "상급지"},
    "영등포구": {"code": "11560", "zone": "마용성·한강벨트", "tier": "상급지"},
    "동작구": {"code": "11590", "zone": "마용성·한강벨트", "tier": "상급지"},
    "광진구": {"code": "11215", "zone": "마용성·한강벨트", "tier": "상급지"},
    "강동구": {"code": "11740", "zone": "동남·신축벨트", "tier": "중상급지"},
    "종로구": {"code": "11110", "zone": "도심권", "tier": "중상급지"},
    "중구": {"code": "11140", "zone": "도심권", "tier": "중상급지"},
    "서대문구": {"code": "11410", "zone": "도심권", "tier": "중급지"},
    "동대문구": {"code": "11230", "zone": "동북·신축벨트", "tier": "중급지"},
    "성북구": {"code": "11290", "zone": "동북·신축벨트", "tier": "중급지"},
    "강서구": {"code": "11500", "zone": "서남·마곡벨트", "tier": "중급지"},
    "은평구": {"code": "11380", "zone": "서북권", "tier": "중저가"},
    "관악구": {"code": "11620", "zone": "서남권", "tier": "중저가"},
    "구로구": {"code": "11530", "zone": "서남권", "tier": "중저가"},
    "노원구": {"code": "11350", "zone": "노도강·동북", "tier": "중저가"},
    "도봉구": {"code": "11320", "zone": "노도강·동북", "tier": "중저가"},
    "강북구": {"code": "11305", "zone": "노도강·동북", "tier": "중저가"},
    "중랑구": {"code": "11260", "zone": "동북권", "tier": "중저가"},
    "금천구": {"code": "11545", "zone": "서남권", "tier": "중저가"},
}

MOLIT_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
MOLIT_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"


def _parse_int_amount(raw: str) -> float:
    """Parse Korean trade price string (e.g. '255,000' in 10k KRW -> 25.5 eok KRW)."""
    cleaned = str(raw or "").replace(",", "").strip()
    if not cleaned:
        return 0.0
    try:
        return float(cleaned) / 10_000.0
    except ValueError:
        return 0.0


def _recent_ym_list(months: int = 3) -> list[str]:
    now = datetime.now(timezone(timedelta(hours=9)))
    y, m = now.year, now.month
    out = []
    for _ in range(months):
        out.append(f"{y:04d}{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_molit_apt_trades(
    service_key: str,
    lawd_cd: str,
    months: int = 3,
) -> pd.DataFrame:
    """Fetch LIVE Seoul apartment sales transactions from MOLIT Open API (data.go.kr)."""
    key = unquote(service_key.strip())
    if not key:
        return pd.DataFrame()

    rows: list[dict] = []
    for ym in _recent_ym_list(months):
        params = {
            "serviceKey": key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": ym,
            "pageNo": 1,
            "numOfRows": 1000,
        }
        try:
            resp = requests.get(MOLIT_TRADE_URL, params=params, timeout=10)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item"):
                apt_nm = (item.findtext("aptNm") or item.findtext("아파트") or "").strip()
                dong = (item.findtext("umdNm") or item.findtext("법정동") or "").strip()
                amt_raw = item.findtext("dealAmount") or item.findtext("거래금액") or "0"
                area_raw = item.findtext("excluUseAr") or item.findtext("전용면적") or "0"
                floor_raw = item.findtext("floor") or item.findtext("층") or ""
                yr = (item.findtext("dealYear") or item.findtext("년") or ym[:4]).strip()
                mo = (item.findtext("dealMonth") or item.findtext("월") or ym[4:]).strip().zfill(2)
                dy = (item.findtext("dealDay") or item.findtext("일") or "01").strip().zfill(2)
                build_yr = (item.findtext("buildYear") or item.findtext("건축년도") or "").strip()
                cdeal = (item.findtext("cdealType") or "").strip()
                if cdeal == "O":  # skip cancelled deals
                    continue
                price_eok = _parse_int_amount(amt_raw)
                if not apt_nm or price_eok <= 0:
                    continue
                rows.append(
                    {
                        "apt_name": apt_nm,
                        "dong": dong,
                        "price_eok": round(price_eok, 2),
                        "area_m2": float(area_raw) if area_raw else 0.0,
                        "floor": floor_raw,
                        "deal_date": f"{yr}-{mo}-{dy}",
                        "build_year": int(build_yr) if build_yr.isdigit() else None,
                    }
                )
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("deal_date", ascending=False)
    return df


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_molit_apt_rents(
    service_key: str,
    lawd_cd: str,
    months: int = 3,
) -> pd.DataFrame:
    """Fetch LIVE Seoul apartment Jeonse (monthlyRent == 0) records from MOLIT Open API."""
    key = unquote(service_key.strip())
    if not key:
        return pd.DataFrame()

    rows: list[dict] = []
    for ym in _recent_ym_list(months):
        params = {
            "serviceKey": key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": ym,
            "pageNo": 1,
            "numOfRows": 1000,
        }
        try:
            resp = requests.get(MOLIT_RENT_URL, params=params, timeout=10)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item"):
                monthly_rent = _parse_int_amount(item.findtext("monthlyRent") or item.findtext("월세금액") or "0")
                if monthly_rent > 0:
                    continue  # Jeonse only
                apt_nm = (item.findtext("aptNm") or item.findtext("아파트") or "").strip()
                dep_eok = _parse_int_amount(item.findtext("deposit") or item.findtext("보증금액") or "0")
                area_raw = item.findtext("excluUseAr") or item.findtext("전용면적") or "0"
                yr = (item.findtext("dealYear") or ym[:4]).strip()
                mo = (item.findtext("dealMonth") or ym[4:]).strip().zfill(2)
                dy = (item.findtext("dealDay") or "01").strip().zfill(2)
                if not apt_nm or dep_eok <= 0:
                    continue
                rows.append(
                    {
                        "apt_name": apt_nm,
                        "jeonse_eok": round(dep_eok, 2),
                        "area_m2": float(area_raw) if area_raw else 0.0,
                        "deal_date": f"{yr}-{mo}-{dy}",
                    }
                )
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("deal_date", ascending=False)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ecos_latest(ecos_key: str) -> dict:
    """Optionally fetch live BOK ECOS Base Rate, Mortgage Rate, and Housing Price CSI."""
    key = ecos_key.strip()
    if not key:
        return {}

    now = datetime.now(timezone(timedelta(hours=9)))
    start_ym = f"{now.year - 1}01"
    end_ym = f"{now.year}{now.month:02d}"

    queries = {
        # (stat_code, cycle, item_code)
        "base_rate": ("722Y001", "M", "0101000"),
        "mortgage_rate": ("121Y006", "M", "BECBLA0302"),
        "csi": ("511Y002", "M", "FME"),
    }
    out: dict[str, float] = {}
    for field, (stat_cd, cycle, item_cd) in queries.items():
        url = f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/36/{stat_cd}/{cycle}/{start_ym}/{end_ym}/{item_cd}"
        try:
            r = requests.get(url, timeout=8)
            if r.status_code != 200:
                continue
            rows = r.json().get("StatisticSearch", {}).get("row", [])
            if rows:
                val = float(rows[-1]["DATA_VALUE"])
                out[field] = val
        except Exception:
            continue
    return out


@st.cache_data(ttl=600, show_spinner=False)
def load_seoul_market_data(
    price_basis: str = "real_tx_idx",
    ecos_key: str = "",
    reb_key: str = "",
    uploaded_file_bytes: bytes | None = None,
    uploaded_file_name: str = "",
) -> dict:
    """Load enriched 40-year Seoul apartment dataset + optional raw KB Excel/CSV, ECOS 20Y, and R-ONE overlays."""
    df_raw = load_seoul_40y_history()
    raw_sources: list[str] = []
    kb_meta: dict = {}

    # 1) Auto-load local data/kb_seoul_monthly.xlsx(.csv) OR user-uploaded file
    if uploaded_file_bytes and uploaded_file_name:
        kb_df, kb_meta = parse_kb_or_custom_file(uploaded_file_bytes, uploaded_file_name)
        df_raw, cols = overlay_raw_series(df_raw, kb_df, f"업로드:{uploaded_file_name}")
        raw_sources.extend(cols)
    else:
        local_df, kb_meta = load_local_raw_file_if_present()
        if not local_df.empty:
            df_raw, cols = overlay_raw_series(df_raw, local_df, f"로컬:{kb_meta.get('filename', 'KB')}")
            raw_sources.extend(cols)

    # 2) Optional REB R-ONE 20Y Official Monthly API
    eff_reb = reb_key.strip() or os.getenv("REB_API_KEY", "").strip()
    reb_live = False
    if eff_reb:
        reb_df = fetch_reb_monthly_history(eff_reb)
        if not reb_df.empty:
            df_raw, cols = overlay_raw_series(df_raw, reb_df, "R-ONE")
            raw_sources.extend(cols)
            reb_live = True

    # 3) Optional BOK ECOS 20Y Official Monthly History API (or latest overlay)
    eff_ecos = ecos_key.strip() or os.getenv("ECOS_API_KEY", "").strip()
    ecos_live = False
    if eff_ecos:
        ecos_hist = fetch_ecos_monthly_history(eff_ecos)
        if not ecos_hist.empty:
            df_raw, cols = overlay_raw_series(df_raw, ecos_hist, "ECOS")
            raw_sources.extend(cols)
            ecos_live = True
        else:
            ecos_latest = fetch_ecos_latest(eff_ecos)
            if ecos_latest:
                last_idx = df_raw.index[-1]
                for k in ("base_rate", "mortgage_rate", "csi"):
                    if k in ecos_latest:
                        df_raw.loc[last_idx, k] = ecos_latest[k]
                raw_sources.append("rates(ECOS최신)")
                ecos_live = True

    df = enrich_seoul_df(df_raw, price_col=price_basis)
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    seoul_real = summarize_region_series(df, "real_tx_idx", "서울 실거래가지수", "REAL TX")
    seoul_sale = summarize_region_series(df, "sale_idx", "서울 매매가격지수", "KB/REB")
    gangnam = summarize_region_series(df, "gangnam_idx", "강남권 (동남권)", "GANGNAM")
    gangbuk = summarize_region_series(df, "gangbuk_idx", "강북권 (강북14구)", "GANGBUK")

    selected = seoul_real if price_basis == "real_tx_idx" else seoul_sale

    has_raw_price = any(c.startswith(("sale_idx(", "real_tx_idx(")) for c in raw_sources)
    if has_raw_price and ecos_live:
        provenance_badge = "✅ 100% 공식 원시 실데이터 (KB/R-ONE + ECOS)"
        provenance_level = "full_raw"
    elif has_raw_price:
        provenance_badge = f"✅ 공식 원시 가격시계열 연결 ({kb_meta.get('filename') or 'R-ONE'})"
        provenance_level = "raw_price"
    elif ecos_live:
        provenance_badge = "🔵 ECOS 금리·CSI 실데이터 + 40년 앵커 아카이브"
        provenance_level = "partial_raw"
    else:
        provenance_badge = "⚠️ 앵커 보간 40년 아카이브 (KB 엑셀 업로드 시 원데이터 전환)"
        provenance_level = "archive"

    return {
        "df": df,
        "price_basis": price_basis,
        "selected": selected,
        "seoul_real": seoul_real,
        "seoul_sale": seoul_sale,
        "gangnam": gangnam,
        "gangbuk": gangbuk,
        "supply_demand": float(latest["supply_demand"]),
        "supply_demand_delta": float(latest["supply_demand"] - prev["supply_demand"]),
        "jeonse_ratio": float(latest["jeonse_ratio"]),
        "jeonse_ratio_delta": float(latest["jeonse_ratio"] - prev["jeonse_ratio"]),
        "jeonse_support": float(latest["Jeonse_Support"]),
        "jeonse_lead_spread": float(latest["Jeonse_Lead_Spread"]),
        "rsi": float(latest["RSI_12"]),
        "rsi_delta": float(latest["RSI_12"] - prev["RSI_12"]),
        "mortgage_rate": float(latest["mortgage_rate"]),
        "rate_chg_3m": float(latest["Rate_Chg_3M"]) if pd.notna(latest["Rate_Chg_3M"]) else 0.0,
        "base_rate": float(latest["base_rate"]),
        "csi": float(latest["csi"]),
        "volume": int(latest["volume"]),
        "vol_ratio_pct": float(latest["Vol_Ratio_Pct"]),
        "annual_supply": float(latest["annual_supply"]),
        "khai": float(latest["khai"]),
        "rolling_ranks": {
            "R_DD": float(latest["R_DD"]) if pd.notna(latest["R_DD"]) else 50.0,
            "R_RSI": float(latest["R_RSI"]) if pd.notna(latest["R_RSI"]) else 50.0,
            "R_SD": float(latest["R_SD"]) if pd.notna(latest["R_SD"]) else 50.0,
            "R_JR": float(latest["R_JR"]) if pd.notna(latest["R_JR"]) else 50.0,
            "R_JS": float(latest["R_JS"]) if pd.notna(latest["R_JS"]) else 50.0,
            "R_RC": float(latest["R_RC"]) if pd.notna(latest["R_RC"]) else 50.0,
            "R_KHAI": float(latest["R_KHAI"]) if pd.notna(latest["R_KHAI"]) else 50.0,
            "R_SUP": float(latest["R_SUP"]) if pd.notna(latest["R_SUP"]) else 50.0,
        },
        "ecos_live": ecos_live,
        "reb_live": reb_live,
        "raw_sources": raw_sources,
        "kb_meta": kb_meta,
        "provenance_badge": provenance_badge,
        "provenance_level": provenance_level,
        "last_date": df.index[-1],
    }
