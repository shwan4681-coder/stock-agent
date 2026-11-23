"""Drawdown-based Dollar-Cost Averaging (DCA) split-buy calculator & UI."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui_components import _compact_html


STRATEGIES: dict[str, dict] = {
    "피라미드형 (하락할수록 비중 확대 · 추천)": {
        "desc": "얕은 조정에는 적게, 깊은 하락(-20% ~ -30%)에 더 많이 실어 평단가를 효과적으로 낮춥니다.",
        "mode": "pyramid",
    },
    "균등 분할형 (전 구간 동일 금액)": {
        "desc": "모든 -5% 하락 구간마다 똑같은 금액으로 기계적 분할 매수합니다.",
        "mode": "equal",
    },
    "저점 집중형 (공포 구간 공격 매수)": {
        "desc": "-5% ~ -10%는 소액 정찰병만 보내고 -20% 이하 급락장에 자금을 집중합니다.",
        "mode": "aggressive",
    },
}


def compute_weights(levels: list[int], mode: str) -> list[float]:
    """Return normalized percentage weights (summing to 100.0) for each drawdown level."""
    n = len(levels)
    if n == 0:
        return []
    if mode == "equal":
        return [100.0 / n] * n

    if mode == "pyramid":
        # Classic clean weights for 6 levels (-5..-30): 5, 10, 15, 20, 25, 25
        if n == 6:
            return [5.0, 10.0, 15.0, 20.0, 25.0, 25.0]
        raw = [i + 1 for i in range(n)]
        total = sum(raw)
        return [r / total * 100.0 for r in raw]

    if mode == "aggressive":
        if n == 6:
            return [5.0, 5.0, 10.0, 20.0, 30.0, 30.0]
        raw = [(i + 1) ** 2 for i in range(n)]
        total = sum(raw)
        return [r / total * 100.0 for r in raw]

    return [100.0 / n] * n


def build_dca_plan(
    seed_amount: float,
    ath_price: float,
    current_price: float,
    step_pct: int = 5,
    max_dd_pct: int = 30,
    strategy_mode: str = "pyramid",
    custom_weights: list[float] | None = None,
) -> dict:
    """Compute step-by-step split-buy schedule from -step_pct down to -max_dd_pct."""
    levels = list(range(step_pct, max_dd_pct + 1, step_pct))
    if custom_weights is not None and len(custom_weights) == len(levels) and sum(custom_weights) > 0:
        total_w = sum(custom_weights)
        weights = [w / total_w * 100.0 for w in custom_weights]
    else:
        weights = compute_weights(levels, strategy_mode)

    current_dd_pct = ((current_price / ath_price) - 1.0) * 100.0 if ath_price > 0 else 0.0

    rows = []
    cum_invested = 0.0
    cum_units = 0.0
    reached_invested = 0.0
    reached_units = 0.0
    next_target_found = False

    for lvl, w in zip(levels, weights):
        target_dd = -float(lvl)
        target_price = ath_price * (1.0 - lvl / 100.0)
        buy_amount = seed_amount * (w / 100.0)
        units = buy_amount / target_price if target_price > 0 else 0.0

        cum_invested += buy_amount
        cum_units += units
        cum_avg_price = cum_invested / cum_units if cum_units > 0 else target_price
        cum_avg_dd = ((cum_avg_price / ath_price) - 1.0) * 100.0 if ath_price > 0 else 0.0
        recovery_roi_pct = ((ath_price / cum_avg_price) - 1.0) * 100.0 if cum_avg_price > 0 else 0.0

        if current_dd_pct <= target_dd:
            status = "reached"
            status_label = "도달 (매수 구간)"
            reached_invested += buy_amount
            reached_units += units
            gap_from_now_pct = 0.0
        elif not next_target_found:
            status = "next"
            gap_from_now_pct = ((target_price / current_price) - 1.0) * 100.0 if current_price > 0 else 0.0
            status_label = f"다음 목표 ({gap_from_now_pct:+.1f}%)"
            next_target_found = True
        else:
            status = "pending"
            gap_from_now_pct = ((target_price / current_price) - 1.0) * 100.0 if current_price > 0 else 0.0
            status_label = f"대기 ({gap_from_now_pct:+.1f}%)"

        rows.append(
            {
                "level_pct": target_dd,
                "level_label": f"-{lvl}%",
                "target_price": target_price,
                "weight_pct": w,
                "buy_amount": buy_amount,
                "cum_invested": cum_invested,
                "cum_avg_price": cum_avg_price,
                "cum_avg_dd_pct": cum_avg_dd,
                "recovery_roi_pct": recovery_roi_pct,
                "status": status,
                "status_label": status_label,
                "gap_from_now_pct": gap_from_now_pct,
            }
        )

    final_avg_price = cum_invested / cum_units if cum_units > 0 else ath_price
    final_avg_dd = ((final_avg_price / ath_price) - 1.0) * 100.0 if ath_price > 0 else 0.0
    final_recovery_roi = ((ath_price / final_avg_price) - 1.0) * 100.0 if final_avg_price > 0 else 0.0
    final_recovery_profit = seed_amount * (final_recovery_roi / 100.0)

    reached_ratio = (reached_invested / seed_amount * 100.0) if seed_amount > 0 else 0.0
    remaining_cash = max(0.0, seed_amount - reached_invested)
    reached_avg_price = (reached_invested / reached_units) if reached_units > 0 else None

    return {
        "rows": rows,
        "df": pd.DataFrame(rows),
        "seed_amount": seed_amount,
        "ath_price": ath_price,
        "current_price": current_price,
        "current_dd_pct": current_dd_pct,
        "reached_invested": reached_invested,
        "reached_ratio_pct": reached_ratio,
        "remaining_cash": remaining_cash,
        "reached_avg_price": reached_avg_price,
        "final_avg_price": final_avg_price,
        "final_avg_dd_pct": final_avg_dd,
        "final_recovery_roi_pct": final_recovery_roi,
        "final_recovery_profit": final_recovery_profit,
    }


def format_money(amount: float, currency: str) -> str:
    if currency == "KRW":
        if abs(amount) >= 100_000_000:
            eok = amount / 100_000_000
            return f"₩{amount:,.0f} ({eok:.2f}억)"
        if abs(amount) >= 10_000:
            man = amount / 10_000
            return f"₩{amount:,.0f} ({man:,.0f}만)"
        return f"₩{amount:,.0f}"
    return f"${amount:,.2f}"


def format_money_short(amount: float, currency: str) -> str:
    if currency == "KRW":
        return f"₩{amount:,.0f}"
    return f"${amount:,.0f}"


def render_dca_summary_cards(plan: dict, currency: str, asset_label: str) -> str:
    """Render 4 sleek KPI summary cards for the split-buy plan."""
    reached_avg_str = (
        f"도달 구간 평단 {plan['reached_avg_price']:,.2f}"
        if plan["reached_avg_price"] is not None
        else "아직 -5% 구간 미도달 (전액 현금 대기)"
    )

    return _compact_html(f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px; margin:12px 0 18px 0;">
      <div class="glass-card" style="padding:16px 18px;">
        <div class="card-kicker"><span>기준 지수 현재 낙폭</span><span class="ticker-badge">{asset_label}</span></div>
        <div style="font-family:'JetBrains Mono', monospace; font-size:1.75rem; font-weight:800; color:#f59e0b; margin:8px 0 4px 0;">{plan['current_dd_pct']:.2f}%</div>
        <div style="font-size:0.78rem; color:#94a3b8;">현재 {plan['current_price']:,.2f} / 고점 {plan['ath_price']:,.2f}</div>
      </div>
      <div class="glass-card" style="padding:16px 18px;">
        <div class="card-kicker"><span>현재 시점 누적 투입액</span><span class="ticker-badge">{plan['reached_ratio_pct']:.0f}% 투입</span></div>
        <div style="font-family:'JetBrains Mono', monospace; font-size:1.55rem; font-weight:800; color:#38bdf8; margin:8px 0 4px 0;">{format_money_short(plan['reached_invested'], currency)}</div>
        <div style="font-size:0.78rem; color:#94a3b8;">잔여 현금: <b style="color:#e2e8f0;">{format_money_short(plan['remaining_cash'], currency)}</b></div>
      </div>
      <div class="glass-card" style="padding:16px 18px;">
        <div class="card-kicker"><span>전액 체결 시 최종 평단가</span><span class="ticker-badge">고점 대비 {plan['final_avg_dd_pct']:.1f}%</span></div>
        <div style="font-family:'JetBrains Mono', monospace; font-size:1.75rem; font-weight:800; color:#c084fc; margin:8px 0 4px 0;">{plan['final_avg_price']:,.2f}</div>
        <div style="font-size:0.78rem; color:#94a3b8;">{reached_avg_str}</div>
      </div>
      <div class="glass-card" style="padding:16px 18px;">
        <div class="card-kicker"><span>전고점 회복 시 예상 수익</span><span class="ticker-badge" style="color:#34d399;">+{plan['final_recovery_roi_pct']:.1f}%</span></div>
        <div style="font-family:'JetBrains Mono', monospace; font-size:1.55rem; font-weight:800; color:#10b981; margin:8px 0 4px 0;">+{format_money_short(plan['final_recovery_profit'], currency)}</div>
        <div style="font-size:0.78rem; color:#94a3b8;">총 시드 {format_money_short(plan['seed_amount'], currency)} 전액 체결 가정</div>
      </div>
    </div>
    """)


