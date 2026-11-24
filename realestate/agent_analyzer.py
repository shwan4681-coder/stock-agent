"""Seoul Real Estate Agent: 0~100 Buy Index, Quantitative Briefing (with Apt Picks), and Gemini Q&A."""

from __future__ import annotations

import requests

from realestate.indicators import lerp_score


def classify_supply_demand(sd: float) -> tuple[str, str, str]:
    if sd <= 76:
        return "극단적 매도우위 (거래절벽 공포)", "#15803d", "매수 실종 · 역발상 급매 사냥 구간"
    if sd <= 90:
        return "매도우위 (관망·조정)", "#1d4ed8", "매수자 협상 우위 · 급매 탐색 유리"
    if sd <= 102:
        return "수급 균형 (중립)", "#b45309", "매수·매도 힘 균형 상태"
    if sd <= 112:
        return "매수우위 (상승 모멘텀)", "#c2410c", "매수세 우세 · 호가 상승 구간"
    return "과열 (추격매수 주의)", "#b91c1c", "단기 과열 · 추격 매수 리스크 높음"


def classify_jeonse_support(js: float, jr: float) -> tuple[str, str, str]:
    if js >= 4.0:
        return "강력한 전세 하방지지", "#15803d", f"전세가율 {jr:.1f}% · 전세가 매매가를 밀어올리는 구간"
    if js >= 1.0:
        return "양호한 실수요 받침", "#1d4ed8", f"전세가율 {jr:.1f}% · 전세 상승세가 하단 방어"
    if js >= -2.5:
        return "전세 지지 중립", "#b45309", f"전세가율 {jr:.1f}% · 매매-전세 균형 구간"
    return "전세 지지 약화 (괴리 확대)", "#b91c1c", f"전세가율 {jr:.1f}% · 매매가 선반영 부담"


def classify_seoul_drawdown(dd_pct: float) -> tuple[str, str]:
    if dd_pct >= -2.0:
        return "신고가 부근", "#15803d"
    if dd_pct >= -6.0:
        return "단기 숨고르기", "#1d4ed8"
    if dd_pct >= -12.0:
        return "조정장 (급매 출현)", "#b45309"
    return "대형 하락장 (역대급 할인)", "#b91c1c"


def classify_grade(total: int) -> tuple[str, str, str, str]:
    if total >= 78:
        return (
            "🟢 강력 매수",
            "STRONG BUY",
            "#15803d",
            "직전 10년 분포 대비 전세 하방지지·금리/구매력 완화·고점 낙폭·수급 공포가 집중 충족된 역대급 매수 적기입니다.",
        )
    if total >= 64:
        return (
            "🔵 매수 추천",
            "BUY",
            "#1d4ed8",
            "하락 조정과 수급 위축이 겹친 매수자 우위 시장입니다. 핵심 입지 급매 중심으로 적극 검토할 자리입니다.",
        )
    if total >= 44:
        return (
            "🟡 중립 · 관망",
            "NEUTRAL",
            "#b45309",
            "뚜렷한 역대급 저점이나 과열이 아닌 균형·숨고르기 구간입니다. 상급지 급매와 갈아타기 기회만 선별하세요.",
        )
    if total >= 28:
        return (
            "🟠 매수 주의",
            "CAUTION",
            "#c2410c",
            "고점 부근이거나 구매력 부담이 커진 구간입니다. 무리한 영끌·추격 매수는 피하고 조정을 기다리세요.",
        )
    return (
        "🔴 매수 금지",
        "DO NOT BUY",
        "#b91c1c",
        "역사적 과열·고점 및 전세가 괴리 구간입니다(1991·2006·2008·2021형 경고). 현금·유동성 방어에 집중하세요.",
    )


