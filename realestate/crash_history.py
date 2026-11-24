"""Seoul Apartment Historical Corrections & Crashes Archive (1991 ~ 2026)."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go


def _compact(html: str) -> str:
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


# Major Seoul apartment downturns: Peak-to-trough drawdown (Index vs Actual Tx) & Trough-to-ATH recovery
SEOUL_CRASH_EVENTS: list[dict] = [
    {
        "era": "2022~2023",
        "name": "초고속 금리인상 · 유동성 축소 폭락장",
        "period": "2022.01 ~ 2023.01",
        "tier": "대폭락",
        "idx_dd": -13.8,
        "real_dd": -22.2,
        "rec_months": 20.0,
        "rec_label": "약 1년 8개월 (상급지)",
        "cause": "한은 기준금리 0.5%→3.5% 급등으로 거래절벽(월 600건대) → 규제 완화·특례보금자리론·공급부족으로 초고속 반등",
    },
    {
        "era": "2020",
        "name": "코로나19 초기 · 대출규제 단기 눌림",
        "period": "2020.01 ~ 2020.04",
        "tier": "단기조정",
        "idx_dd": -1.5,
        "real_dd": -4.2,
        "rec_months": 3.0,
        "rec_label": "약 3개월",
        "cause": "12.16 초고가 대출금지 + 팬데믹 공포 → 한은 0.5% 사상 초저금리 인하 직후 역대급 상승장 폭발",
    },
    {
        "era": "2018~2019",
        "name": "9.13 대책 · 종부세 강화 조정기",
        "period": "2018.09 ~ 2019.04",
        "tier": "조정장",
        "idx_dd": -2.0,
        "real_dd": -6.5,
        "rec_months": 7.0,
        "rec_label": "약 7개월",
        "cause": "다주택 종부세·대출 규제 강화로 거래 급감 → 2019년 하반기 금리 인하 및 민간택지 분양가상한제 공급우려로 반등",
    },
    {
        "era": "2008~2013",
        "name": "글로벌 금융위기 · 하우스푸어 장기침체",
        "period": "2008.06 ~ 2013.08",
        "tier": "장기침체",
        "idx_dd": -15.5,
        "real_dd": -22.3,
        "rec_months": 34.0,
        "rec_label": "저점 후 약 2년 10개월 (총 7년)",
        "cause": "서브프라임 위기 + 2기 신도시(판교·광교 등) 입주 폭탄 + 보금자리주택 공급 → 전세가율 70% 돌파 후 대세상승 전환",
    },
    {
        "era": "2003~2004",
        "name": "10.29 대책 · 카드사태 눌림목",
        "period": "2003.10 ~ 2004.12",
        "tier": "조정장",
        "idx_dd": -3.1,
        "real_dd": -5.2,
        "rec_months": 9.0,
        "rec_label": "약 9개월",
        "cause": "다주택 양도세 중과 및 카드대란 신용 위축 → 저금리 유동성과 강남 재건축 수요로 2005~06 버블세븐 급등",
    },
    {
        "era": "1997~1998",
        "name": "IMF 외환위기 국가부도 폭락장",
        "period": "1997.10 ~ 1998.09",
        "tier": "대폭락",
        "idx_dd": -15.4,
        "real_dd": -22.2,
        "rec_months": 24.0,
        "rec_label": "약 2년 (V자 회복)",
        "cause": "외환위기·금리 17% 폭등·대규모 구조조정 → 양도세 면제·분양가 자율화·저금리 전환으로 2000~01년 전고점 돌파",
    },
    {
        "era": "1991~1993",
        "name": "1기 신도시 200만호 입주 쇼크",
        "period": "1991.04 ~ 1993.12",
        "tier": "장기침체",
        "idx_dd": -15.0,
        "real_dd": -19.5,
        "rec_months": 78.0,
        "rec_label": "약 6년 6개월 (IMF 겹침)",
        "cause": "분당·일산·평촌·산본·중동 대규모 공급 폭탄 + 토지공개념 규제 → 1990년대 중반 긴 횡보 조정",
    },
]


def render_seoul_history_summary_cards(idx_now_dd: float, real_now_dd: float) -> str:
    idx_avg = float(np.mean([e["idx_dd"] for e in SEOUL_CRASH_EVENTS]))
    real_avg = float(np.mean([e["real_dd"] for e in SEOUL_CRASH_EVENTS]))
    severe = [e for e in SEOUL_CRASH_EVENTS if e["real_dd"] <= -18.0]
    severe_rec_med = float(np.median([e["rec_months"] for e in severe]))
    closest = min(SEOUL_CRASH_EVENTS, key=lambda e: abs(e["real_dd"] - real_now_dd))

    return _compact(f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px; margin:10px 0 18px 0;">
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>현재 서울 5년 고점 대비 낙폭</span><span class="ticker-badge">NOW</span></div>
        <div style="font-size:1.5rem; font-weight:700; color:#b45309; margin:8px 0 4px 0; font-variant-numeric:tabular-nums;">매매 {idx_now_dd:.1f}% · 실거래 {real_now_dd:.1f}%</div>
        <div style="font-size:0.77rem; color:#57534e;">가장 유사한 과거: <b style="color:#1c1917;">{closest['era']} {closest['name'].split('·')[0]}</b></div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>역대 7대 하락장 평균 낙폭</span><span class="ticker-badge">1991~2026</span></div>
        <div style="font-size:1.5rem; font-weight:700; color:#b91c1c; margin:8px 0 4px 0; font-variant-numeric:tabular-nums;">지수 {idx_avg:.1f}% · 실거래 {real_avg:.1f}%</div>
        <div style="font-size:0.77rem; color:#57534e;">대형 폭락기 실거래가 평균 낙폭은 약 -21.5%</div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>정책·단기 조정 평균 회복</span><span class="ticker-badge" style="color:#15803d; background:rgba(21,128,61,0.1);">-4% ~ -7%</span></div>
        <div style="font-size:1.72rem; font-weight:700; color:#15803d; margin:8px 0 4px 0; font-variant-numeric:tabular-nums;">약 6.3개월</div>
        <div style="font-size:0.77rem; color:#57534e;">2004·2019·2020년 규제성 눌림목 전고점 회복</div>
      </div>
      <div class="glass-card" style="padding:18px 20px;">
        <div class="card-kicker"><span>대형 폭락장 회복 중앙값</span><span class="ticker-badge" style="color:#1d4ed8; background:rgba(29,78,216,0.1);">-19% 이상</span></div>
        <div style="font-size:1.72rem; font-weight:700; color:#1d4ed8; margin:8px 0 4px 0; font-variant-numeric:tabular-nums;">약 {severe_rec_med:.0f}개월</div>
        <div style="font-size:0.77rem; color:#57534e;">저점 통과 후 전고점 재돌파 기준 (공급폭탄 시 장기화)</div>
      </div>
    </div>
    """)


