"""Dunchon 2-dong Unified Moa Town & Life Apt 101-401 Dedicated Valuation/News Module.

Includes:
1. Unified Dunchon 2-dong Moa Town (1·2·3구역 통합 추진) master progress tracker & timeline
2. Personalized Life Apartment 101-dong 401-ho profile (전용 84.6㎡ · 대지지분 10.56평 · 매수가 12.5억)
3. Appraisal Value (감정평가액) · Rights Value (권리가액) · General/Member Presale Price (일반/조합원 분양가) · Extra Contribution (추가분담금) Calculator (59㎡ & 84㎡ side-by-side)
4. Land Transaction Permit Zone (토허제) 2026.12.31 D-Day & Rights Cutoff Panel
5. Live Google News RSS feeds + curated key articles
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote
import xml.etree.ElementTree as ET

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from realestate.data_fetcher import fetch_molit_apt_rents, fetch_molit_apt_trades


def _compact(html: str) -> str:
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


# ==============================================================================
# 1. Personalized Profile: Dunchon-dong Life Apartment 101-dong 401-ho
# ==============================================================================
LIFE_APT_PROFILE = {
    "apt_name": "둔촌동 라이프아파트",
    "unit_label": "101동 401호",
    "address": "서울시 강동구 둔촌동 544 · 544-1 일원 (풍성로65길 29)",
    "lot_no": "둔촌동 544 외 (다필지 합산)",
    "lawd_cd": "11740",
    "build_year": 1993,
    "build_month": 3,
    "age_years": 33,
    "households": 78,
    "max_floors": 12,
    "total_land_m2": 3662.0,            # 용적률 산정 연면적(7,360.37㎡) ÷ 용적률(201%) ≈ 3,662㎡ (약 1,108평, 다필지)
    "exclu_m2": 84.65,                  # 101동 전용 84.6~84.7㎡ (공급 28평형)
    "supply_py": 28.0,
    "land_share_m2": 44.0,              # 다필지 합산 기준 84㎡ 대지지분 약 43~44㎡ (약 13.3평 · 상가 제외)
    "land_share_py": 13.30,
    "land_official_per_m2_won": 8_384_000,   # 2026년 둔촌동 544 개별공시지가 8,384,000원/㎡
    "land_official_per_py_man": 2771.6,      # 평당 약 2,772만원
    "land_official_total_eok": 3.69,         # 44.0㎡ × 8,384,000원 = 약 3.69억
    "official_price_2026_eok": 5.50,         # 2026년 84㎡ 공동주택 공시가격 5.31~5.74억 (401호 추정 5.50억)
    "official_price_range_str": "5.31억 ~ 5.74억",
    "far_pct": 201,
    "bcr_pct": 24,
    "my_buy_price_eok": 12.50,
    "latest_price_eok": 12.35,
    "latest_range_str": "12.0억 ~ 12.7억 (2026.10 실거래)",
    "prev_year_eok": 8.18,
    "est_jeonse_eok": 5.50,
    "nearby_foreon_eok": 27.80,
}

LIFE_PRICE_HISTORY: list[tuple[str, float, str]] = [
    ("2021-09", 9.60, "2021 상승장 전고점대"),
    ("2022-11", 7.60, "2022 고금리 조정기"),
    ("2023-08", 7.90, "특례보금자리 반등"),
    ("2024-06", 8.05, "모아타운 고시 후 횡보"),
    ("2025-01", 8.18, "28평형 10층 실거래 (8.18억)"),
    ("2025-06", 8.45, "10층 실거래 (8.45억)"),
    ("2025-11", 9.80, "조합인가·통합 기대 반영"),
    ("2026-04", 11.10, "전 구역 조합설립 완료"),
    ("2026-10", 12.50, "전용 84㎡ 12.0~12.7억 신고가 · 내 매수"),
]

# Unified Dunchon 2-dong Moa Town (1+2+3 통합 추진) Master Roadmap
UNIFIED_MOATOWN_STAGES: list[dict] = [
    {"step": "1단계", "name": "관리계획 승인·고시", "date": "2023.12", "state": "done", "note": "통합심의 통과 · 공식 지정 완료"},
    {"step": "2단계", "name": "전 구역 조합설립인가", "date": "2025.08~2026.03", "state": "done", "note": "1·2·3구역 조합설립 및 신탁대행 완료"},
    {"step": "3단계", "name": "1·2·3구역 통합 · 시공사 선정", "date": "2026~2027 (현재)", "state": "current", "note": "통합 추진 + 라이프 편입·관리계획 변경 핵심 국면"},
    {"step": "4단계", "name": "사업시행인가 · 감정평가", "date": "예상 2027~2028", "state": "pending", "note": "종전자산 감정평가 및 조합원 분양신청"},
    {"step": "5단계", "name": "관리처분 · 이주/철거", "date": "예상 2028~2029", "state": "pending", "note": "권리가액·분담금 최종 확정 및 이주"},
    {"step": "6단계", "name": "착공 · 일반분양 · 입주", "date": "예상 2030~2033", "state": "pending", "note": "약 1,600~2,000세대 통합 브랜드 대단지 완공"},
]

TOHEOJE_INFO = {
    "status": "지정 유지 중 (서울시 25개 전 자치구 아파트 일괄 지정)",
    "expiry_date": date(2026, 12, 31),
    "residence_rule": "허가일(잔금/입주 가능일)로부터 4개월 내 전입 + 2년 실거주 의무 (갭투자 불가)",
    "moatown_pinpoint": "모아타운 구역 내 지목 '도로(사도)' 등 지분 쪼개기 방지 핀셋 토허제 병행",
    "cutoff_b": "2022년 1월 20일 (B구역 권리산정기준일)",
    "cutoff_a": "2023년 11월 2일 (A구역·확대구역 권리산정기준일)",
    "owner_action": "연말(2026.12.31) 정부·서울시 연장/해제 발표에 따라 2027년 초 거래량 및 매도 유동성 분기점 도래",
}

CURATED_ARTICLES: dict[str, list[dict]] = {
    "moatown": [
        {
            "title": "강동구 둔촌2동 모아타운 1·2·3구역 전 구역 조합설립 완료… 통합 시너지·시공사 선정 본궤도",
            "source": "하우징타임즈 · 정비업계 종합",
            "date": "2026-04",
            "tag": "통합추진",
            "summary": "2023.12 관리계획 고시 이후 1·2·3구역 모두 조합설립인가 및 신탁 사업대행 완료. 통합 추진 시 ~2,000세대급 대단지 시너지 기대.",
            "url": "https://search.naver.com/search.naver?where=news&query=" + quote("둔촌2동 모아타운 통합 조합설립 시공사"),
        },
        {
            "title": "둔촌동 77-41번지 일대 모아타운, 시공사 수의계약·통합 설계로 브랜드 대단지 추진",
            "source": "하우징헤럴드 · 아유경제",
            "date": "2026-06",
            "tag": "시공사선정",
            "summary": "5호선 둔촌동역·9호선 중앙보훈병원역 더블역세권 + 올림픽파크포레온 인접 입지. 관리계획 추정비례율 140%대(공사비 상승 반영 재산정 주시).",
            "url": "https://search.naver.com/search.naver?where=news&query=" + quote("둔촌동 77-41 모아타운 시공사"),
        },
        {
            "title": "둔촌2동 모아타운, 인접 구축 편입·정비계획 변경 시 약 2,000세대 규모 확대 가능성",
            "source": "위키리크스한국 · 매일경제",
            "date": "2026-05",
            "tag": "구역확대",
            "summary": "기존 1,600세대 계획에서 주변 노후 소규모 공동주택 추가 편입 시 사업면적 확대 및 기반시설 효율화로 대단지 프리미엄 강화 기대.",
            "url": "https://search.naver.com/search.naver?where=news&query=" + quote("둔촌2동 모아타운 2000가구 확대"),
        },
    ],
    "life_apt": [
        {
            "title": "둔촌동 라이프아파트 등 인접 구축, 모아타운 추가 편입 논의와 자산가치 재평가",
            "source": "하우징워치 · 매일경제",
            "date": "2026-03",
            "tag": "편입이슈",
            "summary": "2023년 초기 관리계획에서는 제외(제척)됐으나, 통합 모아타운 추진과 올림픽파크포레온 입주 효과로 라이프아파트 편입·정비 기대감 확대.",
            "url": "https://search.naver.com/search.naver?where=news&query=" + quote("둔촌동 라이프아파트 모아타운"),
        },
        {
            "title": "둔촌동 라이프아파트 101동(전용 84㎡), 2025년 8억대 → 2026년 10월 12.0~12.7억 신고가",
            "source": "국토부 실거래 · KB시세 종합",
            "date": "2026-10",
            "tag": "시세급등",
            "summary": "전용 84.6㎡(대지지분 약 10.56평, 2026 공시가격 5.3억대) 기준 1년 반 만에 4억 이상 급등하며 모아타운 기대감을 선반영 중.",
            "url": "https://search.naver.com/search.naver?where=news&query=" + quote("둔촌동 라이프 아파트 실거래가"),
        },
        {
            "title": "구축 소규모 아파트의 모아타운 편입 핵심 관문: 주민 동의율 · 관리계획 변경 · 감정평가",
            "source": "정비사업 리서치",
            "date": "2026-08",
            "tag": "체크포인트",
            "summary": "추가 편입 확정에는 라이프 주민 동의율 확보 + 서울시·강동구 관리계획 변경 승인 + 기존 통합 조합과의 권리/분담금 합의가 핵심.",
            "url": "https://search.naver.com/search.naver?where=news&query=" + quote("모아타운 추가 편입 관리계획 변경"),
        },
    ],
    "toheoje": [
        {
            "title": "서울 25개 전 자치구 아파트 토지거래허가구역, 2026년 12월 31일 만료 앞두고 연장·해제 촉각",
            "source": "서울시 · 경제언론 종합",
            "date": "2026-11",
            "tag": "연말 만료",
            "summary": "강동구 둔촌동 아파트 포함 서울 전역 아파트 토허제 법정 기한이 2026.12.31 도래. 연말 정부·서울시 최종 발표 예정.",
            "url": "https://search.naver.com/search.naver?where=news&query=" + quote("서울 강동구 토지거래허가구역 2026년 12월"),
        },
        {
            "title": "둔촌동 77-41 모아타운 권리산정기준일: B구역 2022.01.20 / A·확대구역 2023.11.02",
            "source": "강동구청 고시",
            "date": "2024-01",
            "tag": "권리산정일",
            "summary": "1993년 준공된 기존 구분등기 아파트(라이프 101동 401호)는 지분쪼개기 대상이 아니나, 통합·확대 편입 시 신규 고시 조건 재확인 필요.",
            "url": "https://search.naver.com/search.naver?where=news&query=" + quote("둔촌동 77-41 권리산정기준일"),
        },
    ],
}


# ==============================================================================
# 2. Valuation & Presale Engine (감정평가액 · 권리가액 · 일반/조합원 분양가 · 분담금)
# ==============================================================================
def compute_life_101_401_valuation(
    buy_price_eok: float = 12.50,
    official_price_eok: float = 5.50,
    land_share_py: float = 13.30,
    land_unit_man: float = 7200.0,
    bldg_val_eok: float = 0.85,
    appraisal_mode: str = "대지지분+건물 합산 (기준안)",
    custom_appraisal_eok: float = 10.40,
    prop_rate_pct: float = 105.0,
    gen_py_price_man: float = 5200.0,
    member_discount_pct: float = 18.0,
    post_84_eok: float = 23.0,
    post_59_eok: float = 17.5,
) -> dict:
    """Estimate 101-401 appraisal value, rights value, general & member presale prices, and net profit."""
    # Method 1: Official price x 1.35 (conservative current official-price basis)
    est_by_official = official_price_eok * 1.35
    # Method 2: Land share (10.56 py) x per-py land appraisal + depreciated building value
    est_by_land = (land_share_py * land_unit_man / 10_000.0) + bldg_val_eok
    # Method 3: Future appraisal reflection (when 2027-28 official price catches up to 12.5 eok market)
    est_by_market_75 = buy_price_eok * 0.74

    if "공시가격" in appraisal_mode:
        appraisal_eok = est_by_official
    elif "시세 74%" in appraisal_mode:
        appraisal_eok = est_by_market_75
    elif "직접" in appraisal_mode:
        appraisal_eok = custom_appraisal_eok
    else:
        appraisal_eok = est_by_land

    rights_eok = appraisal_eok * (prop_rate_pct / 100.0)

    # Presale price calculations (59m2 = ~25 supply py, 84m2 = ~34 supply py)
    member_py_man = gen_py_price_man * (1.0 - member_discount_pct / 100.0)

    plans = []
    for label, supply_py, post_mkt in [
        ("전용 59㎡ (25평형)", 25.0, post_59_eok),
        ("전용 84㎡ (34평형 · 국평)", 34.0, post_84_eok),
    ]:
        gen_price_eok = (gen_py_price_man * supply_py) / 10_000.0
        mem_price_eok = (member_py_man * supply_py) / 10_000.0
        extra_contrib_eok = mem_price_eok - rights_eok  # positive = pay extra, negative = refund
        total_cost_eok = buy_price_eok + extra_contrib_eok
        est_profit_eok = post_mkt - total_cost_eok
        est_roi_pct = (est_profit_eok / total_cost_eok * 100.0) if total_cost_eok > 0 else 0.0
        # Premium paid above rights value (실질 프리미엄 P = 매수가 - 권리가액)
        premium_p_eok = buy_price_eok - rights_eok

        plans.append(
            {
                "type": label,
                "supply_py": supply_py,
                "gen_price_eok": gen_price_eok,
                "mem_price_eok": mem_price_eok,
                "rights_eok": rights_eok,
                "extra_contrib_eok": extra_contrib_eok,
                "total_cost_eok": total_cost_eok,
                "post_mkt_eok": post_mkt,
                "est_profit_eok": est_profit_eok,
                "est_roi_pct": est_roi_pct,
                "premium_p_eok": premium_p_eok,
            }
        )

    return {
        "buy_price_eok": buy_price_eok,
        "land_share_py": land_share_py,
        "land_share_m2": land_share_py * 3.3058,
        "appraisal_eok": appraisal_eok,
        "est_by_official": est_by_official,
        "est_by_land": est_by_land,
        "est_by_market_75": est_by_market_75,
        "prop_rate_pct": prop_rate_pct,
        "rights_eok": rights_eok,
        "premium_p_eok": buy_price_eok - rights_eok,
        "gen_py_price_man": gen_py_price_man,
        "member_py_man": member_py_man,
        "member_discount_pct": member_discount_pct,
        "plans": plans,
    }


# ==============================================================================
# 3. Live Google News RSS Fetcher + MOLIT Live Life Apt Trades
# ==============================================================================
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_google_news_rss(query: str, max_items: int = 6) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    try:
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.text)
        items = []
        for el in root.findall(".//item")[:max_items]:
            title = (el.findtext("title") or "").strip()
            link = (el.findtext("link") or "").strip()
            pub_raw = (el.findtext("pubDate") or "").strip()
            src_el = el.find("source")
            source = (src_el.text or "Google 뉴스").strip() if src_el is not None else "Google 뉴스"
            pub_fmt = pub_raw[:16]
            try:
                dt = parsedate_to_datetime(pub_raw).astimezone(timezone(timedelta(hours=9)))
                pub_fmt = dt.strftime("%Y-%m-%d")
            except Exception:
                pass
            if title and link:
                items.append(
                    {"title": title, "source": source, "date": pub_fmt, "tag": "실시간 뉴스", "summary": "", "url": link}
                )
        return items
    except Exception:
        return []


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_life_apt_live_trades(molit_key: str) -> dict:
    if not molit_key.strip():
        return {"is_live": False, "trades": pd.DataFrame(), "rents": pd.DataFrame()}

    tdf = fetch_molit_apt_trades(molit_key, "11740", months=12)
    rdf = fetch_molit_apt_rents(molit_key, "11740", months=12)

    life_t = pd.DataFrame()
    if not tdf.empty:
        mask = tdf["apt_name"].str.contains("라이프", na=False) & tdf["dong"].str.contains("둔촌", na=False)
        life_t = tdf[mask].copy()
        if life_t.empty:
            life_t = tdf[tdf["apt_name"].str.contains("라이프", na=False)].copy()

    life_r = pd.DataFrame()
    if not rdf.empty:
        life_r = rdf[rdf["apt_name"].str.contains("라이프", na=False)].copy()

    return {"is_live": not life_t.empty, "trades": life_t, "rents": life_r}


# ==============================================================================
# 4. Apple Titanium Light UI Renderers & Charts
# ==============================================================================
def render_moatown_hero(live_price: float, buy_price: float, is_live_tx: bool) -> str:
    today_kst = datetime.now(timezone(timedelta(hours=9))).date()
    d_days = (TOHEOJE_INFO["expiry_date"] - today_kst).days
    dday_str = f"D-{d_days}" if d_days > 0 else ("D-DAY" if d_days == 0 else f"만료 후 {abs(d_days)}일")
    pnl_eok = live_price - buy_price
    pnl_col = "#4ade80" if pnl_eok >= 0 else "#fca5a5"
    tx_badge = "국토부 LIVE" if is_live_tx else "2026.10 실거래"

    return _compact(f"""
    <div class="hero-wrap">
      <div>
        <div style="font-size:0.73rem; letter-spacing:0.09em; color:#a8a29e; font-weight:700;">DUNCHON 2-DONG UNIFIED MOATOWN × LIFE APT 101-401</div>
        <div style="font-size:1.52rem; font-weight:800; letter-spacing:-0.03em; margin-top:4px;">둔촌2동 통합 모아타운 &amp; 라이프아파트 101동 401호</div>
        <div style="font-size:0.82rem; color:#d6d3d1; margin-top:4px;">
          {LIFE_APT_PROFILE['address']} · 전용 {LIFE_APT_PROFILE['exclu_m2']:.2f}㎡ · 대지지분 <b>약 44㎡(13.3평)</b> · 2026 개별공시지가 <b>838.4만/㎡</b> · 공동주택 공시가 <b>5.31~5.74억</b>
        </div>
      </div>
      <div style="display:flex; gap:10px; flex-wrap:wrap;">
        <div style="background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.12); border-radius:14px; padding:10px 15px;">
          <div style="font-size:0.7rem; color:#a8a29e;">내 매수가 vs 시세 ({tx_badge})</div>
          <div style="font-size:1.18rem; font-weight:800; font-variant-numeric:tabular-nums;">
            {buy_price:.2f}억 <span style="font-size:0.78rem; color:{pnl_col};">→ 현재 {live_price:.2f}억 ({pnl_eok:+.2f}억)</span>
          </div>
        </div>
        <div style="background:rgba(185,28,28,0.28); border:1px solid rgba(248,113,113,0.35); border-radius:14px; padding:10px 15px;">
          <div style="font-size:0.7rem; color:#fecaca;">강동구 토허제 만료 (2026.12.31)</div>
          <div style="font-size:1.18rem; font-weight:800; color:#fef2f2; font-variant-numeric:tabular-nums;">{dday_str} <span style="font-size:0.75rem; color:#fecaca;">연말 발표 주목</span></div>
        </div>
      </div>
    </div>
    """)


def render_valuation_summary_cards(val: dict) -> str:
    p84 = val["plans"][1]
    p59 = val["plans"][0]
    p_col = "#15803d" if p84["est_profit_eok"] >= 0 else "#b91c1c"
    return _compact(f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:13px; margin:10px 0 16px 0;">
      <div class="glass-card" style="padding:17px 19px;">
        <div class="card-kicker"><span>101동 401호 예상 감정평가액</span><span class="ticker-badge">대지 {val['land_share_m2']:.1f}㎡({val['land_share_py']:.2f}평)</span></div>
        <div style="font-size:1.72rem; font-weight:800; color:#1c1917; margin:6px 0 2px 0; font-variant-numeric:tabular-nums;">약 {val['appraisal_eok']:.2f}억</div>
        <div style="font-size:0.75rem; color:#57534e;">공시가×1.35 {val['est_by_official']:.2f}억 · 지분합산 {val['est_by_land']:.2f}억 · 시세74% {val['est_by_market_75']:.2f}억</div>
      </div>
      <div class="glass-card" style="padding:17px 19px;">
        <div class="card-kicker"><span>예상 권리가액 (비례율 {val['prop_rate_pct']:.0f}%)</span><span class="ticker-badge">실질 P {val['premium_p_eok']:+.2f}억</span></div>
        <div style="font-size:1.72rem; font-weight:800; color:#1d4ed8; margin:6px 0 2px 0; font-variant-numeric:tabular-nums;">약 {val['rights_eok']:.2f}억</div>
        <div style="font-size:0.75rem; color:#57534e;">감정가 {val['appraisal_eok']:.2f}억 × 비례율 {val['prop_rate_pct']:.0f}% (매수가 12.5억 대비 P {val['premium_p_eok']:.2f}억)</div>
      </div>
      <div class="glass-card" style="padding:17px 19px;">
        <div class="card-kicker"><span>예상 분양가 (평당 {val['gen_py_price_man']:,.0f}만)</span><span class="ticker-badge">조합원 -{val['member_discount_pct']:.0f}%</span></div>
        <div style="font-size:1.25rem; font-weight:800; color:#1c1917; margin:7px 0 3px 0; font-variant-numeric:tabular-nums;">
          84㎡ 일반 {p84['gen_price_eok']:.1f}억 · 조합 {p84['mem_price_eok']:.1f}억
        </div>
        <div style="font-size:0.75rem; color:#57534e;">59㎡ 일반 {p59['gen_price_eok']:.1f}억 · 조합원 <b>{p59['mem_price_eok']:.1f}억</b> (평당 {val['member_py_man']:,.0f}만)</div>
      </div>
      <div class="glass-card" style="padding:17px 19px;">
        <div class="card-kicker"><span>84㎡ 신청 시 총원가 &amp; 안전마진</span><span class="ticker-badge" style="color:{p_col}; background:{p_col}16;">분담금 {p84['extra_contrib_eok']:+.2f}억</span></div>
        <div style="font-size:1.68rem; font-weight:800; color:{p_col}; margin:6px 0 2px 0; font-variant-numeric:tabular-nums;">{p84['est_profit_eok']:+.2f}억 ({p84['est_roi_pct']:+.1f}%)</div>
        <div style="font-size:0.75rem; color:#57534e;">총원가 {p84['total_cost_eok']:.2f}억 vs 완공 시세 {p84['post_mkt_eok']:.1f}억 가정</div>
      </div>
    </div>
    """)


