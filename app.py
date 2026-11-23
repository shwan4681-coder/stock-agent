"""US Market Stock Agent — Sleek Streamlit + HTML/CSS Real-time Dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from agent_analyzer import ask_gemini_agent, generate_agent_briefing
from data_fetcher import load_all_market_data
from ui_components import (
    CUSTOM_CSS,
    build_fear_greed_history_chart,
    build_nasdaq_chart,
    build_sp500_drawdown_chart,
    render_agent_briefing_html,
    render_drawdown_comparison_html,
    render_fear_greed_card,
    render_hero_html,
    render_index_kpi_card,
    render_oscillator_card,
)

st.set_page_config(
    page_title="US Market Stock Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------- Sidebar Controls ----------------
with st.sidebar:
    st.markdown("### ⚙️ 대시보드 설정")

    nasdaq_choice = st.radio(
        "나스닥 기준 지수",
        options=["NASDAQ 종합 (^IXIC)", "NASDAQ 100 (^NDX)"],
        index=0,
    )
    nasdaq_symbol = "^IXIC" if "^IXIC" in nasdaq_choice else "^NDX"

    period_map = {
        "3개월": 63,
        "6개월": 126,
        "1년": 252,
        "2년": 504,
        "5년 (전체)": 0,
    }
    period_label = st.select_slider(
        "차트 조회 기간",
        options=list(period_map.keys()),
        value="1년",
    )
    lookback_days = period_map[period_label]

    refresh_map = {
        "끄기 (수동)": 0,
        "1분마다 자동 갱신": 60_000,
        "5분마다 자동 갱신": 300_000,
    }
    refresh_choice = st.selectbox(
        "실시간 자동 새로고침",
        options=list(refresh_map.keys()),
        index=1,
    )
    refresh_ms = refresh_map[refresh_choice]

    if st.button("🔄 지금 즉시 새로고침", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("### 🤖 AI Q&A (선택 사항)")
    st.caption(
        "기본 퀀트 에이전트는 API 키 없이 100% 무료로 동작합니다. "
        "추가로 자연어 질문을 원하시면 Google AI Studio 무료 Gemini API 키를 입력하세요."
    )
    gemini_key = st.text_input("Gemini API Key (선택)", type="password", placeholder="AIza...")

    st.divider()
    st.caption("데이터 출처 (무료 · 키 불필요)")
    st.caption("• 시세/거래량: Yahoo Finance")
    st.caption("• 투심 지표: CNN Fear & Greed API")

if refresh_ms > 0:
    st_autorefresh(interval=refresh_ms, key="market_autorefresh")

# ---------------- Load Real-Time Data ----------------
with st.spinner("실시간 미국 증시 데이터를 불러오는 중..."):
    try:
        data = load_all_market_data(nasdaq_symbol=nasdaq_symbol)
    except Exception as exc:
        st.error(f"실시간 데이터를 불러오는 중 오류가 발생했습니다: {exc}")
        st.stop()

sp500 = data["sp500"]
nasdaq = data["nasdaq"]
fg = data["fear_greed"]
vix = data["vix"]
briefing = generate_agent_briefing(data)

kst_now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S KST")

# ---------------- 1. Hero Header ----------------
st.markdown(render_hero_html(kst_now, vix.get("price"), vix.get("change_pct", 0.0)), unsafe_allow_html=True)

# ---------------- 2. Core 3-Column Overview (S&P 500 · NASDAQ · Fear & Greed) ----------------
col1, col2, col3 = st.columns([1, 1, 1], gap="medium")
with col1:
    st.markdown(render_index_kpi_card(sp500), unsafe_allow_html=True)
with col2:
    st.markdown(render_index_kpi_card(nasdaq), unsafe_allow_html=True)
with col3:
    st.markdown(render_fear_greed_card(fg), unsafe_allow_html=True)

# ---------------- 3. NASDAQ RSI & MFI Spotlight ----------------
st.markdown('<div class="section-title">⚡ 나스닥 핵심 모멘텀 · 자금흐름 지표 (RSI &amp; MFI)</div>', unsafe_allow_html=True)
osc_c1, osc_c2 = st.columns(2, gap="medium")
with osc_c1:
    st.markdown(
        render_oscillator_card("RSI", nasdaq.get("rsi"), nasdaq.get("rsi_delta", 0.0), nasdaq["name"]),
        unsafe_allow_html=True,
    )
with osc_c2:
    st.markdown(
        render_oscillator_card("MFI", nasdaq.get("mfi"), nasdaq.get("mfi_delta", 0.0), nasdaq["name"]),
        unsafe_allow_html=True,
    )

# ---------------- 4. Drawdown From High Comparison ----------------
st.markdown('<div class="section-title">📉 고점 대비 낙폭(Drawdown) 한눈에 비교</div>', unsafe_allow_html=True)
st.markdown(
    render_drawdown_comparison_html([data["sp500"], data["nasdaq_comp"], data["nasdaq_100"]]),
    unsafe_allow_html=True,
)

# ---------------- 5. AI Quant Stock Agent Briefing ----------------
st.markdown('<div class="section-title">🤖 주식 에이전트 실시간 시장 진단</div>', unsafe_allow_html=True)
st.markdown(render_agent_briefing_html(briefing), unsafe_allow_html=True)

# Optional Gemini interactive Q&A
with st.expander("💬 주식 에이전트에게 현재 시장 상황 질문하기 (무료 Gemini API 키 연결 시 활성화)", expanded=False):
    user_q = st.text_input(
        "질문 입력",
        placeholder="예: 지금 나스닥 RSI랑 공포지수 기준으로 분할 매수 시작해도 될까?",
    )
    if st.button("에이전트에게 질문", type="primary"):
        if not gemini_key.strip():
            st.info("왼쪽 사이드바(>)에서 무료 Gemini API Key를 입력하시면 실시간 데이터를 바탕으로 AI가 답변해 드립니다.")
        elif not user_q.strip():
            st.warning("질문 내용을 입력해 주세요.")
        else:
            with st.spinner("실시간 지표 기반으로 분석 중..."):
                try:
                    answer = ask_gemini_agent(gemini_key, user_q, data, briefing)
                    st.markdown(answer)
                except Exception as exc:
                    st.error(f"AI 응답 오류: {exc}")

# ---------------- 6. Detailed Interactive Charts ----------------
st.markdown('<div class="section-title">📊 상세 인터랙티브 차트</div>', unsafe_allow_html=True)
tab_nq, tab_sp, tab_fg = st.tabs([
    f"🚀 {nasdaq['name']} (가격 · RSI · MFI)",
    "🏛️ S&P 500 (가격 · 고점 대비 낙폭)",
    "😱 공포·탐욕 지수 1년 추이",
])

with tab_nq:
    st.plotly_chart(build_nasdaq_chart(nasdaq, lookback_days=lookback_days), width="stretch")

with tab_sp:
    st.plotly_chart(build_sp500_drawdown_chart(sp500, lookback_days=lookback_days), width="stretch")

with tab_fg:
    fg_fig = build_fear_greed_history_chart(fg)
    if fg_fig is not None:
        st.plotly_chart(fg_fig, width="stretch")
    else:
        st.info("공포·탐욕 히스토리 데이터를 일시적으로 불러오지 못했습니다.")

st.caption(
    f"데이터 소스: Yahoo Finance ({sp500['symbol']}, {nasdaq['symbol']}) · {fg['source']} | "
    "본 대시보드는 정보 제공 목적이며 투자 판단의 책임은 본인에게 있습니다."
)
