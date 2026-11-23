"""Sleek custom HTML/CSS cards, SVG Fear & Greed gauge, and Plotly charts."""

from __future__ import annotations

import math
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from agent_analyzer import classify_drawdown, classify_mfi, classify_rsi


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

:root {
  --bg-main: #070b14;
  --bg-card: rgba(15, 23, 42, 0.78);
  --bg-card-hover: rgba(22, 33, 58, 0.9);
  --border-subtle: rgba(148, 163, 184, 0.14);
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --accent-cyan: #38bdf8;
  --accent-green: #10b981;
  --accent-red: #ef4444;
  --accent-amber: #f59e0b;
}

html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
}

.stApp {
  background:
    radial-gradient(circle at 12% 8%, rgba(56, 189, 248, 0.11), transparent 36%),
    radial-gradient(circle at 88% 12%, rgba(99, 102, 241, 0.10), transparent 38%),
    radial-gradient(circle at 50% 95%, rgba(16, 185, 129, 0.06), transparent 40%),
    #070b14;
  color: var(--text-primary);
}

.block-container {
  padding-top: 1.4rem !important;
  padding-bottom: 2.5rem !important;
  max-width: 1440px !important;
}

/* Hero banner */
.hero-wrap {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.65));
  border: 1px solid rgba(56, 189, 248, 0.22);
  border-radius: 20px;
  padding: 22px 28px;
  margin-bottom: 20px;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}
.hero-title {
  font-size: 1.65rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  background: linear-gradient(90deg, #f8fafc 0%, #7dd3fc 55%, #a78bfa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}
.hero-sub {
  color: #94a3b8;
  font-size: 0.9rem;
  margin-top: 4px;
}
.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.35);
  color: #6ee7b7;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}
.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 10px #10b981;
  animation: pulse 1.8s infinite;
}
@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.45; transform: scale(1.25); }
  100% { opacity: 1; transform: scale(1); }
}

/* Glass cards */
.glass-card {
  background: var(--bg-card);
  backdrop-filter: blur(14px);
  border: 1px solid var(--border-subtle);
  border-radius: 18px;
  padding: 20px 22px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.28);
  transition: border-color 0.2s ease, transform 0.2s ease;
  height: 100%;
}
.glass-card:hover {
  border-color: rgba(56, 189, 248, 0.35);
}