def render_dca_table_html(plan: dict, currency: str) -> str:
    """Render sleek dark HTML split-buy schedule table."""
    row_htmls = []
    for r in plan["rows"]:
        if r["status"] == "reached":
            badge_bg, badge_fg, badge_bd = "rgba(16,185,129,0.18)", "#34d399", "rgba(16,185,129,0.5)"
            row_bg = "rgba(16, 185, 129, 0.06)"
            icon = "✅ "
        elif r["status"] == "next":
            badge_bg, badge_fg, badge_bd = "rgba(56,189,248,0.22)", "#7dd3fc", "rgba(56,189,248,0.65)"
            row_bg = "rgba(56, 189, 248, 0.09)"
            icon = "🎯 "
        else:
            badge_bg, badge_fg, badge_bd = "rgba(148,163,184,0.14)", "#94a3b8", "rgba(148,163,184,0.3)"
            row_bg = "transparent"
            icon = "⏳ "

        row_htmls.append(
            f'<tr style="background:{row_bg}; border-bottom:1px solid rgba(148,163,184,0.1);">'
            f'<td style="padding:13px 12px; font-family:\'JetBrains Mono\',monospace; font-weight:800; color:#f8fafc;">고점 대비 {r["level_label"]}</td>'
            f'<td style="padding:13px 12px; font-family:\'JetBrains Mono\',monospace; color:#e2e8f0; text-align:right;">{r["target_price"]:,.2f}</td>'
            f'<td style="padding:13px 12px; text-align:center;"><span style="display:inline-block; padding:3px 10px; border-radius:999px; font-size:0.75rem; font-weight:700; background:{badge_bg}; color:{badge_fg}; border:1px solid {badge_bd};">{icon}{r["status_label"]}</span></td>'
            f'<td style="padding:13px 12px; font-family:\'JetBrains Mono\',monospace; color:#cbd5e1; text-align:right;">{r["weight_pct"]:.1f}%</td>'
            f'<td style="padding:13px 12px; font-family:\'JetBrains Mono\',monospace; font-weight:800; font-size:0.98rem; color:#38bdf8; text-align:right;">{format_money(r["buy_amount"], currency)}</td>'
            f'<td style="padding:13px 12px; font-family:\'JetBrains Mono\',monospace; color:#cbd5e1; text-align:right;">{format_money_short(r["cum_invested"], currency)}</td>'
            f'<td style="padding:13px 12px; font-family:\'JetBrains Mono\',monospace; color:#c084fc; text-align:right;">{r["cum_avg_price"]:,.2f} <span style="font-size:0.75rem; color:#94a3b8;">({r["cum_avg_dd_pct"]:.1f}%)</span></td>'
            f'<td style="padding:13px 12px; font-family:\'JetBrains Mono\',monospace; font-weight:700; color:#10b981; text-align:right;">+{r["recovery_roi_pct"]:.1f}%</td>'
            f'</tr>'
        )

    return _compact_html(f"""
    <div class="glass-card" style="padding:18px 20px; overflow-x:auto;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:700; font-size:1rem; color:#f8fafc;">구간별 분할 매수 실행표</span>
        <span style="font-size:0.78rem; color:#94a3b8;">✅ 도달 완료 구간 · 🎯 다음 매수 대기 구간 · ⏳ 추가 하락 대비 현금</span>
      </div>
      <table style="width:100%; border-collapse:collapse; font-size:0.86rem;">
        <thead>
          <tr style="border-bottom:1px solid rgba(148,163,184,0.22); color:#94a3b8; font-size:0.76rem; text-transform:uppercase; letter-spacing:0.04em;">
            <th style="padding:10px 12px; text-align:left;">낙폭 구간</th>
            <th style="padding:10px 12px; text-align:right;">목표 지수</th>
            <th style="padding:10px 12px; text-align:center;">현재 상태</th>
            <th style="padding:10px 12px; text-align:right;">비중</th>
            <th style="padding:10px 12px; text-align:right;">회차 매수 금액</th>
            <th style="padding:10px 12px; text-align:right;">누적 투자금</th>
            <th style="padding:10px 12px; text-align:right;">예상 누적 평단가</th>
            <th style="padding:10px 12px; text-align:right;">고점 회복 수익률</th>
          </tr>
        </thead>
        <tbody>
          {"".join(row_htmls)}
        </tbody>
      </table>
    </div>
    """)