def render_presale_comparison_table(val: dict) -> str:
    rows = []
    for p in val["plans"]:
        pcol = "#15803d" if p["est_profit_eok"] >= 0 else "#b91c1c"
        contrib_lbl = f"+{p['extra_contrib_eok']:.2f}억 납부" if p["extra_contrib_eok"] >= 0 else f"{abs(p['extra_contrib_eok']):.2f}억 환급"
        rows.append(
            f'<tr style="border-bottom:1px solid rgba(28,25,23,0.07);">'
            f'<td style="padding:13px 10px; font-weight:800; color:#1c1917;">{p["type"]}</td>'
            f'<td style="padding:13px 8px; text-align:right; color:#57534e; font-variant-numeric:tabular-nums;">{p["gen_price_eok"]:.2f}억</td>'
            f'<td style="padding:13px 8px; text-align:right; font-weight:700; color:#1d4ed8; font-variant-numeric:tabular-nums;">{p["mem_price_eok"]:.2f}억</td>'
            f'<td style="padding:13px 8px; text-align:right; color:#1c1917; font-variant-numeric:tabular-nums;">{p["rights_eok"]:.2f}억</td>'
            f'<td style="padding:13px 8px; text-align:right; font-weight:700; color:#b45309; font-variant-numeric:tabular-nums;">{contrib_lbl}</td>'
            f'<td style="padding:13px 8px; text-align:right; font-weight:700; color:#1c1917; font-variant-numeric:tabular-nums;">{p["total_cost_eok"]:.2f}억</td>'
            f'<td style="padding:13px 8px; text-align:right; color:#57534e; font-variant-numeric:tabular-nums;">{p["post_mkt_eok"]:.1f}억</td>'
            f'<td style="padding:13px 8px; text-align:right; font-weight:800; color:{pcol}; font-variant-numeric:tabular-nums;">{p["est_profit_eok"]:+.2f}억 ({p["est_roi_pct"]:+.1f}%)</td>'
            f'</tr>'
        )
    return _compact(f"""
    <div class="glass-card" style="padding:20px 22px; overflow-x:auto; margin-bottom:14px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:800; font-size:0.98rem; color:#1c1917;">🧮 둔촌2동 통합 모아타운 · 라이프 101동 401호 평형별 분양가 &amp; 분담금 시뮬레이션</span>
        <span style="font-size:0.74rem; color:#78716c;">총 투자원가 = 내 매수가({val['buy_price_eok']:.2f}억) + 예상 추가분담금 (취득세·이주비 이자 별도)</span>
      </div>
      <table style="width:100%; border-collapse:collapse; font-size:0.84rem;">
        <thead>
          <tr style="border-bottom:1px solid rgba(28,25,23,0.12); color:#78716c; font-size:0.74rem; font-weight:600;">
            <th style="padding:9px 10px; text-align:left;">신청 평형</th>
            <th style="padding:9px 8px; text-align:right;">예상 일반분양가</th>
            <th style="padding:9px 8px; text-align:right;">예상 조합원분양가</th>
            <th style="padding:9px 8px; text-align:right;">내 권리가액</th>
            <th style="padding:9px 8px; text-align:right;">예상 추가분담금</th>
            <th style="padding:9px 8px; text-align:right;">총 투자원가</th>
            <th style="padding:9px 8px; text-align:right;">완공 예상시세</th>
            <th style="padding:9px 8px; text-align:right;">예상 안전마진</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
      <div style="margin-top:12px; padding:11px 14px; border-radius:12px; background:#f2efe9; font-size:0.78rem; color:#57534e; line-height:1.55;">
        <b style="color:#1c1917;">💡 둔촌동 544·544-1 라이프아파트 101동 401호 공부 실측 근거:</b>
        건축물대장 용적률 산정 연면적(<b>7,360.37㎡</b>) ÷ 용적률(<b>201%</b>) = 다필지 합산 대지 약 <b>3,662㎡(1,108평)</b> →
        상가 지분 제외 시 전용 84㎡ 대지지분은 <b>약 43~44㎡ (13.1~13.5평)</b>입니다.
        *(일부 플랫폼에 뜨는 10.55평은 대표지번 544번지 단일필지 2,719.6㎡만 단순 나눈 수치)* ·
        2026년 <b>개별공시지가 8,384,000원/㎡</b>(평당 2,772만) · <b>공동주택 공시가격 5.31억~5.74억</b>.
        등기부등본상 소수점 대지지분을 위 입력칸에 직접 넣으시면 감정가·분담금이 즉시 정밀 재계산됩니다.
      </div>
    </div>
    """)


