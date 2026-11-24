"""Real Official Raw Data Loader for Seoul Real Estate Backtesting.

Supports 3 real raw-data channels with ZERO extra pip dependencies (no openpyxl needed):
1. KB부동산 데이터허브 월간 시계열 엑셀(.xlsx) 또는 CSV 파일 업로드 / data/ 폴더 자동 감지
2. 한국은행 ECOS Open API 20년 월간 실데이터 자동 수집 (기준금리 · 주담대금리 · 주택가격전망CSI)
3. 한국부동산원 R-ONE Open API 월간 실데이터 자동 수집 (매매가격지수 · 전세가격지수 · 매매수급지수)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pandas as pd
import requests
import streamlit as st


DATA_DIR = Path(__file__).parent / "data"


# ==============================================================================
# 1. Pure-Python XLSX Reader (stdlib zipfile + ElementTree, no openpyxl needed)
# ==============================================================================
def _col_letters_to_idx(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha()).upper()
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def read_xlsx_sheets_pure(file_bytes: bytes) -> dict[str, list[list]]:
    """Read all sheets of an .xlsx file into {sheet_name: rows_2d} using only Python stdlib."""
    ns_main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ns_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
        # 1) Shared strings
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            ss_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in ss_root.findall(f"{{{ns_main}}}si"):
                texts = [t.text or "" for t in si.iter(f"{{{ns_main}}}t")]
                shared.append("".join(texts))

        # 2) Sheet names & rIds
        wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
        rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {
            rel.attrib["Id"]: rel.attrib["Target"].lstrip("/")
            for rel in rels_root
            if "Id" in rel.attrib and "Target" in rel.attrib
        }

        out: dict[str, list[list]] = {}
        for sheet in wb_root.findall(f".//{{{ns_main}}}sheet"):
            name = sheet.attrib.get("name", "Sheet")
            rid = sheet.attrib.get(f"{{{ns_rel}}}id", "")
            target = rid_to_target.get(rid, "")
            if not target:
                continue
            if not target.startswith("xl/"):
                target = "xl/" + target
            if target not in zf.namelist():
                continue

            sh_root = ET.fromstring(zf.read(target))
            rows: list[list] = []
            for row_el in sh_root.findall(f".//{{{ns_main}}}sheetData/{{{ns_main}}}row"):
                row_vals: dict[int, object] = {}
                max_c = -1
                for c_el in row_el.findall(f"{{{ns_main}}}c"):
                    ref = c_el.attrib.get("r", "")
                    c_idx = _col_letters_to_idx(ref) if ref else (max_c + 1)
                    max_c = max(max_c, c_idx)
                    c_type = c_el.attrib.get("t", "")
                    val: object = None
                    if c_type == "s":
                        v_el = c_el.find(f"{{{ns_main}}}v")
                        if v_el is not None and v_el.text and v_el.text.isdigit():
                            si_i = int(v_el.text)
                            val = shared[si_i] if si_i < len(shared) else ""
                    elif c_type == "inlineStr":
                        val = "".join(t.text or "" for t in c_el.iter(f"{{{ns_main}}}t"))
                    else:
                        v_el = c_el.find(f"{{{ns_main}}}v")
                        if v_el is not None and v_el.text is not None:
                            txt = v_el.text.strip()
                            try:
                                val = float(txt)
                            except ValueError:
                                val = txt
                    row_vals[c_idx] = val
                if max_c >= 0:
                    rows.append([row_vals.get(i, None) for i in range(max_c + 1)])
            out[name] = rows
        return out


def _parse_kr_month(val: object) -> pd.Timestamp | None:
    """Parse KB Excel date cell (Excel serial number, '1986.1', '1986-01', '1986년 1월', '198601')."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, (int, float)):
        num = float(val)
        # Excel serial date (1980-01-01 ~= 29221, 2035-01-01 ~= 49310)
        if 25000 <= num <= 55000:
            dt = pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(round(num)))
            return pd.Timestamp(year=dt.year, month=dt.month, day=1)
        # YYYYMM numeric like 198601
        if 198001 <= num <= 203512:
            s = str(int(round(num)))
            if len(s) == 6:
                y, m = int(s[:4]), int(s[4:6])
                if 1 <= m <= 12:
                    return pd.Timestamp(year=y, month=m, day=1)
        return None

    s = str(val).strip()
    if not s:
        return None
    m = re.match(r"^(19\d{2}|20\d{2})[\.\-\/년\s]+(\d{1,2})", s)
    if m:
        yr, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return pd.Timestamp(year=yr, month=mo, day=1)
    m2 = re.match(r"^(19\d{2}|20\d{2})(\d{2})$", s)
    if m2:
        yr, mo = int(m2.group(1)), int(m2.group(2))
        if 1 <= mo <= 12:
            return pd.Timestamp(year=yr, month=mo, day=1)
    return None


