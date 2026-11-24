"""Apple Titanium Light HTML/CSS cards, SVG Supply-Demand Dial, and Plotly charts for Seoul Real Estate Agent."""

from __future__ import annotations

import math
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from realestate.agent_analyzer import (
    classify_jeonse_support,
    classify_seoul_drawdown,
    classify_supply_demand,
)


def _compact_html(html: str) -> str:
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


CUSTOM_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

:root {
  --lux-bg: #edeae4;
  --lux-card: #faf9f6;
  --lux-sub: #f2efe9;
  --lux-ink: #1c1917;
  --lux-secondary: #57534e;
  --lux-tertiary: #78716c;
  --lux-border: rgba(28, 25, 23, 0.09);
  --lux-titanium: #18181b;
  --lux-gold: #b08338;
  --lux-navy: #1e40af;
  --lux-green: #15803d;
  --lux-red: #b91c1c;
  --lux-amber: #b45309;
  --lux-shadow: 0 4px 20px rgba(28, 25, 23, 0.05);
}

html, body, [class*="css"] {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Apple SD Gothic Neo', 'Pretendard', sans-serif !important;
  color: var(--lux-ink);
  -webkit-font-smoothing: antialiased;
}

.stApp {
  background: linear-gradient(180deg, #eae6df 0%, #f1eee8 100%) !important;
  color: var(--lux-ink) !important;
}

.block-container {
  padding-top: 1.05rem !important;
  padding-bottom: 3rem !important;
  max-width: 1220px !important;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {
  background: rgba(234, 230, 223, 0.85) !important;
  backdrop-filter: saturate(180%) blur(18px);
}

div[data-testid="stButtonGroup"] {
  background: rgba(28, 25, 23, 0.06);
  border-radius: 999px;
  padding: 5px;
  margin-bottom: 14px;
  border: 1px solid rgba(28, 25, 23, 0.06);
}
div[data-testid="stButtonGroup"] > div {
  display: flex !important;
  width: 100% !important;
  gap: 6px !important;
}
div[data-testid="stButtonGroup"] button {
  flex: 1 1 0% !important;
  border-radius: 999px !important;
  height: 40px !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  background: transparent !important;
  color: #57534e !important;
  transition: all 0.2s ease !important;
}
div[data-testid="stButtonGroup"] button:hover {
  color: #1c1917 !important;
  background: rgba(255, 255, 255, 0.55) !important;
}
div[data-testid="stButtonGroup"] button[aria-pressed="true"],
div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {
  background: #18181b !important;
  color: #faf9f6 !important;
  box-shadow: 0 4px 12px rgba(24, 24, 27, 0.22) !important;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 6px;
  background: rgba(28, 25, 23, 0.06);
  border-radius: 999px;
  padding: 5px;
  margin-bottom: 16px;
  display: flex;
  width: 100%;
}
.stTabs [data-baseweb="tab"] {
  flex: 1 1 0%;
  justify-content: center;
  height: 38px;
  border-radius: 999px !important;
  color: #57534e !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  background: transparent !important;
  border: none !important;
}
.stTabs [aria-selected="true"] {
  background: #18181b !important;
  color: #faf9f6 !important;
  box-shadow: 0 4px 12px rgba(24, 24, 27, 0.22) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
  display: none !important;
}

.brand-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 2px 12px 2px;
}
.brand-title {
  font-size: 1.1rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #1c1917;
}
.brand-sub {
  font-size: 0.78rem;
  color: #78716c;
  font-weight: 500;
}

.hero-wrap {
  background: linear-gradient(135deg, #18181b 0%, #27272a 60%, #1f242d 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 22px;
  padding: 22px 26px;
  color: #faf9f6;
  margin-bottom: 16px;
  box-shadow: 0 12px 30px rgba(24, 24, 27, 0.14);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}

.glass-card {
  background: var(--lux-card);
  border: 1px solid var(--lux-border);
  border-radius: 20px;
  box-shadow: var(--lux-shadow);
  padding: 20px 22px;
}

.card-kicker {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.79rem;
  font-weight: 700;
  color: #57534e;
  letter-spacing: -0.01em;
}
.ticker-badge {
  font-size: 0.69rem;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(28, 25, 23, 0.06);
  color: #57534e;
  letter-spacing: 0.02em;
}

.section-title {
  font-size: 1.12rem;
  font-weight: 800;
  color: #1c1917;
  letter-spacing: -0.02em;
  margin: 22px 0 10px 0;
}

.agent-panel {
  background: var(--lux-card);
  border: 1px solid var(--lux-border);
  border-radius: 20px;
  padding: 20px 22px;
  box-shadow: var(--lux-shadow);
}
.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(28, 25, 23, 0.08);
}
.agent-stance {
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 800;
  white-space: nowrap;
}
.signal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
  margin-top: 14px;
}
.signal-item {
  background: #f2efe9;
  border-radius: 14px;
  padding: 13px 15px;
  font-size: 0.81rem;
  color: #44403c;
  line-height: 1.5;
}
.signal-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  margin-bottom: 6px;
}
</style>
"""


def render_top_brand_bar(provenance_badge: str = "", live_molit: bool = False) -> str:
    badge = provenance_badge or "40년 공공통계 아카이브"
    if live_molit:
        badge = f"국토부 LIVE · {badge}"
    return _compact_html(f"""
    <div class="brand-bar">
      <div>
        <span class="brand-title">🏛️ SEOUL REAL ESTATE AGENT</span>
        <span class="brand-sub" style="margin-left:10px;">서울 아파트 매수 신호 · 대장단지 실거래 · 38년 Out-of-Sample 백테스트</span>
      </div>
      <span class="ticker-badge" style="background:#18181b; color:#faf9f6;">{badge}</span>
    </div>
    """)


def render_hero_html(kst_now: str, data: dict) -> str:
    return _compact_html(f"""
    <div class="hero-wrap">
      <div>
        <div style="font-size:0.73rem; letter-spacing:0.09em; color:#a8a29e; font-weight:700;">SEOUL APARTMENT QUANT DASHBOARD</div>
        <div style="font-size:1.55rem; font-weight:800; letter-spacing:-0.03em; margin-top:4px;">서울 부동산 시장 실시간 진단 &amp; 40년 검증</div>
        <div style="font-size:0.82rem; color:#d6d3d1; margin-top:4px;">기준월 {data['last_date'].strftime('%Y년 %m월')} · 업데이트 {kst_now}</div>
      </div>
      <div style="display:flex; gap:10px; flex-wrap:wrap;">
        <div style="background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.12); border-radius:14px; padding:10px 15px;">
          <div style="font-size:0.7rem; color:#a8a29e;">주담대 평균금리</div>
          <div style="font-size:1.18rem; font-weight:800; font-variant-numeric:tabular-nums;">{data['mortgage_rate']:.2f}% <span style="font-size:0.75rem; color:#d6d3d1;">(기준 {data['base_rate']:.2f}%)</span></div>
        </div>
        <div style="background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.12); border-radius:14px; padding:10px 15px;">
          <div style="font-size:0.7rem; color:#a8a29e;">서울 월 거래량</div>
          <div style="font-size:1.18rem; font-weight:800; font-variant-numeric:tabular-nums;">{data['volume']:,}건 <span style="font-size:0.75rem; color:#d6d3d1;">(평균비 {data['vol_ratio_pct']:.0f}%)</span></div>
        </div>
      </div>
    </div>
    """)


def render_seoul_buy_index_card(idx: dict) -> str:
    col = idx["color"]
    score = idx["score"]
    pills = []
    for it in idx["items"]:
        met_bg = "rgba(21,128,61,0.12)" if it["met"] else "#f2efe9"
        met_fg = "#15803d" if it["met"] else "#1c1917"
        icon = "✅ " if it["met"] else ""
        pills.append(
            f'<div style="background:{met_bg}; border-radius:14px; padding:12px 14px; border:1px solid rgba(28,25,23,0.06);">'
            f'<div style="display:flex; justify-content:space-between; font-size:0.76rem; font-weight:700; color:#57534e;">'
            f'<span>{icon}{it["label"]}</span><span style="color:{met_fg};">{it["pts"]}/25점</span>'
            f'</div>'
            f'<div style="font-size:1.05rem; font-weight:800; color:#1c1917; margin-top:4px; font-variant-numeric:tabular-nums;">{it["value"]}</div>'
            f'<div style="font-size:0.71rem; color:#78716c; margin-top:2px;">만점 조건: {it["rule"]}</div>'
            f'</div>'
        )
    filter_badge = "직전 10년 롤링 백분위 결합 (미래누수 0%)" if idx.get("use_macro_filter") else "고정 임계값 사이클형"
    return _compact_html(f"""
    <div class="glass-card" style="margin-bottom:16px; padding:22px 24px;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
        <div>
          <div style="font-size:0.76rem; font-weight:700; color:#78716c; letter-spacing:0.06em;">SEOUL MARKET BUY RECOMMENDATION INDEX · {filter_badge}</div>
          <div style="display:flex; align-items:baseline; gap:12px; margin-top:4px; flex-wrap:wrap;">
            <span style="font-size:2.45rem; font-weight:900; color:{col}; letter-spacing:-0.04em; font-variant-numeric:tabular-nums;">{score}<span style="font-size:1.05rem; color:#78716c;"> / 100</span></span>
            <span style="padding:5px 13px; border-radius:999px; font-size:0.88rem; font-weight:800; background:{col}18; color:{col};">{idx['grade']}</span>
            <span style="font-size:0.79rem; color:#78716c;">만점 충족 {idx['met_count']}/4개</span>
          </div>
          <div style="font-size:0.85rem; color:#44403c; margin-top:6px;">{idx['comment']}</div>
        </div>
        <div style="min-width:200px; flex:0 1 260px;">
          <div style="height:10px; border-radius:999px; background:linear-gradient(90deg, #b91c1c 0%, #c2410c 25%, #b45309 50%, #1d4ed8 72%, #15803d 100%); position:relative;">
            <div style="position:absolute; left:{score}%; top:-4px; width:18px; height:18px; border-radius:50%; background:#18181b; border:3px solid #faf9f6; transform:translateX(-50%); box-shadow:0 2px 8px rgba(0,0,0,0.3);"></div>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:0.69rem; color:#78716c; margin-top:6px;">
            <span>0 금지</span><span>44 중립</span><span>64 추천</span><span>78+ 강력</span>
          </div>
        </div>
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:11px; margin-top:16px;">
        {"".join(pills)}
      </div>
    </div>
    """)


def render_region_kpi_card(reg: dict) -> str:
    up = reg["mom_pct"] >= 0
    chg_col = "#15803d" if up else "#b91c1c"
    dd_lbl, dd_col = classify_seoul_drawdown(reg["dd_5y_pct"])
    return _compact_html(f"""
    <div class="glass-card" style="height:100%;">
      <div class="card-kicker"><span>{reg['name']}</span><span class="ticker-badge">{reg['badge']}</span></div>
      <div style="font-size:2.05rem; font-weight:800; color:#1c1917; letter-spacing:-0.03em; margin:8px 0 2px 0; font-variant-numeric:tabular-nums;">{reg['value']:.1f}</div>
      <div style="font-size:0.86rem; font-weight:700; color:{chg_col}; font-variant-numeric:tabular-nums;">
        {"▲" if up else "▼"} 전월비 {reg['mom_pct']:+.2f}% · 전년비 {reg['yoy_pct']:+.1f}%
      </div>
      <div style="margin-top:13px; padding:11px 13px; border-radius:14px; background:#f2efe9;">
        <div style="display:flex; justify-content:space-between; font-size:0.76rem; color:#57534e;">
          <span>5년 고점 대비 낙폭</span>
          <span style="font-weight:800; color:{dd_col}; font-variant-numeric:tabular-nums;">{reg['dd_5y_pct']:.1f}% ({dd_lbl})</span>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.73rem; color:#78716c; margin-top:5px;">
          <span>5년 고점 {reg['peak_5y']:.1f} ({reg['peak_5y_date'].strftime('%Y.%m')})</span>
          <span>회복 여력 +{reg['recovery_pct']:.1f}%</span>
        </div>
      </div>
    </div>
    """)


def render_supply_demand_dial_card(sd: float, sd_delta: float, csi: float) -> str:
    """Custom SVG semi-circle dial for Seoul Sale Supply-Demand Index (50~150 visual span)."""
    lbl, col, sub = classify_supply_demand(sd)
    clamped = max(55.0, min(145.0, sd))
    norm = (clamped - 55.0) / 90.0  # 0 (left: 55 extreme buyer fear) -> 1 (right: 145 extreme greed)
    angle_deg = 180.0 - norm * 180.0
    rad = math.radians(angle_deg)
    cx, cy, r = 110.0, 102.0, 72.0
    nx = cx + r * math.cos(rad)
    ny = cy - r * math.sin(rad)

    return _compact_html(f"""
    <div class="glass-card" style="height:100%;">
      <div class="card-kicker"><span>서울 매매수급지수 (공포·과열)</span><span class="ticker-badge">REB 0~200</span></div>
      <div style="text-align:center; margin-top:4px;">
        <svg viewBox="0 0 220 120" width="100%" style="max-width:225px; display:block; margin:0 auto;">
          <path d="M 28 102 A 82 82 0 0 1 192 102" fill="none" stroke="#e7e2d9" stroke-width="14" stroke-linecap="round"/>
          <path d="M 28 102 A 82 82 0 0 1 82 25" fill="none" stroke="#15803d" stroke-width="14" stroke-linecap="round"/>
          <path d="M 86 24 A 82 82 0 0 1 134 24" fill="none" stroke="#b45309" stroke-width="14"/>
          <path d="M 138 25 A 82 82 0 0 1 192 102" fill="none" stroke="#b91c1c" stroke-width="14" stroke-linecap="round"/>
          <line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#18181b" stroke-width="3.2" stroke-linecap="round"/>
          <circle cx="{cx}" cy="{cy}" r="6" fill="#18181b"/>
          <text x="110" y="90" text-anchor="middle" font-size="24" font-weight="800" fill="#1c1917">{sd:.1f}</text>
          <text x="26" y="117" font-size="9.5" fill="#15803d" font-weight="700">60 공포</text>
          <text x="110" y="16" text-anchor="middle" font-size="9.5" fill="#78716c" font-weight="700">100 균형</text>
          <text x="194" y="117" text-anchor="end" font-size="9.5" fill="#b91c1c" font-weight="700">140 과열</text>
        </svg>
        <div style="font-size:0.86rem; font-weight:800; color:{col}; margin-top:2px;">{lbl}</div>
        <div style="font-size:0.74rem; color:#78716c; margin-top:3px;">전월비 {sd_delta:+.1f}p · 주택가격전망 CSI <b style="color:#1c1917;">{csi:.1f}</b></div>
      </div>
    </div>
    """)


def render_seoul_oscillator_card(kind: str, val: float, delta: float, extra: str) -> str:
    if kind == "RSI":
        title = "서울 아파트 월간 RSI(12)"
        badge = "12M CYCLE"
        if val <= 34:
            lbl, col, desc = "강한 과매도 (저점권)", "#15803d", "1년 사이클 기준 가격 하락 누적 · 반등 탐색 구간"
        elif val <= 48:
            lbl, col, desc = "조정·약세 구간", "#1d4ed8", "고점 피로감 해소 중 · 급매 협상 유리"
        elif val <= 65:
            lbl, col, desc = "중립·완만 상승", "#b45309", "가격 모멘텀 균형 구간"
        else:
            lbl, col, desc = "단기 과열 (과매수)", "#b91c1c", "연속 상승 피로감 누적 · 추격 매수 유의"
        bar_pct = max(0.0, min(100.0, val))
        val_str = f"{val:.1f}"
        delta_str = f"전월비 {delta:+.1f}"
    else:
        title = "전세 하방지지 & 전세가율"
        badge = extra
        lbl, col, desc = classify_jeonse_support(val, float(extra.replace("전세가율 ", "").replace("%", "")))
        bar_pct = max(0.0, min(100.0, (val + 10.0) / 20.0 * 100.0))
        val_str = f"{val:+.1f}"
        delta_str = f"전세-매매 선행차 {delta:+.1f}%p"

    return _compact_html(f"""
    <div class="glass-card" style="padding:18px 20px;">
      <div class="card-kicker"><span>{title}</span><span class="ticker-badge">{badge}</span></div>
      <div style="display:flex; justify-content:space-between; align-items:baseline; margin:8px 0 6px 0;">
        <span style="font-size:1.85rem; font-weight:800; color:#1c1917; font-variant-numeric:tabular-nums;">{val_str}</span>
        <span style="padding:3px 10px; border-radius:999px; font-size:0.76rem; font-weight:700; background:{col}16; color:{col};">{lbl}</span>
      </div>
      <div style="height:8px; background:#e7e2d9; border-radius:999px; position:relative; margin:8px 0;">
        <div style="position:absolute; left:{bar_pct:.1f}%; top:-3px; width:14px; height:14px; border-radius:50%; background:{col}; border:2px solid #faf9f6; transform:translateX(-50%);"></div>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#57534e; margin-top:6px;">
        <span>{desc}</span><b style="color:#1c1917;">{delta_str}</b>
      </div>
    </div>
    """)


def render_agent_briefing_html(briefing: dict) -> str:
    col = briefing["stance_color"]
    tone_map = {
        "opportunity": ("#15803d", "rgba(21,128,61,0.12)"),
        "info": ("#1d4ed8", "rgba(29,78,216,0.12)"),
        "warning": ("#b91c1c", "rgba(185,28,28,0.12)"),
        "neutral": ("#57534e", "rgba(87,83,78,0.12)"),
    }
    cards = []
    for s in briefing["signals"]:
        fg, bg = tone_map.get(s["tone"], ("#57534e", "#e7e2d9"))
        cards.append(
            f'<div class="signal-item">'
            f'<span class="signal-tag" style="background:{bg}; color:{fg};">{s["tag"]}</span><br/>{s["text"]}'
            f'</div>'
        )
    return _compact_html(f"""
    <div class="agent-panel">
      <div class="agent-header">
        <div>
          <div style="font-size:0.74rem; color:#78716c; font-weight:700; letter-spacing:0.06em;">SEOUL REAL ESTATE AGENT BRIEFING</div>
          <div style="font-size:1.02rem; font-weight:600; color:#1c1917; margin-top:4px;">{briefing['summary']}</div>
        </div>
        <div class="agent-stance" style="background:{col}18; color:{col};">{briefing['stance']} ({briefing['score']}점)</div>
      </div>
      <div class="signal-grid">{"".join(cards)}</div>
    </div>
    """)


def build_seoul_main_chart(df: pd.DataFrame, price_col: str, years: int = 10) -> go.Figure:
    """3-panel interactive chart: Seoul Index + Monthly RSI(12) + Supply-Demand & Jeonse Ratio."""
    sub = df.tail(years * 12) if years > 0 else df
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.055,
        row_heights=[0.52, 0.24, 0.24],
    )
    fig.add_trace(
        go.Scatter(x=sub.index, y=sub[price_col], name="서울 아파트 지수", line=dict(color="#18181b", width=2.4)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=sub.index, y=sub["MA_12"], name="12개월선", line=dict(color="#1d4ed8", width=1.4, dash="dot")),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=sub.index, y=sub["MA_36"], name="36개월선", line=dict(color="#b08338", width=1.4, dash="dash")),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=sub.index, y=sub["RSI_12"], name="월간 RSI(12)", line=dict(color="#15803d", width=1.8)),
        row=2, col=1,
    )
    fig.add_hline(y=34, line_dash="dot", line_color="#15803d", row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#b91c1c", row=2, col=1)

    fig.add_trace(
        go.Scatter(x=sub.index, y=sub["supply_demand"], name="매매수급지수", line=dict(color="#b45309", width=1.8)),
        row=3, col=1,
    )
    fig.add_hline(y=100, line_dash="dot", line_color="#78716c", row=3, col=1)
    fig.add_hline(y=76, line_dash="dot", line_color="#15803d", row=3, col=1)

    fig.update_yaxes(side="right", gridcolor="rgba(0,0,0,0.06)", tickfont=dict(size=10.5, color="#57534e"))
    fig.update_layout(
        height=610,
        margin=dict(l=28, r=60, t=42, b=24),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=11.5),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)"),
        hovermode="x unified",
    )
    return fig


def build_seoul_drawdown_chart(df: pd.DataFrame, years: int = 20) -> go.Figure:
    sub = df.tail(years * 12) if years > 0 else df
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["DD_5Y"],
            name="5년 고점 대비 낙폭 (%)",
            fill="tozeroy",
            fillcolor="rgba(185, 28, 28, 0.12)",
            line=dict(color="#b91c1c", width=2.0),
            hovertemplate="%{x|%Y-%m}<br>낙폭: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_hline(y=-14, line_dash="dash", line_color="#15803d", annotation_text=" -14% 역대급 급매 만점선", annotation_position="bottom left")
    fig.add_hline(y=-7, line_dash="dot", line_color="#1d4ed8", annotation_text=" -7% 조정 진입", annotation_position="top left")
    fig.update_yaxes(side="right", ticksuffix="%", gridcolor="rgba(0,0,0,0.06)")
    fig.update_layout(
        title=dict(text="서울 아파트 5년 고점 대비 낙폭 (Drawdown) 추이", font=dict(size=14, color="#1c1917")),
        height=390,
        margin=dict(l=32, r=60, t=58, b=28),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        hovermode="x unified",
    )
    return fig
