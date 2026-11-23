"""Stock Agent quantitative briefing & optional free Gemini LLM Q&A engine."""

from __future__ import annotations

import requests


def classify_rsi(rsi: float | None) -> tuple[str, str, str]:
    if rsi is None:
        return "데이터 없음", "#94a3b8", "계산 대기 중"
    if rsi <= 30:
        return "과매도 (Oversold)", "#10b981", "단기 매도 압력 극심 · 반등 가능 구간"
    if rsi <= 42:
        return "약세 접근", "#38bdf8", "하락 모멘텀 우위 · 분할 관심 구간"
    if rsi < 58:
        return "중립 (Neutral)", "#eab308", "매수·매도 힘 균형 상태"
    if rsi < 70:
        return "강세 모멘텀", "#f97316", "상승 추세 유지 · 추격 매수 유의"
    return "과매수 (Overbought)", "#ef4444", "단기 과열 구간 · 조정 리스크 경계"


def classify_mfi(mfi: float | None) -> tuple[str, str, str]:
    if mfi is None:
        return "데이터 없음", "#94a3b8", "거래량 데이터 확인 필요"
    if mfi <= 20:
        return "강한 과매도 (자금 이탈 극심)", "#10b981", "거래량 동반 투매 · 바닥권 시그널"
    if mfi <= 35:
        return "자금 유출 우위", "#38bdf8", "매수 자금 약화 · 저점 다지기 확인 필요"
    if mfi < 65:
        return "자금 흐름 중립", "#eab308", "정상적인 거래대금 순환 구간"
    if mfi < 80:
        return "자금 유입 활발", "#f97316", "매수세 유입 강함 · 상승 탄력 양호"
    return "과매수 (자금 과열)", "#ef4444", "거래량 과열 · 단기 차익실현 주의"


def classify_drawdown(dd_pct: float) -> tuple[str, str]:
    if dd_pct >= -3.0:
        return "신고가 부근", "#10b981"
    if dd_pct >= -10.0:
        return "정상 눌림목", "#38bdf8"
    if dd_pct >= -20.0:
        return "조정장 (Correction)", "#f59e0b"
    return "약세장 (Bear Market)", "#ef4444"


