"""Apple.com inspired minimalist HTML/CSS cards, SVG Fear & Greed dial, and Plotly charts."""

from __future__ import annotations

import math
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from agent_analyzer import classify_drawdown, classify_mfi, classify_rsi


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

/* Hide default streamlit chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {
  background: rgba(234, 230, 223, 0.85) !important;
  backdrop-filter: saturate(180%) blur(18px);
}

/* Smooth Organic Capsule Pill Navigation (for segmented_control & inner tabs) */
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
div[data-testid="stButtonGroup"] button:focus,
div[data-testid="stButtonGroup"] button:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 6px;
  background: rgba(28, 25, 23, 0.06);
  border-radius: 999px;
  padding: 5px;
  margin-bottom: 18px;
  display: flex;
  width: 100%;
  border: 1px solid rgba(28, 25, 23, 0.06);
}
.stTabs [data-baseweb="tab"] {
  flex: 1 1 0%;
  justify-content: center;
  height: 40px;
  border-radius: 999px !important;
  padding: 0 14px !important;
  color: #57534e !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  letter-spacing: -0.01em;
  white-space: nowrap;
  background: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  transition: background-color 0.22s ease, color 0.22s ease, box-shadow 0.22s ease;
}
.stTabs [data-baseweb="tab"]:focus,
.stTabs [data-baseweb="tab"]:focus-visible,
.stTabs [data-baseweb="tab"]:active,
.stTabs button[role="tab"]:focus,
.stTabs button[role="tab"]:focus-visible {
  outline: none !important;
  box-shadow: none !important;
  border: none !important;
}
.stTabs [data-baseweb="tab"]:hover {
  color: #1c1917 !important;
  background: rgba(255, 255, 255, 0.55) !important;
}
.stTabs [aria-selected="true"],
.stTabs [aria-selected="true"]:hover,
.stTabs [aria-selected="true"]:focus {
  background: #18181b !important;
  color: #faf9f6 !important;
  font-weight: 600 !important;
  box-shadow: 0 4px 12px rgba(24, 24, 27, 0.22) !important;
  outline: none !important;
  border: none !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
  display: none !important;
}

/* Luxury Space-Titanium Hero Header (Anchors the page with depth & richness) */
.hero-wrap {
  background: linear-gradient(135deg, #18181b 0%, #27272a 60%, #1f242d 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 22px;
  padding: 24px 28px;
  margin-bottom: 18px;
  box-shadow: 0 12px 32px rgba(24, 24, 27, 0.16);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}
.hero-title {
  font-size: 1.78rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: #faf9f6;
  margin: 0;
  line-height: 1.18;
}
.hero-sub {
  color: #a8a29e;
  font-size: 0.89rem;
  font-weight: 400;
  margin-top: 5px;
  letter-spacing: -0.01em;
}
.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: rgba(255, 255, 255, 0.09);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #f5f5f4;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
}

/* Warm Ivory Luxury Cards */
.glass-card {
  background: var(--lux-card);
  border: 1px solid var(--lux-border);
  border-radius: 22px;
  padding: 22px 24px;
  box-shadow: var(--lux-shadow);
  transition: box-shadow 0.22s ease, transform 0.22s ease;
  height: 100%;
}
.glass-card:hover {
  box-shadow: 0 8px 26px rgba(28, 25, 23, 0.08);
}

.card-kicker {
  font-size: 0.8rem;
  letter-spacing: -0.01em;
  color: #57534e;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ticker-badge {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 999px;
  background: #ece8e0;
  color: #57534e;
  font-variant-numeric: tabular-nums;
}
.card-price {
  font-size: 2.15rem;
  font-weight: 700;
  color: #1c1917;
  margin: 8px 0 3px 0;
  letter-spacing: -0.035em;
  font-variant-numeric: tabular-nums;
}
.delta-up {
  color: #15803d;
  font-weight: 600;
  font-size: 0.9rem;
  font-variant-numeric: tabular-nums;
}
.delta-down {
  color: #b91c1c;
  font-weight: 600;
  font-size: 0.9rem;
  font-variant-numeric: tabular-nums;
}

/* Warm Sand Sub-panel inside card */
.dd-box {
  margin-top: 16px;
  padding: 13px 15px;
  border-radius: 15px;
  background: var(--lux-sub);
  border: 1px solid rgba(28, 25, 23, 0.05);
}
.dd-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 0.82rem;
  margin-bottom: 6px;
}
.dd-val {
  font-weight: 700;
  font-size: 1.02rem;
  font-variant-numeric: tabular-nums;
}
.bar-track {
  width: 100%;
  height: 6px;
  background: #e2ddd3;
  border-radius: 999px;
  overflow: hidden;
  margin: 6px 0;
}
.bar-fill {
  height: 100%;
  border-radius: 999px;
}
.meta-sub {
  font-size: 0.77rem;
  color: #57534e;
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-variant-numeric: tabular-nums;
}

