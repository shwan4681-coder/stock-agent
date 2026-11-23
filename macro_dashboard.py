"""Global Macro & Cross-Asset Dashboard (FX, US Treasuries, Commodities, Crypto, Global Indices)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from ui_components import _compact_html


MACRO_CATALOG: list[dict] = [
    # 1. FX & Dollar
    {
        "symbol": "KRW=X",
        "name": "원/달러 환율",
        "category": "💱 환율 · 달러",
        "prefix": "₩",
        "suffix": "",
        "decimals": 2,
        "desc": "미국 주식 원화 환산 수익률 및 외국인 수급 핵심 지표",
        "invert_color": False,
    },
    {
        "symbol": "DX-Y.NYB",
        "name": "달러 인덱스 (DXY)",
        "category": "💱 환율 · 달러",
        "prefix": "",
        "suffix": "",
        "decimals": 2,
        "desc": "주요 6개국 통화 대비 달러 가치 · 강달러 시 위험자산 압박",
        "invert_color": False,
    },
    {
        "symbol": "JPY=X",
        "name": "엔/달러 환율",
        "category": "💱 환율 · 달러",
        "prefix": "¥",
        "suffix": "",
        "decimals": 2,
        "desc": "엔 캐리 트레이드 자금 흐름 및 일본은행 정책 민감 지표",
        "invert_color": False,
    },
    # 2. US Treasuries & Volatility
    {
        "symbol": "^TNX",
        "name": "미국 10년물 국채금리",
        "category": "🏦 미국 국채 · 변동성",
        "prefix": "",
        "suffix": "%",
        "decimals": 2,
        "desc": "글로벌 자산 할인율 기준 · 급등 시 성장주·나스닥 밸류 부담",
        "invert_color": True,
    },
    {
        "symbol": "IEF",
        "name": "미국 10년물 국채가격 (IEF)",
        "category": "🏦 미국 국채 · 변동성",
        "prefix": "$",
        "suffix": "",
        "decimals": 2,
        "desc": "미국 7~10년 중기국채 ETF 가격 · 10년물 금리와 반대로 이동",
        "invert_color": False,
    },
    {
        "symbol": "TLT",
        "name": "미국 20년+ 장기국채 (TLT)",
        "category": "🏦 미국 국채 · 변동성",
        "prefix": "$",
        "suffix": "",
        "decimals": 2,
        "desc": "금리 인하 사이클·경기 침체 헤지용 초장기 국채 가격 ETF",
        "invert_color": False,
    },
    {
        "symbol": "^IRX",
        "name": "미국 3개월물 국채금리",
        "category": "🏦 미국 국채 · 변동성",
        "prefix": "",
        "suffix": "%",
        "decimals": 2,
        "desc": "연준 기준금리 반영 단기금리 · 10년물과 장단기 금리차 산출",
        "invert_color": True,
    },
    {
        "symbol": "^VIX",
        "name": "VIX 공포지수",
        "category": "🏦 미국 국채 · 변동성",
        "prefix": "",
        "suffix": "",
        "decimals": 2,
        "desc": "S&P 500 30일 내재 변동성 · 20 이하 안정 / 30 이상 패닉",
        "invert_color": True,
    },
    # 3. Commodities & Inflation
    {
        "symbol": "CL=F",
        "name": "WTI 국제유가",
        "category": "🛢️ 원자재 · 경기 선행",
        "prefix": "$",
        "suffix": "",
        "decimals": 2,
        "desc": "에너지 인플레이션 핵심 · $80~90 돌파 시 물가 재점화 우려",
        "invert_color": False,
    },
    {
        "symbol": "GC=F",
        "name": "국제 금 가격",
        "category": "🛢️ 원자재 · 경기 선행",
        "prefix": "$",
        "suffix": "",
        "decimals": 1,
        "desc": "대표 안전자산 · 지정학 리스크·화폐가치 하락 헤지 수단",
        "invert_color": False,
    },
    {
        "symbol": "HG=F",
        "name": "구리 선물 (닥터 코퍼)",
        "category": "🛢️ 원자재 · 경기 선행",
        "prefix": "$",
        "suffix": "",
        "decimals": 2,
        "desc": "글로벌 제조업·AI 전력 인프라 실물 경기 선행지표",
        "invert_color": False,
    },
    # 4. Crypto & Global Risk Assets
    {
        "symbol": "BTC-USD",
        "name": "비트코인 (BTC)",
        "category": "🪙 디지털 자산 · 글로벌 증시",
        "prefix": "$",
        "suffix": "",
        "decimals": 0,
        "desc": "24시간 글로벌 유동성 및 위험자산 선호도 최선행 지표",
        "invert_color": False,
    },
    {
        "symbol": "ETH-USD",
        "name": "이더리움 (ETH)",
        "category": "🪙 디지털 자산 · 글로벌 증시",
        "prefix": "$",
        "suffix": "",
        "decimals": 0,
        "desc": "디지털 자산 시장 리스크 온/오프 탄력도 측정 지표",
        "invert_color": False,
    },
    {
        "symbol": "^SOX",
        "name": "필라델피아 반도체 (SOX)",
        "category": "🪙 디지털 자산 · 글로벌 증시",
        "prefix": "",
        "suffix": "",
        "decimals": 1,
        "desc": "글로벌 AI·반도체 업황 및 나스닥 기술주 선행 풍향계",
        "invert_color": False,
    },
    {
        "symbol": "^KS11",
        "name": "코스피 (KOSPI)",
        "category": "🪙 디지털 자산 · 글로벌 증시",
        "prefix": "",
        "suffix": "",
        "decimals": 2,
        "desc": "국내 증시 대표 지수 · 반도체·원달러 환율 민감도 확인",
        "invert_color": False,
    },
]


def _fetch_one_macro(meta: dict) -> dict | None:
    sym = meta["symbol"]
    t = yf.Ticker(sym)
    hist = t.history(period="1y", interval="1d", auto_adjust=False)
    if hist is None or hist.empty:
        return None
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = [c[0] for c in hist.columns]
    if getattr(hist.index, "tz", None) is not None:
        hist.index = hist.index.tz_localize(None)
    hist = hist[["Open", "High", "Low", "Close"]].dropna(subset=["Close"])
    if hist.empty:
        return None

    price = float(hist["Close"].iloc[-1])
    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
    chg = price - prev
    chg_pct = (chg / prev * 100.0) if prev else 0.0
    high_1y = float(hist["High"].max())
    low_1y = float(hist["Low"].min())
    dd_1y = ((price / high_1y) - 1.0) * 100.0 if high_1y > 0 else 0.0
    pos_52w = ((price - low_1y) / (high_1y - low_1y) * 100.0) if high_1y > low_1y else 50.0

    return {
        **meta,
        "price": price,
        "change": chg,
        "change_pct": chg_pct,
        "high_1y": high_1y,
        "low_1y": low_1y,
        "dd_1y": dd_1y,
        "pos_52w": max(0.0, min(100.0, pos_52w)),
        "hist": hist,
    }


@st.cache_data(ttl=180, show_spinner=False)
def load_macro_dashboard_data() -> dict[str, dict]:
    """Fetch all 15 global macro indicators in parallel."""
    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(_fetch_one_macro, m): m["symbol"] for m in MACRO_CATALOG}
        for fut in as_completed(futs, timeout=30):
            try:
                res = fut.result(timeout=12)
                if res:
                    out[res["symbol"]] = res
            except Exception:
                continue
    return out


def _fmt_val(item: dict, val: float) -> str:
    dec = item["decimals"]
    num = f"{val:,.{dec}f}"
    return f"{item['prefix']}{num}{item['suffix']}"


def render_macro_regime_banner(macro: dict[str, dict]) -> str:
    """Render top luxury Macro Regime Diagnosis banner synthesizing Rates, FX, Oil, Gold, BTC."""
    tnx = macro.get("^TNX")
    irx = macro.get("^IRX")
    dxy = macro.get("DX-Y.NYB")
    krw = macro.get("KRW=X")
    wti = macro.get("CL=F")
    vix = macro.get("^VIX")
    btc = macro.get("BTC-USD")

    bullets = []
    pressure_pts = 0

    if tnx:
        y10 = tnx["price"]
        spread_str = ""
        if irx:
            spread = y10 - irx["price"]
            spread_str = f" · 장단기 금리차(10Y-3M) {spread:+.2f}%p"
        if y10 >= 4.5:
            pressure_pts += 2
            bullets.append(("금리 압박", "#b91c1c", f"미 10년물 금리가 {y10:.2f}%로 고금리 구간입니다{spread_str}. 기술주 멀티플에 부담 요인입니다."))
        elif y10 <= 3.8:
            bullets.append(("금리 우호", "#15803d", f"미 10년물 금리 {y10:.2f}%로 주식 밸류에이션에 우호적입니다{spread_str}."))
        else:
            pressure_pts += 1
            bullets.append(("금리 중립", "#b45309", f"미 10년물 금리 {y10:.2f}%로 중립~경계 구간입니다{spread_str}."))

    if krw and dxy:
        if dxy["price"] >= 104.0 or krw["price"] >= 1380:
            pressure_pts += 1
            bullets.append(("강달러 경계", "#b45309", f"달러 인덱스 {dxy['price']:.2f} · 원/달러 ₩{krw['price']:,.1f}로 달러 강세가 위험자산에 부담을 주고 있습니다."))
        else:
            bullets.append(("환율 안정", "#15803d", f"달러 인덱스 {dxy['price']:.2f} · 원/달러 ₩{krw['price']:,.1f}로 비교적 안정적입니다."))

    if wti:
        if wti["price"] >= 80.0:
            pressure_pts += 1
            bullets.append(("유가 경계", "#b45309", f"WTI 유가가 ${wti['price']:.2f}로 $80 이상입니다. 인플레이션 우려 재점화 여부를 주시하세요."))
        else:
            bullets.append(("유가 안정", "#15803d", f"WTI 유가 ${wti['price']:.2f}로 물가 자극 우려가 제한적입니다."))

    if btc and vix:
        if vix["price"] >= 25.0:
            pressure_pts += 1
            bullets.append(("위험회피(Risk-Off)", "#b91c1c", f"VIX {vix['price']:.1f} · 비트코인 ${btc['price']:,.0f}(고점 대비 {btc['dd_1y']:.1f}%)로 시장 변동성이 큰 방어 국면입니다."))
        else:
            bullets.append(("위험선호(Risk-On)", "#15803d", f"VIX {vix['price']:.1f} · 비트코인 ${btc['price']:,.0f}로 글로벌 유동성 심리가 양호합니다."))

    if pressure_pts >= 4:
        regime, reg_col = "🔴 거시 압박 · 방어적 분할 대응", "#b91c1c"
        summary = "고금리·변동성·강달러/유가 등 거시 변수가 주식시장에 부담을 주는 국면입니다. 우량주 위주 천천히 분할 접근하세요."
    elif pressure_pts >= 2:
        regime, reg_col = "🟡 혼조 · 금리·유가 주시", "#b45309"
        summary = "일부 거시 지표에 경계 신호가 켜져 있습니다. 10년물 국채금리와 달러 방향성을 함께 체크하세요."
    else:
        regime, reg_col = "🟢 거시 우호 · 위험자산 친화", "#15803d"
        summary = "금리·환율·유가·변동성이 전반적으로 안정되어 주식 등 위험자산에 우호적인 거시 환경입니다."

    cards = "".join(
        f'<div class="signal-item">'
        f'<span class="signal-tag" style="background:{c}16; color:{c};">{t}</span><br/>{txt}'
        f'</div>'
        for t, c, txt in bullets
    )
    return _compact_html(f"""
    <div class="agent-panel" style="margin-bottom:18px;">
      <div class="agent-header">
        <div>
          <div style="font-size:0.74rem; color:#78716c; font-weight:700; letter-spacing:0.06em; text-transform:uppercase;">GLOBAL MACRO REGIME</div>
          <div style="font-size:1.05rem; font-weight:600; color:#1c1917; margin-top:4px;">{summary}</div>
        </div>
        <div class="agent-stance" style="background:{reg_col}16; color:{reg_col};">{regime}</div>
      </div>
      <div class="signal-grid">{cards}</div>
    </div>
    """)


def render_macro_category_grid(items: list[dict]) -> str:
    """Render responsive grid of luxury macro cards for one category."""
    cards = []
    for it in items:
        up = it["change"] >= 0
        arrow = "▲" if up else "▼"
        if it.get("invert_color"):
            chg_col = "#b91c1c" if up else "#15803d"
        else:
            chg_col = "#15803d" if up else "#b91c1c"

        val_str = _fmt_val(it, it["price"])
        high_str = _fmt_val(it, it["high_1y"])
        low_str = _fmt_val(it, it["low_1y"])
        pos = it["pos_52w"]

        cards.append(
            f'<div class="glass-card" style="padding:18px 20px;">'
            f'<div class="card-kicker"><span>{it["name"]}</span><span class="ticker-badge">{it["symbol"]}</span></div>'
            f'<div style="font-size:1.72rem; font-weight:700; color:#1c1917; letter-spacing:-0.03em; margin:8px 0 2px 0; font-variant-numeric:tabular-nums;">{val_str}</div>'
            f'<div style="font-size:0.86rem; font-weight:600; color:{chg_col}; font-variant-numeric:tabular-nums;">{arrow} {it["change"]:+.2f} ({it["change_pct"]:+.2f}%)</div>'
            f'<div style="margin-top:12px; padding:10px 12px; border-radius:12px; background:#f2efe9;">'
            f'<div style="display:flex; justify-content:space-between; font-size:0.72rem; color:#57534e; font-variant-numeric:tabular-nums;">'
            f'<span>52주 저 {low_str}</span><span>고점 대비 <b style="color:#1c1917;">{it["dd_1y"]:.1f}%</b></span><span>고 {high_str}</span>'
            f'</div>'
            f'<div style="position:relative; height:6px; background:#dfd9ce; border-radius:999px; margin-top:7px;">'
            f'<div style="position:absolute; left:{pos:.1f}%; top:-3px; width:12px; height:12px; border-radius:50%; background:#18181b; border:2px solid #faf9f6; transform:translateX(-50%);"></div>'
            f'</div>'
            f'</div>'
            f'<div style="font-size:0.75rem; color:#78716c; margin-top:9px; line-height:1.45;">{it["desc"]}</div>'
            f'</div>'
        )
    return _compact_html(
        f'<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:14px; margin-bottom:10px;">{"".join(cards)}</div>'
    )


def build_macro_trend_chart(item: dict, chart_style: str = "캔들 차트") -> go.Figure:
    """Build Apple Titanium Light 1-year chart for any selected macro indicator."""
    sub = item["hist"]
    y_min = float(sub["Low"].min())
    y_max = float(sub["High"].max())
    y_pad = max((y_max - y_min) * 0.08, 0.01)

    fig = go.Figure()
    if chart_style == "캔들 차트":
        fig.add_trace(
            go.Candlestick(
                x=sub.index,
                open=sub["Open"],
                high=sub["High"],
                low=sub["Low"],
                close=sub["Close"],
                name=item["name"],
                increasing_line_color="#1d8f34",
                increasing_fillcolor="#34c759",
                decreasing_line_color="#d70015",
                decreasing_fillcolor="#ff3b30",
            )
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=sub.index,
                y=sub["Close"],
                name=item["name"],
                line=dict(color="#18181b", width=2.3),
                hovertemplate=f"{item['prefix']}%{{y:,.{item['decimals']}f}}{item['suffix']}<extra></extra>",
            )
        )

    ma50 = sub["Close"].rolling(50).mean()
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=ma50,
            name="50일선",
            line=dict(color="#1d4ed8", width=1.5, dash="dot"),
        )
    )
    fig.add_hline(
        y=item["high_1y"],
        line_dash="dash",
        line_width=1.1,
        line_color="rgba(28, 25, 23, 0.35)",
        annotation_text=f" 52주 고점 {_fmt_val(item, item['high_1y'])}",
        annotation_position="top left",
        annotation_font=dict(color="#57534e", size=11),
    )

    x_span = max((sub.index[-1] - sub.index[0]).days, 10)
    x_left = sub.index[0] - pd.Timedelta(days=max(3, int(x_span * 0.03)))
    x_right = sub.index[-1] + pd.Timedelta(days=max(6, int(x_span * 0.06)))

    fig.update_yaxes(
        range=[y_min - y_pad, y_max + y_pad],
        side="right",
        automargin=True,
        tickprefix=item["prefix"],
        ticksuffix=item["suffix"],
        gridcolor="rgba(0,0,0,0.06)",
        tickfont=dict(color="#57534e", size=11),
    )
    fig.update_xaxes(
        range=[x_left, x_right],
        automargin=True,
        rangeslider_visible=False,
        gridcolor="rgba(0,0,0,0.04)",
        tickfont=dict(color="#57534e", size=11),
    )
    fig.update_layout(
        title=dict(
            text=f"{item['name']} ({item['symbol']}) 1년 추이 · 현재 {_fmt_val(item, item['price'])} ({item['change_pct']:+.2f}%)",
            font=dict(size=14, color="#1c1917"),
        ),
        height=430,
        margin=dict(l=38, r=72, t=64, b=28),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)", font=dict(color="#57534e", size=12)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#faf9f6", bordercolor="#d6d3d1", font=dict(color="#1c1917", size=12)),
    )
    return fig
