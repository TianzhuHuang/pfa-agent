"""
投研分析师 (The Analyst)

职责：只负责读数据。结合用户持仓，对 Scout 找回的信息
      进行深度解读，判断利好利空。
技术重点：Prompt Engineering、价值投资框架。

支持的 action:
  - analyze:   从新闻列表生成深度分析 (payload: items, holdings)

使用模型：通义千问 qwen-plus (DASHSCOPE_API_KEY)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.protocol import AgentMessage, make_response, make_error
from pfa.data.store import AnalysisRecord, save_analysis

CST = timezone(timedelta(hours=8))

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_MODEL = "qwen-plus"


def _call_llm(prompt: str, api_key: str, model: str = DASHSCOPE_MODEL) -> str:
    """Call DashScope OpenAI-compatible API."""
    resp = requests.post(
        DASHSCOPE_URL,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={"model": model,
              "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.3, "max_tokens": 2000},
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()
    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"LLM 返回空: {json.dumps(body, ensure_ascii=False)[:300]}")
    return choices[0]["message"]["content"], body.get("usage", {})


def build_analysis_prompt(holdings_desc: str, news_json: str) -> str:
    return (
        f"你是一位专业的基金经理助理。以下是用户当前持仓标的：\n"
        f"{holdings_desc}\n\n"
        f"以下是最近抓取到的与这些持仓相关的新闻列表（JSON 格式）：\n"
        f"{news_json}\n\n"
        f"请完成以下任务：\n"
        f"1. 从上述新闻中筛选出**最值得关注的 3 条信息**。\n"
        f"2. 对每条信息，说明：\n"
        f"   - 涉及哪个持仓标的\n"
        f"   - 为什么值得关注（对持仓可能产生什么影响）\n"
        f"   - 建议的关注等级（高/中/低）\n\n"
        f"输出要求：\n"
        f"- 使用中文回答\n"
        f"- 结构清晰，编号列出\n"
        f"- 每条附上原始新闻标题和链接\n"
        f"- 最后给出一句话总结：今天持仓整体的信息面情况"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(
    items: List[Dict], holdings: List[Dict]
) -> Dict[str, Any]:
    """Run analysis on a list of news items + holdings. Returns analysis dict."""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未设置")

    news_for_prompt = []
    for n in items:
        news_for_prompt.append({
            "holding": f"{n.get('symbol_name', n.get('symbol', '?'))}({n.get('symbol', '')})",
            "title": n.get("title", ""),
            "date": n.get("published_at", ""),
            "snippet": n.get("content_snippet", "")[:200],
            "url": n.get("url", ""),
        })

    holdings_desc = "、".join(
        f"{h.get('name', h['symbol'])}({h['symbol']}.{h.get('market', '?')})"
        for h in holdings
    )
    prompt = build_analysis_prompt(
        holdings_desc, json.dumps(news_for_prompt, ensure_ascii=False, indent=2)
    )

    text, usage = _call_llm(prompt, api_key)

    result = {
        "analysis_time": datetime.now(CST).isoformat(),
        "model": DASHSCOPE_MODEL,
        "holdings_analyzed": holdings_desc,
        "news_count_input": len(news_for_prompt),
        "token_usage": usage,
        "analysis": text,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rec = AnalysisRecord(
        id=ts, analysis_time=result["analysis_time"],
        model=result["model"], holdings_analyzed=holdings_desc,
        news_count_input=len(news_for_prompt),
        analysis=text, token_usage=usage,
    )
    save_analysis(rec)

    return result


# ---------------------------------------------------------------------------
# Agent message handler
# ---------------------------------------------------------------------------

def handle(msg: AgentMessage) -> AgentMessage:
    try:
        if msg.action == "analyze":
            result = analyze(
                msg.payload.get("items", []),
                msg.payload.get("holdings", []),
            )
            return make_response(msg, "analyst", **result)
        else:
            return make_error(msg, "analyst", f"未知 action: {msg.action}")
    except Exception as e:
        return make_error(msg, "analyst", str(e))