def build_valuation_waterfall_chart(val: dict) -> go.Figure:
    """Compare 59m2 vs 84m2 Total Cost (Buy Price + Extra Contribution) against General Presale & Post-Build Value."""
    p59, p84 = val["plans"][0], val["plans"][1]
    cats = ["전용 59㎡ (25평)", "전용 84㎡ (34평)"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=cats,
            y=[val["buy_price_eok"], val["buy_price_eok"]],
            name="내 매수가 (12.5억)",
            marker_color="#18181b",
            text=[f"매수 {val['buy_price_eok']:.1f}억"] * 2,
            textposition="inside",
            textfont=dict(color="#faf9f6", size=11),
        )
    )
    fig.add_trace(
        go.Bar(
            x=cats,
            y=[max(0.0, p59["extra_contrib_eok"]), max(0.0, p84["extra_contrib_eok"])],
            name="예상 추가분담금",
            marker_color="#b45309",
            text=[f"+{p59['extra_contrib_eok']:.2f}억", f"+{p84['extra_contrib_eok']:.2f}억"],
            textposition="inside",
            textfont=dict(color="#faf9f6", size=11),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=cats,
            y=[p59["gen_price_eok"], p84["gen_price_eok"]],
            mode="markers+text",
            name="예상 일반분양가",
            marker=dict(size=13, color="#1d4ed8", symbol="diamond"),
            text=[f"일반분양 {p59['gen_price_eok']:.1f}억", f"일반분양 {p84['gen_price_eok']:.1f}억"],
            textposition="middle right",
            textfont=dict(color="#1d4ed8", size=11),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=cats,
            y=[p59["post_mkt_eok"], p84["post_mkt_eok"]],
            mode="markers+text",
            name="완공 후 예상시세",
            marker=dict(size=14, color="#15803d", symbol="star"),
            text=[f"완공시세 {p59['post_mkt_eok']:.1f}억 (+{p59['est_profit_eok']:.1f}억)", f"완공시세 {p84['post_mkt_eok']:.1f}억 (+{p84['est_profit_eok']:.1f}억)"],
            textposition="top center",
            textfont=dict(color="#15803d", size=11),
        )
    )
    max_y = max(p84["post_mkt_eok"], p84["total_cost_eok"], p84["gen_price_eok"]) * 1.18
    fig.update_layout(
        title=dict(text="라이프 101동 401호 · 평형별 총 투자원가 vs 일반분양가 vs 완공 예상시세", font=dict(size=14, color="#1c1917")),
        barmode="stack",
        height=390,
        margin=dict(l=46, r=70, t=64, b=34),
        yaxis=dict(range=[0, max_y], ticksuffix="억", gridcolor="rgba(0,0,0,0.06)"),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)"),
    )
    return fig


