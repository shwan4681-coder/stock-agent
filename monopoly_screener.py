"""Wide-Moat Monopoly Screener, Warren Buffett Scorecard & Real-Time Buy Signal Engine."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

from indicators import compute_mfi, compute_rsi
from ui_components import _compact_html


# Curated global wide-moat monopoly & oligopoly universe (30 leaders across 5 core sectors)
# Qualitative moat / market share / leadership profiles are paired with 100% live Yahoo Finance financials & price signals.
MONOPOLY_UNIVERSE: dict[str, dict] = {
    # --- 반도체 · AI 인프라 ---
    "NVDA": {
        "name_kr": "엔비디아",
        "sector": "반도체·AI",
        "market_share_pct": 85,
        "moat_type": "독점 (AI GPU · CUDA 생태계)",
        "moat_note": "데이터센터 AI 가속기 점유율 ~85%+ · CUDA 소프트웨어 락인",
        "mgmt_score": 5,
        "mgmt_note": "젠슨 황 창업자 CEO · 압도적 기술 비전과 고ROIC 자본배분",
    },
    "ASML": {
        "name_kr": "ASML",
        "sector": "반도체·AI",
        "market_share_pct": 100,
        "moat_type": "완전 독점 (EUV 노광장비)",
        "moat_note": "첨단 반도체 필수 EUV 노광장비 글로벌 100% 단독 공급",
        "mgmt_score": 5,
        "mgmt_note": "장기 R&D 집중 및 글로벌 공급망 통제력 최상위",
    },
    "TSM": {
        "name_kr": "TSMC",
        "sector": "반도체·AI",
        "market_share_pct": 65,
        "moat_type": "독점적 선두 (첨단 파운드리)",
        "moat_note": "글로벌 파운드리 ~65%+(3nm/5nm 선단공정 80%+) · 고객과 비경쟁 원칙",
        "mgmt_score": 5,
        "mgmt_note": "철저한 기술 리더십·수율 관리 및 안정적 설비투자(CapEx) 규율",
    },
    "AVGO": {
        "name_kr": "브로드컴",
        "sector": "반도체·AI",
        "market_share_pct": 65,
        "moat_type": "독점적 선두 (맞춤형 AI 칩)",
        "moat_note": "하이퍼스케일러 커스텀 AI ASIC 및 고속 이더넷 스위치 점유율 ~65%+",
        "mgmt_score": 5,
        "mgmt_note": "혹 탄 CEO · 탁월한 M&A(VMware 등) 통합 및 고배당·현금흐름 경영",
    },
    "KLAC": {
        "name_kr": "KLA",
        "sector": "반도체·AI",
        "market_share_pct": 55,
        "moat_type": "독점적 선두 (반도체 검사·계측)",
        "moat_note": "웨이퍼 공정 제어·검사 장비 글로벌 점유율 ~55%+ · 미세화 필수 수혜",
        "mgmt_score": 5,
        "mgmt_note": "고마진 서비스 매출 확대 및 일관된 자사주 매입·배당 성장",
    },
    "SNPS": {
        "name_kr": "시높시스",
        "sector": "반도체·AI",
        "market_share_pct": 50,
        "moat_type": "과독점 (반도체 설계 EDA)",
        "moat_note": "케이던스와 반도체 설계 소프트웨어(EDA) 글로벌 양강 과독점",
        "mgmt_score": 5,
        "mgmt_note": "Ansys 인수로 칩-시스템 통합 설계 해자 확장 · 높은 반복 구독 매출",
    },
    "CDNS": {
        "name_kr": "케이던스 디자인",
        "sector": "반도체·AI",
        "market_share_pct": 50,
        "moat_type": "과독점 (반도체 설계 EDA)",
        "moat_note": "시높시스와 EDA 툴 양강 과독점 · AI 칩 설계 복잡도 증가 수혜",
        "mgmt_score": 5,
        "mgmt_note": "높은 전환 비용 기반 안정적 고마진 및 소프트웨어 중심 고ROIC",
    },
    "ANET": {
        "name_kr": "아리스타 네트웍스",
        "sector": "반도체·AI",
        "market_share_pct": 50,
        "moat_type": "독점적 선두 (AI 데이터센터 스위치)",
        "moat_note": "하이퍼스케일 고속(400G/800G) 클라우드 네트워킹 점유율 선두",
        "mgmt_score": 5,
        "mgmt_note": "제이슈리 울랄 CEO · 무차입 요새형 재무 및 EOS 소프트웨어 경쟁력",
    },
    "ARM": {
        "name_kr": "ARM 홀딩스",
        "sector": "반도체·AI",
        "market_share_pct": 95,
        "moat_type": "독점 (저전력 CPU 아키텍처)",
        "moat_note": "스마트폰 CPU 아키텍처 점유율 ~95%+ · 로열티·라이선스 통행세 모델",
        "mgmt_score": 4,
        "mgmt_note": "v9 아키텍처 전환으로 칩당 로열티 단가 상승 및 데이터센터 확장",
    },
    # --- 소프트웨어 · 클라우드 ---
    "MSFT": {
        "name_kr": "마이크로소프트",
        "sector": "소프트웨어·클라우드",
        "market_share_pct": 75,
        "moat_type": "독점 (기업 OS · 오피스)",
        "moat_note": "기업용 OS/오피스 ~75%+ · Azure 클라우드 및 AI 코파일럿 락인",
        "mgmt_score": 5,
        "mgmt_note": "사티아 나델라 CEO · 클라우드/AI 전환 성공 & 주주친화 배당·자사주",
    },
    "INTU": {
        "name_kr": "인튜이트",
        "sector": "소프트웨어·클라우드",
        "market_share_pct": 75,
        "moat_type": "독점 (미국 세무·회계 SW)",
        "moat_note": "TurboTax(개인세무)·QuickBooks(중소기업 회계) 미국 점유율 ~75%+",
        "mgmt_score": 5,
        "mgmt_note": "높은 전환비용과 가격결정력 · AI 기반 금융 플랫폼 확장",
    },
    "NOW": {
        "name_kr": "서비스나우",
        "sector": "소프트웨어·클라우드",
        "market_share_pct": 55,
        "moat_type": "독점적 선두 (기업 IT 워크플로우)",
        "moat_note": "포춘 500 기업의 85%+ 도입 · 98%대 갱신율의 엔터프라이즈 표준",
        "mgmt_score": 5,
        "mgmt_note": "빌 맥더멋 CEO · 탁월한 대형 엔터프라이즈 영업력 및 AI 에이전트 확장",
    },
    "CRWD": {
        "name_kr": "크라우드스트라이크",
        "sector": "소프트웨어·클라우드",
        "market_share_pct": 50,
        "moat_type": "선두 과독점 (클라우드 보안)",
        "moat_note": "차세대 클라우드 엔드포인트 보안(Falcon) 플랫폼 모듈 확장성",
        "mgmt_score": 4,
        "mgmt_note": "조지 커츠 창업자 CEO · 높은 잉여현금흐름 마진과 플랫폼 통합 전략",
    },
    # --- 금융 · 결제 · 데이터 ---
    "FICO": {
        "name_kr": "페어 아이작 (FICO)",
        "sector": "금융·데이터",
        "market_share_pct": 90,
        "moat_type": "독점 (미국 표준 신용점수)",
        "moat_note": "미국 모기지·대출 심사 표준 FICO 스코어 점유율 ~90% · 초강력 가격결정력",
        "mgmt_score": 5,
        "mgmt_note": "윌 랜싱 CEO · 강력한 가격 인상 전략과 공격적 자사주 소각",
    },
    "V": {
        "name_kr": "비자",
        "sector": "금융·데이터",
        "market_share_pct": 53,
        "moat_type": "과독점 (글로벌 카드 결제망)",
        "moat_note": "글로벌 카드 결제 점유율 ~53% · 인플레이션 수혜 통행세 비즈니스",
        "mgmt_score": 5,
        "mgmt_note": "안정적 65%+ 영업이익률 유지 · 지속적 배당 성장 및 자사주 매입",
    },
    "MA": {
        "name_kr": "마스터카드",
        "sector": "금융·데이터",
        "market_share_pct": 50,
        "moat_type": "과독점 (비자와 글로벌 양강)",
        "moat_note": "비자와 글로벌 결제망 양강 과독점 · 부가가치 보안/데이터 매출 고성장",
        "mgmt_score": 5,
        "mgmt_note": "초고ROE 자본효율성 · 꾸준한 주주환원 정책",
    },
    "SPGI": {
        "name_kr": "S&P 글로벌",
        "sector": "금융·데이터",
        "market_share_pct": 50,
        "moat_type": "과독점 (신용평가 · S&P500 지수)",
        "moat_note": "무디스와 글로벌 신용평가 양강 과독점 · S&P 500 지수 라이선스 통행세",
        "mgmt_score": 5,
        "mgmt_note": "50년 이상 배당귀족 · IHS Markit 합병으로 데이터 해자 강화",
    },
    "MCO": {
        "name_kr": "무디스",
        "sector": "금융·데이터",
        "market_share_pct": 50,
        "moat_type": "과독점 (워렌 버핏 핵심 보유주)",
        "moat_note": "S&P와 글로벌 채권 신용평가 양강 과독점 · 버크셔 해서웨이 장기 보유",
        "mgmt_score": 5,
        "mgmt_note": "신용평가 규제 장벽 + Analytics 구독 매출 비중 확대로 안정성 극대화",
    },
    "MSCI": {
        "name_kr": "MSCI",
        "sector": "금융·데이터",
        "market_share_pct": 65,
        "moat_type": "독점적 표준 (글로벌 기관 지수)",
        "moat_note": "글로벌 ETF·연기금 벤치마크 지수 라이선스 및 포트폴리오 분석 표준",
        "mgmt_score": 5,
        "mgmt_note": "헨리 페르난데스 CEO · 50%대 초고영업이익률 및 강력한 주주환원",
    },
    # --- 빅테크 · 플랫폼 · 소비재 ---
    "GOOGL": {
        "name_kr": "알파벳 (구글)",
        "sector": "플랫폼·소비재",
        "market_share_pct": 90,
        "moat_type": "독점 (글로벌 검색 · 유튜브)",
        "moat_note": "글로벌 검색 점유율 ~90% · 유튜브·안드로이드·구글 클라우드 생태계",
        "mgmt_score": 4,
        "mgmt_note": "막대한 현금창출력 기반 AI 자체 칩(TPU) 투자 및 자사주 매입 확대",
    },
    "META": {
        "name_kr": "메타",
        "sector": "플랫폼·소비재",
        "market_share_pct": 60,
        "moat_type": "과독점 (글로벌 SNS 네트워크)",
        "moat_note": "일활성이용자 32억+ · 인스타그램/페이스북/왓츠앱 대체불가 네트워크 효과",
        "mgmt_score": 4,
        "mgmt_note": "마크 저커버그 창업자 CEO · 효율성 개선 및 오픈소스 AI 투자",
    },
    "AAPL": {
        "name_kr": "애플",
        "sector": "플랫폼·소비재",
        "market_share_pct": 60,
        "moat_type": "독점적 생태계 (프리미엄 iOS)",
        "moat_note": "글로벌 프리미엄 스마트폰·활성 기기 22억대 · 앱스토어/서비스 고마진 락인",
        "mgmt_score": 5,
        "mgmt_note": "팀 쿡 CEO · 워렌 버핏이 극찬한 공급망 관리 및 역대급 자사주 매입",
    },
    "AMZN": {
        "name_kr": "아마존",
        "sector": "플랫폼·소비재",
        "market_share_pct": 50,
        "moat_type": "독점적 선두 (AWS · 미국 커머스)",
        "moat_note": "글로벌 클라우드(AWS) 1위 + 프라임 물류망·고마진 광고 사업 급성장",
        "mgmt_score": 5,
        "mgmt_note": "앤디 재시 CEO · 물류 지역화 효율 개선으로 영업이익률 구조적 도약",
    },
    "NFLX": {
        "name_kr": "넷플릭스",
        "sector": "플랫폼·소비재",
        "market_share_pct": 50,
        "moat_type": "독점적 1위 (글로벌 프리미엄 OTT)",
        "moat_note": "전 세계 3억+ 유료 구독자 · 규모의 경제로 경쟁사 대비 압도적 수익성",
        "mgmt_score": 5,
        "mgmt_note": "광고 요금제·계정 공유 단속 성공으로 FCF 및 영업이익률 급상승",
    },
    "BKNG": {
        "name_kr": "부킹 홀딩스",
        "sector": "플랫폼·소비재",
        "market_share_pct": 65,
        "moat_type": "독점적 선두 (유럽·글로벌 숙박 OTA)",
        "moat_note": "Booking.com·아고다 기반 글로벌 호텔 예약 네트워크 효과",
        "mgmt_score": 5,
        "mgmt_note": "글렌 포겔 CEO · 자산 경량(Asset-light) 초고현금흐름 및 자사주 소각",
    },
    "MELI": {
        "name_kr": "메르카도리브레",
        "sector": "플랫폼·소비재",
        "market_share_pct": 55,
        "moat_type": "독점적 1위 (중남미 이커머스·핀테크)",
        "moat_note": "중남미 아마존+페이팔(Mercado Pago) 결합 생태계 압도적 1위",
        "mgmt_score": 5,
        "mgmt_note": "마르코스 갈페린 창업자 CEO · 중남미 디지털 금융·물류 인프라 장악",
    },
    "COST": {
        "name_kr": "코스트코",
        "sector": "플랫폼·소비재",
        "market_share_pct": 60,
        "moat_type": "독점적 1위 (창고형 멤버십 유통)",
        "moat_note": "멤버십 갱신율 ~93% · 규모의 경제(Scale Economies Shared) 찰리 멍거 최애주",
        "mgmt_score": 5,
        "mgmt_note": "철저한 최저마진·고객신뢰 원칙과 안정적 멤버십 수수료 수익 구조",
    },
    # --- 헬스케어 · 바이오 ---
    "ISRG": {
        "name_kr": "인튜이티브 서지컬",
        "sector": "헬스케어",
        "market_share_pct": 80,
        "moat_type": "독점 (수술용 로봇 다빈치)",
        "moat_note": "최소침습 로봇수술 글로벌 점유율 ~80% · 소모품 반복매출 구조",
        "mgmt_score": 5,
        "mgmt_note": "무차입 요새형 재무구조 · 의료진 교육 생태계 기반 장기 독점 구축",
    },
    "LLY": {
        "name_kr": "일라이 릴리",
        "sector": "헬스케어",
        "market_share_pct": 55,
        "moat_type": "과독점 선두 (비만·당뇨 GLP-1)",
        "moat_note": "마운자로·젭바운드 기반 글로벌 비만치료제 시장 과독점 선도",
        "mgmt_score": 5,
        "mgmt_note": "데이비드 릭스 CEO · 대규모 R&D 및 생산설비 선제 투자로 격차 확대",
    },
    "IDXX": {
        "name_kr": "아이덱스 래버러토리스",
        "sector": "헬스케어",
        "market_share_pct": 55,
        "moat_type": "독점적 선두 (반려동물 진단)",
        "moat_note": "동물병원 진단기기 설치 후 소모품·시약 반복매출(Razor & Blade) 해자",
        "mgmt_score": 5,
        "mgmt_note": "99%에 가까운 고객 유지율과 높은 ROIC 기반 자본배분",
    },
}


def _pick_row(df: pd.DataFrame | None, candidates: list[str]) -> pd.Series | None:
    if df is None or df.empty:
        return None
    idx_map = {str(k).strip().lower(): k for k in df.index}
    for cand in candidates:
        key = idx_map.get(cand.lower())
        if key is not None:
            s = df.loc[key].dropna()
            if not s.empty:
                return s
    return None


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return None


def analyze_single_stock(
    symbol: str,
    custom_share_pct: int | None = None,
    custom_mgmt_score: int | None = None,
) -> dict:
    """Fetch live Yahoo Finance financials + price indicators and evaluate Monopoly + Buffett criteria."""
    sym = symbol.strip().upper()
    meta = MONOPOLY_UNIVERSE.get(
        sym,
        {
            "name_kr": sym,
            "sector": "사용자 지정",
            "market_share_pct": custom_share_pct if custom_share_pct is not None else 50,
            "moat_type": "사용자 입력 종목 (해자 직접 확인)",
            "moat_note": "시장 점유율·경영진 항목은 슬라이더로 직접 조정 가능합니다.",
            "mgmt_score": custom_mgmt_score if custom_mgmt_score is not None else 4,
            "mgmt_note": "재무 ROIC/ROE와 경영진 주주환원 이력을 함께 확인하세요.",
        },
    ).copy()

    if custom_share_pct is not None:
        meta["market_share_pct"] = custom_share_pct
    if custom_mgmt_score is not None:
        meta["mgmt_score"] = custom_mgmt_score

    ticker = yf.Ticker(sym)
    hist = ticker.history(period="2y", interval="1d", auto_adjust=False)
    if hist is None or hist.empty:
        raise RuntimeError(f"'{sym}' 주가 데이터를 찾을 수 없습니다. 티커를 확인해 주세요.")
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = [c[0] for c in hist.columns]
    if getattr(hist.index, "tz", None) is not None:
        hist.index = hist.index.tz_localize(None)
    hist = hist[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])

    hist["RSI_14"] = compute_rsi(hist["Close"], 14)
    hist["MFI_14"] = compute_mfi(hist["High"], hist["Low"], hist["Close"], hist["Volume"], 14)
    hist["MA_50"] = hist["Close"].rolling(50).mean()
    hist["MA_200"] = hist["Close"].rolling(200).mean()

    price = float(hist["Close"].iloc[-1])
    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
    chg_pct = ((price - prev) / prev * 100.0) if prev else 0.0
    high_2y = float(hist["High"].max())
    dd_pct = ((price / high_2y) - 1.0) * 100.0 if high_2y > 0 else 0.0
    rsi = _safe_float(hist["RSI_14"].iloc[-1])
    mfi = _safe_float(hist["MFI_14"].iloc[-1])

    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    if sym not in MONOPOLY_UNIVERSE:
        meta["name_kr"] = info.get("shortName") or info.get("longName") or sym
        meta["sector"] = info.get("sector") or meta["sector"]

    # Annual statements (Yahoo Finance provides 4~5 annual fiscal periods)
    try:
        inc = ticker.income_stmt
    except Exception:
        inc = pd.DataFrame()
    try:
        cf = ticker.cashflow
    except Exception:
        cf = pd.DataFrame()

    rev_s = _pick_row(inc, ["Total Revenue", "Operating Revenue", "Revenue"])
    op_s = _pick_row(inc, ["Operating Income", "Total Operating Income As Reported", "EBIT"])
    fcf_s = _pick_row(cf, ["Free Cash Flow"])

    annual_rows = []
    if rev_s is not None:
        # Sort chronological (oldest -> newest)
        rev_sorted = rev_s.sort_index()
        for dt_col, rev_val in rev_sorted.items():
            rv = _safe_float(rev_val)
            if not rv or rv <= 0:
                continue
            op_val = _safe_float(op_s.get(dt_col)) if (op_s is not None and dt_col in op_s.index) else None
            op_margin = (op_val / rv * 100.0) if op_val is not None else None
            fcf_val = _safe_float(fcf_s.get(dt_col)) if (fcf_s is not None and dt_col in fcf_s.index) else None
            fcf_margin_y = (fcf_val / rv * 100.0) if fcf_val is not None else None
            yr_label = str(dt_col)[:4]
            annual_rows.append(
                {
                    "year": yr_label,
                    "revenue": rv,
                    "op_margin_pct": op_margin,
                    "fcf_margin_pct": fcf_margin_y,
                }
            )

    # 1. Revenue CAGR (Multi-year annual CAGR)
    rev_cagr_pct = None
    if len(annual_rows) >= 2:
        r_start = annual_rows[0]["revenue"]
        r_end = annual_rows[-1]["revenue"]
        n_years = len(annual_rows) - 1
        if r_start > 0 and r_end > 0 and n_years > 0:
            rev_cagr_pct = ((r_end / r_start) ** (1.0 / n_years) - 1.0) * 100.0

    recent_rev_growth = _safe_float(info.get("revenueGrowth"))
    if recent_rev_growth is not None:
        recent_rev_growth *= 100.0
    if rev_cagr_pct is None:
        rev_cagr_pct = recent_rev_growth

    # 2. Operating margin 5Y consistency (>= 20%)
    valid_op_margins = [r["op_margin_pct"] for r in annual_rows if r["op_margin_pct"] is not None]
    op_years_total = len(valid_op_margins)
    op_years_pass = sum(1 for m in valid_op_margins if m >= 20.0)
    latest_op_margin = valid_op_margins[-1] if valid_op_margins else (
        _safe_float(info.get("operatingMargins")) * 100.0 if _safe_float(info.get("operatingMargins")) is not None else None
    )
    avg_op_margin = float(np.mean(valid_op_margins)) if valid_op_margins else latest_op_margin

    # 3. Warren Buffett core fundamental criteria
    roe_raw = _safe_float(info.get("returnOnEquity"))
    roe_pct = roe_raw * 100.0 if roe_raw is not None else None

    gm_raw = _safe_float(info.get("grossMargins"))
    gross_margin_pct = gm_raw * 100.0 if gm_raw is not None else None

    fcf_info = _safe_float(info.get("freeCashflow"))
    rev_info = _safe_float(info.get("totalRevenue"))
    fcf_margin_pct = (fcf_info / rev_info * 100.0) if (fcf_info is not None and rev_info and rev_info > 0) else None
    if fcf_margin_pct is None and annual_rows:
        valid_fcf = [r["fcf_margin_pct"] for r in annual_rows if r["fcf_margin_pct"] is not None]
        if valid_fcf:
            fcf_margin_pct = valid_fcf[-1]

    dte = _safe_float(info.get("debtToEquity"))  # Yahoo returns percentage e.g. 14.3 means 14.3%
    current_ratio = _safe_float(info.get("currentRatio"))
    forward_pe = _safe_float(info.get("forwardPE"))
    peg = _safe_float(info.get("pegRatio")) or _safe_float(info.get("trailingPegRatio"))

    # ---------------- 8-Criteria Scorecard (100 pts) ----------------
    # 1) Management (12 pts)
    mgmt_pass = meta["mgmt_score"] >= 4
    mgmt_pts = 12 if meta["mgmt_score"] >= 5 else 9 if meta["mgmt_score"] >= 4 else 4

    # 2) Revenue CAGR >= 20% (16 pts)
    rev_pass = rev_cagr_pct is not None and rev_cagr_pct >= 20.0
    if rev_cagr_pct is not None:
        rev_pts = 16 if rev_cagr_pct >= 20.0 else 11 if rev_cagr_pct >= 12.0 else 6 if rev_cagr_pct >= 7.0 else 2
    else:
        rev_pts = 5

    # 3) Operating Margin >= 20% for multi-year (16 pts)
    op_all_pass = op_years_total >= 3 and op_years_pass == op_years_total
    if op_all_pass:
        op_pts = 16
    elif op_years_total > 0 and op_years_pass >= max(1, op_years_total - 1):
        op_pts = 12
    elif latest_op_margin is not None and latest_op_margin >= 20.0:
        op_pts = 9
    else:
        op_pts = 3

    # 4) Market Share >= 50% Monopoly/Oligopoly (16 pts)
    share_pct = meta["market_share_pct"]
    share_pass = share_pct >= 50
    share_pts = 16 if share_pct >= 70 else 13 if share_pct >= 50 else 5

    # 5) Buffett ROE >= 15% (10 pts)
    roe_pass = roe_pct is not None and roe_pct >= 15.0
    roe_pts = 10 if (roe_pct is not None and roe_pct >= 20.0) else 8 if roe_pass else 3

    # 6) Buffett Pricing Power: Gross Margin >= 40% (10 pts)
    gm_pass = gross_margin_pct is not None and gross_margin_pct >= 40.0
    gm_pts = 10 if (gross_margin_pct is not None and gross_margin_pct >= 55.0) else 8 if gm_pass else 3

    # 7) Buffett Owner Earnings: FCF Margin >= 15% (10 pts)
    fcf_pass = fcf_margin_pct is not None and fcf_margin_pct >= 15.0
    fcf_pts = 10 if (fcf_margin_pct is not None and fcf_margin_pct >= 20.0) else 8 if fcf_pass else 3

    # 8) Buffett Fortress Balance Sheet: Debt/Equity < 100% or Current Ratio >= 1.2 (10 pts)
    if dte is not None:
        debt_pass = dte <= 100.0
        debt_pts = 10 if dte <= 50.0 else 8 if dte <= 100.0 else 5 if (current_ratio and current_ratio >= 1.3) else 2
    else:
        debt_pass = current_ratio is not None and current_ratio >= 1.2
        debt_pts = 7 if debt_pass else 4

    moat_score = int(mgmt_pts + rev_pts + op_pts + share_pts + roe_pts + gm_pts + fcf_pts + debt_pts)

    # ---------------- Real-Time Buy Signal Engine ----------------
    # Combines Quality (moat_score) + Valuation/Discount (Drawdown, RSI, MFI, PEG)
    buy_points = 0
    buy_reasons = []

    if dd_pct <= -20.0:
        buy_points += 35
        buy_reasons.append(f"고점 대비 {dd_pct:.1f}% 깊은 할인")
    elif dd_pct <= -12.0:
        buy_points += 25
        buy_reasons.append(f"고점 대비 {dd_pct:.1f}% 조정 눌림목")
    elif dd_pct <= -6.0:
        buy_points += 12
        buy_reasons.append(f"고점 대비 {dd_pct:.1f}% 완만한 조정")

    if rsi is not None and rsi <= 32.0:
        buy_points += 25
        buy_reasons.append(f"RSI {rsi:.1f} 과매도")
    elif rsi is not None and rsi <= 42.0:
        buy_points += 14
        buy_reasons.append(f"RSI {rsi:.1f} 약세 접근")
    elif rsi is not None and rsi >= 70.0:
        buy_points -= 15
        buy_reasons.append(f"RSI {rsi:.1f} 단기 과열")

    if mfi is not None and mfi <= 30.0:
        buy_points += 15
        buy_reasons.append(f"MFI {mfi:.1f} 저점 자금이탈")
    elif mfi is not None and mfi >= 80.0:
        buy_points -= 10

    if peg is not None and 0 < peg <= 1.5:
        buy_points += 20
        buy_reasons.append(f"PEG {peg:.2f} 저평가 성장")
    elif peg is not None and 0 < peg <= 2.2:
        buy_points += 10
        buy_reasons.append(f"PEG {peg:.2f} 합리적 밸류")
    elif forward_pe is not None and forward_pe <= 25.0:
        buy_points += 10
        buy_reasons.append(f"Fwd PER {forward_pe:.1f}x 양호")

    if moat_score >= 80 and buy_points >= 55:
        signal = "🟢 강력 매수 관심"
        signal_code = "strong_buy"
        signal_color = "#10b981"
    elif moat_score >= 72 and buy_points >= 32:
        signal = "🔵 분할 매수 관심"
        signal_code = "accumulate"
        signal_color = "#38bdf8"
    elif moat_score >= 70:
        signal = "🟡 초우량 · 눌림 대기"
        signal_code = "watch"
        signal_color = "#eab308"
    else:
        signal = "⚪ 조건 일부 미달"
        signal_code = "filtered"
        signal_color = "#94a3b8"

    checklist = [
        {
            "title": "1. 훌륭한 경영진 & 자본배분",
            "passed": mgmt_pass,
            "value": f"{meta['mgmt_score']}/5점",
            "rule": "4점 이상",
            "note": meta["mgmt_note"],
        },
        {
            "title": "2. 연평균 매출 성장률 (CAGR)",
            "passed": rev_pass,
            "value": f"{rev_cagr_pct:+.1f}%" if rev_cagr_pct is not None else "N/A",
            "rule": "연 20% 이상",
            "note": f"최근 {max(1, len(annual_rows)-1)}개년 연평균 성장 (최근 분기 YoY: {recent_rev_growth:+.1f}%)" if recent_rev_growth is not None else "연간 재무제표 기준",
        },
        {
            "title": "3. 영업이익률 5년 지속성",
            "passed": op_all_pass,
            "value": f"{op_years_pass}/{op_years_total}년 (평균 {avg_op_margin:.1f}%)" if (op_years_total and avg_op_margin is not None) else "N/A",
            "rule": "매년 20% 이상",
            "note": "Yahoo Finance 최근 연간 손익계산서 전 기간 영업이익률 20% 돌파 여부",
        },
        {
            "title": "4. 시장 점유율 (독점·과독점)",
            "passed": share_pass,
            "value": f"약 {share_pct}%+",
            "rule": "50% 이상",
            "note": meta["moat_note"],
        },
        {
            "title": "5. [버핏] 자기자본이익률 (ROE)",
            "passed": roe_pass,
            "value": f"{roe_pct:.1f}%" if roe_pct is not None else "N/A",
            "rule": "15% 이상",
            "note": "주주 자본으로 얼마나 높은 이익을 복리로 창출하는지 측정",
        },
        {
            "title": "6. [버핏] 가격결정력 (매출총이익률)",
            "passed": gm_pass,
            "value": f"{gross_margin_pct:.1f}%" if gross_margin_pct is not None else "N/A",
            "rule": "40% 이상",
            "note": "높은 매출총이익률은 경쟁자가 흉내 낼 수 없는 경제적 해자의 증거",
        },
        {
            "title": "7. [버핏] 주주이익 (FCF 마진)",
            "passed": fcf_pass,
            "value": f"{fcf_margin_pct:.1f}%" if fcf_margin_pct is not None else "N/A",
            "rule": "15% 이상",
            "note": "회계상 순이익이 아닌 실제 회사 금고에 쌓이는 잉여현금흐름 비율",
        },
        {
            "title": "8. [버핏] 요새형 재무건전성 (부채비율)",
            "passed": debt_pass,
            "value": f"D/E {dte:.1f}%" if dte is not None else (f"유동비율 {current_ratio:.2f}" if current_ratio else "N/A"),
            "rule": "부채비율 100% 이하",
            "note": "금리 상승이나 경기 침체에도 흔들리지 않는 보수적 재무구조",
        },
    ]

    return {
        "symbol": sym,
        "name_kr": meta["name_kr"],
        "sector": meta["sector"],
        "moat_type": meta["moat_type"],
        "market_share_pct": share_pct,
        "mgmt_score": meta["mgmt_score"],
        "price": price,
        "chg_pct": chg_pct,
        "high_2y": high_2y,
        "dd_pct": dd_pct,
        "rsi": rsi,
        "mfi": mfi,
        "rev_cagr_pct": rev_cagr_pct,
        "op_years_pass": op_years_pass,
        "op_years_total": op_years_total,
        "avg_op_margin": avg_op_margin,
        "latest_op_margin": latest_op_margin,
        "roe_pct": roe_pct,
        "gross_margin_pct": gross_margin_pct,
        "fcf_margin_pct": fcf_margin_pct,
        "dte": dte,
        "forward_pe": forward_pe,
        "peg": peg,
        "moat_score": moat_score,
        "buy_points": buy_points,
        "signal": signal,
        "signal_code": signal_code,
        "signal_color": signal_color,
        "buy_reasons": buy_reasons or ["펀더멘털 우량 · 기술적 눌림목 대기"],
        "checklist": checklist,
        "annual_rows": annual_rows,
        "hist": hist,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def scan_monopoly_universe() -> list[dict]:
    """Fetch and score all curated wide-moat monopoly stocks in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(analyze_single_stock, sym): sym for sym in MONOPOLY_UNIVERSE}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception:
                continue
    # Sort: strong_buy -> accumulate -> watch -> filtered, then by moat_score desc
    order = {"strong_buy": 0, "accumulate": 1, "watch": 2, "filtered": 3}
    results.sort(key=lambda x: (order.get(x["signal_code"], 9), -x["moat_score"], -x["buy_points"]))
    return results