def generate_agent_briefing(data: dict) -> dict:
    """Synthesize S&P 500, NASDAQ (RSI/MFI), Drawdown, and Fear & Greed into an actionable agent report."""
    sp = data["sp500"]
    nq = data["nasdaq"]
    fg = data["fear_greed"]
    vix = data["vix"]

    score = 50  # 0 (극단적 과열/주의) ~ 100 (역발상 매수 기회)
    signals: list[dict] = []

    # 1. Fear & Greed signal
    fg_score = fg["score"]
    if fg_score <= 25:
        score += 18
        signals.append({
            "tag": "공포·탐욕",
            "tone": "opportunity",
            "text": f"CNN 공포·탐욕 지수가 {fg_score:.1f}점({fg['kr_label']})으로 극심한 투심 위축 구간입니다. 역사적으로 중장기 분할 매수 승률이 높았던 영역입니다.",
        })
    elif fg_score <= 45:
        score += 8
        signals.append({
            "tag": "공포·탐욕",
            "tone": "info",
            "text": f"공포·탐욕 지수 {fg_score:.1f}점({fg['kr_label']})으로 투자 심리가 보수적입니다.",
        })
    elif fg_score >= 75:
        score -= 18
        signals.append({
            "tag": "공포·탐욕",
            "tone": "warning",
            "text": f"공포·탐욕 지수 {fg_score:.1f}점({fg['kr_label']})으로 시장 과열 신호입니다. 신규 추격 매수보다 현금 비중 관리가 유리합니다.",
        })
    else:
        signals.append({
            "tag": "공포·탐욕",
            "tone": "neutral",
            "text": f"공포·탐욕 지수 {fg_score:.1f}점({fg['kr_label']})으로 심리가 비교적 안정적입니다.",
        })

    # 2. NASDAQ RSI & MFI signal
    nq_rsi = nq.get("rsi")
    nq_mfi = nq.get("mfi")
    if nq_rsi is not None and nq_mfi is not None:
        if nq_rsi <= 35 and nq_mfi <= 30:
            score += 17
            signals.append({
                "tag": "나스닥 RSI/MFI",
                "tone": "opportunity",
                "text": f"{nq['name']} RSI({nq_rsi:.1f})와 MFI({nq_mfi:.1f})가 동반 과매도권에 진입했습니다. 가격과 거래량 자금 흐름 모두 단기 바닥 신호를 가리킵니다.",
            })
        elif nq_rsi >= 70 or nq_mfi >= 80:
            score -= 15
            signals.append({
                "tag": "나스닥 RSI/MFI",
                "tone": "warning",
                "text": f"{nq['name']} RSI({nq_rsi:.1f}) / MFI({nq_mfi:.1f})가 과매수 영역입니다. 단기 숨 고르기 가능성을 염두에 두세요.",
            })
        else:
            gap = nq_mfi - nq_rsi
            if gap > 12:
                signals.append({
                    "tag": "나스닥 자금흐름",
                    "tone": "info",
                    "text": f"MFI({nq_mfi:.1f})가 RSI({nq_rsi:.1f})보다 높아 가격 대비 거래대금 유입(저가 매수세)이 상대적으로 강합니다.",
                })
            elif gap < -12:
                signals.append({
                    "tag": "나스닥 자금흐름",
                    "tone": "warning",
                    "text": f"MFI({nq_mfi:.1f})가 RSI({nq_rsi:.1f})보다 낮아 반등 시 거래량 뒷받침이 약한 상태입니다.",
                })
            else:
                signals.append({
                    "tag": "나스닥 RSI/MFI",
                    "tone": "neutral",
                    "text": f"{nq['name']} RSI {nq_rsi:.1f} · MFI {nq_mfi:.1f}로 가격과 거래량 모멘텀이 균형 구간에 있습니다.",
                })

    # 3. Drawdown from High signal
    sp_dd = sp["dd_ath_pct"]
    nq_dd = nq["dd_ath_pct"]
    if nq_dd <= -20.0:
        score += 15
        signals.append({
            "tag": "고점 대비 낙폭",
            "tone": "opportunity",
            "text": f"{nq['name']} 고점 대비 {nq_dd:.2f}%(약세장 진입), S&P 500 {sp_dd:.2f}% 하락 상태입니다. 고점 회복 시 +{nq['recovery_ath_pct']:.1f}% 상승 여력이 존재합니다.",
        })
    elif nq_dd <= -10.0 or sp_dd <= -10.0:
        score += 8
        signals.append({
            "tag": "고점 대비 낙폭",
            "tone": "info",
            "text": f"S&P 500 고점 대비 {sp_dd:.2f}%, {nq['name']} {nq_dd:.2f}%로 조정장(Correction) 구간입니다. 급락 시 단계적 분할 접근 전략이 유효합니다.",
        })
    else:
        score -= 5
        signals.append({
            "tag": "고점 대비 낙폭",
            "tone": "neutral",
            "text": f"S&P 500 고점 대비 {sp_dd:.2f}%, {nq['name']} {nq_dd:.2f}%로 고점 부근에서 견조하게 버티고 있습니다.",
        })

    # 4. VIX volatility check
    vix_price = vix.get("price")
    if vix_price is not None:
        if vix_price >= 28:
            signals.append({
                "tag": "변동성(VIX)",
                "tone": "warning",
                "text": f"VIX 공포지수가 {vix_price:.2f}로 매우 높습니다. 단기 급등락 변동성이 크므로 한 번에 몰빵 매수보다 분할 매수가 안전합니다.",
            })
        elif vix_price <= 15:
            signals.append({
                "tag": "변동성(VIX)",
                "tone": "neutral",
                "text": f"VIX {vix_price:.2f}로 시장 변동성이 안정적인 구간입니다.",
            })

    score = max(0, min(100, score))

    if score >= 75:
        stance = "역발상 분할 매수 관심 구간"
        stance_color = "#10b981"
        summary = "극단적 공포와 고점 대비 큰 낙폭이 겹친 구간입니다. 변동성을 감안해 3~5회 이상 시간 분산 매수를 고려해볼 만한 자리입니다."
    elif score >= 60:
        stance = "점진적 매집 · 저점 탐색"
        stance_color = "#38bdf8"
        summary = "조정 구간에서 기술적 과매도 또는 심리 위축 신호가 감지됩니다. 핵심 지수 ETF 중심으로 분할 접근을 검토할 수 있습니다."
    elif score >= 42:
        stance = "중립 · 추세 확인 관망"
        stance_color = "#eab308"
        summary = "뚜렷한 과매도나 과열 신호가 섞여 있는 균형 구간입니다. 기존 보유 비중을 유지하며 추세 방향을 확인하세요."
    else:
        stance = "단기 과열 경계 · 리스크 관리"
        stance_color = "#ef4444"
        summary = "고점 부근 과열 및 탐욕 신호가 우세합니다. 추격 매수를 자제하고 일부 수익 실현 또는 현금 비중 확보를 권장합니다."

    return {
        "score": score,
        "stance": stance,
        "stance_color": stance_color,
        "summary": summary,
        "signals": signals,
    }


