"""US Stock Market Historical Corrections & Crashes (S&P 500 & NASDAQ Drawdown + Recovery Time)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ui_components import _compact_html


# Historical US major corrections & bear markets (peak-to-trough max drawdown & trough-to-new-ATH recovery)
CRASH_EVENTS: list[dict] = [
    {
        "era": "2025",
        "name": "관세 · 무역전쟁 쇼크",
        "period": "2025.02 ~ 2025.04",
        "tier": "약세·급락",
        "sp_dd": -18.9,
        "sp_rec_months": 2.7,
        "sp_rec_label": "약 2.7개월",
        "nq_dd": -24.3,
        "nq_rec_months": 2.7,
        "nq_rec_label": "약 2.7개월",
        "cause": "전면적 상호관세 발표 충격 → 관세 유예 협상 및 빅테크 실적 반등으로 초고속 V자 회복",
    },
    {
        "era": "2022",
        "name": "인플레이션 · 고금리 긴축장",
        "period": "2022.01 ~ 2022.10",
        "tier": "약세장",
        "sp_dd": -25.4,
        "sp_rec_months": 15.0,
        "sp_rec_label": "약 1년 3개월",
        "nq_dd": -36.4,
        "nq_rec_months": 16.0,
        "nq_rec_label": "약 1년 4개월",
        "cause": "연준 40년 만의 초고속 금리인상(0%→5.25%) 및 러-우 전쟁 에너지 쇼크",
    },
    {
        "era": "2020",
        "name": "코로나19 팬데믹 쇼크",
        "period": "2020.02 ~ 2020.03",
        "tier": "대폭락",
        "sp_dd": -33.9,
        "sp_rec_months": 5.0,
        "sp_rec_label": "약 5개월",
        "nq_dd": -30.1,
        "nq_rec_months": 2.5,
        "nq_rec_label": "약 2.5개월",
        "cause": "글로벌 봉쇄로 33일 만에 폭락 → 연준 무제한 양적완화·재정부양으로 사상 최단기 회복",
    },
    {
        "era": "2018",
        "name": "미-중 무역분쟁 · 연준 긴축",
        "period": "2018.09 ~ 2018.12",
        "tier": "약세·조정",
        "sp_dd": -19.8,
        "sp_rec_months": 4.0,
        "sp_rec_label": "약 4개월",
        "nq_dd": -23.6,
        "nq_rec_months": 4.0,
        "nq_rec_label": "약 4개월",
        "cause": "연준 매파적 금리인상 + 미중 관세 충돌 → 2019년 초 연준 피벗(완화 전환) 직후 반등",
    },
    {
        "era": "2015",
        "name": "중국 위안화 쇼크 · 유가 급락",
        "period": "2015.05 ~ 2016.02",
        "tier": "조정장",
        "sp_dd": -14.2,
        "sp_rec_months": 5.0,
        "sp_rec_label": "약 5개월",
        "nq_dd": -18.2,
        "nq_rec_months": 5.0,
        "nq_rec_label": "약 5개월",
        "cause": "중국 경기 둔화·위안화 절하 및 WTI 유가 $26대 폭락에 따른 신흥국·에너지 신용 불안",
    },
    {
        "era": "2011",
        "name": "미국 신용등급 강등 · 유럽위기",
        "period": "2011.04 ~ 2011.10",
        "tier": "조정장",
        "sp_dd": -19.4,
        "sp_rec_months": 5.0,
        "sp_rec_label": "약 5개월",
        "nq_dd": -18.7,
        "nq_rec_months": 4.0,
        "nq_rec_label": "약 4개월",
        "cause": "S&P의 미국 국가신용등급 사상 첫 강등(AAA→AA+) 및 그리스·남유럽 재정위기 확산",
    },
    {
        "era": "2008",
        "name": "글로벌 금융위기 (서브프라임)",
        "period": "2007.10 ~ 2009.03",
        "tier": "대폭락",
        "sp_dd": -56.8,
        "sp_rec_months": 49.0,
        "sp_rec_label": "약 4년 1개월",
        "nq_dd": -55.6,
        "nq_rec_months": 24.0,
        "nq_rec_label": "약 2년 (07고점)",
        "cause": "미국 주택 버블 붕괴 및 리먼 브라더스 파산으로 글로벌 금융시스템 붕괴 위기",
    },
    {
        "era": "2000",
        "name": "닷컴 버블 붕괴",
        "period": "2000.03 ~ 2002.10",
        "tier": "대폭락",
        "sp_dd": -49.1,
        "sp_rec_months": 55.0,
        "sp_rec_label": "약 4년 7개월",
        "nq_dd": -78.0,
        "nq_rec_months": 150.0,
        "nq_rec_label": "약 12년 6개월",
        "cause": "실적 없는 인터넷주 극단적 거품(PER 100배+) 붕괴 + 9.11 테러·회계 스캔들 겹침",
    },
    {
        "era": "1990",
        "name": "걸프전 · 저축대부조합 침체",
        "period": "1990.07 ~ 1990.10",
        "tier": "약세·조정",
        "sp_dd": -19.9,
        "sp_rec_months": 4.0,
        "sp_rec_label": "약 4개월",
        "nq_dd": -31.1,
        "nq_rec_months": 5.0,
        "nq_rec_label": "약 5개월",
        "cause": "이라크의 쿠웨이트 침공으로 유가 급등 및 단기 경기침체 → 전쟁 조기 종결로 신속 반등",
    },
    {
        "era": "1987",
        "name": "블랙 먼데이 (Black Monday)",
        "period": "1987.08 ~ 1987.12",
        "tier": "대폭락",
        "sp_dd": -33.5,
        "sp_rec_months": 20.0,
        "sp_rec_label": "약 1년 8개월",
        "nq_dd": -35.9,
        "nq_rec_months": 22.0,
        "nq_rec_label": "약 1년 10개월",
        "cause": "프로그램 매매 연쇄 투매로 하루 만에 다우 -22.6% 폭락 (실물 경기침체 없이 2년 내 회복)",
    },
    {
        "era": "1973",
        "name": "1차 오일쇼크 · 스태그플레이션",
        "period": "1973.01 ~ 1974.10",
        "tier": "대폭락",
        "sp_dd": -48.2,
        "sp_rec_months": 69.0,
        "sp_rec_label": "약 5년 9개월",
        "nq_dd": -59.9,
        "nq_rec_months": 46.0,
        "nq_rec_label": "약 3년 10개월",
        "cause": "중동 석유 금수조치로 유가 4배 폭등 + 극심한 스태그플레이션과 워터게이트 정치 위기",
    },
]


def render_history_summary_cards(sp_now_dd: float, nq_now_dd: float) -> str:
    """Render 4 luxury summary KPI cards comparing current drawdown against US market history."""
    sp_avg = float(np.mean([e["sp_dd"] for e in CRASH_EVENTS]))
    nq_avg = float(np.mean([e["nq_dd"] for e in CRASH_EVENTS]))
    mild_events = [e for e in CRASH_EVENTS if e["sp_dd"] > -26.0]
    mild_rec_avg = float(np.mean([e["sp_rec_months"] for e in mild_events]))
    severe_events = [e for e in CRASH_EVENTS if e["sp_dd"] <= -30.0]
    severe_rec_med = float(np.median([e["sp_rec_months"] for e in severe_events]))

    # Find closest historical event to today's NASDAQ drawdown
    closest = min(CRASH_EVENTS, key=lambda e: abs(e["nq_dd"] - nq_now_dd))

    return _compact_html(f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px; margin:10px 0 18px 0;">
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>현재 실시간 낙폭</span><span class="ticker-badge">TODAY</span></div>
        <div style="font-size:1.55rem; font-weight:700; color:#b45309; margin:8px 0 4px 0; letter-spacing:-0.03em; font-variant-numeric:tabular-nums;">S&amp;P {sp_now_dd:.1f}% · 나스닥 {nq_now_dd:.1f}%</div>
        <div style="font-size:0.77rem; color:#57534e;">가장 유사한 과거: <b style="color:#1c1917;">{closest['era']} {closest['name']}</b></div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>역대 11대 사건 평균 낙폭</span><span class="ticker-badge">1973~2025</span></div>
        <div style="font-size:1.55rem; font-weight:700; color:#b91c1c; margin:8px 0 4px 0; letter-spacing:-0.03em; font-variant-numeric:tabular-nums;">S&amp;P {sp_avg:.1f}% · 나스닥 {nq_avg:.1f}%</div>
        <div style="font-size:0.77rem; color:#57534e;">대형 위기 포함 전체 평균 최대 하락률</div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>조정~일반 약세장 평균 회복</span><span class="ticker-badge" style="color:#15803d; background:rgba(21,128,61,0.1);">-14% ~ -25%</span></div>
        <div style="font-size:1.75rem; font-weight:700; color:#15803d; margin:8px 0 4px 0; letter-spacing:-0.03em; font-variant-numeric:tabular-nums;">약 {mild_rec_avg:.1f}개월</div>
        <div style="font-size:0.77rem; color:#57534e;">저점 통과 후 전고점 돌파까지 (2022년 제외 시 4개월)</div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>대형 폭락장 중앙값 회복</span><span class="ticker-badge" style="color:#1d4ed8; background:rgba(29,78,216,0.1);">-30% 이상</span></div>
        <div style="font-size:1.75rem; font-weight:700; color:#1d4ed8; margin:8px 0 4px 0; letter-spacing:-0.03em; font-variant-numeric:tabular-nums;">약 {severe_rec_med:.0f}개월</div>
        <div style="font-size:0.77rem; color:#57534e;">1973·1987·2000·2008·2020년 S&amp;P 회복 중앙값</div>
      </div>
    </div>
    """)