def render_unified_moatown_panel() -> str:
    """Single unified Dunchon 2-dong Moa Town (1·2·3구역 통합) progress roadmap + Life Apt incorporation panel."""
    steps_html = []
    for stp in UNIFIED_MOATOWN_STAGES:
        if stp["state"] == "done":
            bg, fg, icon = "rgba(21,128,61,0.12)", "#15803d", "✅ "
            border = "rgba(21,128,61,0.22)"
        elif stp["state"] == "current":
            bg, fg, icon = "rgba(29,78,216,0.14)", "#1d4ed8", "🔥 "
            border = "rgba(29,78,216,0.35)"
        else:
            bg, fg, icon = "#f2efe9", "#78716c", "⏳ "
            border = "rgba(28,25,23,0.08)"
        steps_html.append(
            f'<div style="background:{bg}; border:1px solid {border}; border-radius:14px; padding:12px 14px;">'
            f'<div style="display:flex; justify-content:space-between; font-size:0.72rem; font-weight:700; color:{fg};">'
            f'<span>{icon}{stp["step"]}</span><span>{stp["date"]}</span>'
            f'</div>'
            f'<div style="font-size:0.9rem; font-weight:800; color:#1c1917; margin:4px 0 3px 0;">{stp["name"]}</div>'
            f'<div style="font-size:0.75rem; color:#57534e; line-height:1.42;">{stp["note"]}</div>'
            f'</div>'
        )

    return _compact(f"""
    <div class="agent-panel" style="margin-bottom:16px;">
      <div class="agent-header">
        <div>
          <div style="font-size:0.74rem; color:#1d4ed8; font-weight:700; letter-spacing:0.06em;">UNIFIED MASTERPLAN · 강동구 둔촌2동 모아타운 (1·2·3구역 통합 추진)</div>
          <div style="font-size:1.08rem; font-weight:800; color:#1c1917; margin-top:4px;">전 구역 조합설립 완료 → 통합 시공사 선정 &amp; 라이프아파트 편입·확대 국면</div>
          <div style="font-size:0.8rem; color:#57534e; margin-top:3px;">
            전체 규모 약 <b>1,600 ~ 2,000세대</b> (라이프 등 인접 구축 편입 시 대단지 극대화) · 5호선 둔촌동역 &amp; 9호선 중앙보훈병원역 더블역세권 · 올림픽파크포레온 인접
          </div>
        </div>
        <div class="agent-stance" style="background:rgba(29,78,216,0.14); color:#1d4ed8;">통합 진행률 약 55%</div>
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(185px, 1fr)); gap:10px; margin-top:14px;">
        {"".join(steps_html)}
      </div>
      <div style="margin-top:14px; padding:12px 15px; border-radius:14px; background:#f2efe9; font-size:0.8rem; color:#44403c; line-height:1.55;">
        <b style="color:#1c1917;">🏢 라이프아파트(78세대) 편입 핵심 체크리스트:</b>
        ① 초기 2023.12 관리계획에서는 미포함(제척) 상태였으나, 1·2·3구역 통합 추진과 맞물려 <b>구역 확대 편입(관리계획 변경)</b>이 핵심 호재로 작용 중 ·
        ② 편입 확정 관문: <b>라이프 주민 동의율 확보 → 통합 조합 합의 → 강동구청·서울시 관리계획 변경 심의 통과</b> ·
        ③ 편입 시 기존 대단지 시너지로 <b>일반분양가·브랜드 가치·환금성</b>이 독자 소규모 재건축 대비 크게 상승합니다.
      </div>
    </div>
    """)


