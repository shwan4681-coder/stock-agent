"""Seoul Apartment Purchase, LTV/DSR Loan & Peak-Discount Target Simulator."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _compact(html: str) -> str:
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


def calc_monthly_payment_man(loan_eok: float, annual_rate_pct: float, years: int) -> float:
    """Equal principal & interest monthly payment in 10k KRW (만원)."""
    if loan_eok <= 0:
        return 0.0
    principal_man = loan_eok * 10_000.0
    r = (annual_rate_pct / 100.0) / 12.0
    n = years * 12
    if r <= 0:
        return principal_man / n
    return principal_man * (r * (1.0 + r) ** n) / ((1.0 + r) ** n - 1.0)


def max_loan_by_dsr_eok(
    annual_income_man: float,
    annual_rate_pct: float,
    years: int,
    dsr_limit_pct: float = 40.0,
    stress_add_pct: float = 1.2,
) -> float:
    """Max mortgage loan (eok KRW) under Korean Stress DSR 40% limit."""
    eff_rate = annual_rate_pct + stress_add_pct
    max_monthly_man = (annual_income_man * (dsr_limit_pct / 100.0)) / 12.0
    r = (eff_rate / 100.0) / 12.0
    n = years * 12
    if r <= 0:
        return (max_monthly_man * n) / 10_000.0
    factor = (r * (1.0 + r) ** n) / ((1.0 + r) ** n - 1.0)
    return (max_monthly_man / factor) / 10_000.0


def build_apt_buy_plan(
    cash_eok: float,
    annual_income_man: float,
    rate_pct: float,
    years: int,
    ltv_pct: float,
    stress_add_pct: float,
    apt_name: str,
    current_eok: float,
    peak_eok: float,
    jeonse_eok: float,
) -> dict:
    """Build LTV/DSR affordability + -5%..-25% bargain target table for a target apartment."""
    dsr_max_loan = max_loan_by_dsr_eok(annual_income_man, rate_pct, years, 40.0, stress_add_pct)
    # Max affordable price under both LTV and DSR:
    # Price <= cash / (1 - LTV) AND Price <= cash + dsr_max_loan
    max_price_ltv = cash_eok / max(0.05, 1.0 - ltv_pct / 100.0)
    max_price_dsr = cash_eok + dsr_max_loan
    max_affordable_eok = min(max_price_ltv, max_price_dsr)
    binding_rule = "DSR 한도 제약" if max_price_dsr < max_price_ltv else f"LTV {ltv_pct:.0f}% 제약"

    # Current purchase breakdown (approx 3.5% acquisition tax/fees included in cash note)
    needed_loan_now = max(0.0, current_eok - cash_eok)
    max_loan_on_apt = min(current_eok * (ltv_pct / 100.0), dsr_max_loan)
    shortfall_now = max(0.0, needed_loan_now - max_loan_on_apt)
    monthly_now_man = calc_monthly_payment_man(min(needed_loan_now, max_loan_on_apt), rate_pct, years)
    gap_need_now = max(0.0, current_eok - jeonse_eok)

    cur_dd_pct = ((current_eok / peak_eok) - 1.0) * 100.0 if peak_eok > 0 else 0.0

    rows = []
    for lvl in [0, 5, 10, 15, 20, 25]:
        target_px = peak_eok * (1.0 - lvl / 100.0)
        loan_req = max(0.0, target_px - cash_eok)
        loan_cap = min(target_px * (ltv_pct / 100.0), dsr_max_loan)
        can_buy = loan_req <= loan_cap + 1e-6
        monthly_man = calc_monthly_payment_man(loan_req, rate_pct, years)
        gap_eok = max(0.0, target_px - jeonse_eok)
        rec_profit_eok = peak_eok - target_px
        rec_roi_pct = ((peak_eok / target_px) - 1.0) * 100.0 if target_px > 0 else 0.0

        if lvl == 0:
            lbl = "전고점 (0%)"
        else:
            lbl = f"고점 -{lvl}%"

        if cur_dd_pct <= -lvl:
            status = "reached"
            st_lbl = "도달 완료"
        elif can_buy:
            status = "buyable"
            st_lbl = "내 예산 매수 가능"
        else:
            status = "short"
            st_lbl = f"자금 {loan_req - loan_cap:.1f}억 부족"

        rows.append(
            {
                "lvl": lvl,
                "label": lbl,
                "target_eok": target_px,
                "loan_req_eok": loan_req,
                "monthly_man": monthly_man,
                "gap_eok": gap_eok,
                "rec_profit_eok": rec_profit_eok,
                "rec_roi_pct": rec_roi_pct,
                "can_buy": can_buy,
                "status": status,
                "status_label": st_lbl,
            }
        )

    return {
        "apt_name": apt_name,
        "cash_eok": cash_eok,
        "current_eok": current_eok,
        "peak_eok": peak_eok,
        "jeonse_eok": jeonse_eok,
        "cur_dd_pct": cur_dd_pct,
        "dsr_max_loan_eok": dsr_max_loan,
        "max_affordable_eok": max_affordable_eok,
        "binding_rule": binding_rule,
        "needed_loan_now": needed_loan_now,
        "shortfall_now": shortfall_now,
        "monthly_now_man": monthly_now_man,
        "gap_need_now": gap_need_now,
        "rows": rows,
        "df": pd.DataFrame(rows),
    }


def render_loan_summary_cards(plan: dict) -> str:
    buy_ok = plan["shortfall_now"] <= 0.01
    ok_col = "#15803d" if buy_ok else "#b91c1c"
    ok_txt = "현재가 실거주 매수 가능" if buy_ok else f"현금/대출 {plan['shortfall_now']:.1f}억 부족"
    gap_ok = plan["cash_eok"] >= plan["gap_need_now"]
    gap_note = "전세 끼고 매수 가능" if gap_ok else f"갭 자금 {plan['gap_need_now'] - plan['cash_eok']:.1f}억 추가 필요"

    return _compact(f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px; margin:12px 0 18px 0;">
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>내 예산 최대 매수가</span><span class="ticker-badge">{plan['binding_rule']}</span></div>
        <div style="font-size:1.78rem; font-weight:700; color:#1d4ed8; margin:7px 0 3px 0; font-variant-numeric:tabular-nums;">{plan['max_affordable_eok']:.1f}억</div>
        <div style="font-size:0.77rem; color:#57534e;">보유 현금 {plan['cash_eok']:.1f}억 + 스트레스 DSR 최대 대출 {plan['dsr_max_loan_eok']:.1f}억</div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>타겟 단지 현재가 진단</span><span class="ticker-badge" style="color:{ok_col}; background:{ok_col}16;">{plan['apt_name']}</span></div>
        <div style="font-size:1.55rem; font-weight:700; color:{ok_col}; margin:7px 0 3px 0; font-variant-numeric:tabular-nums;">{plan['current_eok']:.1f}억 ({plan['cur_dd_pct']:.1f}%)</div>
        <div style="font-size:0.77rem; color:#57534e;">{ok_txt}</div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>예상 월 원리금 상환</span><span class="ticker-badge">월 고정비</span></div>
        <div style="font-size:1.78rem; font-weight:700; color:#1c1917; margin:7px 0 3px 0; font-variant-numeric:tabular-nums;">월 {plan['monthly_now_man']:,.0f}만</div>
        <div style="font-size:0.77rem; color:#57534e;">대출 {min(plan['needed_loan_now'], plan['dsr_max_loan_eok']):.1f}억 원리금균등 상환 기준</div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>전세 끼고(갭) 필요 자금</span><span class="ticker-badge">전세 {plan['jeonse_eok']:.1f}억</span></div>
        <div style="font-size:1.78rem; font-weight:700; color:#15803d; margin:7px 0 3px 0; font-variant-numeric:tabular-nums;">{plan['gap_need_now']:.1f}억</div>
        <div style="font-size:0.77rem; color:#57534e;">{gap_note} (취득세·중개보수 별도)</div>
      </div>
    </div>
    """)