def render_seoul_crash_table(events: list[dict], idx_now_dd: float, real_now_dd: float) -> str:
    rows = [
        f'<tr style="background:rgba(29, 78, 216, 0.06); border-bottom:1.5px solid rgba(29, 78, 216, 0.25);">'
        f'<td style="padding:13px 10px;"><b style="color:#1d4ed8; font-size:0.92rem;">📍 현재 서울 시황</b><div style="font-size:0.74rem; color:#57534e; margin-top:2px;">진행 중 · 5년 고점 대비</div></td>'
        f'<td style="padding:13px 8px; text-align:center;"><span style="display:inline-block; padding:3px 9px; border-radius:999px; font-size:0.73rem; font-weight:700; background:rgba(29,78,216,0.14); color:#1d4ed8;">NOW</span></td>'
        f'<td style="padding:13px 8px; text-align:right; font-weight:800; color:#1d4ed8; font-variant-numeric:tabular-nums;">{idx_now_dd:.1f}%</td>'
        f'<td style="padding:13px 8px; text-align:right; font-weight:800; color:#1d4ed8; font-variant-numeric:tabular-nums;">{real_now_dd:.1f}%</td>'
        f'<td style="padding:13px 8px; text-align:center; color:#57534e; font-size:0.8rem;">진행 중</td>'
        f'<td style="padding:13px 10px; font-size:0.78rem; color:#1c1917;">현재 서울 아파트 조정 폭을 역대 IMF·금융위기·2022 고금리장과 직접 비교하세요.</td>'
        f'</tr>'
    ]
    for e in events:
        if e["tier"] == "대폭락":
            bg, fg = "rgba(185, 28, 28, 0.12)", "#b91c1c"
        elif e["tier"] == "장기침체":
            bg, fg = "rgba(180, 83, 9, 0.12)", "#b45309"
        else:
            bg, fg = "rgba(21, 128, 61, 0.12)", "#15803d"
        rows.append(
            f'<tr style="border-bottom:1px solid rgba(28,25,23,0.07);">'
            f'<td style="padding:13px 10px;"><b style="color:#1c1917; font-size:0.9rem;">{e["era"]} {e["name"]}</b><div style="font-size:0.73rem; color:#78716c; margin-top:2px;">{e["period"]}</div></td>'
            f'<td style="padding:13px 8px; text-align:center;"><span style="display:inline-block; padding:3px 9px; border-radius:999px; font-size:0.73rem; font-weight:600; background:{bg}; color:{fg};">{e["tier"]}</span></td>'
            f'<td style="padding:13px 8px; text-align:right; font-weight:700; color:#57534e; font-variant-numeric:tabular-nums;">{e["idx_dd"]:.1f}%</td>'
            f'<td style="padding:13px 8px; text-align:right; font-weight:700; color:#b91c1c; font-variant-numeric:tabular-nums;">{e["real_dd"]:.1f}%</td>'
            f'<td style="padding:13px 8px; text-align:center; font-weight:600; color:#15803d; font-size:0.82rem;">{e["rec_label"]}</td>'
            f'<td style="padding:13px 10px; font-size:0.78rem; color:#57534e; line-height:1.45;">{e["cause"]}</td>'
            f'</tr>'
        )

    return _compact(f"""
    <div class="glass-card" style="padding:20px 22px; overflow-x:auto;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:700; font-size:0.98rem; color:#1c1917;">📜 서울 아파트 역대 주요 하락 · 폭락 &amp; 회복기간 연대기 (1991~2026)</span>
        <span style="font-size:0.75rem; color:#78716c;">매매지수 낙폭 vs 실거래가 체감 낙폭 · 저점→전고점 회복 소요기간</span>
      </div>
      <table style="width:100%; border-collapse:collapse; font-size:0.84rem;">
        <thead>
          <tr style="border-bottom:1px solid rgba(28,25,23,0.12); color:#78716c; font-size:0.74rem; font-weight:600;">
            <th style="padding:9px 10px; text-align:left; min-width:190px;">사건명 · 기간</th>
            <th style="padding:9px 8px; text-align:center;">구분</th>
            <th style="padding:9px 8px; text-align:right;">매매지수 낙폭</th>
            <th style="padding:9px 8px; text-align:right;">실거래 낙폭</th>
            <th style="padding:9px 8px; text-align:center;">회복기간</th>
            <th style="padding:9px 10px; text-align:left; min-width:230px;">배경 및 반등 트리거</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
    """)