def render_toheoje_panel() -> str:
    return _compact(f"""
    <div class="agent-panel" style="margin-bottom:16px;">
      <div class="agent-header">
        <div>
          <div style="font-size:0.74rem; color:#b91c1c; font-weight:700; letter-spacing:0.06em;">LAND TRANSACTION PERMIT ZONE · 토지거래허가구역(토허제) &amp; 권리산정기준일</div>
          <div style="font-size:1.05rem; font-weight:700; color:#1c1917; margin-top:4px;">{TOHEOJE_INFO["status"]}</div>
        </div>
        <div class="agent-stance" style="background:rgba(185,28,28,0.12); color:#b91c1c;">만료기한 2026.12.31</div>
      </div>
      <div class="signal-grid">
        <div class="signal-item">
          <span class="signal-tag" style="background:#b91c1c18; color:#b91c1c;">실거주 의무 · 매매 규제</span><br/>
          {TOHEOJE_INFO["residence_rule"]}
        </div>
        <div class="signal-item">
          <span class="signal-tag" style="background:#b4530918; color:#b45309;">권리산정기준일 (둔촌 77-41)</span><br/>
          • <b>{TOHEOJE_INFO["cutoff_b"]}</b><br/>
          • <b>{TOHEOJE_INFO["cutoff_a"]}</b><br/>
          <span style="font-size:0.74rem; color:#78716c;">(1993년 준공 구분등기 라이프 101동 401호는 지분쪼개기 대상 아님 · 편입 변경 고시 시 조건 재확인)</span>
        </div>
        <div class="signal-item">
          <span class="signal-tag" style="background:#1d4ed818; color:#1d4ed8;">모아타운 핀셋 토허제</span><br/>
          {TOHEOJE_INFO["moatown_pinpoint"]}
        </div>
        <div class="signal-item">
          <span class="signal-tag" style="background:#15803d18; color:#15803d;">보유자 핵심 체크 (2026 연말)</span><br/>
          {TOHEOJE_INFO["owner_action"]}
        </div>
      </div>
    </div>
    """)