def render_loan_table_html(plan: dict) -> str:
    rows = []
    for r in plan["rows"]:
        if r["can_buy"]:
            bg, fg = "rgba(21,128,61,0.10)", "#15803d"
            icon = "✅ "
        else:
            bg, fg = "rgba(185,28,28,0.10)", "#b91c1c"
            icon = "⏳ "
        row_bg = "rgba(29,78,216,0.04)" if r["status"] == "reached" else "transparent"
        rows.append(
            f'<tr style="background:{row_bg}; border-bottom:1px solid rgba(28,25,23,0.07);">'
            f'<td style="padding:12px 10px; font-weight:700; color:#1c1917;">{r["label"]}</td>'
            f'<td style="padding:12px 8px; text-align:right; font-weight:700; color:#1c1917; font-variant-numeric:tabular-nums;">{r["target_eok"]:.2f}억</td>'
            f'<td style="padding:12px 8px; text-align:center;"><span style="display:inline-block; padding:3px 10px; border-radius:999px; font-size:0.74rem; font-weight:600; background:{bg}; color:{fg};">{icon}{r["status_label"]}</span></td>'
            f'<td style="padding:12px 8px; text-align:right; color:#1d4ed8; font-weight:700; font-variant-numeric:tabular-nums;">{r["loan_req_eok"]:.2f}억</td>'
            f'<td style="padding:12px 8px; text-align:right; color:#57534e; font-variant-numeric:tabular-nums;">월 {r["monthly_man"]:,.0f}만원</td>'
            f'<td style="padding:12px 8px; text-align:right; color:#1c1917; font-variant-numeric:tabular-nums;">{r["gap_eok"]:.2f}억</td>'
            f'<td style="padding:12px 8px; text-align:right; font-weight:700; color:#15803d; font-variant-numeric:tabular-nums;">+{r["rec_profit_eok"]:.1f}억 (+{r["rec_roi_pct"]:.1f}%)</td>'
            f'</tr>'
        )
    return _compact(f"""
    <div class="glass-card" style="padding:20px 22px; overflow-x:auto;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:700; font-size:0.98rem; color:#1c1917;">🎯 {plan['apt_name']} 고점 대비 급매 타겟별 자금 · 대출 시뮬레이션</span>
        <span style="font-size:0.75rem; color:#78716c;">전고점 {plan['peak_eok']:.1f}억 · 현재 {plan['current_eok']:.1f}억 기준</span>
      </div>
      <table style="width:100%; border-collapse:collapse; font-size:0.84rem;">
        <thead>
          <tr style="border-bottom:1px solid rgba(28,25,23,0.12); color:#78716c; font-size:0.74rem; font-weight:600;">
            <th style="padding:9px 10px; text-align:left;">조정 구간</th>
            <th style="padding:9px 8px; text-align:right;">목표 매수가</th>
            <th style="padding:9px 8px; text-align:center;">예산 판정</th>
            <th style="padding:9px 8px; text-align:right;">필요 주담대</th>
            <th style="padding:9px 8px; text-align:right;">월 원리금</th>
            <th style="padding:9px 8px; text-align:right;">전세 갭 자금</th>
            <th style="padding:9px 8px; text-align:right;">전고점 회복 차익</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
    """)


