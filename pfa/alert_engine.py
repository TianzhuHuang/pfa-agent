"""
持仓异动预警引擎

三类触发:
  1. 价格触发: 涨跌幅超过阈值
  2. 关键词触发: 新闻含高敏词（减持/重组/立案等）
  3. 研报触发: 出现个股深度解析

AI 解析: 结合持仓成本计算实际影响 + 校验投资备忘录逻辑
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

ROOT = Path = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CST = timezone(timedelta(hours=8))
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# High-sensitivity keywords (A-share context)
ALERT_KEYWORDS = [
    "减持", "增持", "重组", "立案", "调查", "处罚", "退市", "暂停上市",
    "业绩预亏", "业绩预减", "下调评级", "上调评级", "回购", "分红",
    "突发", "紧急", "暴跌", "暴涨", "涨停", "跌停", "熔断",
    "被查", "违规", "造假", "爆雷", "踩雷", "黑天鹅",
]

DEFAULT_THRESHOLD_PCT = 3.0


@dataclass
class Alert:
    """一条预警记录。"""
    symbol: str
    name: str
    alert_type: str          # price / keyword / report
    severity: str            # high / medium / low
    title: str
    detail: str
    current_price: float = 0
    change_pct: float = 0
    portfolio_impact_cny: float = 0
    ai_comment: str = ""
    action_hint: str = ""
    memo_check: str = ""
    triggered_at: str = ""
    source_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ===================================================================
# Trigger detection
# ===================================================================

def check_price_alerts(
    holdings: List[Dict],
    prices: Dict[str, Dict],
    threshold_pct: float = DEFAULT_THRESHOLD_PCT,
) -> List[Alert]:
    """Check for price movement alerts."""
    alerts = []
    now = datetime.now(CST).isoformat()

    for h in holdings:
        sym = h["symbol"]
        name = h.get("name", sym)
        p = prices.get(sym, {})
        pct = p.get("percent")
        current = p.get("current")

        if pct is None or current is None:
            continue

        pct = float(pct)
        current = float(current)

        if abs(pct) >= threshold_pct:
            cost = float(h.get("cost_price", 0) or 0)
            qty = float(h.get("quantity", 0) or 0)
            impact = (current - cost) * qty if cost > 0 and qty > 0 else 0

            severity = "high" if abs(pct) >= 5 else "medium"
            direction = "暴涨" if pct > 0 else "暴跌"

            alerts.append(Alert(
                symbol=sym, name=name,
                alert_type="price",
                severity=severity,
                title=f"{name} {direction} {pct:+.2f}%",
                detail=f"现价 {current}，{'涨' if pct > 0 else '跌'} {abs(pct):.2f}%",
                current_price=current,
                change_pct=pct,
                portfolio_impact_cny=impact,
                triggered_at=now,
            ))
    return alerts


def check_keyword_alerts(
    holdings: List[Dict],
    news_items: List[Dict],
) -> List[Alert]:
    """Check news for high-sensitivity keywords related to holdings."""
    alerts = []
    now = datetime.now(CST).isoformat()

    holding_names = {h["symbol"]: h.get("name", h["symbol"]) for h in holdings}
    holding_set = set(holding_names.keys())

    for item in news_items:
        title = item.get("title", "")
        snippet = item.get("content_snippet", "")
        text = f"{title} {snippet}"
        item_sym = item.get("symbol", "")

        if item_sym not in holding_set:
            continue

        matched_kw = [kw for kw in ALERT_KEYWORDS if kw in text]
        if not matched_kw:
            continue

        severity = "high" if any(k in text for k in ["立案", "退市", "暴跌", "爆雷", "造假"]) else "medium"

        alerts.append(Alert(
            symbol=item_sym,
            name=holding_names.get(item_sym, item_sym),
            alert_type="keyword",
            severity=severity,
            title=f"{holding_names.get(item_sym, item_sym)}: {matched_kw[0]}",
            detail=title[:80],
            triggered_at=now,
            source_url=item.get("url", ""),
        ))

    # Deduplicate by symbol + keyword
    seen = set()
    unique = []
    for a in alerts:
        key = f"{a.symbol}:{a.title}"
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


# ===================================================================
# AI analysis for alerts
# ===================================================================

def enrich_alert_with_ai(
    alert: Alert,
    holding: Dict,
    memos: List[Dict],
) -> Alert:
    """Use AI to analyze the alert in context of portfolio + memos."""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        return alert

    cost = holding.get("cost_price", 0)
    qty = holding.get("quantity", 0)
    memo_text = ""
    if memos:
        memo_text = "\n".join(
            f"- [{m.get('action','?')}] {m.get('text','')[:80]}"
            for m in memos[:3]
        )

    prompt = f"""你是一位投研预警分析师。以下是一条持仓异动预警：

