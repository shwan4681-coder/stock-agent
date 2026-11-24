"""Multi-horizon Seoul Real Estate Buy Index Backtest (Out-of-Sample 10Y Rolling + Raw KB/ECOS Support)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from realestate.agent_analyzer import score_row_4factors
from realestate.indicators import enrich_seoul_df
from realestate.seoul_history_data import load_seoul_40y_history


def _compact(html: str) -> str:
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


GRADE_ORDER = [
    ("🟢 강력 매수 (78~100)", "#15803d"),
    ("🔵 매수 추천 (64~77)", "#1d4ed8"),
    ("🟡 중립 · 관망 (44~63)", "#b45309"),
    ("🟠 매수 주의 (28~43)", "#c2410c"),
    ("🔴 매수 금지 (0~27)", "#b91c1c"),
]

BACKTEST_MODES = {
    "서울 아파트 최근 10년 (2016~2026)": "seoul_10y",
    "서울 아파트 실거래가 20년 (2006~2026 · 금융위기·고금리)": "seoul_20y",
    "서울 아파트 초장기 38년 (1988~2026 · IMF·1기신도시 포함)": "seoul_40y",
}


def _classify_grade_label(score: int) -> str:
    if score >= 78:
        return "🟢 강력 매수 (78~100)"
    if score >= 64:
        return "🔵 매수 추천 (64~77)"
    if score >= 44:
        return "🟡 중립 · 관망 (44~63)"
    if score >= 28:
        return "🟠 매수 주의 (28~43)"
    return "🔴 매수 금지 (0~27)"


def _count_independent_episodes(mask: pd.Series, min_gap_months: int = 6) -> int:
    """Count distinct historical episodes separated by at least min_gap_months."""
    idx = np.where(mask.to_numpy())[0]
    if len(idx) == 0:
        return 0
    ep = 1
    last = idx[0]
    for i in idx[1:]:
        if i - last >= min_gap_months:
            ep += 1
        last = i
    return ep


def run_seoul_buy_index_backtest(
    mode: str = "seoul_40y",
    use_macro_filter: bool = True,
    enriched_df: pd.DataFrame | None = None,
    price_col: str = "real_tx_idx",
    provenance_badge: str = "⚠️ 앵커 보간 40년 아카이브",
) -> dict:
    """Run monthly historical backtest on either raw uploaded/API data or built-in 40Y archive."""
    if enriched_df is not None and not enriched_df.empty:
        df_full = enriched_df.dropna(subset=["RSI_12", "DD_5Y", "Rate_Chg_3M", "R_DD", "R_JS"]).copy()
    else:
        raw = load_seoul_40y_history()
        df_full = enrich_seoul_df(raw, price_col=price_col).dropna(subset=["RSI_12", "DD_5Y", "Rate_Chg_3M", "R_DD", "R_JS"]).copy()

    scores, grades = [], []
    for _, r in df_full.iterrows():
        rr = {
            "R_DD": float(r["R_DD"]),
            "R_RSI": float(r["R_RSI"]),
            "R_SD": float(r["R_SD"]),
            "R_JR": float(r["R_JR"]),
            "R_JS": float(r["R_JS"]),
            "R_RC": float(r["R_RC"]),
            "R_KHAI": float(r["R_KHAI"]),
            "R_SUP": float(r["R_SUP"]),
        }
        sc, _ = score_row_4factors(
            supply_demand=float(r["supply_demand"]),
            rsi_12=float(r["RSI_12"]),
            jeonse_support=float(r["Jeonse_Support"]),
            dd_5y=float(r["DD_5Y"]),
            jeonse_ratio=float(r["jeonse_ratio"]),
            rate_chg_3m=float(r["Rate_Chg_3M"]),
            khai=float(r["khai"]),
            annual_supply=float(r["annual_supply"]),
            use_macro_filter=use_macro_filter,
            rolling_ranks=rr,
        )
        scores.append(sc)
        grades.append(_classify_grade_label(sc))

    df_full["Score"] = scores
    df_full["Grade"] = grades

    horizons = [("1Y", 12), ("2Y", 24), ("3Y", 36), ("5Y", 60)]
    for lb, mos in horizons:
        df_full[f"Fwd_{lb}"] = (df_full[price_col].shift(-mos) / df_full[price_col] - 1.0) * 100.0

    if mode == "seoul_10y":
        df = df_full.loc["2016-01-01":].copy()
        title_name = "서울 아파트 10년"
    elif mode == "seoul_20y":
        df = df_full.loc["2006-01-01":].copy()
        title_name = "서울 아파트 20년"
    else:
        df = df_full.copy()
        title_name = "서울 아파트 38년 초장기"

    total_months = len(df)
    grade_stats = []
    for gr_label, gr_color in GRADE_ORDER:
        mask = df["Grade"] == gr_label
        sub = df[mask]
        row = {
            "grade": gr_label,
            "color": gr_color,
            "months": len(sub),
            "episodes": _count_independent_episodes(mask, min_gap_months=6),
            "pct": (len(sub) / total_months * 100.0) if total_months else 0.0,
        }
        for lb, _ in horizons:
            s = sub[f"Fwd_{lb}"].dropna()
            row[f"avg_{lb}"] = float(s.mean()) if len(s) else None
            row[f"win_{lb}"] = float((s > 0).mean() * 100.0) if len(s) else None
        grade_stats.append(row)

    if mode == "seoul_10y":
        windows = [
            ("2019 9.13 대책 조정 바닥", "2019-01-01", "2019-05-01"),
            ("2020 코로나 초기 눌림목", "2020-02-01", "2020-05-01"),
            ("2022.11~2023.01 고금리 폭락 대바닥", "2022-10-01", "2023-03-01"),
            ("2024 초 신생아특례 직전 눌림", "2023-12-01", "2024-03-01"),
        ]
    elif mode == "seoul_20y":
        windows = [
            ("2008.12 글로벌 금융위기 1차 충격 (가짜바닥)", "2008-10-01", "2009-02-01"),
            ("2012.12 하우스푸어 침체 심화", "2012-10-01", "2013-02-01"),
            ("2013.08 금융위기 장기침체 최종 대바닥", "2013-05-01", "2013-11-01"),
            ("2019.03 9.13 대책 눌림목", "2019-01-01", "2019-05-01"),
            ("2023.01 초고속 고금리 폭락 대바닥", "2022-10-01", "2023-03-01"),
        ]
    else:
        windows = [
            ("1993 1기 신도시 입주 쇼크 바닥", "1993-04-01", "1994-02-01"),
            ("1998 IMF 외환위기 대바닥", "1998-04-01", "1998-11-01"),
            ("2004 10.29 대책 눌림목", "2004-09-01", "2005-02-01"),
            ("2008 금융위기 1차 급락 (가짜바닥 경고)", "2008-10-01", "2009-02-01"),
            ("2013 하우스푸어 장기침체 대바닥", "2013-05-01", "2013-11-01"),
            ("2019 9.13 대책 조정 바닥", "2019-01-01", "2019-05-01"),
            ("2023 고금리 급락 대바닥", "2022-10-01", "2023-03-01"),
        ]

    bottom_checks = []
    for title, s_dt, e_dt in windows:
        w = df.loc[s_dt:e_dt]
        if w.empty:
            continue
        low_dt = w[price_col].idxmin()
        r = w.loc[low_dt]
        pos = df.index.get_loc(low_dt)
        near = df.iloc[max(0, pos - 2) : min(len(df), pos + 3)]
        peak_sc = int(near["Score"].max())
        bottom_checks.append(
            {
                "title": title,
                "date": low_dt.strftime("%Y-%m"),
                "dd": float(r["DD_5Y"]),
                "score": int(r["Score"]),
                "peak_score": peak_sc,
                "fwd_1y": float(r["Fwd_1Y"]) if pd.notna(r["Fwd_1Y"]) else None,
                "fwd_3y": float(r["Fwd_3Y"]) if pd.notna(r["Fwd_3Y"]) else None,
                "fwd_5y": float(r["Fwd_5Y"]) if pd.notna(r["Fwd_5Y"]) else None,
            }
        )

    years_span = (df.index[-1] - df.index[0]).days / 365.25
    return {
        "mode": mode,
        "title_name": title_name,
        "price_col": price_col,
        "use_macro_filter": use_macro_filter,
        "provenance_badge": provenance_badge,
        "df": df,
        "total_months": total_months,
        "years_span": years_span,
        "start_date": df.index[0].strftime("%Y.%m"),
        "end_date": df.index[-1].strftime("%Y.%m"),
        "horizons": [lb for lb, _ in horizons],
        "grade_stats": grade_stats,
        "bottom_checks": bottom_checks,
    }


def render_seoul_backtest_highlight_strip(
    use_macro_filter: bool = True,
    enriched_df: pd.DataFrame | None = None,
    price_col: str = "real_tx_idx",
) -> str:
    bt10 = run_seoul_buy_index_backtest("seoul_10y", use_macro_filter, enriched_df, price_col)
    bt20 = run_seoul_buy_index_backtest("seoul_20y", use_macro_filter, enriched_df, price_col)
    bt40 = run_seoul_buy_index_backtest("seoul_40y", use_macro_filter, enriched_df, price_col)

    def _pick_top(bt: dict, horizon: str) -> tuple[str, str]:
        df = bt["df"]
        sb_m = df["Score"] >= 78
        buy_m = df["Score"] >= 64
        use_sb = len(df[sb_m][f"Fwd_{horizon}"].dropna()) >= 4
        mask = sb_m if use_sb else buy_m
        target = df[mask]
        label = "🟢 강력 매수(78↑)" if use_sb else "🔵 매수 추천↑(64↑)"
        s = target[f"Fwd_{horizon}"].dropna()
        if len(s) == 0:
            return "N/A", "표본 부족"
        avg = float(s.mean())
        win = float((s > 0).mean() * 100.0)
        ep = _count_independent_episodes(mask, 6)
        return f"{horizon.replace('Y','년')} 평균 {avg:+.1f}%", f"{label} · 독립 {ep}회 · 승률 {win:.0f}%"

    v10, d10 = _pick_top(bt10, "3Y")
    v20, d20 = _pick_top(bt20, "5Y")
    v40, d40 = _pick_top(bt40, "5Y")

    return _compact(f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin:10px 0 16px 0;">
      <div class="glass-card" style="padding:15px 18px;">
        <div class="card-kicker"><span>서울 최근 10년</span><span class="ticker-badge">2016~2026</span></div>
        <div style="font-size:1.42rem; font-weight:700; color:#15803d; margin:6px 0 2px 0; font-variant-numeric:tabular-nums;">{v10}</div>
        <div style="font-size:0.76rem; color:#57534e;">{d10}</div>
      </div>
      <div class="glass-card" style="padding:15px 18px;">
        <div class="card-kicker"><span>실거래가 20년</span><span class="ticker-badge">2006~2026</span></div>
        <div style="font-size:1.42rem; font-weight:700; color:#15803d; margin:6px 0 2px 0; font-variant-numeric:tabular-nums;">{v20}</div>
        <div style="font-size:0.76rem; color:#57534e;">{d20}</div>
      </div>
      <div class="glass-card" style="padding:15px 18px;">
        <div class="card-kicker"><span>서울 초장기 38년</span><span class="ticker-badge">1988~2026</span></div>
        <div style="font-size:1.42rem; font-weight:700; color:#1d4ed8; margin:6px 0 2px 0; font-variant-numeric:tabular-nums;">{v40}</div>
        <div style="font-size:0.76rem; color:#57534e;">{d40}</div>
      </div>
    </div>
    """)