def render_crash_history_table(events: list[dict], sp_now_dd: float, nq_now_dd: float) -> str:
    """Render complete luxury HTML chronicle table including a highlighted TODAY row at the top."""
    rows = [
        f'<tr style="background:rgba(29, 78, 216, 0.06); border-bottom:1.5px solid rgba(29, 78, 216, 0.25);">'
        f'<td style="padding:13px 10px;"><b style="color:#1d4ed8; font-size:0.92rem;">📍 현재 시황 (실시간)</b><div style="font-size:0.74rem; color:#57534e; margin-top:2px;">진행 중 · 5년 고점 대비</div></td>'
        f'<td style="padding:13px 8px; text-align:center;"><span style="display:inline-block; padding:3px 9px; border-radius:999px; font-size:0.73rem; font-weight:700; background:rgba(29,78,216,0.14); color:#1d4ed8;">LIVE</span></td>'
        f'<td style="padding:13px 8px; text-align:right; font-weight:800; color:#1d4ed8; font-variant-numeric:tabular-nums;">{sp_now_dd:.2f}%</td>'
        f'<td style="padding:13px 8px; text-align:center; color:#57534e; font-size:0.8rem;">진행 중</td>'
        f'<td style="padding:13px 8px; text-align:right; font-weight:800; color:#1d4ed8; font-variant-numeric:tabular-nums;">{nq_now_dd:.2f}%</td>'
        f'<td style="padding:13px 8px; text-align:center; color:#57534e; font-size:0.8rem;">진행 중</td>'
        f'<td style="padding:13px 10px; font-size:0.78rem; color:#1c1917;">현재 고점 대비 낙폭을 과거 조정·폭락 사례와 직접 비교해 분할 매수 기준점으로 활용하세요.</td>'
        f'</tr>'
    ]

    for e in events:
        if e["tier"] == "대폭락":
            bg, fg = "rgba(185, 28, 28, 0.12)", "#b91c1c"
        elif "약세" in e["tier"]:
            bg, fg = "rgba(180, 83, 9, 0.12)", "#b45309"
        else:
            bg, fg = "rgba(21, 128, 61, 0.12)", "#15803d"

        rows.append(
            f'<tr style="border-bottom:1px solid rgba(28,25,23,0.07);">'
            f'<td style="padding:13px 10px;"><b style="color:#1c1917; font-size:0.9rem;">{e["era"]} {e["name"]}</b><div style="font-size:0.73rem; color:#78716c; margin-top:2px; font-variant-numeric:tabular-nums;">{e["period"]}</div></td>'
            f'<td style="padding:13px 8px; text-align:center;"><span style="display:inline-block; padding:3px 9px; border-radius:999px; font-size:0.73rem; font-weight:600; background:{bg}; color:{fg};">{e["tier"]}</span></td>'
            f'<td style="padding:13px 8px; text-align:right; font-weight:700; color:#b91c1c; font-variant-numeric:tabular-nums;">{e["sp_dd"]:.1f}%</td>'
            f'<td style="padding:13px 8px; text-align:center; font-weight:600; color:#15803d; font-size:0.82rem;">{e["sp_rec_label"]}</td>'
            f'<td style="padding:13px 8px; text-align:right; font-weight:700; color:#b91c1c; font-variant-numeric:tabular-nums;">{e["nq_dd"]:.1f}%</td>'
            f'<td style="padding:13px 8px; text-align:center; font-weight:600; color:#15803d; font-size:0.82rem;">{e["nq_rec_label"]}</td>'
            f'<td style="padding:13px 10px; font-size:0.78rem; color:#57534e; line-height:1.45;">{e["cause"]}</td>'
            f'</tr>'
        )

    return _compact_html(f"""
    <div class="glass-card" style="padding:20px 22px; overflow-x:auto;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:700; font-size:0.98rem; color:#1c1917;">📜 미국 증시 역대 주요 조정 · 폭락 &amp; 회복기간 연대기</span>
        <span style="font-size:0.75rem; color:#78716c;">낙폭: 고점→저점 최대 하락률 · 회복기간: 저점→전고점 재돌파 소요 기간</span>
      </div>
      <table style="width:100%; border-collapse:collapse; font-size:0.84rem;">
        <thead>
          <tr style="border-bottom:1px solid rgba(28,25,23,0.12); color:#78716c; font-size:0.74rem; font-weight:600;">
            <th style="padding:9px 10px; text-align:left; min-width:170px;">사건명 · 기간</th>
            <th style="padding:9px 8px; text-align:center;">구분</th>
            <th style="padding:9px 8px; text-align:right;">S&amp;P 500 낙폭</th>
            <th style="padding:9px 8px; text-align:center;">S&amp;P 회복기간</th>
            <th style="padding:9px 8px; text-align:right;">나스닥 낙폭</th>
            <th style="padding:9px 8px; text-align:center;">나스닥 회복기간</th>
            <th style="padding:9px 10px; text-align:left; min-width:220px;">배경 및 회복 특징</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows)}
        </tbody>
      </table>
    </div>
    """)