def build_dca_chart(plan: dict, currency: str) -> go.Figure:
    """Build high-contrast dual-axis chart: Buy amount bars per drawdown level + Avg cost curve."""
    df = plan["df"]
    bar_colors = [
        "#10b981" if s == "reached" else "#38bdf8" if s == "next" else "#475569"
        for s in df["status"]
    ]
    unit_label = "원" if currency == "KRW" else "USD"
    text_labels = [format_money_short(v, currency) for v in df["buy_amount"]]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=df["level_label"],
            y=df["buy_amount"],
            name=f"구간 매수 금액 ({unit_label})",
            marker=dict(color=bar_colors, line=dict(color="rgba(248,250,252,0.25)", width=1)),
            text=text_labels,
            textposition="outside",
            textfont=dict(color="#f8fafc", size=11),
            hovertemplate="구간 %{x}<br>매수액: %{text}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["level_label"],
            y=df["cum_avg_price"],
            name="예상 누적 평단가",
            mode="lines+markers",
            line=dict(color="#e879f9", width=2.8),
            marker=dict(size=8, color="#e879f9", line=dict(color="#0f172a", width=2)),
            hovertemplate="누적 평단가: %{y:,.2f}<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=df["level_label"],
            y=df["target_price"],
            name="구간 목표 지수",
            mode="lines+markers",
            line=dict(color="#fbbf24", width=1.8, dash="dot"),
            marker=dict(size=6, color="#fbbf24"),
            hovertemplate="목표 지수: %{y:,.2f}<extra></extra>",
        ),
        secondary_y=True,
    )

    max_buy = float(df["buy_amount"].max()) if len(df) else 1.0
    fig.update_yaxes(
        title_text=f"회차 매수 금액 ({unit_label})",
        range=[0, max_buy * 1.25],
        gridcolor="rgba(148, 163, 184, 0.16)",
        tickfont=dict(color="#e2e8f0", size=11),
        title_font=dict(color="#94a3b8", size=12),
        secondary_y=False,
    )
    p_min = float(df["target_price"].min()) * 0.96
    p_max = float(plan["ath_price"]) * 1.03
    fig.update_yaxes(
        title_text="지수 / 예상 평단가",
        range=[p_min, p_max],
        tickformat=",.0f",
        gridcolor="rgba(148, 163, 184, 0.08)",
        tickfont=dict(color="#e2e8f0", size=11),
        title_font=dict(color="#94a3b8", size=12),
        secondary_y=True,
    )
    fig.update_xaxes(
        title_text="고점 대비 낙폭 구간 (초록=도달 · 하늘=다음목표 · 회색=대기)",
        tickfont=dict(color="#f8fafc", size=12),
        title_font=dict(color="#94a3b8", size=12),
    )

    fig.update_layout(
        title=dict(text="구간별 분할 매수 금액 & 누적 평단가 하락 효과", font=dict(size=14, color="#f8fafc")),
        height=430,
        margin=dict(l=16, r=20, t=72, b=36),
        paper_bgcolor="#0b1220",
        plot_bgcolor="#111b2e",
        font=dict(color="#f1f5f9", family="Inter, sans-serif", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(15, 23, 42, 0.85)",
            bordercolor="rgba(148, 163, 184, 0.25)",
            borderwidth=1,
            font=dict(color="#f1f5f9", size=12),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#0f172a", bordercolor="#38bdf8", font=dict(color="#f8fafc", size=12)),
    )
    return fig