.card-kicker {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94a3b8;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ticker-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.12);
  color: #cbd5e1;
}
.card-price {
  font-family: 'JetBrains Mono', monospace;
  font-size: 2.05rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 8px 0 4px 0;
  letter-spacing: -0.02em;
}
.delta-up { color: #10b981; font-weight: 600; font-family: 'JetBrains Mono', monospace; font-size: 0.92rem; }
.delta-down { color: #ef4444; font-weight: 600; font-family: 'JetBrains Mono', monospace; font-size: 0.92rem; }

/* Drawdown callout inside card */
.dd-box {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(2, 6, 23, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.12);
}
.dd-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 0.84rem;
  margin-bottom: 6px;
}
.dd-val {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 1.05rem;
}
.bar-track {
  width: 100%;
  height: 7px;
  background: rgba(148, 163, 184, 0.16);
  border-radius: 999px;
  overflow: hidden;
  margin: 6px 0;
}
.bar-fill {
  height: 100%;
  border-radius: 999px;
}
.meta-sub {
  font-size: 0.76rem;
  color: #94a3b8;
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
}

/* RSI / MFI gauge bar */
.osc-card {
  background: rgba(15, 23, 42, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 16px;
  padding: 16px 18px;
}
.osc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.osc-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: #cbd5e1;
  letter-spacing: 0.04em;
}
.osc-badge {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 999px;
}
.osc-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.9rem;
  font-weight: 800;
  margin: 6px 0 2px 0;
}
.osc-track {
  position: relative;
  height: 10px;
  border-radius: 999px;
  margin: 12px 0 6px 0;
  background: linear-gradient(90deg, #10b981 0%, #10b981 25%, #38bdf8 35%, #eab308 50%, #f97316 70%, #ef4444 100%);
}
.osc-thumb {
  position: absolute;
  top: -4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #f8fafc;
  border: 3px solid #0f172a;
  box-shadow: 0 0 10px rgba(248, 250, 252, 0.8);
  transform: translateX(-50%);
}
.osc-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

/* Agent panel */
.agent-panel {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.72));
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 18px;
  padding: 20px 24px;
  margin-bottom: 18px;
}
.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.agent-stance {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 0.88rem;
}
.signal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.signal-item {
  background: rgba(2, 6, 23, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  padding: 11px 14px;
  font-size: 0.84rem;
  line-height: 1.5;
  color: #e2e8f0;
}
.signal-tag {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  margin-bottom: 5px;
}

/* Section title */
.section-title {
  font-size: 1.12rem;
  font-weight: 700;
  color: #f1f5f9;
  margin: 18px 0 12px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Hide default streamlit chrome clutter */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Sleek mobile-first top navigation tab bar */
.stTabs [data-baseweb="tab-list"] {
  gap: 8px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(56, 189, 248, 0.28);
  border-radius: 14px;
  padding: 6px;
  margin-bottom: 14px;
  display: flex;
  width: 100%;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.stTabs [data-baseweb="tab"] {
  flex: 1 1 0%;
  justify-content: center;
  height: 44px;
  border-radius: 10px;
  padding: 0 10px !important;
  color: #cbd5e1 !important;
  font-weight: 700 !important;
  font-size: 0.92rem !important;
  white-space: nowrap;
  background: transparent;
  border: 1px solid transparent;
  transition: all 0.18s ease;
}
.stTabs [data-baseweb="tab"]:hover {
  color: #f8fafc !important;
  background: rgba(56, 189, 248, 0.10);
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.24), rgba(99, 102, 241, 0.24)) !important;
  border: 1px solid rgba(56, 189, 248, 0.65) !important;
  color: #f8fafc !important;
  box-shadow: 0 4px 14px rgba(56, 189, 248, 0.2);
}
.stTabs [data-baseweb="tab-highlight"] {
  display: none !important;
}
.stTabs [data-baseweb="tab-border"] {
  display: none !important;
}

/* Mobile responsiveness */
@media (max-width: 640px) {
  .block-container {
    padding-top: 0.65rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
  }
  .stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    padding: 4px;
    margin-bottom: 10px;
  }
  .stTabs [data-baseweb="tab"] {
    height: 40px;
    padding: 0 4px !important;
    font-size: 0.78rem !important;
  }
  .hero-wrap {
    padding: 14px 16px;
    margin-bottom: 12px;
  }
  .hero-title {
    font-size: 1.3rem;
  }
}
</style>
"""


def _compact_html(html: str) -> str:
    """Remove blank lines and leading indentation so Markdown never turns HTML into code blocks."""
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


def render_hero_html(updated_kst: str, vix_price: float | None, vix_chg: float) -> str:
    vix_str = f"VIX {vix_price:.2f} ({vix_chg:+.1f}%)" if vix_price is not None else "VIX N/A"
    return _compact_html(f"""
    <div class="hero-wrap">
      <div>
        <div class="hero-title">US Market Stock Agent</div>
        <div class="hero-sub">S&amp;P 500 · NASDAQ (RSI &amp; MFI) · CNN 공포·탐욕 지수 · 고점 대비 낙폭 실시간 모니터링</div>
      </div>
      <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
        <div class="live-pill" style="background:rgba(56,189,248,0.12); border-color:rgba(56,189,248,0.35); color:#7dd3fc;">
          {vix_str}
        </div>
        <div class="live-pill">
          <span class="pulse-dot"></span>
          LIVE · {updated_kst}
        </div>
      </div>
    </div>
    """)


def render_index_kpi_card(idx: dict) -> str:
    """Render sleek glassmorphism card for S&P 500 or NASDAQ with Drawdown from High."""
    up = idx["change"] >= 0
    delta_cls = "delta-up" if up else "delta-down"
    arrow = "▲" if up else "▼"
    dd_label, dd_color = classify_drawdown(idx["dd_ath_pct"])

    # Fill bar represents drawdown magnitude on 0% to -35% scale
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
          <span style="color:#cbd5e1; font-weight:600;">고점 대비 낙폭 (ATH)</span>
          <span class="dd-val" style="color:{dd_color};">{idx['dd_ath_pct']:.2f}%</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width:{dd_mag:.1f}%; background:{dd_color};"></div>
        </div>
        <div class="meta-sub">
          <span>최고점 {idx['ath_price']:,.2f} ({ath_date_str})</span>
          <span style="color:{dd_color}; font-weight:600;">{dd_label}</span>
        </div>
        <div class="meta-sub" style="margin-top:4px; padding-top:6px; border-top:1px solid rgba(148,163,184,0.1);">
          <span>52주 고점 대비: <b style="color:#e2e8f0;">{idx['dd_52w_pct']:.2f}%</b></span>
          <span>고점 회복 필요: <b style="color:#38bdf8;">+{idx['recovery_ath_pct']:.1f}%</b></span>
        </div>
      </div>
      <div class="meta-sub" style="margin-top:12px;">
        <span>RSI(14): <b style="color:#f8fafc;">{rsi_val}</b></span>
        <span>MFI(14): <b style="color:#f8fafc;">{mfi_val}</b></span>
      </div>
    </div>
    """)


