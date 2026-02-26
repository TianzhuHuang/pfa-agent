"""
Telegram 推送 — 将投研晨报推送到手机

环境变量:
  TELEGRAM_BOT_TOKEN: Bot API Token
  TELEGRAM_CHAT_ID: 接收消息的 Chat ID

用法:
  python -m pfa.telegram_push              # 手动推送最新晨报
  python -m pfa.telegram_push --discover   # 获取 Chat ID
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CST = timezone(timedelta(hours=8))
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _call(method: str, token: str, **params) -> Dict:
    url = TELEGRAM_API.format(token=token, method=method)
    resp = requests.post(url, json=params, timeout=15)
    return resp.json()


def discover_chat_id(token: str) -> Optional[str]:
    """Get the chat_id from the most recent message to the bot."""
    data = _call("getUpdates", token, limit=5)
    if data.get("ok") and data.get("result"):
        for update in reversed(data["result"]):
            msg = update.get("message", {})
            chat = msg.get("chat", {})
            if chat.get("id"):
                return str(chat["id"])
    return None


def send_message(token: str, chat_id: str, text: str,
                 parse_mode: str = "Markdown") -> bool:
    """Send a text message via Telegram."""
    result = _call("sendMessage", token,
                   chat_id=chat_id, text=text,
                   parse_mode=parse_mode,
                   disable_web_page_preview=True)
    return result.get("ok", False)


def format_briefing_telegram(briefing: Dict) -> str:
    """Format a structured briefing dict into Telegram-friendly Markdown."""
    lines = []

    # Header
    now = datetime.now(CST)
    lines.append(f"📊 *PFA 投研晨报* · {now.strftime('%m月%d日 %A')}")
    lines.append("")

    # Sentiment
    ms = briefing.get("market_sentiment", {})
    score = ms.get("score", 50)
    label = ms.get("label", "Neutral")
    emoji = "📈" if label == "Bullish" else "📉" if label == "Bearish" else "➡️"
    lines.append(f"{emoji} *{label}* (情绪: {score}/100)")
    reason = ms.get("reason", "")
    if reason:
        lines.append(f"_{reason}_")
    lines.append("")

    # Must-reads
    must_reads = briefing.get("must_reads", [])
    if must_reads:
        lines.append("*📌 今日必读*")
        for i, item in enumerate(must_reads[:5], 1):
            title = item.get("title", "")
            summary = item.get("summary", "")
            sentiment = item.get("sentiment", "")
            s_emoji = "🔴" if sentiment == "positive" else "🟢" if sentiment == "negative" else "⚪"
            impact = item.get("impact_on_portfolio", "")
            lines.append(f"{i}. {s_emoji} *{title}*")
            if summary:
                lines.append(f"   {summary}")
            if impact:
                lines.append(f"   💼 _{impact}_")
            lines.append("")

    # Portfolio moves
    moves = briefing.get("portfolio_moves", [])
    if moves:
        lines.append("*📋 持仓异动*")
        for m in moves:
            name = m.get("name", "")
            sym = m.get("symbol", "")
            evt = m.get("event_summary", "")
            s = m.get("sentiment", "neutral")
            s_emoji = "🔴" if s == "positive" else "🟢" if s == "negative" else "⚪"
            lines.append(f"  {s_emoji} *{name}*({sym}): {evt}")
        lines.append("")

    # One-liner
    one = briefing.get("one_liner", "")
    if one:
        lines.append(f"💡 _{one}_")

    return "\n".join(lines)


def push_briefing(briefing: Dict,
                  token: Optional[str] = None,
                  chat_id: Optional[str] = None) -> bool:
    """Format and push a briefing to Telegram."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("[TELEGRAM] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return False

    text = format_briefing_telegram(briefing)
    ok = send_message(token, chat_id, text)
    if ok:
        print(f"[TELEGRAM] Briefing pushed to chat {chat_id}")
    else:
        print(f"[TELEGRAM] Push failed")
    return ok


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("Set TELEGRAM_BOT_TOKEN first")
        sys.exit(1)

    if args.discover:
        cid = discover_chat_id(token)
        if cid:
            print(f"Chat ID: {cid}")
            print(f"Set: export TELEGRAM_CHAT_ID={cid}")
        else:
            print("No messages found. Send a message to the bot first.")
    else:
        from pfa.data.store import load_all_analyses
        analyses = load_all_analyses()
        if analyses:
            try:
                briefing = json.loads(analyses[0].analysis)
                chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
                if not chat_id:
                    chat_id = discover_chat_id(token)
                if chat_id:
                    push_briefing(briefing, token, chat_id)
                else:
                    print("No chat_id. Send a message to the bot first.")
            except json.JSONDecodeError:
                print("Latest analysis is not structured JSON")
        else:
            print("No analyses found. Run the pipeline first.")