def _extract_seoul_series_from_sheet(rows: list[list]) -> pd.Series:
    """Auto-detect the '서울' column and monthly date column in a KB time-series sheet."""
    if not rows or len(rows) < 10:
        return pd.Series(dtype=float)

    seoul_col = None
    # Scan top 12 header rows for '서울' (prefer exact '서울' or '서울특별시', avoiding sub-districts like '서울강북')
    for r in rows[:12]:
        for c_idx, cell in enumerate(r):
            txt = str(cell or "").replace(" ", "").strip()
            if txt in ("서울", "서울특별시", "서울전체", "서울시"):
                seoul_col = c_idx
                break
        if seoul_col is not None:
            break

    if seoul_col is None:
        return pd.Series(dtype=float)

    # Extract (date, value) pairs from rows where col 0 or col 1 parses as a month
    parsed: dict[pd.Timestamp, float] = {}
    for r in rows:
        if len(r) <= seoul_col:
            continue
        dt = _parse_kr_month(r[0]) or (len(r) > 1 and _parse_kr_month(r[1])) or None
        if dt is None:
            continue
        raw_v = r[seoul_col]
        if raw_v is None:
            continue
        try:
            v = float(str(raw_v).replace(",", "").strip())
            if np.isfinite(v) and v > 0:
                parsed[dt] = v
        except ValueError:
            continue

    if len(parsed) < 12:
        return pd.Series(dtype=float)
    return pd.Series(parsed).sort_index()


def parse_kb_or_custom_file(file_bytes: bytes, filename: str) -> tuple[pd.DataFrame, dict]:
    """Parse uploaded KB Monthly Time-Series .xlsx OR custom .csv into standardized Seoul monthly DataFrame."""
    fname = filename.lower()
    meta: dict = {"filename": filename, "loaded_cols": [], "start": None, "end": None, "rows": 0}

    if fname.endswith(".csv"):
        df_csv = pd.read_csv(io.BytesIO(file_bytes))
        df_csv.columns = [c.strip() for c in df_csv.columns]
        # Identify date col
        date_col = next((c for c in df_csv.columns if c.lower() in ("date", "month", "년월", "기준월", "날짜")), df_csv.columns[0])
        dates = df_csv[date_col].apply(_parse_kr_month)
        df_csv = df_csv.assign(_dt=dates).dropna(subset=["_dt"]).set_index("_dt").sort_index()
        df_csv.index.name = "date"

        col_aliases = {
            "sale_idx": ["sale_idx", "매매지수", "매매가격지수", "서울매매", "kb매매"],
            "real_tx_idx": ["real_tx_idx", "실거래가지수", "실거래지수"],
            "jeonse_idx": ["jeonse_idx", "전세지수", "전세가격지수", "서울전세"],
            "jeonse_ratio": ["jeonse_ratio", "전세가율", "전세비율"],
            "supply_demand": ["supply_demand", "매매수급지수", "매수우위지수", "수급지수"],
            "mortgage_rate": ["mortgage_rate", "주담대금리", "주택담보대출금리"],
            "base_rate": ["base_rate", "기준금리"],
            "volume": ["volume", "거래량", "월거래량"],
            "csi": ["csi", "주택가격전망csi", "주택가격전망"],
        }
        out = pd.DataFrame(index=df_csv.index)
        for std_col, aliases in col_aliases.items():
            for orig in df_csv.columns:
                if orig.lower().replace(" ", "") in aliases:
                    s = pd.to_numeric(df_csv[orig], errors="coerce")
                    if s.notna().sum() >= 12:
                        out[std_col] = s
                        meta["loaded_cols"].append(std_col)
                        break

        if not out.empty:
            meta["rows"] = len(out)
            meta["start"] = out.index.min().strftime("%Y.%m")
            meta["end"] = out.index.max().strftime("%Y.%m")
        return out, meta

    if fname.endswith(".xlsx"):
        sheets = read_xlsx_sheets_pure(file_bytes)
        series_map: dict[str, pd.Series] = {}

        # Match KB official sheet naming conventions
        for sh_name, rows in sheets.items():
            norm = sh_name.replace(" ", "").lower()
            if ("매매" in norm and ("아파트" in norm or "apt" in norm)) or norm in ("매매종합", "매매지수"):
                if "sale_idx" not in series_map or "아파트" in norm:
                    s = _extract_seoul_series_from_sheet(rows)
                    if not s.empty:
                        series_map["sale_idx"] = s
            elif ("전세" in norm and ("아파트" in norm or "apt" in norm) and "비율" not in norm and "율" not in norm) or norm in ("전세종합", "전세지수"):
                if "jeonse_idx" not in series_map or "아파트" in norm:
                    s = _extract_seoul_series_from_sheet(rows)
                    if not s.empty:
                        series_map["jeonse_idx"] = s
            elif "전세가율" in norm or "매매가격대비전세" in norm or "전세비율" in norm:
                s = _extract_seoul_series_from_sheet(rows)
                if not s.empty:
                    series_map["jeonse_ratio"] = s
            elif "매수우위" in norm or "매매수급" in norm:
                s = _extract_seoul_series_from_sheet(rows)
                if not s.empty:
                    series_map["supply_demand"] = s

        if not series_map:
            return pd.DataFrame(), meta

        out = pd.DataFrame(series_map).sort_index()
        meta["loaded_cols"] = list(series_map.keys())
        meta["rows"] = len(out)
        meta["start"] = out.index.min().strftime("%Y.%m")
        meta["end"] = out.index.max().strftime("%Y.%m")
        return out, meta

    return pd.DataFrame(), meta


