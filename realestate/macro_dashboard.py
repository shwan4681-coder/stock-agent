"""Korea & Seoul Real Estate Macro Dashboard (Rates, Supply, Jeonse, CSI + Live Yahoo FX/KOSPI/US10Y)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


def _compact(html: str) -> str:
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


LIVE_MARKET_PROXIES: list[dict] = [
    {"symbol": "KRW=X", "name": "원/달러 환율", "prefix": "₩", "suffix": "", "decimals": 1, "desc": "고환율 시 한은 금리인하 여력 제약"},
    {"symbol": "^TNX", "name": "미국 10년물 국채금리", "prefix": "", "suffix": "%", "decimals": 2, "desc": "국내 은행채·주담대 금리의 글로벌 기준선"},
    {"symbol": "^KS11", "name": "코스피 (KOSPI)", "prefix": "", "suffix": "", "decimals": 1, "desc": "국내 자산시장 위험선호·부의효과 참고"},
    {"symbol": "GC=F", "name": "국제 금 가격", "prefix": "$", "suffix": "", "decimals": 0, "desc": "화폐가치 하락·실물자산 인플레이션 헤지"},
]


def _fetch_one_yf(meta: dict) -> dict | None:
    try:
        hist = yf.Ticker(meta["symbol"]).history(period="6mo", interval="1d", auto_adjust=False)
        if hist is None or hist.empty:
            return None
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = [c[0] for c in hist.columns]
        close = hist["Close"].dropna()
        if close.empty:
            return None
        price = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) >= 2 else price
        chg_pct = ((price / prev) - 1.0) * 100.0 if prev else 0.0
        return {**meta, "price": price, "change_pct": chg_pct}
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def load_live_cross_macro() -> list[dict]:
    out = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(_fetch_one_yf, m) for m in LIVE_MARKET_PROXIES]
        for f in as_completed(futs, timeout=15):
            try:
                res = f.result(timeout=8)
                if res:
                    out.append(res)
            except Exception:
                continue
    # Preserve order
    order = {m["symbol"]: i for i, m in enumerate(LIVE_MARKET_PROXIES)}
    out.sort(key=lambda x: order.get(x["symbol"], 99))
    return out


def render_seoul_macro_regime_banner(data: dict) -> str:
    rate = data["mortgage_rate"]
    base = data["base_rate"]
    supply = data["annual_supply"]
    khai = data["khai"]
    csi = data["csi"]
    vol = data["volume"]

    pressure = 0
    bullets = []

    if rate >= 4.8:
        pressure += 2
        bullets.append(("금리 압박", "#b91c1c", f"주담대 평균금리 {rate:.2f}% (기준 {base:.2f}%)로 이자 상환 부담이 커 매수세를 제약합니다."))
    elif rate <= 3.8:
        bullets.append(("금리 우호", "#15803d", f"주담대 금리 {rate:.2f}% (기준 {base:.2f}%)로 레버리지 실수요 진입에 우호적입니다."))
    else:
        pressure += 1
        bullets.append(("금리 중립", "#b45309", f"주담대 금리 {rate:.2f}% (기준 {base:.2f}%)로 중립~경계 구간입니다."))

    if supply <= 28000:
        bullets.append(("공급 절벽 (상승 압력)", "#15803d", f"서울 연 입주예정물량 약 {supply:,.0f}호(적정 4만호 크게 하회)로 중장기 전세·매매 하방이 매우 단단합니다."))
    elif supply >= 48000:
        pressure += 2
        bullets.append(("공급 과잉 주의", "#b91c1c", f"서울 연 입주물량 {supply:,.0f}호로 단기 전세가·매매가 하방 압력이 존재합니다."))
    else:
        bullets.append(("공급 적정", "#1d4ed8", f"서울 연 입주물량 {supply:,.0f}호로 수급 균형 구간입니다."))

    if khai >= 175:
        pressure += 1
        bullets.append(("구매력 부담(K-HAI)", "#b91c1c", f"서울 주택구입부담지수 {khai:.0f}로 소득 대비 대출 원리금 부담이 높은 편입니다."))
    elif khai <= 135:
        bullets.append(("구매력 양호(K-HAI)", "#15803d", f"서울 K-HAI {khai:.0f}로 역사적 평균 대비 구입 부담이 완화된 구간입니다."))
    else:
        bullets.append(("구매력 경계(K-HAI)", "#b45309", f"서울 K-HAI {khai:.0f} · 대출 규제(DSR) 영향으로 고가 구간 추격이 제한됩니다."))

    if csi >= 105:
        bullets.append(("기대심리(CSI)", "#1d4ed8", f"주택가격전망 CSI {csi:.1f} · 월 거래량 {vol:,}건으로 상승 기대심리가 유지되고 있습니다."))
    elif csi <= 90:
        bullets.append(("기대심리 위축(CSI)", "#15803d", f"주택가격전망 CSI {csi:.1f} · 월 거래량 {vol:,}건으로 비관론이 짙어 역발상 급매 탐색에 유리합니다."))
    else:
        bullets.append(("심리 관망(CSI)", "#b45309", f"주택가격전망 CSI {csi:.1f} · 월 거래량 {vol:,}건으로 상승·하락 관망세가 팽팽합니다."))

    if pressure >= 3:
        regime, rcol = "🔴 거시 압박 · 급매 선별 대기", "#b91c1c"
        summary = "고금리·구입부담 등 거시 압박이 큽니다. 추격 매수보다 현금 여력을 지키며 깊은 급매만 노리세요."
    elif pressure >= 1:
        regime, rcol = "🟡 공급절벽 vs 금리·규제 힘겨루기", "#b45309"
        summary = "입주물량 부족이 하단을 받치지만 금리·DSR 부담으로 단기 숨고르기가 교차하는 차별화 장세입니다."
    else:
        regime, rcol = "🟢 거시·공급 우호 · 적극 매수 환경", "#15803d"
        summary = "금리 완화·공급 부족·구매력 개선이 동시에 맞물려 서울 핵심지 우상향에 우호적인 국면입니다."

    cards = "".join(
        f'<div class="signal-item"><span class="signal-tag" style="background:{c}16; color:{c};">{t}</span><br/>{txt}</div>'
        for t, c, txt in bullets
    )
    return _compact(f"""
    <div class="agent-panel" style="margin-bottom:16px;">
      <div class="agent-header">
        <div>
          <div style="font-size:0.74rem; color:#78716c; font-weight:700; letter-spacing:0.06em;">SEOUL REAL ESTATE MACRO REGIME</div>
          <div style="font-size:1.03rem; font-weight:600; color:#1c1917; margin-top:4px;">{summary}</div>
        </div>
        <div class="agent-stance" style="background:{rcol}16; color:{rcol};">{regime}</div>
      </div>
      <div class="signal-grid">{cards}</div>
    </div>
    """)


def render_kr_macro_cards(data: dict) -> str:
    items = [
        ("한국은행 기준금리", "BOK BASE", f"{data['base_rate']:.2f}%", "통화정책 방향 · 인하 사이클 시 부동산 선행 반등"),
        ("주담대 평균금리", "MORTGAGE", f"{data['mortgage_rate']:.2f}%", "예금은행 신규 주담대 기준 · 4% 하회 시 매수 탄력"),
        ("주택가격전망 CSI", "BOK CSI", f"{data['csi']:.1f}", "100 이상 상승 전망 / 100 미만 하락 전망"),
        ("서울 K-HAI 부담지수", "HF K-HAI", f"{data['khai']:.0f}", "중위소득 대비 주담대 상환 부담 (낮을수록 여력 큼)"),
        ("서울 연 입주예정물량", "SUPPLY", f"{data['annual_supply']:,.0f}호", "적정 수요(연 4만호) 대비 부족 시 전세·매매 상승 압력"),
        ("서울 아파트 월 거래량", "VOLUME", f"{data['volume']:,}건", f"3년 평균 대비 {data['vol_ratio_pct']:.0f}% (4,000건↑ 활발 / 1,500건↓ 절벽)"),
    ]
    cards = []
    for title, badge, val, desc in items:
        cards.append(
            f'<div class="glass-card" style="padding:17px 19px;">'
            f'<div class="card-kicker"><span>{title}</span><span class="ticker-badge">{badge}</span></div>'
            f'<div style="font-size:1.68rem; font-weight:700; color:#1c1917; margin:7px 0 4px 0; font-variant-numeric:tabular-nums;">{val}</div>'
            f'<div style="font-size:0.75rem; color:#78716c; line-height:1.45;">{desc}</div>'
            f'</div>'
        )
    return _compact(
        f'<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:13px; margin-bottom:14px;">{"".join(cards)}</div>'
    )


def render_live_cross_cards(live_items: list[dict]) -> str:
    if not live_items:
        return ""
    cards = []
    for it in live_items:
        up = it["change_pct"] >= 0
        col = "#15803d" if up else "#b91c1c"
        val_str = f"{it['prefix']}{it['price']:,.{it['decimals']}f}{it['suffix']}"
        cards.append(
            f'<div class="glass-card" style="padding:16px 18px;">'
            f'<div class="card-kicker"><span>{it["name"]}</span><span class="ticker-badge">LIVE {it["symbol"]}</span></div>'
            f'<div style="font-size:1.52rem; font-weight:700; color:#1c1917; margin:6px 0 2px 0; font-variant-numeric:tabular-nums;">{val_str}</div>'
            f'<div style="font-size:0.82rem; font-weight:600; color:{col}; font-variant-numeric:tabular-nums;">{"▲" if up else "▼"} {it["change_pct"]:+.2f}%</div>'
            f'<div style="font-size:0.74rem; color:#78716c; margin-top:6px;">{it["desc"]}</div>'
            f'</div>'
        )
    return _compact(
        f'<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:13px; margin-bottom:14px;">{"".join(cards)}</div>'
    )


def build_macro_history_chart(df: pd.DataFrame) -> go.Figure:
    """Dual-axis 20Y chart: Seoul Real Tx Index vs Mortgage Rate & Annual Supply."""
    sub = df.loc["2006-01-01":]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["real_tx_idx"],
            name="서울 실거래가지수",
            line=dict(color="#18181b", width=2.4),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["mortgage_rate"],
            name="주담대 금리 (%)",
            yaxis="y2",
            line=dict(color="#b91c1c", width=1.9, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["jeonse_ratio"],
            name="서울 전세가율 (%)",
            yaxis="y2",
            line=dict(color="#1d4ed8", width=1.6),
            opacity=0.65,
            visible="legendonly",
        )
    )
    fig.update_layout(
        title=dict(text="서울 실거래가지수 vs 주택담보대출 금리 20년 상관 추이 (2006~2026)", font=dict(size=14, color="#1c1917")),
        height=420,
        margin=dict(l=46, r=58, t=64, b=30),
        yaxis=dict(title="서울 실거래가지수", gridcolor="rgba(0,0,0,0.06)"),
        yaxis2=dict(title="금리 / 전세가율 (%)", overlaying="y", side="right", ticksuffix="%", showgrid=False),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)"),
        hovermode="x unified",
    )
    return fig
