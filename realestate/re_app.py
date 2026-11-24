"""Render entry point for the embedded Seoul Real Estate Agent inside US Stock Agent."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import streamlit as st

from realestate.agent_analyzer import (
    ask_gemini_realestate_agent,
    compute_seoul_buy_index,
    generate_seoul_briefing,
)
from realestate.apt_screener import (
    build_apt_price_comparison_chart,
    render_apt_deep_dive_html,
    render_apt_summary_cards,
    render_apt_table_html,
    render_district_overview_html,
    scan_seoul_apartments,
    search_custom_seoul_apartment,
)
from realestate.backtest_view import (
    BACKTEST_MODES,
    build_seoul_backtest_chart,
    render_seoul_backtest_highlight_strip,
    render_seoul_backtest_tables_html,
    run_seoul_buy_index_backtest,
)
from realestate.crash_history import (
    SEOUL_CRASH_EVENTS,
    build_seoul_crash_drawdown_chart,
    render_seoul_crash_table,
    render_seoul_history_summary_cards,
)
from realestate.data_fetcher import SEOUL_DISTRICTS, load_seoul_market_data
from realestate.loan_calculator import (
    build_apt_buy_plan,
    build_loan_chart,
    render_loan_summary_cards,
    render_loan_table_html,
)
from realestate.macro_dashboard import (
    build_macro_history_chart,
    load_live_cross_macro,
    render_kr_macro_cards,
    render_live_cross_cards,
    render_seoul_macro_regime_banner,
)
from realestate.moatown_view import (
    CURATED_ARTICLES,
    LIFE_APT_PROFILE,
    build_life_apt_price_chart,
    build_valuation_waterfall_chart,
    compute_life_101_401_valuation,
    fetch_google_news_rss,
    fetch_life_apt_live_trades,
    render_moatown_hero,
    render_news_card_list,
    render_presale_comparison_table,
    render_toheoje_panel,
    render_unified_moatown_panel,
    render_valuation_summary_cards,
)
from realestate.real_data_loader import build_sample_csv_template
from realestate.ui_components import (
    CUSTOM_CSS as RE_CUSTOM_CSS,
    build_seoul_drawdown_chart,
    build_seoul_main_chart,
    render_agent_briefing_html,
    render_hero_html,
    render_region_kpi_card,
    render_seoul_buy_index_card,
    render_seoul_oscillator_card,
    render_supply_demand_dial_card,
)


def render_seoul_realestate_app() -> None:
    """Render full 6-tab Seoul Real Estate Agent (called when top-right 부동산 mode is active)."""
    st.markdown(RE_CUSTOM_CSS, unsafe_allow_html=True)

    # ---------------- Sidebar Controls ----------------
    with st.sidebar:
        st.markdown("### ⚙️ 서울 부동산 설정")

        price_choice = st.radio(
            "서울 기준 지수",
            options=["실거래가지수 (실제 거래 민감)", "매매가격지수 (KB·부동산원 추세)"],
            index=0,
            key="re_price_choice",
        )
        price_basis = "real_tx_idx" if "실거래가" in price_choice else "sale_idx"

        use_macro_filter = st.toggle(
            "직전 10년 롤링 백분위 결합 (미래누수 0% · 추천)",
            value=True,
            key="re_rolling_toggle",
            help="ON: 각 시점 직전 10년(120개월) 과거 분포 백분위 + 경제 구조 기준 결합 | OFF: 고정 절대 임계값 비교",
        )

        lookback_map = {"5년": 5, "10년": 10, "20년": 20, "40년 (전체)": 0}
        lookback_lbl = st.select_slider(
            "상세 차트 조회 기간",
            options=list(lookback_map.keys()),
            value="10년",
            key="re_lookback_slider",
        )
        lookback_years = lookback_map[lookback_lbl]

        st.divider()
        st.markdown("### 📂 원시 실데이터 파일 업로드 (KB/CSV)")
        st.caption(
            "KB부동산 데이터허브 월간 시계열 엑셀(.xlsx) 또는 CSV를 올리면 "
            "보간 없는 100% 공식 원데이터로 40년 백테스트를 즉시 재계산합니다."
        )
        uploaded_raw = st.file_uploader(
            "KB 월간 시계열(.xlsx) / CSV 업로드",
            type=["xlsx", "csv"],
            label_visibility="collapsed",
            key="re_kb_uploader",
        )
        st.download_button(
            "📄 커스텀 CSV 양식 다운로드",
            data=build_sample_csv_template(),
            file_name="seoul_monthly_template.csv",
            mime="text/csv",
            width="stretch",
            key="re_csv_dl",
        )

        st.divider()
        st.markdown("### 🔑 무료 공공 API 키 연동 (선택)")
        st.caption("무료 키 입력 시 국토부 최신 실거래가 · 한은 ECOS 20년 금리 · R-ONE 지수를 실시간 결합합니다.")
        molit_key = st.text_input(
            "공공데이터포털 API Key (국토부 실거래가)",
            value=os.getenv("DATA_GO_KR_API_KEY", ""),
            type="password",
            placeholder="data.go.kr Decoding Key",
            key="re_molit_key",
        )
        ecos_key = st.text_input(
            "한국은행 ECOS API Key (20년 금리·CSI)",
            value=os.getenv("ECOS_API_KEY", ""),
            type="password",
            placeholder="ecos.bok.or.kr Key",
            key="re_ecos_key",
        )
        reb_key = st.text_input(
            "한국부동산원 R-ONE API Key (월간 지수)",
            value=os.getenv("REB_API_KEY", ""),
            type="password",
            placeholder="reb.or.kr/r-one Key",
            key="re_reb_key",
        )
        gemini_key = st.text_input(
            "Gemini API Key (AI Q&A, 선택)",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            placeholder="AIza...",
            key="re_gemini_key",
        )

        if st.button("🔄 캐시 비우고 새로고침", width="stretch", key="re_refresh_btn"):
            st.cache_data.clear()
            st.rerun()

    # ---------------- Load Core Seoul Data & Apartments ----------------
    up_bytes = uploaded_raw.getvalue() if uploaded_raw is not None else None
    up_name = uploaded_raw.name if uploaded_raw is not None else ""

    with st.spinner("서울 부동산 시계열 및 전 자치구 52대 대장단지 가격을 불러오는 중..."):
        data = load_seoul_market_data(
            price_basis=price_basis,
            ecos_key=ecos_key,
            reb_key=reb_key,
            uploaded_file_bytes=up_bytes,
            uploaded_file_name=up_name,
        )
        apts = scan_seoul_apartments(molit_key=molit_key)

    buy_idx = compute_seoul_buy_index(data, use_macro_filter=use_macro_filter)
    briefing = generate_seoul_briefing(data, apt_list=apts)
    kst_now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST")

    # ---------------- 6-Tab Navigation ----------------
    nav_options = ["📊 시장현황", "👑 지역·단지발굴", "🏗️ 모아타운", "🌍 거시·금리", "📜 역대하락·백테스트", "🧮 매수·대출계산"]
    active_page = st.segmented_control(
        "부동산 메뉴",
        options=nav_options,
        default="📊 시장현황",
        selection_mode="single",
        label_visibility="collapsed",
        width="stretch",
        key="re_nav_tabs",
    )
    if not active_page:
        active_page = "📊 시장현황"

    # ==========================================================================
    # TAB 1: 시장현황
    # ==========================================================================
    if active_page == "📊 시장현황":
        st.markdown(render_hero_html(kst_now, data), unsafe_allow_html=True)
        st.markdown(render_seoul_buy_index_card(buy_idx), unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 1, 1], gap="medium")
        with c1:
            st.markdown(render_region_kpi_card(data["selected"]), unsafe_allow_html=True)
        with c2:
            st.markdown(render_region_kpi_card(data["gangnam"]), unsafe_allow_html=True)
        with c3:
            st.markdown(
                render_supply_demand_dial_card(data["supply_demand"], data["supply_demand_delta"], data["csi"]),
                unsafe_allow_html=True,
            )

        st.markdown('<div class="section-title">⚡ 서울 모멘텀 &amp; 전세 하방지지</div>', unsafe_allow_html=True)
        o1, o2 = st.columns(2, gap="medium")
        with o1:
            st.markdown(render_seoul_oscillator_card("RSI", data["rsi"], data["rsi_delta"], "12M"), unsafe_allow_html=True)
        with o2:
            st.markdown(
                render_seoul_oscillator_card(
                    "JEONSE",
                    data["jeonse_support"],
                    data["jeonse_lead_spread"],
                    f"전세가율 {data['jeonse_ratio']:.1f}%",
                ),
                unsafe_allow_html=True,
            )

        st.markdown('<div class="section-title">🤖 서울 부동산 종합 진단 &amp; 주목 대장단지</div>', unsafe_allow_html=True)
        st.markdown(render_agent_briefing_html(briefing), unsafe_allow_html=True)

        with st.expander("💬 현재 서울 시황 · 특정 단지 가격에 대해 AI 질문하기 (Gemini API 연결 시)", expanded=False):
            q = st.text_input(
                "질문 입력",
                placeholder="예: 지금 15억~25억 예산으로 마포래미안푸르지오랑 고덕그라시움 중 어디가 매수 신호가 좋아?",
                key="re_ai_q",
            )
            if st.button("질문하기", type="primary", key="re_ai_btn"):
                if not gemini_key.strip():
                    st.info("왼쪽 사이드바에서 무료 Gemini API Key를 입력하면 서울 시황 및 실제 단지 가격 기반으로 답변합니다.")
                elif not q.strip():
                    st.warning("질문 내용을 입력해 주세요.")
                else:
                    with st.spinner("서울 시황과 대장단지 실거래가를 종합 분석 중..."):
                        try:
                            ans = ask_gemini_realestate_agent(gemini_key, q, data, briefing, apts)
                            st.markdown(ans)
                        except Exception as exc:
                            st.error(f"AI 응답 오류: {exc}")

        st.markdown('<div class="section-title">📈 서울 아파트 시계열 &amp; 고점 대비 낙폭 차트</div>', unsafe_allow_html=True)
        t_main, t_dd = st.tabs(["🏛️ 서울 지수 · RSI · 매매수급", "📉 5년 고점 대비 낙폭 (Drawdown)"])
        with t_main:
            st.plotly_chart(build_seoul_main_chart(data["df"], price_basis, years=lookback_years), width="stretch", theme=None)
        with t_dd:
            st.plotly_chart(build_seoul_drawdown_chart(data["df"], years=max(lookback_years, 20) if lookback_years else 0), width="stretch", theme=None)

    # ==========================================================================
    # TAB 2: 지역·단지발굴
    # ==========================================================================
    elif active_page == "👑 지역·단지발굴":
        dist_cnt = len({a["district"] for a in apts})
        st.markdown('<div class="section-title" style="margin-top:8px;">👑 서울 전 자치구 · 대장 아파트 실거래가 &amp; 매수 신호</div>', unsafe_allow_html=True)
        st.caption(
            f"서울 {dist_cnt}개 전 자치구 대표 대장 아파트 {len(apts)}곳의 전용 84㎡ 실거래가 · 전고점 대비 낙폭 · 전세가율 · 매매-전세 갭 · 입지 해자를 스캔합니다. "
            "(사이드바에 무료 공공데이터포털 API 키를 입력하면 국토부 실시간 실거래가로 자동 갱신됩니다.)"
        )

        st.markdown(render_apt_summary_cards(apts), unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size:1.02rem;">🗺️ 서울 권역별 대표 대장단지 요약</div>', unsafe_allow_html=True)
        st.markdown(render_district_overview_html(apts), unsafe_allow_html=True)

        f1, f2 = st.columns([2.2, 1.0], gap="small")
        with f1:
            apt_filter = st.radio(
                "조건 필터",
                options=[f"전체 ({len(apts)}단지)", "🟢 강력 매수", "🔵 매수·급매 관심", "고점 -10% 이상", "전세가율 55%↑"],
                horizontal=True,
                label_visibility="collapsed",
                key="re_apt_filter",
            )
        with f2:
            apt_search_kw = st.text_input(
                "단지명/동 검색",
                placeholder="🔍 단지명·동 검색 (예: 잠실, 반포, 신촌)",
                label_visibility="collapsed",
                key="re_apt_search",
            ).strip()

        g1, g2, g3 = st.columns([1.1, 1.1, 1.1], gap="small")
        with g1:
            districts_opt = ["전체 자치구 (25개구)"] + sorted({a["district"] for a in apts})
            sel_dist = st.selectbox("자치구 필터", options=districts_opt, index=0, label_visibility="collapsed", key="re_sel_dist")
        with g2:
            budget_filter = st.selectbox(
                "예산대 필터",
                options=["전체 가격대", "15억 이하", "15억 ~ 25억", "25억 ~ 35억", "35억 이상"],
                index=0,
                label_visibility="collapsed",
                key="re_budget_filter",
            )
        with g3:
            zones = ["전체 권역"] + sorted({a["zone"] for a in apts})
            sel_zone = st.selectbox("권역 필터", options=zones, index=0, label_visibility="collapsed", key="re_sel_zone")

        filtered = apts
        if sel_zone != "전체 권역":
            filtered = [a for a in filtered if a["zone"] == sel_zone]
        if not sel_dist.startswith("전체"):
            filtered = [a for a in filtered if a["district"] == sel_dist]
        if apt_search_kw:
            filtered = [
                a for a in filtered
                if apt_search_kw in a["apt_name"] or apt_search_kw in a["district"] or apt_search_kw in a["dong"]
            ]
        if "강력 매수" in apt_filter:
            filtered = [a for a in filtered if a["signal_code"] == "strong_buy"]
        elif "매수·급매" in apt_filter:
            filtered = [a for a in filtered if a["signal_code"] in ("strong_buy", "accumulate")]
        elif "-10%" in apt_filter:
            filtered = [a for a in filtered if a["dd_peak_pct"] <= -10.0]
        elif "전세가율" in apt_filter:
            filtered = [a for a in filtered if a["jeonse_ratio"] >= 55.0]

        if budget_filter == "15억 이하":
            filtered = [a for a in filtered if a["price_eok"] <= 15.0]
        elif budget_filter == "15억 ~ 25억":
            filtered = [a for a in filtered if 15.0 < a["price_eok"] <= 25.0]
        elif budget_filter == "25억 ~ 35억":
            filtered = [a for a in filtered if 25.0 < a["price_eok"] <= 35.0]
        elif budget_filter == "35억 이상":
            filtered = [a for a in filtered if a["price_eok"] > 35.0]

        st.markdown(render_apt_table_html(filtered), unsafe_allow_html=True)

        st.markdown('<div class="section-title">🔍 아파트 단지별 상세 진단 &amp; 가격 비교</div>', unsafe_allow_html=True)
        apt_labels = [
            f"{a['district']} {a['apt_name']} ({a['price_eok']:.1f}억 · {a['dd_peak_pct']:.1f}%) · {a['signal']} {a['buy_score']}점"
            for a in apts
        ]
        sel_lbl = st.selectbox("상세 분석할 대장단지 선택", options=apt_labels, index=0, key="re_sel_apt")
        sel_apt = apts[apt_labels.index(sel_lbl)]
        st.markdown(render_apt_deep_dive_html(sel_apt), unsafe_allow_html=True)
        st.plotly_chart(build_apt_price_comparison_chart(apts, sel_apt), width="stretch", theme=None)

        with st.expander("🔎 목록에 없는 서울 아파트 단지 직접 실거래가 조회하기 (국토부 API 연동)", expanded=False):
            sc1, sc2, sc3 = st.columns([1.2, 1.8, 1.0])
            with sc1:
                q_dist = st.selectbox("자치구 선택", options=list(SEOUL_DISTRICTS.keys()), index=0, key="re_q_dist")
            with sc2:
                q_name = st.text_input("아파트 단지명 키워드", placeholder="예: 반포자이, 리센츠, 라이프, 은마", key="re_q_name")
            with sc3:
                st.markdown("<div style='height:27px;'></div>", unsafe_allow_html=True)
                do_search = st.button("실거래 조회", type="primary", width="stretch", key="re_q_btn")

            if do_search:
                if not molit_key.strip():
                    st.info("왼쪽 사이드바에서 무료 공공데이터포털(`data.go.kr`) 인증키를 입력하시면 서울 전 단지 실거래가를 실시간 조회할 수 있습니다.")
                elif not q_name.strip():
                    st.warning("조회할 아파트 단지명을 입력해 주세요.")
                else:
                    with st.spinner(f"{q_dist} '{q_name}' 최근 6개월 국토부 실거래가 조회 중..."):
                        res_apt = search_custom_seoul_apartment(molit_key, q_dist, q_name)
                    if res_apt is None:
                        st.warning(f"{q_dist}에서 '{q_name}'의 최근 6개월 실거래 기록을 찾지 못했습니다.")
                    else:
                        st.markdown(render_apt_deep_dive_html(res_apt), unsafe_allow_html=True)
                        if "tx_history" in res_apt and not res_apt["tx_history"].empty:
                            st.dataframe(res_apt["tx_history"], width="stretch", hide_index=True)

    # ==========================================================================
    # TAB 3: 모아타운 (둔촌2동 통합 모아타운 & 라이프아파트 101동 401호)
    # ==========================================================================
    elif active_page == "🏗️ 모아타운":
        life_live = fetch_life_apt_live_trades(molit_key)
        live_price = (
            float(life_live["trades"].iloc[0]["price_eok"])
            if life_live["is_live"]
            else LIFE_APT_PROFILE["latest_price_eok"]
        )

        st.markdown(
            render_moatown_hero(
                live_price=live_price,
                buy_price=LIFE_APT_PROFILE["my_buy_price_eok"],
                is_live_tx=life_live["is_live"],
            ),
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title" style="margin-top:8px;">🏗️ 둔촌2동 모아타운 통합 추진 현황 (1·2·3구역 통합)</div>', unsafe_allow_html=True)
        st.markdown(render_unified_moatown_panel(), unsafe_allow_html=True)

        st.markdown('<div class="section-title">🧮 내 라이프 101동 401호 감정평가액 · 예상 분양가 · 분담금 계산기</div>', unsafe_allow_html=True)
        st.caption(
            "둔촌동 544·544-1 라이프 101동 401호 공부 기준(전용 84.65㎡ · 대지지분 약 13.3평/44㎡ · 2026 개별공시지가 838.4만/㎡ · 공동주택 공시가 5.50억 · 매수가 12.5억)으로 "
            "감정평가액, 추정 비례율, 예상 일반·조합원 분양가와 추가분담금을 시뮬레이션합니다."
        )

        v1, v2, v3, v4 = st.columns([1.3, 0.9, 0.9, 0.9], gap="small")
        with v1:
            appraisal_mode = st.selectbox(
                "감정평가액 추정 방식",
                options=[
                    "대지지분+건물 합산 (기준안 · 약 10.4억)",
                    "평가시점 시세 74% 반영 (중립 · 약 9.25억)",
                    "2026 공시가격 × 1.35배 (보수적 · 약 7.43억)",
                    "감정평가액 직접 입력",
                ],
                index=0,
                key="re_moa_app_mode",
            )
        with v2:
            my_buy_eok = float(st.number_input("내 매수가 (억)", min_value=5.0, max_value=25.0, value=12.50, step=0.1, key="re_moa_buy"))
        with v3:
            my_land_py = float(st.number_input("내 대지지분 (평)", min_value=8.0, max_value=20.0, value=13.30, step=0.1, key="re_moa_landpy"))
        with v4:
            prop_rate_pct = float(st.slider("추정 비례율 (%)", min_value=90, max_value=140, value=105, step=5, key="re_moa_prop"))

        s1, s2, s3, s4 = st.columns(4, gap="small")
        with s1:
            if "직접" in appraisal_mode:
                custom_app = float(st.number_input("직접 감정평가액 (억)", min_value=4.0, max_value=15.0, value=10.4, step=0.1, key="re_moa_capp"))
                land_unit_man = 7200.0
            else:
                custom_app = 10.4
                land_unit_man = float(st.number_input("종전 토지 평당가 (만원)", min_value=5000, max_value=10000, value=7200, step=200, key="re_moa_landu"))
        with s2:
            gen_py_man = float(st.number_input("예상 일반분양 평당가 (만원)", min_value=3500, max_value=7500, value=5200, step=100, key="re_moa_genpy"))
        with s3:
            mem_disc_pct = float(st.slider("조합원 분양 할인율 (%)", min_value=10, max_value=25, value=18, step=1, key="re_moa_disc"))
        with s4:
            post_84_eok = float(st.number_input("완공 후 84㎡ 예상시세 (억)", min_value=15.0, max_value=35.0, value=23.0, step=0.5, key="re_moa_p84"))
        post_59_eok = round(post_84_eok * 0.76, 1)

        val_res = compute_life_101_401_valuation(
            buy_price_eok=my_buy_eok,
            official_price_eok=LIFE_APT_PROFILE["official_price_2026_eok"],
            land_share_py=my_land_py,
            land_unit_man=land_unit_man,
            appraisal_mode=appraisal_mode,
            custom_appraisal_eok=custom_app,
            prop_rate_pct=prop_rate_pct,
            gen_py_price_man=gen_py_man,
            member_discount_pct=mem_disc_pct,
            post_84_eok=post_84_eok,
            post_59_eok=post_59_eok,
        )

        st.markdown(render_valuation_summary_cards(val_res), unsafe_allow_html=True)
        st.markdown(render_presale_comparison_table(val_res), unsafe_allow_html=True)

        ch1, ch2 = st.columns([1.05, 0.95], gap="medium")
        with ch1:
            st.plotly_chart(build_valuation_waterfall_chart(val_res), width="stretch", theme=None)
        with ch2:
            st.plotly_chart(build_life_apt_price_chart(buy_price_eok=my_buy_eok, live_trades=life_live["trades"]), width="stretch", theme=None)

        if life_live["is_live"]:
            with st.expander("📋 국토교통부 라이프아파트 최근 12개월 LIVE 실거래 내역", expanded=False):
                st.dataframe(life_live["trades"], width="stretch", hide_index=True)

        st.markdown('<div class="section-title">🚨 강동구·둔촌동 토지거래허가구역(토허제) &amp; 권리산정기준일</div>', unsafe_allow_html=True)
        st.markdown(render_toheoje_panel(), unsafe_allow_html=True)

        st.markdown('<div class="section-title">📰 최신 관련 기사 모아보기 (실시간 RSS + 핵심 아카이브)</div>', unsafe_allow_html=True)
        with st.spinner("둔촌2동 통합 모아타운 · 라이프아파트 편입 · 강동구 토허제 최신 기사를 불러오는 중..."):
            live_moa = fetch_google_news_rss("둔촌2동 모아타운 OR 둔촌동 77-41 모아타운", max_items=5)
            live_life = fetch_google_news_rss("둔촌동 라이프아파트 OR 둔촌2동 라이프 모아타운", max_items=5)
            live_toh = fetch_google_news_rss("강동구 토지거래허가구역 OR 둔촌동 토허제", max_items=5)

        n1, n2 = st.columns(2, gap="medium")
        with n1:
            moa_articles = (live_moa[:4] if live_moa else []) + CURATED_ARTICLES["moatown"]
            st.markdown(render_news_card_list(moa_articles, "📌 둔촌2동 통합 모아타운 진행 · 시공사 기사", "둔촌2동 모아타운"), unsafe_allow_html=True)
        with n2:
            life_articles = (live_life[:4] if live_life else []) + CURATED_ARTICLES["life_apt"]
            st.markdown(render_news_card_list(life_articles, "🏢 라이프아파트 편입 · 시세 관련 기사", "둔촌동 라이프아파트 모아타운"), unsafe_allow_html=True)

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        toh_articles = (live_toh[:4] if live_toh else []) + CURATED_ARTICLES["toheoje"]
        st.markdown(render_news_card_list(toh_articles, "🚨 강동구 · 둔촌동 토지거래허가구역(토허제) 최신 동향", "강동구 둔촌동 토지거래허가구역"), unsafe_allow_html=True)

    # ==========================================================================
    # TAB 4: 거시·금리
    # ==========================================================================
    elif active_page == "🌍 거시·금리":
        st.markdown('<div class="section-title" style="margin-top:8px;">🌍 한국 부동산 거시 · 금리 · 공급 대시보드</div>', unsafe_allow_html=True)
        st.caption("한국은행 기준금리 · 주담대 금리 · 주택가격전망 CSI · K-HAI 구입부담지수 · 서울 입주물량 + 실시간 환율·미국10년물·코스피")

        st.markdown(render_seoul_macro_regime_banner(data), unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size:1.02rem;">🏦 국내 부동산 핵심 거시 지표</div>', unsafe_allow_html=True)
        st.markdown(render_kr_macro_cards(data), unsafe_allow_html=True)

        with st.spinner("실시간 환율·미 국채금리·코스피 불러오는 중..."):
            live_cross = load_live_cross_macro()
        if live_cross:
            st.markdown('<div class="section-title" style="font-size:1.02rem;">🌐 실시간 글로벌 연동 지표 (Yahoo Finance)</div>', unsafe_allow_html=True)
            st.markdown(render_live_cross_cards(live_cross), unsafe_allow_html=True)

        st.markdown('<div class="section-title">📈 서울 실거래가지수 vs 주담대 금리 20년 상관관계</div>', unsafe_allow_html=True)
        st.plotly_chart(build_macro_history_chart(data["df"]), width="stretch", theme=None)

    # ==========================================================================
    # TAB 5: 역대하락·백테스트
    # ==========================================================================
    elif active_page == "📜 역대하락·백테스트":
        st.markdown('<div class="section-title" style="margin-top:8px;">📜 서울 아파트 역대 하락장 &amp; 38년 매수 지수 백테스트</div>', unsafe_allow_html=True)
        st.caption(
            "1991년 1기 신도시 입주 쇼크 · 1998년 IMF 외환위기 · 2008~2013년 글로벌 금융위기 장기침체 · 2022년 초고속 고금리 폭락까지 "
            "서울 아파트 역사로 매수 추천 지수의 수익률과 승률을 검증합니다."
        )

        idx_now_dd = data["seoul_sale"]["dd_5y_pct"]
        real_now_dd = data["seoul_real"]["dd_5y_pct"]

        st.markdown(render_seoul_history_summary_cards(idx_now_dd, real_now_dd), unsafe_allow_html=True)
        st.markdown(render_seoul_crash_table(SEOUL_CRASH_EVENTS, idx_now_dd, real_now_dd), unsafe_allow_html=True)
        st.plotly_chart(build_seoul_crash_drawdown_chart(SEOUL_CRASH_EVENTS, idx_now_dd, real_now_dd), width="stretch", theme=None)

        st.markdown('<div class="section-title">🧪 서울 부동산 매수 추천 지수 초장기 백테스트 (10년 · 20년 · 38년)</div>', unsafe_allow_html=True)
        if data["provenance_level"] == "archive":
            st.info(
                "💡 **현재 앵커 보간 아카이브로 검증 중입니다.** "
                "왼쪽 사이드바에서 **KB부동산 월간 시계열 엑셀(.xlsx)**을 업로드하면 보간 없는 **100% 공식 원시 월간 데이터**로 즉시 재계산됩니다."
            )
        else:
            st.success(f"현재 적용된 실데이터: **{data['provenance_badge']}** ({', '.join(data['raw_sources'])})")

        bt_col1, bt_col2 = st.columns([2.3, 1.1])
        with bt_col1:
            bt_mode_lbl = st.radio(
                "백테스트 기간 선택",
                options=list(BACKTEST_MODES.keys()),
                index=2,
                horizontal=True,
                label_visibility="collapsed",
                key="re_bt_mode",
            )
        with bt_col2:
            bt_macro_filter = st.toggle(
                "직전 10년 롤링 백분위 결합 (ON/OFF)",
                value=use_macro_filter,
                key="re_bt_rolling",
            )

        st.markdown(
            render_seoul_backtest_highlight_strip(use_macro_filter=bt_macro_filter, enriched_df=data["df"], price_col=price_basis),
            unsafe_allow_html=True,
        )
        bt_res = run_seoul_buy_index_backtest(
            BACKTEST_MODES[bt_mode_lbl],
            use_macro_filter=bt_macro_filter,
            enriched_df=data["df"],
            price_col=price_basis,
            provenance_badge=data["provenance_badge"],
        )
        st.plotly_chart(build_seoul_backtest_chart(bt_res), width="stretch", theme=None)
        st.markdown(render_seoul_backtest_tables_html(bt_res), unsafe_allow_html=True)

    # ==========================================================================
    # TAB 6: 매수·대출계산
    # ==========================================================================
    elif active_page == "🧮 매수·대출계산":
        st.markdown('<div class="section-title" style="margin-top:8px;">🧮 내 예산(LTV·DSR) &amp; 목표 단지 급매 타겟 시뮬레이터</div>', unsafe_allow_html=True)
        apt_opts = [f"{a['district']} {a['apt_name']} ({a['price_eok']:.1f}억 · 고점 {a['peak_eok']:.1f}억)" for a in apts] + ["직접 입력"]
        c_t, c_cash, c_inc = st.columns([1.6, 1.0, 1.0], gap="medium")
        with c_t:
            sel_target_lbl = st.selectbox("목표 아파트 단지 선택", options=apt_opts, index=0, key="re_loan_target")
        with c_cash:
            cash_eok = float(st.number_input("보유 가용 현금 (억원)", min_value=0.5, max_value=100.0, value=10.0, step=0.5, key="re_loan_cash"))
        with c_inc:
            income_man = float(st.number_input("부부합산 연소득 (만원)", min_value=2000, max_value=100_000, value=12_000, step=500, key="re_loan_inc"))

        if sel_target_lbl == "직접 입력":
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                t_name = st.text_input("단지명", value="관심 아파트", key="re_lm_name")
            with m2:
                t_cur = float(st.number_input("현재 매매가 (억)", min_value=1.0, value=20.0, step=0.5, key="re_lm_cur"))
            with m3:
                t_peak = float(st.number_input("전고점 가격 (억)", min_value=1.0, value=23.0, step=0.5, key="re_lm_peak"))
            with m4:
                t_jeonse = float(st.number_input("전세가 (억)", min_value=0.5, value=11.0, step=0.5, key="re_lm_js"))
        else:
            t_apt = apts[apt_opts.index(sel_target_lbl)]
            t_name = f"{t_apt['district']} {t_apt['apt_name']}"
            t_cur = t_apt["price_eok"]
            t_peak = t_apt["peak_eok"]
            t_jeonse = t_apt["jeonse_eok"]

        r1, r2, r3, r4 = st.columns(4, gap="medium")
        with r1:
            loan_rate = float(st.number_input("주담대 금리 (%)", min_value=1.5, max_value=9.0, value=round(data["mortgage_rate"], 2), step=0.1, key="re_l_rate"))
        with r2:
            loan_years = int(st.selectbox("대출 만기", options=[30, 40, 20], index=0, format_func=lambda x: f"{x}년", key="re_l_yrs"))
        with r3:
            ltv_pct = float(st.selectbox("LTV 규제 한도", options=[50, 70, 80, 40], index=1, format_func=lambda x: f"LTV {x}%", key="re_l_ltv"))
        with r4:
            stress_add = float(st.selectbox("스트레스 DSR 가산금리", options=[1.2, 1.5, 0.75, 0.0], index=0, format_func=lambda x: f"+{x:.2f}%p", key="re_l_str"))

        plan = build_apt_buy_plan(
            cash_eok=cash_eok,
            annual_income_man=income_man,
            rate_pct=loan_rate,
            years=loan_years,
            ltv_pct=ltv_pct,
            stress_add_pct=stress_add,
            apt_name=t_name,
            current_eok=t_cur,
            peak_eok=t_peak,
            jeonse_eok=t_jeonse,
        )
        st.markdown(render_loan_summary_cards(plan), unsafe_allow_html=True)
        st.markdown(render_loan_table_html(plan), unsafe_allow_html=True)
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        st.plotly_chart(build_loan_chart(plan), width="stretch", theme=None)

    st.caption(
        "데이터 출처: 국토교통부 실거래가 공개시스템(Open API) · 한국부동산원 R-ONE · KB부동산 장기통계 · 한국은행 ECOS · Yahoo Finance | "
        "본 대시보드는 정보 제공 및 백테스트 연구 목적이며 투자 판단의 책임은 본인에게 있습니다."
    )