def build_seoul_crash_drawdown_chart(events: list[dict], idx_now_dd: float, real_now_dd: float) -> go.Figure:
    ordered = list(reversed(events))
    labels = [f"{e['era']}\n{e['name'].split(' ')[0]}" for e in ordered]
    idx_vals = [e["idx_dd"] for e in ordered]
    real_vals = [e["real_dd"] for e in ordered]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=idx_vals,
            name="매매가격지수 최대 낙폭 (%)",
            marker_color="#18181b",
            text=[f"{v:.1f}%" for v in idx_vals],
            textposition="outside",
            textfont=dict(color="#1c1917", size=10),
        )
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=real_vals,
            name="실거래가지수 최대 낙폭 (%)",
            marker_color="#b91c1c",
            text=[f"{v:.1f}%" for v in real_vals],
            textposition="outside",
            textfont=dict(color="#b91c1c", size=10),
        )
    )
    fig.add_hline(
        y=real_now_dd,
        line_dash="dash",
        line_width=1.6,
        line_color="#1d4ed8",
        annotation_text=f" 현재 서울 실거래 ({real_now_dd:.1f}%)",
        annotation_position="bottom right",
        annotation_font=dict(color="#ffffff", size=11),
        annotation_bgcolor="#1d4ed8",
    )
    fig.add_hline(
        y=idx_now_dd,
        line_dash="dot",
        line_width=1.3,
        line_color="#15803d",
        annotation_text=f" 현재 매매지수 ({idx_now_dd:.1f}%)",
        annotation_position="top left",
        annotation_font=dict(color="#ffffff", size=11),
        annotation_bgcolor="#15803d",
    )

    min_y = min(min(real_vals), real_now_dd) - 6.0
    fig.update_yaxes(range=[min_y, 2.5], ticksuffix="%", automargin=True, gridcolor="rgba(0,0,0,0.06)")
    fig.update_xaxes(automargin=True)
    fig.update_layout(
        title=dict(text="서울 아파트 역대 하락장 최대 낙폭 vs 현재 시황", font=dict(size=14, color="#1c1917")),
        barmode="group",
        height=420,
        margin=dict(l=46, r=52, t=70, b=44),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)"),
        hovermode="x unified",
    )
    return fig