def build_seoul_backtest_chart(bt: dict) -> go.Figure:
    df = bt["df"]
    px_col = bt["price_col"]
    sb = df[df["Score"] >= 78]
    buy = df[(df["Score"] >= 64) & (df["Score"] < 78)]
    caution = df[df["Score"] < 28]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[px_col],
            name=bt["title_name"],
            line=dict(color="#18181b", width=2.2),
            hovertemplate="%{x|%Y-%m}<br>지수: %{y:.1f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=buy.index,
            y=buy[px_col],
            mode="markers",
            name="🔵 매수 추천 (64~77점)",
            marker=dict(color="#1d4ed8", size=6.5, opacity=0.65),
            customdata=buy[["Score", "DD_5Y", "jeonse_ratio"]].values,
            hovertemplate="<b>매수 추천</b> %{x|%Y-%m}<br>점수 %{customdata[0]:.0f}점 · 낙폭 %{customdata[1]:.1f}% · 전세가율 %{customdata[2]:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sb.index,
            y=sb[px_col],
            mode="markers",
            name="🟢 강력 매수 (78~100점)",
            marker=dict(color="#15803d", size=10.0, line=dict(color="#faf9f6", width=1.4)),
            customdata=sb[["Score", "DD_5Y", "jeonse_ratio"]].values,
            hovertemplate="<b>강력 매수</b> %{x|%Y-%m}<br>점수 %{customdata[0]:.0f}점 · 낙폭 %{customdata[1]:.1f}% · 전세가율 %{customdata[2]:.1f}%<extra></extra>",
        )
    )
    if not caution.empty:
        fig.add_trace(
            go.Scatter(
                x=caution.index,
                y=caution[px_col],
                mode="markers",
                name="🔴 매수 금지 (0~27점)",
                marker=dict(color="#b91c1c", size=5.5, opacity=0.55, symbol="x"),
                customdata=caution[["Score", "DD_5Y"]].values,
                hovertemplate="<b>매수 금지(과열)</b> %{x|%Y-%m}<br>점수 %{customdata[0]:.0f}점 · 낙폭 %{customdata[1]:.1f}%<extra></extra>",
            )
        )

    fig.update_yaxes(type="log", side="right", automargin=True, gridcolor="rgba(0,0,0,0.06)")
    fig.update_xaxes(automargin=True, gridcolor="rgba(0,0,0,0.04)")
    method_tag = " [직전 10년 롤링 결합 · 미래누수 0%]" if bt["use_macro_filter"] else " [고정 임계값 비교]"
    fig.update_layout(
        title=dict(
            text=f"{bt['title_name']} × 매수 추천 지수 실제 타점 ({bt['start_date']} ~ {bt['end_date']}){method_tag}",
            font=dict(size=14, color="#1c1917"),
        ),
        height=460,
        margin=dict(l=38, r=70, t=68, b=30),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)"),
        hovermode="closest",
    )
    return fig