def render_fear_greed_card(fg: dict) -> str:
    """Render sleek glassmorphism card with custom SVG semicircle dial for CNN Fear & Greed."""
    score = max(0.0, min(100.0, float(fg["score"])))
    # Angle from 180 deg (left=0) to 0 deg (right=100)
    angle_rad = math.radians(180.0 - (score / 100.0) * 180.0)
    cx, cy, r = 130.0, 106.0, 82.0
    nx = cx + (r - 12) * math.cos(angle_rad)
    ny = cy - (r - 12) * math.sin(angle_rad)

    diff_1d = score - fg["previous_close"]
    diff_color = "#10b981" if diff_1d >= 0 else "#ef4444"

    # Compute exact arc endpoints for 5 segments on (cx=130, cy=106, r=82)
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
        <span class="ticker-badge">CNN F&amp;G</span>
      </div>
      <div style="display:flex; flex-direction:column; align-items:center; margin-top:4px;">
        <svg viewBox="0 0 260 120" width="100%" style="max-width:255px; overflow:visible;">
          <path d="{arc_path(0, 24.5)}" fill="none" stroke="#ef4444" stroke-width="15" opacity="0.92"/>
          <path d="{arc_path(25.5, 44.5)}" fill="none" stroke="#f97316" stroke-width="15" opacity="0.92"/>
          <path d="{arc_path(45.5, 54.5)}" fill="none" stroke="#eab308" stroke-width="15" opacity="0.92"/>
          <path d="{arc_path(55.5, 74.5)}" fill="none" stroke="#22c55e" stroke-width="15" opacity="0.92"/>
          <path d="{arc_path(75.5, 100)}" fill="none" stroke="#10b981" stroke-width="15" opacity="0.92"/>
          <line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#f8fafc" stroke-width="3.5" stroke-linecap="round"/>
          <circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="#f8fafc"/>
          <circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="#0f172a"/>
          <text x="38" y="118" text-anchor="middle" fill="#64748b" font-size="10" font-family="JetBrains Mono, monospace">0</text>
          <text x="130" y="14" text-anchor="middle" fill="#64748b" font-size="10" font-family="JetBrains Mono, monospace">50</text>
          <text x="222" y="118" text-anchor="middle" fill="#64748b" font-size="10" font-family="JetBrains Mono, monospace">100</text>
        </svg>
        <div style="display:flex; align-items:baseline; gap:10px; margin-top:-4px;">
          <span style="font-family:'JetBrains Mono', monospace; font-size:2.05rem; font-weight:800; color:#f8fafc; line-height:1;">{score:.1f}</span>
          <span style="font-size:0.82rem; font-weight:700; color:{fg['color']}; background:{fg['color']}20; border:1px solid {fg['color']}55; padding:3px 10px; border-radius:999px;">{fg['kr_label']} · {fg['rating'].upper()}</span>
        </div>
      </div>
      <div class="dd-box" style="margin-top:10px;">
        <div class="meta-sub" style="margin-top:0;">
          <span>전일 종가: <b style="color:#e2e8f0;">{fg['previous_close']:.1f}</b> <span style="color:{diff_color};">({diff_1d:+.1f})</span></span>
          <span>1주 전: <b style="color:#e2e8f0;">{fg['previous_1_week']:.1f}</b></span>
        </div>
        <div class="meta-sub" style="margin-top:6px;">
          <span>1개월 전: <b style="color:#e2e8f0;">{fg['previous_1_month']:.1f}</b></span>
          <span>1년 전: <b style="color:#e2e8f0;">{fg['previous_1_year']:.1f}</b></span>
        </div>
      </div>
    </div>
    """)


def render_oscillator_card(kind: str, value: float | None, delta: float, index_name: str) -> str:
    """Render RSI(14) or MFI(14) sleek visual gauge card."""
    if kind == "RSI":
        label, color, desc = classify_rsi(value)
        title = f"{index_name} · RSI (14)"
        thresholds = ("0", "30 과매도", "50", "70 과매수", "100")
    else:
        label, color, desc = classify_mfi(value)
        title = f"{index_name} · MFI (14 · 자금흐름)"
        thresholds = ("0", "20 과매도", "50", "80 과매수", "100")

    val_num = max(0.0, min(100.0, float(value))) if value is not None else 50.0
    val_str = f"{value:.1f}" if value is not None else "N/A"
    d_color = "#10b981" if delta >= 0 else "#ef4444"

    return _compact_html(f"""
    <div class="osc-card">
      <div class="osc-header">
        <span class="osc-title">{title}</span>
        <span class="osc-badge" style="background:{color}22; color:{color}; border:1px solid {color}55;">{label}</span>
      </div>
      <div style="display:flex; align-items:baseline; gap:10px;">
        <div class="osc-val" style="color:{color};">{val_str}</div>
        <span style="font-family:'JetBrains Mono', monospace; font-size:0.84rem; color:{d_color};">전일 대비 {delta:+.1f}</span>
      </div>
      <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:4px;">{desc}</div>
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
        "opportunity": ("rgba(16,185,129,0.16)", "#34d399"),
        "warning": ("rgba(239,68,68,0.16)", "#f87171"),
        "info": ("rgba(56,189,248,0.16)", "#7dd3fc"),
        "neutral": ("rgba(148,163,184,0.16)", "#cbd5e1"),
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
    sc = briefing["stance_color"]
    return _compact_html(f"""
    <div class="agent-panel">
      <div class="agent-header">
        <div>
          <div style="font-size:0.78rem; color:#38bdf8; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;">AI QUANT AGENT BRIEFING</div>
          <div style="font-size:1.05rem; font-weight:700; color:#f8fafc; margin-top:3px;">{briefing['summary']}</div>
        </div>
        <div class="agent-stance" style="background:{sc}22; color:{sc}; border:1px solid {sc}66;">
          ● {briefing['stance']} ({briefing['score']}/100)
        </div>
      </div>
      <div class="signal-grid">
        {"".join(cards_html)}
      </div>
    </div>
    """)