def load_local_raw_file_if_present() -> tuple[pd.DataFrame, dict]:
    """Auto-load data/kb_seoul_monthly.xlsx or data/kb_seoul_monthly.csv if dropped into data/."""
    if not DATA_DIR.exists():
        return pd.DataFrame(), {}
    for name in ("kb_seoul_monthly.xlsx", "kb_seoul_monthly.csv", "seoul_monthly.xlsx", "seoul_monthly.csv"):
        p = DATA_DIR / name
        if p.exists() and p.is_file():
            try:
                return parse_kb_or_custom_file(p.read_bytes(), p.name)
            except Exception:
                continue
    return pd.DataFrame(), {}


# ==============================================================================
# 2. Bank of Korea ECOS 20-Year Monthly Raw Series (2003.01 ~ Current)
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ecos_monthly_history(ecos_key: str) -> pd.DataFrame:
    """Fetch 20+ years of real monthly Korean rates & Housing CSI from BOK ECOS Open API."""
    key = ecos_key.strip()
    if not key:
        return pd.DataFrame()

    now = datetime.now(timezone(timedelta(hours=9)))
    start_ym = "200301"
    end_ym = f"{now.year}{now.month:02d}"

    queries = {
        "base_rate": ("722Y001", "M", "0101000"),
        "mortgage_rate": ("121Y006", "M", "BECBLA0302"),
        "csi": ("511Y002", "M", "FME"),
    }
    series_map: dict[str, pd.Series] = {}
    for field, (stat_cd, cycle, item_cd) in queries.items():
        url = f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/400/{stat_cd}/{cycle}/{start_ym}/{end_ym}/{item_cd}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue
            rows = r.json().get("StatisticSearch", {}).get("row", [])
            parsed = {}
            for row in rows:
                dt = _parse_kr_month(row.get("TIME", ""))
                val_raw = row.get("DATA_VALUE")
                if dt is not None and val_raw not in (None, ""):
                    try:
                        parsed[dt] = float(val_raw)
                    except ValueError:
                        continue
            if len(parsed) >= 12:
                series_map[field] = pd.Series(parsed).sort_index()
        except Exception:
            continue

    return pd.DataFrame(series_map).sort_index() if series_map else pd.DataFrame()