def build_life_apt_price_chart(buy_price_eok: float, live_trades: pd.DataFrame | None = None) -> go.Figure:
    hist_df = pd.DataFrame(LIFE_PRICE_HISTORY, columns=["ym", "price", "note"])
    hist_df["dt"] = pd.to_datetime(hist_df["ym"] + "-01")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hist_df["dt"],
            y=hist_df["price"],
            mode="lines+markers+text",
            name="라이프아파트 실거래 추이 (억)",
            line=dict(color="#18181b", width=2.6),
            marker=dict(size=8, color="#18181b"),
            text=[f"{v:.2f}억" for v in hist_df["price"]],
            textposition="top center",
            textfont=dict(size=10, color="#1c1917"),
            customdata=hist_df["note"],
            hovertemplate="%{x|%Y-%m}<br><b>%{y:.2f}억</b><br>%{customdata}<extra></extra>",
        )
    )

    if live_trades is not None and not live_trades.empty:
        lt = live_trades.copy()
        lt["dt"] = pd.to_datetime(lt["deal_date"], errors="coerce")
        lt = lt.dropna(subset=["dt"])
        if not lt.empty:
            fig.add_trace(
                go.Scatter(
                    x=lt["dt"],
                    y=lt["price_eok"],
                    mode="markers",
                    name="국토부 LIVE 실거래 건별",
                    marker=dict(size=10, color="#15803d", symbol="diamond", line=dict(color="#faf9f6", width=1.2)),
                    hovertemplate="<b>LIVE 실거래</b> %{x|%Y-%m-%d}<br>%{y:.2f}억<extra></extra>",
                )
            )

    fig.add_hline(
        y=buy_price_eok,
        line_dash="dash",
        line_width=1.8,
        line_color="#1d4ed8",
        annotation_text=f" 내 매수가 101-401 ({buy_price_eok:.2f}억)",
        annotation_position="bottom right",
        annotation_font=dict(color="#ffffff", size=11),
        annotation_bgcolor="#1d4ed8",
    )

    y_min = min(float(hist_df["price"].min()), buy_price_eok) - 1.2
    y_max = max(float(hist_df["price"].max()), buy_price_eok) + 1.8
    fig.update_yaxes(range=[max(4.0, y_min), y_max], ticksuffix="억", side="right", gridcolor="rgba(0,0,0,0.06)")
    fig.update_layout(
        title=dict(text="둔촌동 라이프아파트 실거래가 흐름 vs 내 매수가 12.5억 (2021~2026)", font=dict(size=14, color="#1c1917")),
        height=370,
        margin=dict(l=32, r=60, t=58, b=28),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)"),
        hovermode="closest",
    )
    return fig