def build_crash_drawdown_chart(events: list[dict], sp_now_dd: float, nq_now_dd: float) -> go.Figure:
    """Grouped bar chart comparing S&P 500 & NASDAQ max drawdowns with TODAY's live reference lines."""
    ordered = list(reversed(events))  # Chronological 1973 -> 2025
    labels = [f"{e['era']}\n{e['name'].split(' ')[0]}" for e in ordered]
    sp_vals = [e["sp_dd"] for e in ordered]
    nq_vals = [e["nq_dd"] for e in ordered]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=sp_vals,
            name="S&P 500 최대 낙폭 (%)",
            marker_color="#18181b",
            text=[f"{v:.1f}%" for v in sp_vals],
            textposition="outside",
            textfont=dict(color="#1c1917", size=10),
        )
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=nq_vals,
            name="NASDAQ 최대 낙폭 (%)",
            marker_color="#b91c1c",
            text=[f"{v:.1f}%" for v in nq_vals],
            textposition="outside",
            textfont=dict(color="#b91c1c", size=10),
        )
    )
    fig.add_hline(
        y=nq_now_dd,
        line_dash="dash",
        line_width=1.6,
        line_color="#1d4ed8",
        annotation_text=f" 현재 나스닥 ({nq_now_dd:.1f}%)",
        annotation_position="bottom right",
        annotation_font=dict(color="#ffffff", size=11),
        annotation_bgcolor="#1d4ed8",
    )
    fig.add_hline(
        y=sp_now_dd,
        line_dash="dot",
        line_width=1.4,
        line_color="#15803d",
        annotation_text=f" 현재 S&P ({sp_now_dd:.1f}%)",
        annotation_position="top left",
        annotation_font=dict(color="#ffffff", size=11),
        annotation_bgcolor="#15803d",
    )

    min_y = min(min(nq_vals), min(sp_vals), nq_now_dd) - 10.0
    fig.update_yaxes(
        range=[min_y, 4.0],
        ticksuffix="%",
        automargin=True,
        gridcolor="rgba(0,0,0,0.06)",
        tickfont=dict(color="#57534e", size=11),
    )
    fig.update_xaxes(automargin=True, tickfont=dict(color="#1c1917", size=11))
    fig.update_layout(
        title=dict(text="역대 주요 사건별 고점 대비 최대 낙폭 vs 현재 시황", font=dict(size=14, color="#1c1917")),
        barmode="group",
        height=440,
        margin=dict(l=46, r=52, t=72, b=46),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)", font=dict(color="#57534e", size=12)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#faf9f6", bordercolor="#d6d3d1", font=dict(color="#1c1917", size=12)),
    )
    return fig