def _lerp_score(val: float, best_val: float, worst_val: float, max_pts: float = 25.0) -> float:
    """Linearly interpolate points when lower value is better (e.g. F&G, RSI, MFI, Drawdown)."""
    if val <= best_val:
        return max_pts
    if val >= worst_val:
        return 0.0
    ratio = (worst_val - val) / (worst_val - best_val)
    return max(0.0, min(max_pts, ratio * max_pts))


def compute_market_buy_index(data: dict) -> dict:
    """Compute transparent 0~100 Market Buy Recommendation Index from 4 core conditions (25 pts each).

    1. CNN Fear & Greed <= 10 (25 pts)
    2. NASDAQ RSI(14) <= 30 (25 pts)
    3. NASDAQ MFI(14) <= 20 (25 pts)
    4. NASDAQ Drawdown from ATH <= -20% (25 pts)
    """
    fg_val = float(data["fear_greed"]["score"])
    nq = data["nasdaq"]
    rsi_val = nq.get("rsi")
    mfi_val = nq.get("mfi")
    dd_val = float(nq["dd_ath_pct"])

    # 1) Fear & Greed <= 10 -> 25 pts, >= 80 -> 0 pts
    fg_pts = round(_lerp_score(fg_val, best_val=10.0, worst_val=80.0, max_pts=25.0), 1)
    fg_met = fg_val <= 10.0

    # 2) NASDAQ RSI <= 30 -> 25 pts, >= 72 -> 0 pts
    rsi_pts = round(_lerp_score(float(rsi_val), best_val=30.0, worst_val=72.0, max_pts=25.0), 1) if rsi_val is not None else 12.5
    rsi_met = rsi_val is not None and rsi_val <= 30.0

    # 3) NASDAQ MFI <= 20 -> 25 pts, >= 80 -> 0 pts
    mfi_pts = round(_lerp_score(float(mfi_val), best_val=20.0, worst_val=80.0, max_pts=25.0), 1) if mfi_val is not None else 12.5
    mfi_met = mfi_val is not None and mfi_val <= 20.0

    # 4) NASDAQ Drawdown <= -20% -> 25 pts, >= -1% -> 0 pts
    dd_pts = round(_lerp_score(dd_val, best_val=-20.0, worst_val=-1.0, max_pts=25.0), 1)
    dd_met = dd_val <= -20.0

    total = int(round(fg_pts + rsi_pts + mfi_pts + dd_pts))
    total = max(0, min(100, total))

    if total >= 85:
        grade = "🟢 강력 매수"
        en_grade = "STRONG BUY"
        color = "#15803d"
        comment = "공포·과매도·고점 낙폭 조건이 집중 충족된 드문 분할 매수 기회 구간입니다."
    elif total >= 68:
        grade = "🔵 매수 추천"
        en_grade = "BUY"
        color = "#1d4ed8"
        comment = "하락 과매도 신호가 우세합니다. 보유 시드를 구간별로 나누어 매수하기 유리한 자리입니다."
    elif total >= 45:
        grade = "🟡 중립 · 관망"
        en_grade = "NEUTRAL"
        color = "#b45309"
        comment = "뚜렷한 저점 할인이나 과열이 아닌 중간 구간입니다. 추세를 확인하며 천천히 대응하세요."
    elif total >= 25:
        grade = "🟠 매수 주의"
        en_grade = "CAUTION"
        color = "#c2410c"
        comment = "고점 부근이거나 투자 심리가 다소 뜨겁습니다. 신규 추격 매수는 신중해야 합니다."
    else:
        grade = "🔴 매수 금지"
        en_grade = "DO NOT BUY"
        color = "#b91c1c"
        comment = "극심한 탐욕과 기술적 과매수 구간입니다. 신규 매수를 멈추고 현금 비중을 지키세요."

    items = [
        {
            "label": "1. 공포·탐욕 지수",
            "rule": "10 이하",
            "value": f"{fg_val:.1f}",
            "pts": fg_pts,
            "met": fg_met,
        },
        {
            "label": "2. 나스닥 RSI(14)",
            "rule": "30 이하",
            "value": f"{rsi_val:.1f}" if rsi_val is not None else "N/A",
            "pts": rsi_pts,
            "met": rsi_met,
        },
        {
            "label": "3. 나스닥 MFI(14)",
            "rule": "20 이하",
            "value": f"{mfi_val:.1f}" if mfi_val is not None else "N/A",
            "pts": mfi_pts,
            "met": mfi_met,
        },
        {
            "label": f"4. {nq['name']} 낙폭",
            "rule": "-20% 이하",
            "value": f"{dd_val:.2f}%",
            "pts": dd_pts,
            "met": dd_met,
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
    }


def ask_gemini_agent(api_key: str, question: str, data: dict, briefing: dict) -> str:
    """Optional free Gemini API Q&A using live market context (REST call, no extra SDK needed)."""
    sp = data["sp500"]
    nq = data["nasdaq"]
    fg = data["fear_greed"]
    vix = data["vix"]

    context = (
        f"[실시간 미국 증시 데이터]\n"
        f"- S&P 500: {sp['price']:,.2f} ({sp['change_pct']:+.2f}%), 고점({sp['ath_price']:,.2f}) 대비 {sp['dd_ath_pct']:.2f}%, RSI(14)={sp['rsi']:.1f}\n"
        f"- {nq['name']}: {nq['price']:,.2f} ({nq['change_pct']:+.2f}%), 고점({nq['ath_price']:,.2f}) 대비 {nq['dd_ath_pct']:.2f}%, RSI(14)={nq['rsi']:.1f}, MFI(14)={nq['mfi']:.1f}\n"
        f"- CNN 공포·탐욕 지수: {fg['score']:.1f} ({fg['kr_label']}), 전일 {fg['previous_close']:.1f}, 1주전 {fg['previous_1_week']:.1f}, 1개월전 {fg['previous_1_month']:.1f}\n"
        f"- VIX: {vix.get('price')}\n"
        f"- 에이전트 정량 판단: {briefing['stance']} (점수 {briefing['score']}/100)\n\n"
        f"당신은 침착하고 객관적인 월스트리트 퀀트 주식 에이전트입니다. 위 실시간 데이터를 바탕으로 아래 질문에 한국어로 명확하고 핵심만 간결하게 답하세요. 투자 책임 고지는 한 줄로 짧게 덧붙이세요.\n\n"
        f"질문: {question}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key.strip()}"
    payload = {"contents": [{"parts": [{"text": context}]}]}
    resp = requests.post(url, json=payload, timeout=25)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API 오류 ({resp.status_code}): {resp.text[:200]}")
    body = resp.json()
    return body["candidates"][0]["content"]["parts"][0]["text"]