def score_row_4factors(
    supply_demand: float,
    rsi_12: float,
    jeonse_support: float,
    dd_5y: float,
    jeonse_ratio: float = 55.0,
    rate_chg_3m: float = 0.0,
    khai: float = 150.0,
    annual_supply: float = 32000.0,
    use_macro_filter: bool = True,
    rolling_ranks: dict | None = None,
) -> tuple[int, tuple[int, int, int, int]]:
    """Quant-calibrated 0~100 Seoul Real Estate Buy Index (4 Core Pillars x 25 pts).

    When use_macro_filter=True (Default: Out-of-Sample 10Y Causal Rolling Percentile Hybrid):
      Combines each pillar's strictly causal 10Y rolling percentile (zero look-ahead) with
      economic structural benchmarks so regime shifts (1998 vs 2013 vs 2023) are normalized automatically.

    When use_macro_filter=False (Fixed Economic Threshold Comparison):
      Uses fixed structural thresholds only for side-by-side backtest comparison.
    """
    abs_p1 = lerp_score(jeonse_ratio, 68.0, 42.0, 13) + lerp_score(jeonse_support, 4.5, -4.5, 12)
    abs_p2 = lerp_score(rate_chg_3m, -0.35, 0.45, 13) + lerp_score(khai, 105.0, 185.0, 12)
    abs_p3 = lerp_score(dd_5y, -16.0, 0.0, 15) + lerp_score(rsi_12, 34.0, 76.0, 10)
    abs_p4 = lerp_score(supply_demand, 75.0, 116.0, 13) + lerp_score(annual_supply, 26000.0, 56000.0, 12)

    if use_macro_filter and rolling_ranks is not None:
        rol_p1 = 0.25 * (0.45 * rolling_ranks["R_JR"] + 0.55 * rolling_ranks["R_JS"])
        rol_p2 = 0.25 * (0.55 * rolling_ranks["R_RC"] + 0.45 * rolling_ranks["R_KHAI"])
        rol_p3 = 0.25 * rolling_ranks["R_DD"]
        rol_p4 = 0.25 * (0.55 * rolling_ranks["R_SD"] + 0.45 * rolling_ranks["R_SUP"])

        p1 = int(round(0.55 * abs_p1 + 0.45 * rol_p1))
        p2 = int(round(0.55 * abs_p2 + 0.45 * rol_p2))
        p3 = int(round(0.65 * abs_p3 + 0.35 * rol_p3))
        p4 = int(round(0.55 * abs_p4 + 0.45 * rol_p4))
        total = max(0, min(100, p1 + p2 + p3 + p4))
        return total, (p1, p2, p3, p4)

    total = max(0, min(100, int(abs_p1 + abs_p2 + abs_p3 + abs_p4)))
    return total, (int(abs_p1), int(abs_p2), int(abs_p3), int(abs_p4))


def compute_seoul_buy_index(data: dict, use_macro_filter: bool = True) -> dict:
    """Compute live 0~100 Seoul Market Buy Recommendation Index."""
    sd_val = float(data["supply_demand"])
    rsi_val = float(data["rsi"])
    js_val = float(data["jeonse_support"])
    jr_val = float(data["jeonse_ratio"])
    dd_val = float(data["selected"]["dd_5y_pct"])
    rc_val = float(data.get("rate_chg_3m", 0.0))
    khai_val = float(data["khai"])
    sup_val = float(data["annual_supply"])
    rr = data.get("rolling_ranks")

    total, (p1, p2, p3, p4) = score_row_4factors(
        supply_demand=sd_val,
        rsi_12=rsi_val,
        jeonse_support=js_val,
        dd_5y=dd_val,
        jeonse_ratio=jr_val,
        rate_chg_3m=rc_val,
        khai=khai_val,
        annual_supply=sup_val,
        use_macro_filter=use_macro_filter,
        rolling_ranks=rr,
    )
    grade, en_grade, color, comment = classify_grade(total)

    rr_note = (
        (
            f"직전 5~10년 백분위 {rr['R_JS']:.0f}%",
            f"직전 10년 금리·부담 {rr['R_RC']:.0f}%",
            f"직전 10년 낙폭 상위 {rr['R_DD']:.0f}%",
            f"직전 10년 수급·공급 {rr['R_SD']:.0f}%",
        )
        if (use_macro_filter and rr)
        else (
            "전세가율 68%↑ · 지지 +4.5",
            "금리 3M -0.35%p · K-HAI 105↓",
            "낙폭 -16%↓ · RSI 34↓",
            "수급 75↓ · 공급 2.6만호↓",
        )
    )

    items = [
        {
            "label": "1. 전세 하방지지",
            "rule": rr_note[0],
            "value": f"전세가율 {jr_val:.1f}% ({js_val:+.1f})",
            "pts": p1,
            "met": p1 >= 20,
        },
        {
            "label": "2. 금리피벗 · K-HAI",
            "rule": rr_note[1],
            "value": f"금리 {rc_val:+.2f}%p · K-HAI {khai_val:.0f}",
            "pts": p2,
            "met": p2 >= 20,
        },
        {
            "label": "3. 고점낙폭 · RSI(12)",
            "rule": rr_note[2],
            "value": f"낙폭 {dd_val:.1f}% · RSI {rsi_val:.1f}",
            "pts": p3,
            "met": p3 >= 20,
        },
        {
            "label": "4. 매매수급 · 입주절벽",
            "rule": rr_note[3],
            "value": f"수급 {sd_val:.1f} · 공급 {sup_val/10000:.1f}만호",
            "pts": p4,
            "met": p4 >= 20,
        },
    ]

    return {
        "score": total,
        "grade": grade,
        "en_grade": en_grade,
        "color": color,
        "comment": comment,
        "met_count": sum(1 for it in items if it["met"]),
        "items": items,
        "use_macro_filter": use_macro_filter,
    }