def render_news_card_list(articles: list[dict], heading: str, search_query: str) -> str:
    naver_url = f"https://search.naver.com/search.naver?where=news&sort=1&query={quote(search_query)}"
    google_url = f"https://news.google.com/search?q={quote(search_query)}&hl=ko&gl=KR&ceid=KR:ko"

    rows = []
    for a in articles:
        is_live = a.get("tag") == "실시간 뉴스"
        t_bg = "rgba(21,128,61,0.12)" if is_live else "rgba(29,78,216,0.10)"
        t_fg = "#15803d" if is_live else "#1d4ed8"
        sum_html = f'<div style="font-size:0.78rem; color:#57534e; margin-top:4px; line-height:1.48;">{a["summary"]}</div>' if a.get("summary") else ""
        rows.append(
            f'<div style="padding:12px 0; border-bottom:1px solid rgba(28,25,23,0.07);">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">'
            f'<span style="display:inline-block; padding:2px 8px; border-radius:999px; font-size:0.7rem; font-weight:700; background:{t_bg}; color:{t_fg};">{a["tag"]}</span>'
            f'<span style="font-size:0.72rem; color:#78716c;">{a["source"]} · {a["date"]}</span>'
            f'</div>'
            f'<div style="margin-top:5px;"><a href="{a["url"]}" target="_blank" style="color:#1c1917; font-weight:700; font-size:0.89rem; text-decoration:none;">{a["title"]} ↗</a></div>'
            f'{sum_html}'
            f'</div>'
        )

    return _compact(f"""
    <div class="glass-card" style="padding:18px 20px; height:100%;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:6px;">
        <span style="font-weight:800; font-size:0.95rem; color:#1c1917;">{heading}</span>
        <span style="font-size:0.73rem;">
          <a href="{naver_url}" target="_blank" style="color:#15803d; font-weight:700; text-decoration:none; margin-right:8px;">네이버 최신뉴스 ↗</a>
          <a href="{google_url}" target="_blank" style="color:#1d4ed8; font-weight:700; text-decoration:none;">구글뉴스 ↗</a>
        </span>
      </div>
      {"".join(rows)}
    </div>
    """)