def render_drawdown_comparison_html(indices: list[dict]) -> str:
    """Render side-by-side HTML Drawdown-from-High tracker for S&P 500, NASDAQ Composite, NASDAQ 100."""
    rows = []
    for idx in indices:
        dd = idx["dd_ath_pct"]
        dd_label, dd_color = classify_drawdown(dd)
        bar_w = min(100.0, abs(dd) / 30.0 * 100.0)
        ath_d = idx["ath_date"].strftime("%Y-%m-%d")
        rows.append(f"""
        <div style="padding:12px 0; border-bottom:1px solid rgba(148,163,184,0.1);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
              <span style="font-weight:700; color:#f8fafc; font-size:0.95rem;">{idx['name']}</span>
              <span class="ticker-badge" style="margin-left:6px;">{idx['symbol']}</span>
              <span style="color:#94a3b8; font-size:0.8rem; margin-left:10px;">현재 {idx['price']:,.2f} / 고점 {idx['ath_price']:,.2f} ({ath_d})</span>
            </div>
            <div style="display:flex; align-items:center; gap:12px;">
              <span style="font-size:0.78rem; color:#94a3b8;">회복 필요 <b style="color:#38bdf8;">+{idx['recovery_ath_pct']:.1f}%</b></span>
              <span class="osc-badge" style="background:{dd_color}22; color:{dd_color}; border:1px solid {dd_color}55;">{dd_label}</span>
              <span style="font-family:'JetBrains Mono', monospace; font-weight:800; font-size:1.05rem; color:{dd_color}; min-width:78px; text-align:right;">{dd:.2f}%</span>
            </div>
          </div>
          <div style="position:relative; height:9px; background:rgba(148,163,184,0.14); border-radius:999px; margin-top:8px; overflow:hidden;">
            <div style="width:{bar_w:.1f}%; height:100%; background:linear-gradient(90deg, {dd_color}99, {dd_color}); border-radius:999px;"></div>
            <div style="position:absolute; left:33.3%; top:0; bottom:0; width:1.5px; background:rgba(245,158,11,0.75);"></div>
            <div style="position:absolute; left:66.6%; top:0; bottom:0; width:1.5px; background:rgba(239,68,68,0.85);"></div>
          </div>
        </div>
        """)
    return _compact_html(f"""
    <div class="glass-card" style="margin-top:6px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:700; font-size:0.95rem; color:#f8fafc;">주요 지수 고점 대비 낙폭(Drawdown) 비교</span>
        <span style="font-size:0.75rem; color:#94a3b8;">기준선: <span style="color:#f59e0b;">│ -10% 조정장</span> · <span style="color:#ef4444;">│ -20% 약세장</span> (막대 최대 -30%)</span>
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
    chart_style: str = "라인 차트",
) -> go.Figure:
    """Build high-contrast 3-row TradingView-style Plotly chart: Price+MA+ATH, RSI(14), MFI(14)."""
    sub = _slice_period(idx["df"], lookback_days)
    ath_price = idx["ath_price"]
    last_price = float(sub["Close"].iloc[-1])
    last_rsi = float(sub["RSI_14"].iloc[-1]) if pd.notna(sub["RSI_14"].iloc[-1]) else None
    last_mfi = float(sub["MFI_14"].iloc[-1]) if pd.notna(sub["MFI_14"].iloc[-1]) else None

    # Tight Y-axis range so price action fills the panel cleanly (never squished to 0!)
    lows = [float(sub["Low"].min())]
    highs = [float(sub["High"].max()), float(ath_price)]
    if sub["MA_200"].notna().any():
        lows.append(float(sub["MA_200"].dropna().min()))
        highs.append(float(sub["MA_200"].dropna().max()))
    y_min = min(lows)
    y_max = max(highs)
    y_pad = max((y_max - y_min) * 0.08, 1.0)

    rsi_title = f"RSI (14) — 현재 {last_rsi:.1f}  |  30 이하 과매도 · 70 이상 과매수" if last_rsi is not None else "RSI (14)"
    mfi_title = f"MFI (14 · 자금흐름) — 현재 {last_mfi:.1f}  |  20 이하 과매도 · 80 이상 과매수" if last_mfi is not None else "MFI (14)"

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.50, 0.25, 0.25],
        subplot_titles=(
            f"{idx['name']} ({idx['symbol']}) — 현재 {last_price:,.2f} (고점 대비 {idx['dd_ath_pct']:.2f}%)",
            rsi_title,
            mfi_title,
        ),
    )

    # Row 1: Candlestick or High-Contrast Line + MA20 / MA50 / MA200 + ATH line
    if chart_style == "캔들 차트":
        fig.add_trace(
            go.Candlestick(
                x=sub.index,
                open=sub["Open"],
                high=sub["High"],
                low=sub["Low"],
                close=sub["Close"],
                name="주가",
                increasing_line_color="#22c55e",
                increasing_fillcolor="#22c55e",
                decreasing_line_color="#ef4444",
                decreasing_fillcolor="#ef4444",
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
                line=dict(color="#38bdf8", width=2.8),
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
            line=dict(color="#fbbf24", width=1.5, dash="dot"),
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
            line=dict(color="#c084fc", width=1.6),
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
            line=dict(color="#fb7185", width=1.8, dash="dash"),
            hovertemplate="%{y:,.2f}<extra>MA200</extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_hline(
        y=ath_price,
        line_dash="dash",
        line_width=1.5,
        line_color="rgba(248, 250, 252, 0.72)",
        annotation_text=f"  최고점 {ath_price:,.0f} ({idx['dd_ath_pct']:.1f}%)",
        annotation_position="top left",
        annotation_font=dict(color="#f8fafc", size=12),
        annotation_bgcolor="rgba(15, 23, 42, 0.85)",
        row=1,
        col=1,
    )
    # Highlight latest price level
    fig.add_hline(
        y=last_price,
        line_dash="dot",
        line_width=1.2,
        line_color="rgba(56, 189, 248, 0.75)",
        annotation_text=f" 현재 {last_price:,.0f} ",
        annotation_position="bottom right",
        annotation_font=dict(color="#070b14", size=11),
        annotation_bgcolor="#38bdf8",
        row=1,
        col=1,
    )

    # Row 2: RSI (14)
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(16, 185, 129, 0.16)", line_width=0, row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239, 68, 68, 0.16)", line_width=0, row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_width=1.2, line_color="#f87171", row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_width=1.0, line_color="rgba(148,163,184,0.45)", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_width=1.2, line_color="#34d399", row=2, col=1)
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["RSI_14"],
            name="RSI(14)",
            line=dict(color="#e879f9", width=2.4),
            hovertemplate="%{y:.1f}<extra>RSI(14)</extra>",
        ),
        row=2,
        col=1,
    )

    # Row 3: MFI (14)
    fig.add_hrect(y0=0, y1=20, fillcolor="rgba(16, 185, 129, 0.16)", line_width=0, row=3, col=1)
    fig.add_hrect(y0=80, y1=100, fillcolor="rgba(239, 68, 68, 0.16)", line_width=0, row=3, col=1)
    fig.add_hline(y=80, line_dash="dash", line_width=1.2, line_color="#f87171", row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_width=1.0, line_color="rgba(148,163,184,0.45)", row=3, col=1)
    fig.add_hline(y=20, line_dash="dash", line_width=1.2, line_color="#34d399", row=3, col=1)
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["MFI_14"],
            name="MFI(14)",
            line=dict(color="#2dd4bf", width=2.4),
            hovertemplate="%{y:.1f}<extra>MFI(14)</extra>",
        ),
        row=3,
        col=1,
    )

    # Axis styling — TradingView style right-side ticks, crisp contrast
    fig.update_yaxes(
        range=[y_min - y_pad, y_max + y_pad],
        tickformat=",.0f",
        side="right",
        gridcolor="rgba(148, 163, 184, 0.18)",
        tickfont=dict(color="#e2e8f0", size=12),
        row=1,
        col=1,
    )
    fig.update_yaxes(
        range=[0, 100],
        tickvals=[0, 30, 50, 70, 100],
        side="right",
        gridcolor="rgba(148, 163, 184, 0.16)",
        tickfont=dict(color="#e2e8f0", size=11),
        row=2,
        col=1,
    )
    fig.update_yaxes(
        range=[0, 100],
        tickvals=[0, 20, 50, 80, 100],
        side="right",
        gridcolor="rgba(148, 163, 184, 0.16)",
        tickfont=dict(color="#e2e8f0", size=11),
        row=3,
        col=1,
    )
    fig.update_xaxes(
        gridcolor="rgba(148, 163, 184, 0.12)",
        tickfont=dict(color="#cbd5e1", size=11),
        rangeslider_visible=False,
    )
    # Brighten subplot titles
    for ann in fig.layout.annotations:
        if ann.font is None or ann.font.color is None:
            ann.font = dict(color="#f8fafc", size=13.5)

    fig.update_layout(
        height=780,
        margin=dict(l=16, r=20, t=72, b=20),
        paper_bgcolor="#0b1220",
        plot_bgcolor="#111b2e",
        font=dict(color="#f1f5f9", family="Inter, sans-serif", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(15, 23, 42, 0.85)",
            bordercolor="rgba(148, 163, 184, 0.25)",
            borderwidth=1,
            font=dict(color="#f1f5f9", size=12),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#0f172a",
            bordercolor="#38bdf8",
            font=dict(color="#f8fafc", size=12),
        ),
    )
    return fig


def build_sp500_drawdown_chart(sp: dict, lookback_days: int = 252) -> go.Figure:
    """Build high-contrast 2-row interactive Plotly chart for S&P 500 price + Drawdown (%)."""
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
            f"S&P 500 (^GSPC) — 현재 {last_price:,.2f} (고점 대비 {sp['dd_ath_pct']:.2f}%)",
            "고점 대비 낙폭 (Drawdown %) — -10% 조정장 · -20% 약세장",
        ),
    )

    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["Close"],
            name="S&P 500",
            line=dict(color="#34d399", width=2.8),
            hovertemplate="%{y:,.2f}<extra>S&P 500</extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["MA_50"],
            name="50일선",
            line=dict(color="#fbbf24", width=1.6),
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
            line=dict(color="#fb7185", width=1.8, dash="dash"),
            hovertemplate="%{y:,.2f}<extra>MA200</extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_hline(
        y=ath_price,
        line_dash="dash",
        line_width=1.5,
        line_color="rgba(248, 250, 252, 0.72)",
        annotation_text=f"  최고점 {ath_price:,.0f} ({sp['dd_ath_pct']:.1f}%)",
        annotation_position="top left",
        annotation_font=dict(color="#f8fafc", size=12),
        annotation_bgcolor="rgba(15, 23, 42, 0.85)",
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=sub.index,
            y=sub["Drawdown_Pct"],
            name="고점 대비 낙폭(%)",
            line=dict(color="#f87171", width=2.2),
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.22)",
            hovertemplate="%{y:.2f}%<extra>Drawdown</extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(
        y=-10,
        line_dash="dash",
        line_width=1.3,
        line_color="#fbbf24",
        annotation_text=" -10% 조정장",
        annotation_font=dict(color="#fbbf24", size=11),
        row=2,
        col=1,
    )
    fig.add_hline(
        y=-20,
        line_dash="dash",
        line_width=1.3,
        line_color="#ef4444",
        annotation_text=" -20% 약세장",
        annotation_font=dict(color="#f87171", size=11),
        row=2,
        col=1,
    )

    fig.update_yaxes(
        range=[y_min - y_pad, y_max + y_pad],
        tickformat=",.0f",
        side="right",
        gridcolor="rgba(148, 163, 184, 0.18)",
        tickfont=dict(color="#e2e8f0", size=12),
        row=1,
        col=1,
    )
    fig.update_yaxes(
        range=[dd_min, 1.5],
        ticksuffix="%",
        side="right",
        gridcolor="rgba(148, 163, 184, 0.16)",
        tickfont=dict(color="#e2e8f0", size=11),
        row=2,
        col=1,
    )
    fig.update_xaxes(
        gridcolor="rgba(148, 163, 184, 0.12)",
        tickfont=dict(color="#cbd5e1", size=11),
    )
    for ann in fig.layout.annotations:
        if ann.font is None or ann.font.color is None:
            ann.font = dict(color="#f8fafc", size=13.5)

    fig.update_layout(
        height=580,
        margin=dict(l=16, r=20, t=72, b=20),
        paper_bgcolor="#0b1220",
        plot_bgcolor="#111b2e",
        font=dict(color="#f1f5f9", family="Inter, sans-serif", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(15, 23, 42, 0.85)",
            bordercolor="rgba(148, 163, 184, 0.25)",
            borderwidth=1,
            font=dict(color="#f1f5f9", size=12),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#0f172a",
            bordercolor="#34d399",
            font=dict(color="#f8fafc", size=12),
        ),
    )
    return fig


def build_fear_greed_history_chart(fg: dict) -> go.Figure | None:
    """Build high-contrast 1-year CNN Fear & Greed Index trend chart."""
    hist = fg.get("history")
    if hist is None or hist.empty:
        return None

    fig = go.Figure()
    fig.add_hrect(
        y0=0,
        y1=25,
        fillcolor="rgba(239,68,68,0.16)",
        line_width=0,
        annotation_text="  극단적 공포 (0~25)",
        annotation_position="bottom left",
        annotation_font=dict(color="#fca5a5", size=11),
    )
    fig.add_hrect(y0=25, y1=45, fillcolor="rgba(249,115,22,0.08)", line_width=0)
    fig.add_hrect(y0=55, y1=75, fillcolor="rgba(34,197,94,0.08)", line_width=0)
    fig.add_hrect(
        y0=75,
        y1=100,
        fillcolor="rgba(16,185,129,0.16)",
        line_width=0,
        annotation_text="  극단적 탐욕 (75~100)",
        annotation_position="top left",
        annotation_font=dict(color="#6ee7b7", size=11),
    )

    fig.add_trace(
        go.Scatter(
            x=hist["date"],
            y=hist["score"],
            name="Fear & Greed",
            line=dict(color="#38bdf8", width=2.6),
            hovertemplate="%{y:.1f}점<extra>공포·탐욕</extra>",
        )
    )
    fig.add_hline(y=50, line_dash="dot", line_color="rgba(226,232,240,0.5)")
    fig.add_hline(
        y=fg["score"],
        line_dash="dot",
        line_width=1.2,
        line_color=fg["color"],
        annotation_text=f" 현재 {fg['score']:.1f} ({fg['kr_label']}) ",
        annotation_position="bottom right",
        annotation_font=dict(color="#070b14", size=11),
        annotation_bgcolor=fg["color"],
    )

    fig.update_yaxes(
        range=[0, 100],
        tickvals=[0, 25, 45, 55, 75, 100],
        side="right",
        gridcolor="rgba(148, 163, 184, 0.16)",
        tickfont=dict(color="#e2e8f0", size=12),
    )
    fig.update_xaxes(
        gridcolor="rgba(148, 163, 184, 0.12)",
        tickfont=dict(color="#cbd5e1", size=11),
    )
    fig.update_layout(
        title=dict(text="CNN 공포·탐욕 지수 1년 추이", font=dict(size=14, color="#f8fafc")),
        height=400,
        margin=dict(l=16, r=20, t=52, b=20),
        paper_bgcolor="#0b1220",
        plot_bgcolor="#111b2e",
        font=dict(color="#f1f5f9", family="Inter, sans-serif", size=12),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#0f172a",
            bordercolor="#38bdf8",
            font=dict(color="#f8fafc", size=12),
        ),
        showlegend=False,
    )
    return fig