def generate_seoul_briefing(data: dict, apt_list: list[dict] | None = None) -> dict:
    """Synthesize macro, supply-demand, Jeonse, drawdown AND concrete Seoul apartment picks."""
    buy_idx = compute_seoul_buy_index(data)
    sd = data["supply_demand"]
    rsi = data["rsi"]
    jr = data["jeonse_ratio"]
    js = data["jeonse_support"]
    dd = data["selected"]["dd_5y_pct"]
    vol = data["volume"]
    rate = data["mortgage_rate"]
    supply = data["annual_supply"]

    signals: list[dict] = []

    # 1. Supply-Demand & Volume
    if sd <= 82:
        signals.append({
            "tag": "매매수급 · 거래량",
            "tone": "opportunity",
            "text": f"서울 매매수급지수 {sd:.1f}(매도우위) · 월 거래량 {vol:,}건으로 매수 심리가 크게 위축된 상태입니다. 역사적으로 급매 협상력이 가장 높아졌던 구간입니다.",
        })
    elif sd <= 98:
        signals.append({
            "tag": "매매수급 · 거래량",
            "tone": "info",
            "text": f"매매수급지수 {sd:.1f} · 월 거래량 {vol:,}건으로 고점 피로감 속 관망·숨고르기 장세입니다. 급매물 선별 매수에 유리한 매수자 우위 국면입니다.",
        })
    else:
        signals.append({
            "tag": "매매수급 · 거래량",
            "tone": "warning",
            "text": f"매매수급지수 {sd:.1f} · 월 거래량 {vol:,}건으로 매수세가 활발합니다. 호가 추격보다 눌림목·차선호지 키맞추기 접근이 안전합니다.",
        })

    # 2. Price Drawdown & Monthly RSI
    if dd <= -10.0:
        signals.append({
            "tag": "고점 낙폭 · RSI",
            "tone": "opportunity",
            "text": f"{data['selected']['name']}가 5년 고점 대비 {dd:.1f}% 하락, 월간 RSI(12) {rsi:.1f}로 깊은 가격 조정이 진행됐습니다.",
        })
    elif dd <= -4.0:
        signals.append({
            "tag": "고점 낙폭 · RSI",
            "tone": "info",
            "text": f"{data['selected']['name']}가 5년 고점 대비 {dd:.1f}% 조정 중(월간 RSI {rsi:.1f})입니다. 전고점 회복 시 +{data['selected']['recovery_pct']:.1f}% 반등 여력이 열려 있습니다.",
        })
    else:
        signals.append({
            "tag": "고점 낙폭 · RSI",
            "tone": "neutral",
            "text": f"{data['selected']['name']}가 5년 고점 대비 {dd:.1f}%로 신고가 부근에서 견조하게 버티고 있습니다(월간 RSI {rsi:.1f}).",
        })

    # 3. Jeonse Floor & Supply Cliff
    if supply <= 28000:
        signals.append({
            "tag": "전세지지 · 입주물량",
            "tone": "opportunity",
            "text": f"서울 연간 입주예정물량이 약 {supply:,.0f}호(적정 4만호 크게 하회)로 공급 절벽이 뚜렷합니다. 전세가율 {jr:.1f}% · 전세 선행 스프레드 {data['jeonse_lead_spread']:+.1f}%p가 하단을 받쳐줍니다.",
        })
    else:
        signals.append({
            "tag": "전세지지 · 입주물량",
            "tone": "neutral",
            "text": f"전세가율 {jr:.1f}%(하방지지 {js:+.1f}) · 연 입주물량 약 {supply:,.0f}호 수준입니다.",
        })

    # 4. Mortgage Rate & Concrete Apartment Complex Picks (with Prices!)
    if apt_list:
        top_picks = sorted(apt_list, key=lambda x: (-x["buy_score"], x["dd_peak_pct"]))[:3]
        pick_strs = [
            f"<b>{a['district']} {a['apt_name']}</b>(84㎡ {a['price_eok']:.1f}억 · 고점 대비 {a['dd_peak_pct']:.1f}% · 전세 {a['jeonse_eok']:.1f}억)"
            for a in top_picks
        ]
        signals.append({
            "tag": "주목 대장단지 · 가격",
            "tone": "opportunity",
            "text": "현재 낙폭·전세지지·입지 해자 기준 주목 단지: " + " / ".join(pick_strs),
        })
    else:
        signals.append({
            "tag": "금리 · 구매력",
            "tone": "info",
            "text": f"주담대 평균금리 {rate:.2f}% · 기준금리 {data['base_rate']:.2f}% · 서울 K-HAI {data['khai']:.0f} 수준입니다.",
        })

    return {
        "score": buy_idx["score"],
        "stance": buy_idx["grade"],
        "stance_color": buy_idx["color"],
        "summary": buy_idx["comment"],
        "signals": signals,
    }


