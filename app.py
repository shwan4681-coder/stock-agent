"""US Market Stock Agent — Sleek Streamlit + HTML/CSS Real-time Dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from agent_analyzer import ask_gemini_agent, generate_agent_briefing
from data_fetcher import load_all_market_data
from dca_calculator import (
    STRATEGIES,
    build_dca_chart,
    build_dca_plan,
    compute_weights,
    render_dca_summary_cards,
    render_dca_table_html,
)
from monopoly_screener import (
    analyze_custom_ticker_cached,
    build_stock_financial_chart,
    render_monopoly_summary_cards,
    render_monopoly_table_html,
    render_stock_deep_dive_html,
    scan_monopoly_universe,
)
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
    st.markdown("### 설정")

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
        "자동 새로고침",
        options=list(refresh_map.keys()),
        index=1,
    )
    refresh_ms = refresh_map[refresh_choice]

    if st.button("지금 새로고침", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("### AI 질의응답 (선택)")
    st.caption(
        "기본 정량 브리핑은 API 키 없이 동작합니다. "
        "추가 자연어 질문을 원하시면 Google AI Studio 무료 Gemini API 키를 입력하세요."
    )
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")

    st.divider()
    st.caption("데이터 출처: Yahoo Finance · CNN Fear & Greed")

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

# ---------------- Top-Most Navigation Tabs (Apple Segmented Bar) ----------------
main_tab_dash, main_tab_monopoly, main_tab_dca = st.tabs([
    "시장 현황",
    "독점 기업",
    "분할 매수",
])

with main_tab_dash:
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
    st.markdown('<div class="section-title">나스닥 모멘텀 및 자금흐름</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="section-title">고점 대비 낙폭 비교</div>', unsafe_allow_html=True)
    st.markdown(
        render_drawdown_comparison_html([data["sp500"], data["nasdaq_comp"], data["nasdaq_100"]]),
        unsafe_allow_html=True,
    )

    # ---------------- 5. Market Briefing ----------------
    st.markdown('<div class="section-title">시장 종합 진단</div>', unsafe_allow_html=True)
    st.markdown(render_agent_briefing_html(briefing), unsafe_allow_html=True)

    # Optional Gemini interactive Q&A
    with st.expander("현재 시장 지표에 대해 질문하기 (Gemini API 연결 시)", expanded=False):
        user_q = st.text_input(
            "질문 입력",
            placeholder="예: 지금 나스닥 RSI와 공포지수 기준으로 분할 매수 시작해도 될까?",
        )
        if st.button("질문하기", type="primary"):
            if not gemini_key.strip():
                st.info("왼쪽 사이드바에서 무료 Gemini API Key를 입력하면 실시간 데이터 기반으로 답변합니다.")
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
    st.markdown('<div class="section-title">상세 차트</div>', unsafe_allow_html=True)
    tab_nq, tab_sp, tab_fg = st.tabs([
        f"{nasdaq['name']}",
        "S&P 500",
        "공포·탐욕",
    ])

    with tab_nq:
        nq_ctrl1, nq_ctrl2 = st.columns([1.4, 2.6])
        with nq_ctrl1:
            nq_chart_style = st.radio(
                "차트 스타일",
                options=["라인 차트", "캔들 차트"],
                horizontal=True,
                label_visibility="collapsed",
            )
        with nq_ctrl2:
            st.caption("우측 축에서 현재가·RSI·MFI를 확인할 수 있으며 드래그로 확대할 수 있습니다.")
        st.plotly_chart(
            build_nasdaq_chart(nasdaq, lookback_days=lookback_days, chart_style=nq_chart_style),
            width="stretch",
            theme=None,
        )

    with tab_sp:
        st.plotly_chart(
            build_sp500_drawdown_chart(sp500, lookback_days=lookback_days),
            width="stretch",
            theme=None,
        )

    with tab_fg:
        fg_fig = build_fear_greed_history_chart(fg)
        if fg_fig is not None:
            st.plotly_chart(fg_fig, width="stretch", theme=None)
        else:
            st.info("공포·탐욕 히스토리 데이터를 일시적으로 불러오지 못했습니다.")

with main_tab_dca:
    st.markdown(
        '<div class="section-title" style="margin-top:8px;">고점 대비 분할 매수 계산기</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "보유 시드머니를 입력하면 실시간 지수 고점 대비 -5% 구간마다(최대 -30%) 매수 금액과 "
        "현재 도달 상태, 예상 평단가를 자동으로 계산합니다."
    )

    # Control Row 1: Benchmark, Currency, Seed Money, Strategy
    c_asset, c_curr, c_seed = st.columns([1.3, 0.8, 1.4], gap="medium")
    with c_asset:
        dca_target = st.selectbox(
            "기준 지수 / 종목",
            options=[
                "NASDAQ 종합 (^IXIC) · 실시간",
                "NASDAQ 100 (^NDX) · 실시간",
                "S&P 500 (^GSPC) · 실시간",
                "직접 입력 (QQQ / 개별 종목)",
            ],
            index=0,
        )
    with c_curr:
        currency_label = st.radio("통화", options=["원화 (₩)", "달러 ($)"], horizontal=True)
        currency = "KRW" if "원화" in currency_label else "USD"

    with c_seed:
        if currency == "KRW":
            seed_man = st.number_input(
                "보유 시드머니 (만원 단위)",
                min_value=10,
                max_value=1_000_000,
                value=1_000,
                step=100,
                help="예: 1,000 입력 시 1,000만원 (₩10,000,000)",
            )
            seed_amount = float(seed_man) * 10_000.0
        else:
            seed_amount = float(
                st.number_input(
                    "보유 시드머니 (USD $)",
                    min_value=100,
                    max_value=10_000_000,
                    value=10_000,
                    step=1_000,
                )
            )

    # Resolve ATH & Current price from live data or manual input
    if "^IXIC" in dca_target:
        ref_idx = data["nasdaq_comp"]
        ath_price = ref_idx["ath_price"]
        cur_price = ref_idx["price"]
        asset_badge = "NASDAQ ^IXIC"
    elif "^NDX" in dca_target:
        ref_idx = data["nasdaq_100"]
        ath_price = ref_idx["ath_price"]
        cur_price = ref_idx["price"]
        asset_badge = "NASDAQ 100 ^NDX"
    elif "^GSPC" in dca_target:
        ref_idx = data["sp500"]
        ath_price = ref_idx["ath_price"]
        cur_price = ref_idx["price"]
        asset_badge = "S&P 500 ^GSPC"
    else:
        m1, m2 = st.columns(2, gap="medium")
        with m1:
            ath_price = float(st.number_input("전고점 가격 입력", min_value=0.01, value=500.0, step=10.0))
        with m2:
            cur_price = float(st.number_input("현재 가격 입력", min_value=0.01, value=420.0, step=10.0))
        asset_badge = "직접 입력"

    # Control Row 2: Strategy + Drawdown settings
    s_col1, s_col2, s_col3 = st.columns([2.0, 1.0, 1.0], gap="medium")
    with s_col1:
        strategy_options = list(STRATEGIES.keys()) + ["직접 비중 입력 (%)"]
        strategy_name = st.selectbox("분할 매수 비중 전략", options=strategy_options, index=0)
    with s_col2:
        step_pct = st.selectbox("하락 간격", options=[5, 3, 10], index=0, format_func=lambda x: f"-{x}% 마다")
    with s_col3:
        max_dd_pct = st.selectbox(
            "최대 하락 가정",
            options=[20, 25, 30, 35, 40, 50],
            index=2,
            format_func=lambda x: f"최대 -{x}%",
        )

    levels = list(range(step_pct, max_dd_pct + 1, step_pct))
    custom_weights = None
    if strategy_name == "직접 비중 입력 (%)":
        st.caption("각 낙폭 구간에 배분할 비중(%)을 입력하세요. 합계가 100%가 아니어도 자동으로 비율에 맞춰 정규화됩니다.")
        default_w = compute_weights(levels, "pyramid")
        w_cols = st.columns(min(len(levels), 6))
        custom_weights = []
        for idx_i, (lvl, dw) in enumerate(zip(levels, default_w)):
            with w_cols[idx_i % len(w_cols)]:
                val = st.number_input(
                    f"-{lvl}% 비중",
                    min_value=0.0,
                    max_value=100.0,
                    value=round(dw, 1),
                    step=5.0,
                    key=f"dca_w_{step_pct}_{max_dd_pct}_{lvl}",
                )
                custom_weights.append(float(val))
        strategy_mode = "custom"
    else:
        st.caption(STRATEGIES[strategy_name]["desc"])
        strategy_mode = STRATEGIES[strategy_name]["mode"]

    plan = build_dca_plan(
        seed_amount=seed_amount,
        ath_price=ath_price,
        current_price=cur_price,
        step_pct=step_pct,
        max_dd_pct=max_dd_pct,
        strategy_mode=strategy_mode,
        custom_weights=custom_weights,
    )

    # 1. Summary KPI cards
    st.markdown(render_dca_summary_cards(plan, currency=currency, asset_label=asset_badge), unsafe_allow_html=True)

    # 2. Schedule HTML table
    st.markdown(render_dca_table_html(plan, currency=currency), unsafe_allow_html=True)

    # 3. Interactive bar + average cost curve chart
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.plotly_chart(build_dca_chart(plan, currency=currency), width="stretch", theme=None)

with main_tab_monopoly:
    st.markdown(
        '<div class="section-title" style="margin-top:8px;">독점 기업 및 매수 신호</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "경영진 · 연평균 매출성장 20%↑ · 영업이익률 다개년 20%↑ · 시장점유율 50%↑ · "
        "워렌 버핏 4대 지표(ROE · 매출총이익률 · FCF 마진 · 부채비율) 및 실시간 매수 신호"
    )

    with st.spinner("글로벌 독점·해자 우량주 12종목의 실시간 재무제표와 지표를 불러오는 중..."):
        monopoly_stocks = scan_monopoly_universe()

    st.markdown(render_monopoly_summary_cards(monopoly_stocks), unsafe_allow_html=True)

    f_col1, f_col2 = st.columns([3.0, 1.0])
    with f_col1:
        mono_filter = st.radio(
            "필터",
            options=[
                "전체 후보 (12종목)",
                "매수·분할매수 신호만",
                "매출 CAGR 20% 이상",
                "영업이익률 전 기간 20% 이상",
            ],
            horizontal=True,
            label_visibility="collapsed",
        )
    with f_col2:
        if st.button("재무·신호 새로고침", width="stretch"):
            scan_monopoly_universe.clear()
            st.rerun()

    filtered_stocks = monopoly_stocks
    if "매수·분할매수" in mono_filter:
        filtered_stocks = [s for s in monopoly_stocks if s["signal_code"] in ("strong_buy", "accumulate")]
    elif "CAGR 20%" in mono_filter:
        filtered_stocks = [s for s in monopoly_stocks if s["rev_cagr_pct"] is not None and s["rev_cagr_pct"] >= 20.0]
    elif "영업이익률" in mono_filter:
        filtered_stocks = [
            s for s in monopoly_stocks if s["op_years_total"] >= 3 and s["op_years_pass"] == s["op_years_total"]
        ]

    st.markdown(render_monopoly_table_html(filtered_stocks), unsafe_allow_html=True)

    # Deep Dive for selected curated stock
    if monopoly_stocks:
        st.markdown('<div class="section-title">종목별 8대 기준 상세 진단</div>', unsafe_allow_html=True)
        stock_labels = [
            f"{s['name_kr']} ({s['symbol']}) · {s['signal']} · {s['moat_score']}점"
            for s in monopoly_stocks
        ]
        sel_label = st.selectbox("상세 분석할 기업 선택", options=stock_labels, index=0)
        sel_stock = monopoly_stocks[stock_labels.index(sel_label)]

        st.markdown(render_stock_deep_dive_html(sel_stock), unsafe_allow_html=True)
        st.plotly_chart(build_stock_financial_chart(sel_stock), width="stretch", theme=None)

    # Custom US stock analyzer
    with st.expander("목록에 없는 미국 종목 직접 분석하기 (예: PLTR, NFLX, LLY, COST, AAPL)", expanded=False):
        cc1, cc2, cc3, cc4 = st.columns([1.4, 1.2, 1.2, 1.0])
        with cc1:
            custom_sym = st.text_input("미국 티커 입력", value="PLTR", placeholder="예: AAPL, LLY, COST").strip().upper()
        with cc2:
            custom_share = st.slider("추정 시장점유율 (%)", min_value=10, max_value=100, value=55, step=5)
        with cc3:
            custom_mgmt = st.slider("경영진 평가 (1~5점)", min_value=1, max_value=5, value=4, step=1)
        with cc4:
            st.markdown("<div style='height:27px;'></div>", unsafe_allow_html=True)
            run_custom = st.button("종목 분석", type="primary", width="stretch")

        if run_custom and custom_sym:
            with st.spinner(f"{custom_sym} 재무제표 및 매수 신호 분석 중..."):
                try:
                    c_stock = analyze_custom_ticker_cached(custom_sym, custom_share, custom_mgmt)
                    st.markdown(render_stock_deep_dive_html(c_stock), unsafe_allow_html=True)
                    st.plotly_chart(build_stock_financial_chart(c_stock), width="stretch", theme=None)
                except Exception as exc:
                    st.error(f"분석 실패: {exc}")

st.caption(
    f"데이터 소스: Yahoo Finance ({sp500['symbol']}, {nasdaq['symbol']}) · {fg['source']} | "
    "본 대시보드는 정보 제공 목적이며 투자 판단의 책임은 본인에게 있습니다."
)