/* RSI / MFI Oscillator Card */
.osc-card {
  background: var(--lux-card);
  border: 1px solid var(--lux-border);
  border-radius: 22px;
  padding: 20px 22px;
  box-shadow: var(--lux-shadow);
}
.osc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.osc-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #57534e;
}
.osc-badge {
  font-size: 0.73rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 999px;
}
.osc-val {
  font-size: 2.0rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 6px 0 2px 0;
  font-variant-numeric: tabular-nums;
}
.osc-track {
  position: relative;
  height: 8px;
  border-radius: 999px;
  margin: 14px 0 7px 0;
  background: linear-gradient(90deg, #16a34a 0%, #22c55e 28%, #ddd8ce 46%, #ddd8ce 58%, #d97706 74%, #dc2626 100%);
}
.osc-thumb {
  position: absolute;
  top: -5px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #faf9f6;
  border: 2.5px solid #18181b;
  box-shadow: 0 2px 6px rgba(24, 24, 27, 0.25);
  transform: translateX(-50%);
}
.osc-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.71rem;
  color: #78716c;
  font-variant-numeric: tabular-nums;
}

/* Agent Briefing Panel */
.agent-panel {
  background: var(--lux-card);
  border: 1px solid var(--lux-border);
  border-radius: 22px;
  padding: 22px 26px;
  margin-bottom: 18px;
  box-shadow: var(--lux-shadow);
}
.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.agent-stance {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.84rem;
  font-variant-numeric: tabular-nums;
}
.signal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
  margin-top: 12px;
}
.signal-item {
  background: var(--lux-sub);
  border: 1px solid rgba(28, 25, 23, 0.05);
  border-radius: 15px;
  padding: 13px 15px;
  font-size: 0.84rem;
  line-height: 1.55;
  color: #1c1917;
}
.signal-tag {
  display: inline-block;
  font-size: 0.71rem;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 999px;
  margin-bottom: 6px;
}

/* Section Title */
.section-title {
  font-size: 1.22rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: #1c1917;
  margin: 24px 0 12px 0;
}

/* Soft Warm Ivory Wrapper around Plotly Charts */
div[data-testid="stPlotlyChart"] {
  background: #faf9f6;
  border: 1px solid rgba(28, 25, 23, 0.09);
  border-radius: 22px;
  padding: 14px 18px 10px 18px;
  box-shadow: 0 4px 20px rgba(28, 25, 23, 0.05);
  overflow: hidden;
}

/* Sidebar warm tone */
section[data-testid="stSidebar"] {
  background-color: #f5f3ee !important;
  border-right: 1px solid rgba(28, 25, 23, 0.08);
}

/* Remove boxy focus ring on buttons/radios too */
button:focus, button:focus-visible {
  outline: none !important;
}