def build_recovery_duration_chart(events: list[dict], exclude_dotcom: bool = False) -> go.Figure:
    """Grouped bar chart of trough-to-new-ATH recovery months for S&P 500 & NASDAQ."""
    ordered = list(reversed(events))
    if exclude_dotcom:
        ordered = [e for e in ordered if e["era"] != "2000"]

    labels = [f"{e['era']}\n{e['name'].split(' ')[0]}" for e in ordered]
    sp_m = [e["sp_rec_months"] for e in ordered]
    nq_m = [e["nq_rec_months"] for e in ordered]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=sp_m,
            name="S&P 500 회복기간 (개월)",
            marker_color="#1d4ed8",
            text=[f"{v:.0f}개월" if v >= 10 else f"{v:.1f}개월" for v in sp_m],
            textposition="outside",
            textfont=dict(color="#1d4ed8", size=10),
        )
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=nq_m,
            name="NASDAQ 회복기간 (개월)",
            marker_color="#15803d",
            text=[f"{v:.0f}개월" if v >= 10 else f"{v:.1f}개월" for v in nq_m],
            textposition="outside",
            textfont=dict(color="#15803d", size=10),
        )
    )

    max_y = max(max(sp_m), max(nq_m)) * 1.22 if ordered else 24.0
    fig.update_yaxes(
        range=[0, max_y],
        ticksuffix="개월",
        automargin=True,
        gridcolor="rgba(0,0,0,0.06)",
        tickfont=dict(color="#57534e", size=11),
    )
    fig.update_xaxes(automargin=True, tickfont=dict(color="#1c1917", size=11))
    fig.update_layout(
        title=dict(text="저점 → 전고점 돌파까지 소요된 회복 기간 (개월)", font=dict(size=14, color="#1c1917")),
        barmode="group",
        height=410,
        margin=dict(l=52, r=46, t=72, b=46),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)", font=dict(color="#57534e", size=12)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#faf9f6", bordercolor="#d6d3d1", font=dict(color="#1c1917", size=12)),
    )
    return fig
