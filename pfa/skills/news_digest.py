from __future__ import annotations

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from pfa.data.store import FeedItem, AnalysisRecord, load_all_feed_items, save_analysis

CST = timezone(timedelta(hours=8))
DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_MODEL = "qwen-plus"


def holding_news_digest(
    *,
    symbols: List[str],
    since_hours: int = 72,
    user_id: str = "admin",
    max_items_per_symbol: int = 15,
) -> Optional[AnalysisRecord]:
    """Summarize recent news for a set of symbols into a single analysis record."""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        return None

    items: List[FeedItem] = []
    for sym in symbols:
        items.extend(load_all_feed_items(symbol=sym, since_hours=since_hours, user_id=user_id)[:max_items_per_symbol])

    if not items:
        return None

    lines = []
    for it in items[:60]:
        ts = (it.published_at or "")[:16]
        lines.append(f"- [{ts}] {it.symbol_name}({it.symbol}) {it.title} | {it.url}")
    news_text = "\n".join(lines)

    prompt = f"""你是一位投研分析师。以下是用户持仓相关的近期新闻清单：\n\n{news_text}\n\n请输出：\n1) 最值得关注的 3-5 条（用编号）\n2) 每条：影响标的、影响方向（利好/利空/中性）、关注等级（高/中/低）、一句话理由\n3) 最后用 2-3 句总结整体信息面\n\n要求：中文、简洁、有结构。"""

    resp = requests.post(
        DASHSCOPE_API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": DASHSCOPE_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 1200},
        timeout=60,
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    body = resp.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "") or ""

    rec = AnalysisRecord(
        id=datetime.now(CST).strftime("%Y%m%d_%H%M%S"),
        analysis_time=datetime.now(CST).isoformat(),
        model=body.get("model", DASHSCOPE_MODEL),
        holdings_analyzed=",".join(symbols),
        news_count_input=len(items),
        analysis=content.strip(),
        token_usage=body.get("usage", {}) or {},
    )
    save_analysis(rec, user_id=user_id)
    return rec