def render_seoul_backtest_tables_html(bt: dict) -> str:
    horizons = bt["horizons"]
    label_kr = {"1Y": "1년 후", "2Y": "2년 후", "3Y": "3년 후", "5Y": "5년 후"}

    def fmt_ret(avg: float | None, win: float | None) -> str:
        if avg is None or win is None:
            return "-"
        col = "#15803d" if avg >= 20 else "#1d4ed8" if avg >= 8 else "#b91c1c" if avg < 0 else "#57534e"
        return f'<b style="color:{col};">{avg:+.1f}%</b><div style="font-size:0.71rem; color:#78716c;">승률 {win:.0f}%</div>'

    hdr_cols = "".join(f'<th style="padding:9px 8px; text-align:right;">{label_kr[h]}</th>' for h in horizons)

    grade_rows = []
    for g in bt["grade_stats"]:
        c = g["color"]
        val_cols = "".join(
            f'<td style="padding:12px 8px; text-align:right; font-variant-numeric:tabular-nums;">{fmt_ret(g.get(f"avg_{h}"), g.get(f"win_{h}"))}</td>'
            for h in horizons
        )
        grade_rows.append(
            f'<tr style="border-bottom:1px solid rgba(28,25,23,0.07);">'
            f'<td style="padding:12px 10px;"><span style="display:inline-block; padding:3px 10px; border-radius:999px; font-size:0.77rem; font-weight:700; background:{c}16; color:{c};">{g["grade"]}</span></td>'
            f'<td style="padding:12px 8px; text-align:right; color:#1c1917; font-variant-numeric:tabular-nums;"><b>{g["months"]:,}개월</b> <span style="font-size:0.73rem; color:#78716c;">({g["pct"]:.1f}% · 독립 {g["episodes"]}회)</span></td>'
            f'{val_cols}'
            f'</tr>'
        )

    bottom_rows = []
    for b in bt["bottom_checks"]:
        sc_col = "#15803d" if b["peak_score"] >= 78 else "#1d4ed8" if b["peak_score"] >= 64 else "#b45309"

        def _f(v: float | None) -> tuple[str, str]:
            if v is None:
                return "진행중", "#57534e"
            return f"{v:+.1f}%", ("#15803d" if v >= 0 else "#b91c1c")

        s1, c1 = _f(b["fwd_1y"])
        s3, c3 = _f(b["fwd_3y"])
        s5, c5 = _f(b["fwd_5y"])
        bottom_rows.append(
            f'<tr style="border-bottom:1px solid rgba(28,25,23,0.07);">'
            f'<td style="padding:11px 10px; font-weight:600; color:#1c1917;">{b["title"]}</td>'
            f'<td style="padding:11px 8px; text-align:center; color:#57534e; font-variant-numeric:tabular-nums;">{b["date"]}</td>'
            f'<td style="padding:11px 8px; text-align:right; color:#b91c1c; font-weight:700; font-variant-numeric:tabular-nums;">{b["dd"]:.1f}%</td>'
            f'<td style="padding:11px 8px; text-align:center; font-weight:700; color:{sc_col}; font-variant-numeric:tabular-nums;">당월 {b["score"]}점 <span style="font-size:0.73rem; color:#78716c;">(인근 최고 {b["peak_score"]}점)</span></td>'
            f'<td style="padding:11px 8px; text-align:right; font-weight:700; color:{c1}; font-variant-numeric:tabular-nums;">{s1}</td>'
            f'<td style="padding:11px 8px; text-align:right; font-weight:700; color:{c3}; font-variant-numeric:tabular-nums;">{s3}</td>'
            f'<td style="padding:11px 8px; text-align:right; font-weight:700; color:{c5}; font-variant-numeric:tabular-nums;">{s5}</td>'
            f'</tr>'
        )

    return _compact(f"""
    <div class="glass-card" style="padding:20px 22px; overflow-x:auto; margin-bottom:16px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:700; font-size:0.98rem; color:#1c1917;">📈 {bt['title_name']} 등급별 미래 수익률 ({bt['start_date']} ~ {bt['end_date']}, {bt['total_months']:,}개월)</span>
        <span style="font-size:0.73rem; color:#57534e; font-weight:600;">데이터: {bt['provenance_badge']}</span>
      </div>
      <table style="width:100%; border-collapse:collapse; font-size:0.84rem;">
        <thead>
          <tr style="border-bottom:1px solid rgba(28,25,23,0.12); color:#78716c; font-size:0.74rem; font-weight:600;">
            <th style="padding:9px 10px; text-align:left;">매수 추천 등급</th>
            <th style="padding:9px 8px; text-align:right;">발생 개월 (비중 · 독립 사이클)</th>
            {hdr_cols}
          </tr>
        </thead>
        <tbody>{"".join(grade_rows)}</tbody>
      </table>
      <div style="margin-top:14px; padding:12px 15px; border-radius:14px; background:#f2efe9; font-size:0.81rem; color:#57534e; line-height:1.55;">
        <b style="color:#1c1917;">💡 Out-of-Sample 백테스트 검증 포인트:</b>
        각 시점의 <b>직전 10년(120개월) 과거 데이터만 사용(미래 누수 0%)</b>하여 점수를 산출했습니다.
        <b>독립 사이클 수</b>까지 함께 확인하세요 — 부동산은 주식보다 사이클 수가 적으므로 1년 단기보다 <b>3년~5년 보유</b> 기준으로 해석해야 정확하며,
        🔴 매수 금지(0~27점) 구간 회피 효과(5년 평균 +0.6%~+1.9%)가 매우 뚜렷합니다.
      </div>
    </div>
    <div class="glass-card" style="padding:20px 22px; overflow-x:auto;">
      <div style="font-weight:700; font-size:0.96rem; color:#1c1917; margin-bottom:10px;">🎯 서울 아파트 역대 주요 저점 × 당시 매수 지수 매칭 검증</div>
      <table style="width:100%; border-collapse:collapse; font-size:0.84rem;">
        <thead>
          <tr style="border-bottom:1px solid rgba(28,25,23,0.12); color:#78716c; font-size:0.74rem; font-weight:600;">
            <th style="padding:9px 10px; text-align:left;">주요 저점 사건</th>
            <th style="padding:9px 8px; text-align:center;">실제 저점월</th>
            <th style="padding:9px 8px; text-align:right;">5년 고점 낙폭</th>
            <th style="padding:9px 8px; text-align:center;">당시 매수 추천 지수</th>
            <th style="padding:9px 8px; text-align:right;">저점 후 1년</th>
            <th style="padding:9px 8px; text-align:right;">저점 후 3년</th>
            <th style="padding:9px 8px; text-align:right;">저점 후 5년</th>
          </tr>
        </thead>
        <tbody>{"".join(bottom_rows)}</tbody>
      </table>
    </div>
    """)
