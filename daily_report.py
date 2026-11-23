"""Standalone daily US market report generator & sender (Telegram + HTML Email).

Designed to run automatically on GitHub Actions every US market close
(Tue-Sat 07:30 KST) even when your MacBook is completely turned off.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
import sys

import pandas as pd
import requests
import yfinance as yf

from agent_analyzer import (
    classify_drawdown,
    classify_mfi,
    classify_rsi,
    generate_agent_briefing,
)
from indicators import summarize_index

CNN_FG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://edition.cnn.com/markets/fear-and-greed",
}


def _clean_hist(hist: pd.DataFrame) -> pd.DataFrame:
    df = hist.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])


def fetch_index_standalone(symbol: str, name: str) -> dict:
    ticker = yf.Ticker(symbol)
    hist = _clean_hist(ticker.history(period="5y", interval="1d", auto_adjust=False))
    if hist.empty:
        raise RuntimeError(f"{symbol} 데이터를 불러오지 못했습니다.")
    return summarize_index(hist, symbol=symbol, name=name)


def fetch_vix_standalone() -> dict:
    try:
        hist = _clean_hist(yf.Ticker("^VIX").history(period="1mo", interval="1d"))
        price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        return {"price": price, "change_pct": ((price - prev) / prev * 100.0) if prev else 0.0}
    except Exception:
        return {"price": None, "change_pct": 0.0}


def rating_to_korean(rating: str) -> tuple[str, str]:
    r = (rating or "").strip().lower()
    if "extreme fear" in r:
        return "극단적 공포", "#ef4444"
    if "fear" in r:
        return "공포", "#f97316"
    if "extreme greed" in r:
        return "극단적 탐욕", "#10b981"
    if "greed" in r:
        return "탐욕", "#22c55e"
    return "중립", "#eab308"


def fetch_fear_greed_standalone(vix_price: float | None) -> dict:
    try:
        resp = requests.get(CNN_FG_URL, headers=CNN_HEADERS, timeout=15)
        resp.raise_for_status()
        fg = resp.json().get("fear_and_greed", {})
        score = float(fg["score"])
        rating = fg.get("rating", "neutral")
        kr_label, color = rating_to_korean(rating)
        return {
            "score": score,
            "rating": rating,
            "kr_label": kr_label,
            "color": color,
            "previous_close": float(fg.get("previous_close", score)),
            "previous_1_week": float(fg.get("previous_1_week", score)),
            "previous_1_month": float(fg.get("previous_1_month", score)),
            "previous_1_year": float(fg.get("previous_1_year", score)),
        }
    except Exception:
        v = vix_price or 20.0
        est = float(max(5.0, min(95.0, 100.0 - (v - 10.0) * 3.0)))
        rating = "extreme fear" if est < 25 else "fear" if est < 45 else "neutral" if est <= 55 else "greed"
        kr_label, color = rating_to_korean(rating)
        return {
            "score": est,
            "rating": rating,
            "kr_label": f"{kr_label} (VIX 추정)",
            "color": color,
            "previous_close": est,
            "previous_1_week": est,
            "previous_1_month": est,
            "previous_1_year": est,
        }


def collect_market_snapshot() -> tuple[dict, dict]:
    sp500 = fetch_index_standalone("^GSPC", "S&P 500")
    nasdaq = fetch_index_standalone("^IXIC", "NASDAQ 종합")
    nasdaq_100 = fetch_index_standalone("^NDX", "NASDAQ 100")
    vix = fetch_vix_standalone()
    fg = fetch_fear_greed_standalone(vix.get("price"))
    data = {
        "sp500": sp500,
        "nasdaq": nasdaq,
        "nasdaq_comp": nasdaq,
        "nasdaq_100": nasdaq_100,
        "vix": vix,
        "fear_greed": fg,
    }
    briefing = generate_agent_briefing(data)
    return data, briefing


def format_telegram_message(data: dict, briefing: dict, dashboard_url: str = "") -> str:
    kst_str = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST")
    sp = data["sp500"]
    nq = data["nasdaq"]
    ndx = data["nasdaq_100"]
    fg = data["fear_greed"]
    vix = data["vix"]

    rsi_label, _, _ = classify_rsi(nq.get("rsi"))
    mfi_label, _, _ = classify_mfi(nq.get("mfi"))
    sp_dd_lbl, _ = classify_drawdown(sp["dd_ath_pct"])
    nq_dd_lbl, _ = classify_drawdown(nq["dd_ath_pct"])

    sp_arrow = "🟢" if sp["change"] >= 0 else "🔴"
    nq_arrow = "🟢" if nq["change"] >= 0 else "🔴"
    fg_diff = fg["score"] - fg["previous_close"]

    lines = [
        f"📊 <b>미국 증시 모닝 브리핑</b> ({kst_str})",
        "",
        f"{sp_arrow} <b>S&amp;P 500</b>: <code>{sp['price']:,.2f}</code> ({sp['change_pct']:+.2f}%)",
        f"   └ 고점 대비: <b>{sp['dd_ath_pct']:.2f}%</b> ({sp_dd_lbl} · 회복 +{sp['recovery_ath_pct']:.1f}%)",
        "",
        f"{nq_arrow} <b>NASDAQ 종합</b>: <code>{nq['price']:,.2f}</code> ({nq['change_pct']:+.2f}%)",
        f"   └ 고점 대비: <b>{nq['dd_ath_pct']:.2f}%</b> ({nq_dd_lbl} · 회복 +{nq['recovery_ath_pct']:.1f}%)",
        f"   └ <b>RSI(14)</b>: <code>{nq['rsi']:.1f}</code> ({rsi_label})",
        f"   └ <b>MFI(14)</b>: <code>{nq['mfi']:.1f}</code> ({mfi_label})",
        f"   └ 참고) 나스닥100 고점 대비: <b>{ndx['dd_ath_pct']:.2f}%</b>",
        "",
        f"😱 <b>CNN 공포·탐욕 지수</b>: <code>{fg['score']:.1f}</code> — <b>{fg['kr_label']}</b> ({fg_diff:+.1f})",
        f"   └ 전일 {fg['previous_close']:.1f} · 1주전 {fg['previous_1_week']:.1f} · 1개월전 {fg['previous_1_month']:.1f}",
    ]
    if vix.get("price") is not None:
        lines.append(f"⚡ <b>VIX 변동성</b>: <code>{vix['price']:.2f}</code> ({vix['change_pct']:+.1f}%)")

    lines += [
        "",
        f"🤖 <b>에이전트 진단</b>: <b>{briefing['stance']} ({briefing['score']}/100)</b>",
        f"{briefing['summary']}",
    ]

    if dashboard_url:
        lines += ["", f"🔗 <a href=\"{dashboard_url}\">실시간 웹 대시보드 열기</a>"]

    return "\n".join(lines)


def format_email_html(data: dict, briefing: dict, dashboard_url: str = "") -> str:
    kst_str = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST")
    sp = data["sp500"]
    nq = data["nasdaq"]
    ndx = data["nasdaq_100"]
    fg = data["fear_greed"]
    rsi_label, rsi_color, _ = classify_rsi(nq.get("rsi"))
    mfi_label, mfi_color, _ = classify_mfi(nq.get("mfi"))

    cta_html = (
        f'<div style="margin-top:20px; text-align:center;">'
        f'<a href="{dashboard_url}" style="display:inline-block; background:#38bdf8; color:#070b14; '
        f'font-weight:700; text-decoration:none; padding:12px 24px; border-radius:10px;">실시간 웹 대시보드 열기 →</a>'
        f'</div>'
        if dashboard_url
        else ""
    )

    signal_items = "".join(
        f'<li style="margin-bottom:8px; color:#cbd5e1;"><b style="color:#7dd3fc;">[{s["tag"]}]</b> {s["text"]}</li>'
        for s in briefing["signals"]
    )

    return f"""
    <html>
    <body style="margin:0; padding:24px; background:#070b14; font-family:-apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif; color:#f8fafc;">
      <div style="max-width:620px; margin:0 auto; background:#0f172a; border:1px solid #1e293b; border-radius:16px; padding:24px;">
        <div style="font-size:12px; color:#38bdf8; font-weight:700; letter-spacing:1px;">US MARKET STOCK AGENT</div>
        <h2 style="margin:6px 0 4px 0; color:#f8fafc;">미국 증시 모닝 리포트</h2>
        <div style="font-size:13px; color:#94a3b8; margin-bottom:20px;">{kst_str}</div>

        <table style="width:100%; border-collapse:separate; border-spacing:0 10px;">
          <tr>
            <td style="background:#070b14; border:1px solid #1e293b; border-radius:12px; padding:14px;">
              <div style="font-size:12px; color:#94a3b8;">S&amp;P 500 (^GSPC)</div>
              <div style="font-size:22px; font-weight:800; margin:4px 0;">{sp['price']:,.2f} <span style="font-size:14px; color:{'#10b981' if sp['change']>=0 else '#ef4444'};">({sp['change_pct']:+.2f}%)</span></div>
              <div style="font-size:13px; color:#cbd5e1;">고점 대비 낙폭: <b style="color:#f59e0b;">{sp['dd_ath_pct']:.2f}%</b> · 고점 회복 필요 +{sp['recovery_ath_pct']:.1f}%</div>
            </td>
          </tr>
          <tr>
            <td style="background:#070b14; border:1px solid #1e293b; border-radius:12px; padding:14px;">
              <div style="font-size:12px; color:#94a3b8;">NASDAQ 종합 (^IXIC)</div>
              <div style="font-size:22px; font-weight:800; margin:4px 0;">{nq['price']:,.2f} <span style="font-size:14px; color:{'#10b981' if nq['change']>=0 else '#ef4444'};">({nq['change_pct']:+.2f}%)</span></div>
              <div style="font-size:13px; color:#cbd5e1;">고점 대비 낙폭: <b style="color:#ef4444;">{nq['dd_ath_pct']:.2f}%</b> (나스닥100: {ndx['dd_ath_pct']:.2f}%)</div>
              <div style="font-size:13px; margin-top:6px;">
                RSI(14): <b style="color:{rsi_color};">{nq['rsi']:.1f} ({rsi_label})</b> &nbsp;|&nbsp;
                MFI(14): <b style="color:{mfi_color};">{nq['mfi']:.1f} ({mfi_label})</b>
              </div>
            </td>
          </tr>
          <tr>
            <td style="background:#070b14; border:1px solid #1e293b; border-radius:12px; padding:14px;">
              <div style="font-size:12px; color:#94a3b8;">CNN 공포 · 탐욕 지수</div>
              <div style="font-size:22px; font-weight:800; margin:4px 0; color:{fg['color']};">{fg['score']:.1f} — {fg['kr_label']}</div>
              <div style="font-size:12px; color:#94a3b8;">전일 {fg['previous_close']:.1f} · 1주전 {fg['previous_1_week']:.1f} · 1개월전 {fg['previous_1_month']:.1f}</div>
            </td>
          </tr>
        </table>

        <div style="margin-top:16px; background:#111c33; border:1px solid #1e3a5f; border-radius:12px; padding:16px;">
          <div style="font-size:12px; color:#38bdf8; font-weight:700;">AI QUANT AGENT 진단 · {briefing['score']}/100</div>
          <div style="font-size:16px; font-weight:700; color:{briefing['stance_color']}; margin:4px 0 8px 0;">{briefing['stance']}</div>
          <div style="font-size:13px; color:#e2e8f0; margin-bottom:10px;">{briefing['summary']}</div>
          <ul style="margin:0; padding-left:18px; font-size:13px; line-height:1.55;">{signal_items}</ul>
        </div>
        {cta_html}
      </div>
    </body>
    </html>
    """


def send_telegram(bot_token: str, chat_id: str, text_html: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text_html,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    resp.raise_for_status()
    print("✅ Telegram report sent successfully.")


def send_email(sender: str, password: str, receiver: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(sender, password)
        server.sendmail(sender, [r.strip() for r in receiver.split(",")], msg.as_string())
    print("✅ Email report sent successfully.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Send daily US Stock Agent report.")
    parser.add_argument("--dry-run", action="store_true", help="Print report without sending.")
    args = parser.parse_args()

    data, briefing = collect_market_snapshot()
    dashboard_url = os.getenv("DASHBOARD_URL", "").strip()
    tg_msg = format_telegram_message(data, briefing, dashboard_url=dashboard_url)

    if args.dry_run:
        print("=== DRY RUN: TELEGRAM MESSAGE PREVIEW ===")
        print(tg_msg)
        return 0

    sent_any = False

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if bot_token and chat_id:
        send_telegram(bot_token, chat_id, tg_msg)
        sent_any = True

    email_sender = os.getenv("EMAIL_SENDER", "").strip()
    email_password = os.getenv("EMAIL_PASSWORD", "").strip()
    email_receiver = os.getenv("EMAIL_RECEIVER", "").strip()
    if email_sender and email_password and email_receiver:
        kst_date = datetime.now(timezone(timedelta(hours=9))).strftime("%m/%d")
        fg = data["fear_greed"]
        nq = data["nasdaq"]
        subject = (
            f"[미국증시 {kst_date}] 나스닥 {nq['change_pct']:+.2f}% "
            f"(고점대비 {nq['dd_ath_pct']:.1f}%) · 공탐 {fg['score']:.0f}({fg['kr_label']})"
        )
        html_body = format_email_html(data, briefing, dashboard_url=dashboard_url)
        send_email(email_sender, email_password, email_receiver, subject, html_body)
        sent_any = True

    if not sent_any:
        print("ℹ️ No TELEGRAM_* or EMAIL_* secrets configured yet. Printing preview:")
        print(tg_msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