@st.cache_data(ttl=900, show_spinner=False)
def analyze_custom_ticker_cached(symbol: str, share_pct: int, mgmt_score: int) -> dict:
    return analyze_single_stock(symbol, custom_share_pct=share_pct, custom_mgmt_score=mgmt_score)


def _apple_signal_color(hex_c: str) -> str:
    return {
        "#10b981": "#1d8f34",
        "#38bdf8": "#0071e3",
        "#eab308": "#9a6700",
        "#94a3b8": "#6e6e73",
    }.get(hex_c.lower(), hex_c)


def render_monopoly_summary_cards(stocks: list[dict]) -> str:
    total = len(stocks)
    buy_cnt = sum(1 for s in stocks if s["signal_code"] in ("strong_buy", "accumulate"))
    strong_cnt = sum(1 for s in stocks if s["signal_code"] == "strong_buy")
    avg_op = np.mean([s["avg_op_margin"] for s in stocks if s["avg_op_margin"] is not None]) if stocks else 0.0
    avg_dd = np.mean([s["dd_pct"] for s in stocks]) if stocks else 0.0
    return _compact_html(f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:14px; margin:10px 0 18px 0;">
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>스캔 독점 후보</span><span class="ticker-badge">LIVE</span></div>
        <div style="font-size:1.85rem; font-weight:700; color:#1d1d1f; margin:6px 0 2px 0; letter-spacing:-0.03em; font-variant-numeric:tabular-nums;">{total}종목</div>
        <div style="font-size:0.78rem; color:#6e6e73;">글로벌 과독점 · 경제적 해자 선도주</div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>매수 · 분할매수 신호</span><span class="ticker-badge" style="color:#1d8f34; background:rgba(29,143,52,0.1);">강력 {strong_cnt}개</span></div>
        <div style="font-size:1.85rem; font-weight:700; color:#1d8f34; margin:6px 0 2px 0; letter-spacing:-0.03em; font-variant-numeric:tabular-nums;">{buy_cnt}종목</div>
        <div style="font-size:0.78rem; color:#6e6e73;">해자 72점↑ · 조정/과매도/저PEG</div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>후보군 평균 영업이익률</span><span class="ticker-badge">AVG</span></div>
        <div style="font-size:1.85rem; font-weight:700; color:#0071e3; margin:6px 0 2px 0; letter-spacing:-0.03em; font-variant-numeric:tabular-nums;">{avg_op:.1f}%</div>
        <div style="font-size:0.78rem; color:#6e6e73;">기준: 다개년 연속 20% 이상</div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>후보군 평균 고점 낙폭</span><span class="ticker-badge">2Y HIGH</span></div>
        <div style="font-size:1.85rem; font-weight:700; color:#c96a00; margin:6px 0 2px 0; letter-spacing:-0.03em; font-variant-numeric:tabular-nums;">{avg_dd:.1f}%</div>
        <div style="font-size:0.78rem; color:#6e6e73;">우량 독점주 할인 폭 실시간 추적</div>
      </div>
    </div>
    """)


def render_monopoly_table_html(stocks: list[dict]) -> str:
    if not stocks:
        return _compact_html('<div class="glass-card">선택한 필터 조건에 해당하는 종목이 없습니다.</div>')

    rows = []
    for s in stocks:
        sc = _apple_signal_color(s["signal_color"])
        rev_str = f"{s['rev_cagr_pct']:+.1f}%" if s["rev_cagr_pct"] is not None else "-"
        rev_col = "#1d8f34" if (s["rev_cagr_pct"] is not None and s["rev_cagr_pct"] >= 20.0) else "#1d1d1f"
        op_str = f"{s['avg_op_margin']:.1f}% ({s['op_years_pass']}/{s['op_years_total']}년)" if s["avg_op_margin"] is not None else "-"
        op_col = "#1d8f34" if (s["op_years_total"] >= 3 and s["op_years_pass"] == s["op_years_total"]) else "#c96a00"
        roe_str = f"{s['roe_pct']:.0f}%" if s["roe_pct"] is not None else "-"
        gm_str = f"{s['gross_margin_pct']:.0f}%" if s["gross_margin_pct"] is not None else "-"
        fcf_str = f"{s['fcf_margin_pct']:.0f}%" if s["fcf_margin_pct"] is not None else "-"
        rsi_str = f"{s['rsi']:.1f}" if s["rsi"] is not None else "-"
        rsi_col = "#1d8f34" if (s["rsi"] is not None and s["rsi"] <= 35) else "#d70015" if (s["rsi"] is not None and s["rsi"] >= 70) else "#1d1d1f"
        dd_col = "#1d8f34" if s["dd_pct"] <= -15 else "#0071e3" if s["dd_pct"] <= -8 else "#6e6e73"
        pe_str = f"{s['forward_pe']:.1f}x" if s["forward_pe"] is not None else "-"

        rows.append(
            f'<tr style="border-bottom:1px solid rgba(0,0,0,0.06);">'
            f'<td style="padding:13px 10px;"><b style="color:#1d1d1f; font-size:0.92rem;">{s["name_kr"]}</b> <span class="ticker-badge">{s["symbol"]}</span><div style="font-size:0.74rem; color:#6e6e73; margin-top:2px;">{s["moat_type"]} · 점유율 약 {s["market_share_pct"]}%</div></td>'
            f'<td style="padding:13px 8px; text-align:right; color:{rev_col}; font-weight:600; font-variant-numeric:tabular-nums;">{rev_str}</td>'
            f'<td style="padding:13px 8px; text-align:right; color:{op_col}; font-weight:600; font-variant-numeric:tabular-nums;">{op_str}</td>'
            f'<td style="padding:13px 8px; text-align:center; font-size:0.78rem; color:#6e6e73; font-variant-numeric:tabular-nums;">ROE {roe_str}<br/>GM {gm_str} · FCF {fcf_str}</td>'
            f'<td style="padding:13px 8px; text-align:right; color:#1d1d1f; font-weight:600; font-variant-numeric:tabular-nums;">${s["price"]:,.2f}<div style="font-size:0.74rem; color:{dd_col};">고점 {s["dd_pct"]:.1f}%</div></td>'
            f'<td style="padding:13px 8px; text-align:center; font-variant-numeric:tabular-nums;"><span style="color:{rsi_col}; font-weight:600;">{rsi_str}</span><div style="font-size:0.72rem; color:#86868b;">Fwd {pe_str}</div></td>'
            f'<td style="padding:13px 8px; text-align:center; font-weight:700; color:#1d1d1f; font-variant-numeric:tabular-nums;">{s["moat_score"]}점</td>'
            f'<td style="padding:13px 10px; text-align:center;"><span style="display:inline-block; padding:4px 10px; border-radius:999px; font-size:0.74rem; font-weight:600; background:{sc}16; color:{sc};">{s["signal"]}</span><div style="font-size:0.72rem; color:#86868b; margin-top:3px;">{s["buy_reasons"][0]}</div></td>'
            f'</tr>'
        )

    return _compact_html(f"""
    <div class="glass-card" style="padding:20px 20px; overflow-x:auto;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:700; font-size:0.98rem; color:#1d1d1f;">글로벌 독점 · 과독점 스크리너</span>
        <span style="font-size:0.76rem; color:#86868b;">매수 신호 우선 → 해자 · 버핏 점수 순</span>
      </div>
      <table style="width:100%; border-collapse:collapse; font-size:0.84rem;">
        <thead>
          <tr style="border-bottom:1px solid rgba(0,0,0,0.10); color:#86868b; font-size:0.74rem; font-weight:600;">
            <th style="padding:9px 10px; text-align:left;">기업 · 독점 분야</th>
            <th style="padding:9px 8px; text-align:right;">매출 CAGR</th>
            <th style="padding:9px 8px; text-align:right;">영업이익률 (연속)</th>
            <th style="padding:9px 8px; text-align:center;">버핏 3대 지표</th>
            <th style="padding:9px 8px; text-align:right;">현재가 / 낙폭</th>
            <th style="padding:9px 8px; text-align:center;">RSI / PER</th>
            <th style="padding:9px 8px; text-align:center;">해자점수</th>
            <th style="padding:9px 10px; text-align:center;">실시간 신호</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows)}
        </tbody>
      </table>
    </div>
    """)


def render_stock_deep_dive_html(s: dict) -> str:
    """Render minimalist Apple-style 8-criterion Monopoly & Warren Buffett scorecard."""
    items = []
    passed_cnt = sum(1 for c in s["checklist"] if c["passed"])
    for c in s["checklist"]:
        if c["passed"]:
            badge = '<span style="color:#1d8f34; font-weight:600;">✅ 충족</span>'
            bg = "#f5f5f7"
        else:
            badge = '<span style="color:#c96a00; font-weight:600;">⚠️ 점검 필요</span>'
            bg = "#fbfbfd"
        items.append(
            f'<div style="background:{bg}; border:1px solid rgba(0,0,0,0.06); border-radius:14px; padding:14px 16px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">'
            f'<span style="font-size:0.82rem; font-weight:600; color:#1d1d1f;">{c["title"]}</span>'
            f'<span style="font-size:0.74rem;">{badge}</span>'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; align-items:baseline; margin:8px 0 4px 0;">'
            f'<span style="font-size:1.18rem; font-weight:700; color:#1d1d1f; font-variant-numeric:tabular-nums;">{c["value"]}</span>'
            f'<span style="font-size:0.72rem; color:#86868b;">기준 {c["rule"]}</span>'
            f'</div>'
            f'<div style="font-size:0.76rem; color:#6e6e73; line-height:1.48;">{c["note"]}</div>'
            f'</div>'
        )

    sc = _apple_signal_color(s["signal_color"])
    reasons_str = " · ".join(s["buy_reasons"])
    return _compact_html(f"""
    <div class="agent-panel" style="margin-top:12px;">
      <div class="agent-header">
        <div>
          <div style="font-size:0.75rem; color:#6e6e73; font-weight:600; letter-spacing:0.02em; text-transform:uppercase;">Wide-Moat Scorecard · {s['symbol']}</div>
          <div style="font-size:1.3rem; font-weight:700; color:#1d1d1f; margin-top:3px; letter-spacing:-0.025em;">{s['name_kr']} ({s['symbol']}) · ${s['price']:,.2f} <span style="font-size:0.9rem; color:#c96a00; font-weight:600;">고점 대비 {s['dd_pct']:.1f}%</span></div>
          <div style="font-size:0.84rem; color:#6e6e73; margin-top:4px;">{reasons_str}</div>
        </div>
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <div class="agent-stance" style="background:#f5f5f7; color:#1d1d1f;">8대 기준 {passed_cnt}/8 충족 · {s['moat_score']}점</div>
          <div class="agent-stance" style="background:{sc}16; color:{sc};">{s['signal']}</div>
        </div>
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:12px; margin-top:12px;">
        {"".join(items)}
      </div>
    </div>
    """)


def build_stock_financial_chart(s: dict) -> go.Figure:
    """Build Apple Studio Light 2-panel chart: Annual Revenue & Operating Margin + 1Y Price."""
    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"secondary_y": True}, {"secondary_y": False}]],
        horizontal_spacing=0.1,
        subplot_titles=(
            f"{s['symbol']} 연간 매출 ($B) · 영업이익률 (%)",
            f"{s['symbol']} 최근 1년 주가 · 200일선 (고점 대비 {s['dd_pct']:.1f}%)",
        ),
    )

    ann = s["annual_rows"]
    if ann:
        years = [r["year"] for r in ann]
        revs_b = [r["revenue"] / 1e9 for r in ann]
        opms = [r["op_margin_pct"] for r in ann]
        fig.add_trace(
            go.Bar(
                x=years,
                y=revs_b,
                name="매출 ($B)",
                marker_color="#0071e3",
                text=[f"${v:.1f}B" for v in revs_b],
                textposition="outside",
                textfont=dict(color="#1d1d1f", size=11),
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=years,
                y=opms,
                name="영업이익률 (%)",
                mode="lines+markers+text",
                line=dict(color="#1d8f34", width=2.4),
                marker=dict(size=7, color="#1d8f34"),
                text=[f"{v:.1f}%" if v is not None else "" for v in opms],
                textposition="top center",
                textfont=dict(color="#1d8f34", size=11),
            ),
            row=1,
            col=1,
            secondary_y=True,
        )
        fig.add_hline(
            y=20.0,
            line_dash="dot",
            line_color="#c96a00",
            annotation_text=" 20% 기준",
            annotation_font=dict(color="#c96a00", size=11),
            row=1,
            col=1,
            secondary_y=True,
        )

    sub = s["hist"].tail(252)
    y_min = float(sub["Low"].min()) * 0.95
    y_max = max(float(sub["High"].max()), float(s["high_2y"])) * 1.04

    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["Close"],
            name="주가 ($)",
            line=dict(color="#1d1d1f", width=2.3),
            hovertemplate="$%{y:,.2f}<extra>종가</extra>",
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["MA_200"],
            name="200일선",
            line=dict(color="#ff9500", width=1.5, dash="dash"),
            hovertemplate="$%{y:,.2f}<extra>MA200</extra>",
        ),
        row=1,
        col=2,
    )
    fig.add_hline(
        y=s["high_2y"],
        line_dash="dash",
        line_width=1.1,
        line_color="rgba(29,29,31,0.35)",
        annotation_text=f" 고점 ${s['high_2y']:,.1f}",
        annotation_font=dict(color="#6e6e73", size=11),
        row=1,
        col=2,
    )

    fig.update_yaxes(gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#6e6e73", size=11), row=1, col=1, secondary_y=False)
    fig.update_yaxes(range=[0, max(75.0, max([r["op_margin_pct"] or 0 for r in ann] + [30]) * 1.2)], ticksuffix="%", gridcolor="rgba(0,0,0,0.03)", tickfont=dict(color="#1d8f34", size=11), row=1, col=1, secondary_y=True)
    fig.update_yaxes(range=[y_min, y_max], tickprefix="$", side="right", gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#6e6e73", size=11), row=1, col=2)
    fig.update_xaxes(gridcolor="rgba(0,0,0,0.04)", tickfont=dict(color="#6e6e73", size=11))

    for ann_obj in fig.layout.annotations:
        if ann_obj.font is None or ann_obj.font.color is None:
            ann_obj.font = dict(color="#1d1d1f", size=13)

    fig.update_layout(
        height=380,
        margin=dict(l=12, r=18, t=58, b=20),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1d1d1f", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0.0, bgcolor="rgba(255,255,255,0)", font=dict(color="#6e6e73", size=11)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#d2d2d7", font=dict(color="#1d1d1f", size=12)),
    )
    return fig