标的: {alert.name}({alert.symbol})
异动类型: {alert.alert_type}
异动详情: {alert.title} — {alert.detail}
当前价: {alert.current_price}, 涨跌: {alert.change_pct:+.2f}%

用户持仓: 成本 {cost}, 数量 {qty}
持仓影响: 约 ¥{alert.portfolio_impact_cny:,.0f}

用户投资备忘录:
{memo_text if memo_text else '（无备忘录）'}

请用**一句话**给出:
1. ai_comment: 简洁分析原因
2. action_hint: 建议动作（维持/加仓/减仓/观望）
3. memo_check: 该事件是否证伪了用户备忘录中的买入理由？(是/否/无法判断 + 一句话说明)

严格按以下 JSON 格式输出:
{{"ai_comment": "...", "action_hint": "...", "memo_check": "..."}}"""

    try:
        resp = requests.post(
            DASHSCOPE_URL,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"model": "qwen-plus",
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.2, "max_tokens": 300},
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        data = json.loads(text)
        alert.ai_comment = data.get("ai_comment", "")
        alert.action_hint = data.get("action_hint", "")
        alert.memo_check = data.get("memo_check", "")
    except Exception:
        pass

    return alert


# ===================================================================
# Format for Telegram
# ===================================================================

def format_alert_telegram(alert: Alert) -> str:
    """Format a single alert for Telegram push."""
    severity_emoji = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(alert.severity, "⚪")
    type_label = {"price": "价格异动", "keyword": "舆情预警", "report": "研报触发"}.get(alert.alert_type, "异动")

    lines = [
        f"{severity_emoji} *{type_label}: {alert.name}*",
        "",
        f"📍 {alert.detail}",
    ]

    if alert.current_price:
        lines.append(f"💰 现价 {alert.current_price}，涨跌 {alert.change_pct:+.2f}%")

    if alert.portfolio_impact_cny:
        sign = "+" if alert.portfolio_impact_cny >= 0 else ""
        lines.append(f"📊 持仓影响: {sign}¥{alert.portfolio_impact_cny:,.0f}")

    if alert.ai_comment:
        lines.append(f"\n🤖 _{alert.ai_comment}_")

    if alert.action_hint:
        lines.append(f"👉 建议: *{alert.action_hint}*")

    if alert.memo_check:
        lines.append(f"📝 备忘校验: _{alert.memo_check}_")

    if alert.source_url:
        lines.append(f"\n[查看原文]({alert.source_url})")

    return "\n".join(lines)


# ===================================================================
# Main scan function
# ===================================================================

def run_alert_scan(
    threshold_pct: float = DEFAULT_THRESHOLD_PCT,
    push_telegram: bool = True,
) -> List[Alert]:
    """Run a full alert scan: price + keyword + AI enrichment + push."""
    from agents.secretary_agent import load_portfolio, get_memos
    from pfa.data.store import load_all_feed_items
    from pfa.telegram_push import send_message

    portfolio = load_portfolio()
    holdings = portfolio.get("holdings", [])
    if not holdings:
        return []

    all_alerts: List[Alert] = []

    # 1. Price alerts
    try:
        from pfa.portfolio_valuation import get_realtime_prices
        prices = get_realtime_prices(holdings)
        price_alerts = check_price_alerts(holdings, prices, threshold_pct)
        all_alerts.extend(price_alerts)
    except Exception as e:
        print(f"[ALERT] Price check failed: {e}")

    # 2. Keyword alerts from recent news
    news = load_all_feed_items(since_hours=4)
    news_dicts = [{"title": n.title, "content_snippet": n.content_snippet,
                   "symbol": n.symbol, "url": n.url} for n in news]
    kw_alerts = check_keyword_alerts(holdings, news_dicts)
    all_alerts.extend(kw_alerts)

    if not all_alerts:
        print("[ALERT] No alerts triggered.")
        return []

    # 3. AI enrichment
    for alert in all_alerts:
        h = next((h for h in holdings if h["symbol"] == alert.symbol), {})
        memos = get_memos(alert.symbol) if h else []
        enrich_alert_with_ai(alert, h, memos)

    # 4. Telegram push
    if push_telegram:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if token and chat_id:
            for alert in all_alerts:
                text = format_alert_telegram(alert)
                send_message(token, chat_id, text)
            print(f"[ALERT] Pushed {len(all_alerts)} alerts to Telegram")

    return all_alerts