# ==============================================================================
# 3. Korea Real Estate Board R-ONE Official Monthly API (2003.11 ~ Current)
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_reb_monthly_history(reb_key: str) -> pd.DataFrame:
    """Optionally fetch real monthly Seoul apartment indices from REB R-ONE Open API."""
    key = reb_key.strip()
    if not key:
        return pd.DataFrame()

    # Standard R-ONE Open API endpoint (requires free key from reb.or.kr/r-one)
    # Table IDs: A_2024_00178 (월간 아파트 매매가격지수), A_2024_00182 (전세가격지수), A_2024_00188 (매매수급지수)
    base_url = "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"
    tables = {
        "sale_idx": ("A_2024_00178", "500001"),
        "jeonse_idx": ("A_2024_00182", "500001"),
        "supply_demand": ("A_2024_00188", "500001"),
    }
    series_map: dict[str, pd.Series] = {}
    for field, (tbl_id, cls_seoul) in tables.items():
        params = {
            "KEY": key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 400,
            "STATBL_ID": tbl_id,
            "DTACYCLE_CD": "MM",
            "CLS_ID": cls_seoul,
        }
        try:
            r = requests.get(base_url, params=params, timeout=10)
            if r.status_code != 200:
                continue
            body = r.json()
            blocks = body.get("SttsApiTblData", [])
            if len(blocks) < 2:
                continue
            rows = blocks[1].get("row", [])
            parsed = {}
            for row in rows:
                dt = _parse_kr_month(row.get("WRTTIME_IDTFR_ID", ""))
                val_raw = row.get("DTA_VAL")
                if dt is not None and val_raw not in (None, ""):
                    try:
                        parsed[dt] = float(val_raw)
                    except ValueError:
                        continue
            if len(parsed) >= 12:
                series_map[field] = pd.Series(parsed).sort_index()
        except Exception:
            continue

    return pd.DataFrame(series_map).sort_index() if series_map else pd.DataFrame()


def overlay_raw_series(
    base_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    source_label: str,
) -> tuple[pd.DataFrame, list[str]]:
    """Overlay verified raw official monthly series onto the base DataFrame (preserving index scale)."""
    if raw_df is None or raw_df.empty:
        return base_df, []

    out = base_df.copy()
    # Extend index if raw_df reaches newer months
    max_dt = max(out.index.max(), raw_df.index.max())
    min_dt = out.index.min()
    if max_dt > out.index.max():
        new_idx = pd.date_range(min_dt, max_dt, freq="MS")
        out = out.reindex(new_idx).ffill()

    updated_cols: list[str] = []
    for col in raw_df.columns:
        if col not in out.columns:
            continue
        s = raw_df[col].dropna()
        if s.empty:
            continue
        valid_idx = s.index.intersection(out.index)
        if len(valid_idx) < 6:
            continue

        if col in ("sale_idx", "real_tx_idx", "jeonse_idx"):
            # Re-base raw index to match base_df at latest overlapping point for seamless continuity
            ref_dt = valid_idx.max()
            scale = float(out.loc[ref_dt, col]) / float(s.loc[ref_dt]) if float(s.loc[ref_dt]) else 1.0
            out.loc[valid_idx, col] = s.loc[valid_idx] * scale
            if col == "sale_idx" and "real_tx_idx" not in raw_df.columns:
                # Also anchor real_tx_idx smoothly to raw KB/REB sale index so 40Y backtest uses raw path
                scale_rt = float(out.loc[ref_dt, "real_tx_idx"]) / float(s.loc[ref_dt]) if float(s.loc[ref_dt]) else 1.0
                out.loc[valid_idx, "real_tx_idx"] = s.loc[valid_idx] * scale_rt
        else:
            out.loc[valid_idx, col] = s.loc[valid_idx]
        updated_cols.append(f"{col}({source_label})")

    return out, updated_cols


def build_sample_csv_template() -> bytes:
    """Return a clean UTF-8 CSV template users can fill or export from KB Data Hub / ECOS."""
    sample = (
        "date,sale_idx,jeonse_idx,jeonse_ratio,supply_demand,mortgage_rate,base_rate,volume,csi\n"
        "2024-01,95.2,88.1,52.6,85.2,3.99,3.50,2550,92.0\n"
        "2024-02,95.1,88.5,52.8,84.5,3.96,3.50,2580,92.0\n"
        "2024-07,98.8,91.0,53.9,101.2,3.50,3.50,9200,115.0\n"
    )
    return sample.encode("utf-8-sig")