def ask_gemini_realestate_agent(
    api_key: str,
    question: str,
    data: dict,
    briefing: dict,
    apt_list: list[dict],
) -> str:
    """Optional free Gemini API Q&A grounded in live Seoul macro + real apartment complex prices."""
    top_apts = sorted(apt_list, key=lambda x: -x["buy_score"])[:10]
    apt_lines = "\n".join(
        f"  - {a['district']} {a['dong']} {a['apt_name']} ({a['area_label']}): "
        f"매매 {a['price_eok']:.2f}억 (전고점 {a['peak_eok']:.2f}억 대비 {a['dd_peak_pct']:.1f}%), "
        f"전세 {a['jeonse_eok']:.2f}억 (전세가율 {a['jeonse_ratio']:.1f}%, 갭 {a['gap_eok']:.2f}억), "
        f"매수점수 {a['buy_score']}점 [{a['signal']}]"
        for a in top_apts
    )

    context = (
        f"[서울 부동산 시장 현황 ({data['last_date'].strftime('%Y-%m')} 기준)]\n"
        f"- 기준 지수({data['selected']['name']}): {data['selected']['value']:.1f} "
        f"(5년 고점 대비 {data['selected']['dd_5y_pct']:.1f}%, 전년 대비 {data['selected']['yoy_pct']:+.1f}%)\n"
        f"- 매매수급지수: {data['supply_demand']:.1f}, 월간 RSI(12): {data['rsi']:.1f}, "
        f"전세가율: {data['jeonse_ratio']:.1f}% (전세 하방지지 {data['jeonse_support']:+.1f})\n"
        f"- 서울 월 거래량: {data['volume']:,}건, 주담대 금리: {data['mortgage_rate']:.2f}%, "
        f"기준금리: {data['base_rate']:.2f}%, 주택가격전망 CSI: {data['csi']:.1f}, 연 입주물량: {data['annual_supply']:,.0f}호\n"
        f"- 서울 매수 추천 지수: {briefing['score']}/100 ({briefing['stance']})\n\n"
        f"[서울 주요 대장 아파트 실거래가·매수신호 스캔 TOP 10]\n{apt_lines}\n\n"
        f"당신은 냉철하고 데이터 중심적인 서울 부동산 애널리스트입니다. "
        f"위 지표와 실제 아파트 단지명·가격(억원)을 구체적으로 인용해 한국어로 명확하고 핵심만 간결하게 답하세요. "
        f"마지막에 투자 판단 책임 고지를 한 줄로 짧게 덧붙이세요.\n\n"
        f"질문: {question}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key.strip()}"
    payload = {"contents": [{"parts": [{"text": context}]}]}
    resp = requests.post(url, json=payload, timeout=25)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API 오류 ({resp.status_code}): {resp.text[:200]}")
    body = resp.json()
    return body["candidates"][0]["content"]["parts"][0]["text"]