/* Mobile responsiveness */
@media (max-width: 640px) {
  .block-container {
    padding-top: 0.65rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
  }
  div[data-testid="stButtonGroup"] {
    padding: 3px;
  }
  div[data-testid="stButtonGroup"] > div {
    gap: 3px !important;
  }
  div[data-testid="stButtonGroup"] button {
    height: 36px !important;
    padding: 0 2px !important;
    font-size: 0.68rem !important;
  }
  .stTabs [data-baseweb="tab-list"] {
    padding: 4px;
    gap: 4px;
    margin-bottom: 12px;
  }
  .stTabs [data-baseweb="tab"] {
    height: 36px;
    padding: 0 6px !important;
    font-size: 0.8rem !important;
  }
  .hero-wrap {
    padding: 18px 18px;
    border-radius: 18px;
  }
  .hero-title {
    font-size: 1.4rem;
  }
  .card-price {
    font-size: 1.85rem;
  }
  .glass-card {
    padding: 18px 18px;
    border-radius: 18px;
  }
}
</style>
"""


def _compact_html(html: str) -> str:
    """Remove blank lines and leading indentation so Markdown never turns HTML into code blocks."""
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


def _apple_color(hex_color: str) -> str:
    """Map legacy bright neon hex colors to refined high-contrast Apple light-mode accents."""
    mapping = {
        "#10b981": "#1d8f34",
        "#22c55e": "#1d8f34",
        "#34d399": "#1d8f34",
        "#38bdf8": "#0071e3",
        "#ef4444": "#d70015",
        "#f97316": "#c96a00",
        "#f59e0b": "#c96a00",
        "#eab308": "#9a6700",
        "#94a3b8": "#6e6e73",
    }
    return mapping.get(hex_color.lower(), hex_color)


def render_top_brand_bar() -> str:
    """Render sleek single-line top brand & creator bar above navigation."""
    return _compact_html("""
    <div style="display:flex; justify-content:space-between; align-items:center; padding:2px 6px 10px 6px; flex-wrap:wrap; gap:6px;">
      <span style="font-size:0.78rem; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; color:#57534e;">US STOCK AGENT</span>
      <span style="font-size:0.78rem; font-weight:600; color:#57534e; background:rgba(28,25,23,0.06); padding:4px 12px; border-radius:999px;">제작자 : <b style="color:#1c1917;">seokhwan</b></span>
    </div>
    """)


def render_hero_html(updated_kst: str, vix_price: float | None, vix_chg: float) -> str:
    vix_str = f"VIX {vix_price:.2f} ({vix_chg:+.1f}%)" if vix_price is not None else "VIX N/A"
    return _compact_html(f"""
    <div class="hero-wrap">
      <div>
        <div style="font-size:0.72rem; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:#d4a359; margin-bottom:4px;">PRIVATE MARKET TERMINAL</div>
        <div class="hero-title">US Market Overview</div>
        <div class="hero-sub">S&amp;P 500 · NASDAQ (RSI · MFI) · 공포·탐욕 지수 · 고점 대비 낙폭</div>
      </div>
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
        <div class="live-pill" style="color:#d6d3d1;">{vix_str}</div>
        <div class="live-pill">
          <span class="pulse-dot"></span>
          {updated_kst}
        </div>
      </div>
    </div>
    """)


def render_market_buy_index_card(buy_idx: dict) -> str:
    """Render top-of-dashboard Market Buy Recommendation Index card (0~100)."""
    score = buy_idx["score"]
    color = buy_idx["color"]
    chips = []
    for it in buy_idx["items"]:
        if it["met"]:
            st_html = '<span style="color:#15803d; font-weight:700;">✅ 25/25점</span>'
            bd = "rgba(21, 128, 61, 0.28)"
        else:
            st_html = f'<span style="color:#78716c; font-weight:600;">{int(it["pts"])}/25점</span>'
            bd = "rgba(28, 25, 23, 0.07)"
        chips.append(
            f'<div style="background:#f2efe9; border:1px solid {bd}; border-radius:14px; padding:11px 13px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:#57534e; font-weight:600;">'
            f'<span>{it["label"]}</span><span>{st_html}</span>'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:5px;">'
            f'<span style="font-size:1.12rem; font-weight:700; color:#1c1917; font-variant-numeric:tabular-nums;">{it["value"]}</span>'
            f'<span style="font-size:0.71rem; color:#78716c;">기준 {it["rule"]}</span>'
            f'</div>'
            f'</div>'
        )

    return _compact_html(f"""
    <div class="glass-card" style="margin-bottom:18px; padding:22px 26px;">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
        <div>
          <div style="font-size:0.74rem; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; color:#78716c;">현 시황 매수 추천 지수 · 4대 핵심 지표 종합</div>
          <div style="display:flex; align-items:center; gap:12px; margin-top:6px; flex-wrap:wrap;">
            <span style="font-size:2.35rem; font-weight:800; letter-spacing:-0.04em; color:#1c1917; font-variant-numeric:tabular-nums; line-height:1;">{score}<span style="font-size:1.05rem; font-weight:600; color:#78716c;"> / 100</span></span>
            <span style="display:inline-flex; align-items:center; padding:6px 15px; border-radius:999px; font-size:0.94rem; font-weight:700; background:{color}16; color:{color}; border:1px solid {color}38;">{buy_idx['grade']}</span>
            <span style="font-size:0.78rem; font-weight:600; color:#57534e; background:#ece8e0; padding:4px 10px; border-radius:999px;">핵심 조건 {buy_idx['met_count']}/4 완전 충족</span>
          </div>
          <div style="font-size:0.86rem; color:#57534e; margin-top:7px;">{buy_idx['comment']}</div>
        </div>
        <div style="min-width:250px; flex:1; max-width:360px;">
          <div style="position:relative; height:10px; border-radius:999px; background:linear-gradient(90deg, #b91c1c 0%, #c2410c 26%, #d97706 50%, #1d4ed8 74%, #15803d 100%); margin-top:6px;">
            <div style="position:absolute; left:{score}%; top:-4px; width:18px; height:18px; border-radius:50%; background:#faf9f6; border:3px solid #18181b; box-shadow:0 2px 8px rgba(0,0,0,0.28); transform:translateX(-50%);"></div>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#78716c; margin-top:7px; font-weight:600;">
            <span>매수 금지</span>
            <span>주의</span>
            <span>관망</span>
            <span>매수 추천</span>
            <span>강력 매수</span>
          </div>
        </div>
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(190px, 1fr)); gap:10px; margin-top:16px;">
        {"".join(chips)}
      </div>
    </div>
    """)


def render_index_kpi_card(idx: dict) -> str:
    """Render minimalist Apple white card for S&P 500 or NASDAQ with Drawdown from High."""
    up = idx["change"] >= 0
    delta_cls = "delta-up" if up else "delta-down"
    arrow = "▲" if up else "▼"
    dd_label, raw_color = classify_drawdown(idx["dd_ath_pct"])
    dd_color = _apple_color(raw_color)

    dd_mag = min(100.0, abs(idx["dd_ath_pct"]) / 35.0 * 100.0)
    ath_date_str = idx["ath_date"].strftime("%Y.%m.%d")
    rsi_val = f"{idx['rsi']:.1f}" if idx.get("rsi") is not None else "-"
    mfi_val = f"{idx['mfi']:.1f}" if idx.get("mfi") is not None else "-"

    return _compact_html(f"""
    <div class="glass-card">
      <div class="card-kicker">
        <span>{idx['name']}</span>
        <span class="ticker-badge">{idx['symbol']}</span>
      </div>
      <div class="card-price">{idx['price']:,.2f}</div>
      <div class="{delta_cls}">{arrow} {idx['change']:+,.2f} ({idx['change_pct']:+.2f}%)</div>
      <div class="dd-box">
        <div class="dd-row">
          <span style="color:#1d1d1f; font-weight:600;">고점 대비 낙폭</span>
          <span class="dd-val" style="color:{dd_color};">{idx['dd_ath_pct']:.2f}%</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width:{dd_mag:.1f}%; background:{dd_color};"></div>
        </div>
        <div class="meta-sub">
          <span>최고점 {idx['ath_price']:,.2f} ({ath_date_str})</span>
          <span style="color:{dd_color}; font-weight:600;">{dd_label}</span>
        </div>
        <div class="meta-sub" style="margin-top:6px; padding-top:6px; border-top:1px solid rgba(0,0,0,0.06);">
          <span>52주 고점 대비 <b style="color:#1d1d1f;">{idx['dd_52w_pct']:.2f}%</b></span>
          <span>회복 필요 <b style="color:#0071e3;">+{idx['recovery_ath_pct']:.1f}%</b></span>
        </div>
      </div>
      <div class="meta-sub" style="margin-top:12px;">
        <span>RSI(14) <b style="color:#1d1d1f;">{rsi_val}</b></span>
        <span>MFI(14) <b style="color:#1d1d1f;">{mfi_val}</b></span>
      </div>
    </div>
    """)


def render_fear_greed_card(fg: dict) -> str:
    """Render minimalist Apple white card with refined SVG semicircle dial for CNN Fear & Greed."""
    score = max(0.0, min(100.0, float(fg["score"])))
    angle_rad = math.radians(180.0 - (score / 100.0) * 180.0)
    cx, cy, r = 130.0, 104.0, 80.0
    nx = cx + (r - 12) * math.cos(angle_rad)
    ny = cy - (r - 12) * math.sin(angle_rad)

    diff_1d = score - fg["previous_close"]
    diff_color = "#1d8f34" if diff_1d >= 0 else "#d70015"
    fg_color = _apple_color(fg["color"])

    def arc_path(start_pct: float, end_pct: float) -> str:
        a1 = math.radians(180.0 - start_pct / 100.0 * 180.0)
        a2 = math.radians(180.0 - end_pct / 100.0 * 180.0)
        x1, y1 = cx + r * math.cos(a1), cy - r * math.sin(a1)
        x2, y2 = cx + r * math.cos(a2), cy - r * math.sin(a2)
        return f"M {x1:.1f} {y1:.1f} A {r:.0f} {r:.0f} 0 0 1 {x2:.1f} {y2:.1f}"

    return _compact_html(f"""
    <div class="glass-card">
      <div class="card-kicker">
        <span>공포 · 탐욕 지수</span>
        <span class="ticker-badge">CNN</span>
      </div>
      <div style="display:flex; flex-direction:column; align-items:center; margin-top:4px;">
        <svg viewBox="0 0 260 116" width="100%" style="max-width:246px; overflow:visible;">
          <path d="{arc_path(0, 24)}" fill="none" stroke="#ff3b30" stroke-width="13" stroke-linecap="round"/>
          <path d="{arc_path(26, 44)}" fill="none" stroke="#ff9500" stroke-width="13" stroke-linecap="round"/>
          <path d="{arc_path(46, 54)}" fill="none" stroke="#d1d1d6" stroke-width="13" stroke-linecap="round"/>
          <path d="{arc_path(56, 74)}" fill="none" stroke="#30d158" stroke-width="13" stroke-linecap="round"/>
          <path d="{arc_path(76, 100)}" fill="none" stroke="#1d8f34" stroke-width="13" stroke-linecap="round"/>
          <line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#1d1d1f" stroke-width="3" stroke-linecap="round"/>
          <circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="#1d1d1f"/>
          <circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.5" fill="#ffffff"/>
          <text x="40" y="114" text-anchor="middle" fill="#86868b" font-size="10">0</text>
          <text x="130" y="14" text-anchor="middle" fill="#86868b" font-size="10">50</text>
          <text x="220" y="114" text-anchor="middle" fill="#86868b" font-size="10">100</text>
        </svg>
        <div style="display:flex; align-items:baseline; gap:10px; margin-top:-2px;">
          <span style="font-size:2.1rem; font-weight:700; color:#1d1d1f; letter-spacing:-0.03em; font-variant-numeric:tabular-nums; line-height:1;">{score:.1f}</span>
          <span style="font-size:0.8rem; font-weight:600; color:{fg_color}; background:{fg_color}14; padding:3px 10px; border-radius:999px;">{fg['kr_label']}</span>
        </div>
      </div>
      <div class="dd-box" style="margin-top:12px;">
        <div class="meta-sub" style="margin-top:0;">
          <span>전일 <b style="color:#1d1d1f;">{fg['previous_close']:.1f}</b> <span style="color:{diff_color};">({diff_1d:+.1f})</span></span>
          <span>1주 전 <b style="color:#1d1d1f;">{fg['previous_1_week']:.1f}</b></span>
        </div>
        <div class="meta-sub" style="margin-top:6px;">
          <span>1개월 전 <b style="color:#1d1d1f;">{fg['previous_1_month']:.1f}</b></span>
          <span>1년 전 <b style="color:#1d1d1f;">{fg['previous_1_year']:.1f}</b></span>
        </div>
      </div>
    </div>
    """)


def render_oscillator_card(kind: str, value: float | None, delta: float, index_name: str) -> str:
    """Render minimalist Apple-style RSI(14) or MFI(14) card."""
    if kind == "RSI":
        label, raw_color, desc = classify_rsi(value)
        title = f"{index_name} · RSI (14)"
        thresholds = ("0", "30 과매도", "50", "70 과매수", "100")
    else:
        label, raw_color, desc = classify_mfi(value)
        title = f"{index_name} · MFI (14)"
        thresholds = ("0", "20 과매도", "50", "80 과매수", "100")

    color = _apple_color(raw_color)
    val_num = max(0.0, min(100.0, float(value))) if value is not None else 50.0
    val_str = f"{value:.1f}" if value is not None else "N/A"
    d_color = "#1d8f34" if delta >= 0 else "#d70015"

    return _compact_html(f"""
    <div class="osc-card">
      <div class="osc-header">
        <span class="osc-title">{title}</span>
        <span class="osc-badge" style="background:{color}14; color:{color};">{label}</span>
      </div>
      <div style="display:flex; align-items:baseline; gap:10px;">
        <div class="osc-val" style="color:#1d1d1f;">{val_str}</div>
        <span style="font-size:0.84rem; font-weight:600; color:{d_color}; font-variant-numeric:tabular-nums;">전일 대비 {delta:+.1f}</span>
      </div>
      <div style="font-size:0.82rem; color:#6e6e73; margin-bottom:2px;">{desc}</div>
      <div class="osc-track">
        <div class="osc-thumb" style="left:{val_num:.1f}%;"></div>
      </div>
      <div class="osc-scale">
        <span>{thresholds[0]}</span>
        <span>{thresholds[1]}</span>
        <span>{thresholds[2]}</span>
        <span>{thresholds[3]}</span>
        <span>{thresholds[4]}</span>
      </div>
    </div>
    """)


def render_agent_briefing_html(briefing: dict) -> str:
    tone_styles = {
        "opportunity": ("rgba(29, 143, 52, 0.12)", "#1d8f34"),
        "warning": ("rgba(215, 0, 21, 0.10)", "#d70015"),
        "info": ("rgba(0, 113, 227, 0.10)", "#0071e3"),
        "neutral": ("rgba(110, 110, 115, 0.12)", "#6e6e73"),
    }
    cards_html = []
    for sig in briefing["signals"]:
        bg, fg_c = tone_styles.get(sig["tone"], tone_styles["neutral"])
        cards_html.append(
            f'<div class="signal-item">'
            f'<span class="signal-tag" style="background:{bg}; color:{fg_c};">{sig["tag"]}</span><br/>'
            f'{sig["text"]}'
            f'</div>'
        )
    sc = _apple_color(briefing["stance_color"])
    return _compact_html(f"""
    <div class="agent-panel">
      <div class="agent-header">
        <div>
          <div style="font-size:0.76rem; color:#6e6e73; font-weight:600; letter-spacing:0.02em; text-transform:uppercase;">Market Summary</div>
          <div style="font-size:1.05rem; font-weight:600; color:#1d1d1f; margin-top:4px; line-height:1.45;">{briefing['summary']}</div>
        </div>
        <div class="agent-stance" style="background:{sc}14; color:{sc};">
          {briefing['stance']} · {briefing['score']}/100
        </div>
      </div>
      <div class="signal-grid">
        {"".join(cards_html)}
      </div>
    </div>
    """)


def render_drawdown_comparison_html(indices: list[dict]) -> str:
    """Render minimalist Apple-style Drawdown-from-High comparison card."""
    rows = []
    for i, idx in enumerate(indices):
        dd = idx["dd_ath_pct"]
        dd_label, raw_color = classify_drawdown(dd)
        dd_color = _apple_color(raw_color)
        bar_w = min(100.0, abs(dd) / 30.0 * 100.0)
        ath_d = idx["ath_date"].strftime("%Y.%m.%d")
        border_bottom = "border-bottom:1px solid rgba(0,0,0,0.06);" if i < len(indices) - 1 else ""
        rows.append(f"""
        <div style="padding:13px 0; {border_bottom}">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
              <span style="font-weight:700; color:#1d1d1f; font-size:0.95rem;">{idx['name']}</span>
              <span class="ticker-badge" style="margin-left:6px;">{idx['symbol']}</span>
              <span style="color:#6e6e73; font-size:0.8rem; margin-left:10px; font-variant-numeric:tabular-nums;">현재 {idx['price']:,.2f} · 고점 {idx['ath_price']:,.2f} ({ath_d})</span>
            </div>
            <div style="display:flex; align-items:center; gap:10px;">
              <span style="font-size:0.78rem; color:#6e6e73;">회복 <b style="color:#0071e3;">+{idx['recovery_ath_pct']:.1f}%</b></span>
              <span class="osc-badge" style="background:{dd_color}14; color:{dd_color};">{dd_label}</span>
              <span style="font-weight:700; font-size:1.02rem; color:{dd_color}; min-width:72px; text-align:right; font-variant-numeric:tabular-nums;">{dd:.2f}%</span>
            </div>
          </div>
          <div style="position:relative; height:7px; background:#e8e8ed; border-radius:999px; margin-top:9px; overflow:hidden;">
            <div style="width:{bar_w:.1f}%; height:100%; background:{dd_color}; border-radius:999px;"></div>
            <div style="position:absolute; left:33.3%; top:0; bottom:0; width:1.5px; background:rgba(201,106,0,0.65);"></div>
            <div style="position:absolute; left:66.6%; top:0; bottom:0; width:1.5px; background:rgba(215,0,21,0.65);"></div>
          </div>
        </div>
        """)
    return _compact_html(f"""
    <div class="glass-card" style="padding:18px 24px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:700; font-size:0.96rem; color:#1d1d1f;">주요 지수 고점 대비 낙폭</span>
        <span style="font-size:0.75rem; color:#86868b;">기준선: -10% 조정장 · -20% 약세장</span>
      </div>
      {"".join(rows)}
    </div>
    """)


def _slice_period(df: pd.DataFrame, lookback_days: int) -> pd.DataFrame:
    if lookback_days <= 0 or len(df) <= lookback_days:
        return df
    return df.tail(lookback_days)


def build_nasdaq_chart(
    idx: dict,
    lookback_days: int = 252,
    chart_style: str = "캔들 차트",
) -> go.Figure:
    """Build Apple Studio Light 3-row Plotly chart: Price+MA+ATH, RSI(14), MFI(14)."""
    sub = _slice_period(idx["df"], lookback_days)
    ath_price = idx["ath_price"]
    last_price = float(sub["Close"].iloc[-1])
    last_rsi = float(sub["RSI_14"].iloc[-1]) if pd.notna(sub["RSI_14"].iloc[-1]) else None
    last_mfi = float(sub["MFI_14"].iloc[-1]) if pd.notna(sub["MFI_14"].iloc[-1]) else None

    lows = [float(sub["Low"].min())]
    highs = [float(sub["High"].max()), float(ath_price)]
    if sub["MA_200"].notna().any():
        lows.append(float(sub["MA_200"].dropna().min()))
        highs.append(float(sub["MA_200"].dropna().max()))
    y_min, y_max = min(lows), max(highs)
    y_pad = max((y_max - y_min) * 0.08, 1.0)

    rsi_title = f"RSI (14) · 현재 {last_rsi:.1f}" if last_rsi is not None else "RSI (14)"
    mfi_title = f"MFI (14) · 현재 {last_mfi:.1f}" if last_mfi is not None else "MFI (14)"

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.075,
        row_heights=[0.52, 0.24, 0.24],
        subplot_titles=(
            f"{idx['name']} ({idx['symbol']}) · {last_price:,.2f} (고점 대비 {idx['dd_ath_pct']:.2f}%)",
            rsi_title,
            mfi_title,
        ),
    )

    if chart_style == "캔들 차트":
        fig.add_trace(
            go.Candlestick(
                x=sub.index,
                open=sub["Open"],
                high=sub["High"],
                low=sub["Low"],
                close=sub["Close"],
                name="주가",
                increasing_line_color="#1d8f34",
                increasing_fillcolor="#34c759",
                decreasing_line_color="#d70015",
                decreasing_fillcolor="#ff3b30",
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=sub.index,
                y=sub["Close"],
                name="종가",
                line=dict(color="#0071e3", width=2.4),
                hovertemplate="%{y:,.2f}<extra>종가</extra>",
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["MA_20"],
            name="20일선",
            line=dict(color="#86868b", width=1.2, dash="dot"),
            hovertemplate="%{y:,.2f}<extra>MA20</extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["MA_50"],
            name="50일선",
            line=dict(color="#5856d6", width=1.4),
            hovertemplate="%{y:,.2f}<extra>MA50</extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["MA_200"],
            name="200일선",
            line=dict(color="#ff9500", width=1.5, dash="dash"),
            hovertemplate="%{y:,.2f}<extra>MA200</extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_hline(
        y=ath_price,
        line_dash="dash",
        line_width=1.2,
        line_color="rgba(29, 29, 31, 0.35)",
        annotation_text=f" 최고점 {ath_price:,.0f} ({idx['dd_ath_pct']:.1f}%)",
        annotation_position="top left",
        annotation_font=dict(color="#6e6e73", size=11),
        row=1,
        col=1,
    )
    fig.add_hline(
        y=last_price,
        line_dash="dot",
        line_width=1.1,
        line_color="rgba(0, 113, 227, 0.55)",
        annotation_text=f" {last_price:,.0f} ",
        annotation_position="bottom right",
        annotation_font=dict(color="#ffffff", size=11),
        annotation_bgcolor="#0071e3",
        row=1,
        col=1,
    )

    # Row 2: RSI
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(52, 199, 89, 0.08)", line_width=0, row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255, 59, 48, 0.08)", line_width=0, row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_width=1, line_color="rgba(215, 0, 21, 0.45)", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_width=1, line_color="rgba(29, 143, 52, 0.45)", row=2, col=1)
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["RSI_14"],
            name="RSI(14)",
            line=dict(color="#5856d6", width=2.0),
            hovertemplate="%{y:.1f}<extra>RSI(14)</extra>",
        ),
        row=2,
        col=1,
    )

    # Row 3: MFI
    fig.add_hrect(y0=0, y1=20, fillcolor="rgba(52, 199, 89, 0.08)", line_width=0, row=3, col=1)
    fig.add_hrect(y0=80, y1=100, fillcolor="rgba(255, 59, 48, 0.08)", line_width=0, row=3, col=1)
    fig.add_hline(y=80, line_dash="dot", line_width=1, line_color="rgba(215, 0, 21, 0.45)", row=3, col=1)
    fig.add_hline(y=20, line_dash="dot", line_width=1, line_color="rgba(29, 143, 52, 0.45)", row=3, col=1)
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["MFI_14"],
            name="MFI(14)",
            line=dict(color="#007aff", width=2.0),
            hovertemplate="%{y:.1f}<extra>MFI(14)</extra>",
        ),
        row=3,
        col=1,
    )

    fig.update_yaxes(
        range=[y_min - y_pad, y_max + y_pad],
        tickformat=",.0f",
        side="right",
        automargin=True,
        gridcolor="rgba(0, 0, 0, 0.06)",
        tickfont=dict(color="#6e6e73", size=11),
        row=1,
        col=1,
    )
    fig.update_yaxes(
        range=[0, 100],
        tickvals=[0, 30, 50, 70, 100],
        side="right",
        automargin=True,
        gridcolor="rgba(0, 0, 0, 0.06)",
        tickfont=dict(color="#6e6e73", size=11),
        row=2,
        col=1,
    )
    fig.update_yaxes(
        range=[0, 100],
        tickvals=[0, 20, 50, 80, 100],
        side="right",
        automargin=True,
        gridcolor="rgba(0, 0, 0, 0.06)",
        tickfont=dict(color="#6e6e73", size=11),
        row=3,
        col=1,
    )
    x_span = max((sub.index[-1] - sub.index[0]).days, 10)
    x_left = sub.index[0] - pd.Timedelta(days=max(3, int(x_span * 0.03)))
    x_right = sub.index[-1] + pd.Timedelta(days=max(6, int(x_span * 0.06)))
    fig.update_xaxes(
        range=[x_left, x_right],
        automargin=True,
        gridcolor="rgba(0, 0, 0, 0.04)",
        tickfont=dict(color="#6e6e73", size=11),
        rangeslider_visible=False,
    )
    for ann in fig.layout.annotations:
        if ann.font is None or ann.font.color is None:
            ann.font = dict(color="#1d1d1f", size=13)

    fig.update_layout(
        height=740,
        margin=dict(l=38, r=68, t=72, b=28),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1d1d1f", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(255,255,255,0)",
            font=dict(color="#6e6e73", size=12),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#d2d2d7", font=dict(color="#1d1d1f", size=12)),
    )
    return fig


def build_sp500_drawdown_chart(
    sp: dict,
    lookback_days: int = 252,
    chart_style: str = "캔들 차트",
) -> go.Figure:
    """Build Apple Studio Light 2-row Plotly chart for S&P 500 price + Drawdown (%)."""
    sub = _slice_period(sp["df"], lookback_days)
    ath_price = sp["ath_price"]
    last_price = float(sub["Close"].iloc[-1])

    lows = [float(sub["Low"].min())]
    highs = [float(sub["High"].max()), float(ath_price)]
    if sub["MA_200"].notna().any():
        lows.append(float(sub["MA_200"].dropna().min()))
        highs.append(float(sub["MA_200"].dropna().max()))
    y_min, y_max = min(lows), max(highs)
    y_pad = max((y_max - y_min) * 0.08, 1.0)
    dd_min = min(-22.0, float(sub["Drawdown_Pct"].min()) - 3.0)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.09,
        row_heights=[0.62, 0.38],
        subplot_titles=(
            f"S&P 500 (^GSPC) · {last_price:,.2f} (고점 대비 {sp['dd_ath_pct']:.2f}%)",
            "고점 대비 낙폭 (Drawdown %)",
        ),
    )

    if chart_style == "캔들 차트":
        fig.add_trace(
            go.Candlestick(
                x=sub.index,
                open=sub["Open"],
                high=sub["High"],
                low=sub["Low"],
                close=sub["Close"],
                name="S&P 500",
                increasing_line_color="#1d8f34",
                increasing_fillcolor="#34c759",
                decreasing_line_color="#d70015",
                decreasing_fillcolor="#ff3b30",
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=sub.index,
                y=sub["Close"],
                name="S&P 500",
                line=dict(color="#1d1d1f", width=2.3),
                hovertemplate="%{y:,.2f}<extra>S&P 500</extra>",
            ),
            row=1,
            col=1,
        )
    fig.add_trace(
        go.Scatter(x=sub.index, y=sub["MA_50"], name="50일선", line=dict(color="#0071e3", width=1.4)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=sub.index, y=sub["MA_200"], name="200일선", line=dict(color="#ff9500", width=1.5, dash="dash")),
        row=1,
        col=1,
    )
    fig.add_hline(
        y=ath_price,
        line_dash="dash",
        line_width=1.2,
        line_color="rgba(29, 29, 31, 0.35)",
        annotation_text=f" 최고점 {ath_price:,.0f} ({sp['dd_ath_pct']:.1f}%)",
        annotation_position="top left",
        annotation_font=dict(color="#6e6e73", size=11),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["Drawdown_Pct"],
            name="낙폭(%)",
            line=dict(color="#d70015", width=1.9),
            fill="tozeroy",
            fillcolor="rgba(215, 0, 21, 0.08)",
            hovertemplate="%{y:.2f}%<extra>Drawdown</extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=-10, line_dash="dot", line_width=1.1, line_color="#c96a00", annotation_text=" -10% 조정", annotation_font=dict(color="#c96a00", size=11), row=2, col=1)
    fig.add_hline(y=-20, line_dash="dot", line_width=1.1, line_color="#d70015", annotation_text=" -20% 약세", annotation_font=dict(color="#d70015", size=11), row=2, col=1)

    x_span = max((sub.index[-1] - sub.index[0]).days, 10)
    x_left = sub.index[0] - pd.Timedelta(days=max(3, int(x_span * 0.03)))
    x_right = sub.index[-1] + pd.Timedelta(days=max(6, int(x_span * 0.06)))
    fig.update_yaxes(range=[y_min - y_pad, y_max + y_pad], tickformat=",.0f", side="right", automargin=True, gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#6e6e73", size=11), row=1, col=1)
    fig.update_yaxes(range=[dd_min, 1.5], ticksuffix="%", side="right", automargin=True, gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#6e6e73", size=11), row=2, col=1)
    fig.update_xaxes(range=[x_left, x_right], automargin=True, gridcolor="rgba(0,0,0,0.04)", tickfont=dict(color="#6e6e73", size=11), rangeslider_visible=False)
    for ann in fig.layout.annotations:
        if ann.font is None or ann.font.color is None:
            ann.font = dict(color="#1d1d1f", size=13)

    fig.update_layout(
        height=560,
        margin=dict(l=38, r=68, t=72, b=28),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1d1d1f", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0.0, bgcolor="rgba(255,255,255,0)", font=dict(color="#6e6e73", size=12)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#d2d2d7", font=dict(color="#1d1d1f", size=12)),
    )
    return fig


def build_fear_greed_history_chart(fg: dict) -> go.Figure | None:
    """Build Apple Studio Light 1-year CNN Fear & Greed Index trend chart."""
    hist = fg.get("history")
    if hist is None or hist.empty:
        return None

    fg_color = _apple_color(fg["color"])
    fig = go.Figure()
    fig.add_hrect(y0=0, y1=25, fillcolor="rgba(255, 59, 48, 0.06)", line_width=0, annotation_text=" 극단적 공포", annotation_position="bottom left", annotation_font=dict(color="#d70015", size=11))
    fig.add_hrect(y0=75, y1=100, fillcolor="rgba(52, 199, 89, 0.06)", line_width=0, annotation_text=" 극단적 탐욕", annotation_position="top left", annotation_font=dict(color="#1d8f34", size=11))

    fig.add_trace(
        go.Scatter(
            x=hist["date"],
            y=hist["score"],
            name="Fear & Greed",
            line=dict(color="#0071e3", width=2.2),
            hovertemplate="%{y:.1f}점<extra>공포·탐욕</extra>",
        )
    )
    fig.add_hline(y=50, line_dash="dot", line_color="rgba(0,0,0,0.18)")
    fig.add_hline(
        y=fg["score"],
        line_dash="dot",
        line_width=1.1,
        line_color=fg_color,
        annotation_text=f" {fg['score']:.1f} ({fg['kr_label']}) ",
        annotation_position="bottom right",
        annotation_font=dict(color="#ffffff", size=11),
        annotation_bgcolor=fg_color,
    )

    x_span = max((hist["date"].iloc[-1] - hist["date"].iloc[0]).days, 10)
    x_left = hist["date"].iloc[0] - pd.Timedelta(days=max(3, int(x_span * 0.03)))
    x_right = hist["date"].iloc[-1] + pd.Timedelta(days=max(6, int(x_span * 0.06)))
    fig.update_yaxes(range=[0, 100], tickvals=[0, 25, 50, 75, 100], side="right", automargin=True, gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#6e6e73", size=11))
    fig.update_xaxes(range=[x_left, x_right], automargin=True, gridcolor="rgba(0,0,0,0.04)", tickfont=dict(color="#6e6e73", size=11), rangeslider_visible=False)
    fig.update_layout(
        title=dict(text="CNN 공포·탐욕 지수 1년 추이", font=dict(size=14, color="#1d1d1f")),
        height=390,
        margin=dict(l=38, r=68, t=54, b=28),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1d1d1f", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#d2d2d7", font=dict(color="#1d1d1f", size=12)),
        showlegend=False,
    )
    return fig