def build_loan_chart(plan: dict) -> go.Figure:
    df = plan["df"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=df["label"],
            y=[min(plan["cash_eok"], t) for t in df["target_eok"]],
            name="보유 현금 투입 (억)",
            marker_color="#18181b",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df["label"],
            y=df["loan_req_eok"],
            name="필요 주담대 (억)",
            marker_color=["#15803d" if ok else "#b91c1c" for ok in df["can_buy"]],
            text=[f"대출 {v:.1f}억" for v in df["loan_req_eok"]],
            textposition="outside",
            textfont=dict(size=10, color="#1c1917"),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["label"],
            y=df["monthly_man"],
            name="월 원리금 (만원)",
            mode="lines+markers",
            line=dict(color="#1d4ed8", width=2.4),
            marker=dict(size=7, color="#1d4ed8"),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title=dict(text=f"{plan['apt_name']} 조정 구간별 자금 조달 구조 & 월 상환액", font=dict(size=14, color="#1c1917")),
        barmode="stack",
        height=410,
        margin=dict(l=52, r=60, t=68, b=36),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)"),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="자금 조달 (억원)", ticksuffix="억", secondary_y=False, gridcolor="rgba(0,0,0,0.06)")
    fig.update_yaxes(title_text="월 원리금 (만원)", ticksuffix="만", secondary_y=True, showgrid=False)
    return fig
