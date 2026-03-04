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
    """Call DashScope OpenAI-compatible API. 绕过代理避免 ProxyError。"""
    resp = requests.post(
        DASHSCOPE_URL,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={"model": model,
              "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.3, "max_tokens": 4096},
        timeout=60,  # 60 秒超时，超时后由 Secretary 返回明确错误
        proxies={"http": None, "https": None},  # 绕过系统代理，避免 ProxyError
    )
    resp.raise_for_status()
    body = resp.json()
    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"LLM 返回空: {json.dumps(body, ensure_ascii=False)[:300]}")
    return choices[0]["message"]["content"], body.get("usage", {})


BRIEFING_PROMPT = """你是一位专业的基金经理助理（投研晨报生成器）。

用户持仓标的：{holdings_desc}

以下是最近抓取到的新闻列表（JSON）：
{news_json}

请生成一份结构化的投研晨报，严格按以下 JSON 格式输出（不要输出任何其他文字，只输出 JSON）：

{{
  "market_sentiment": {{
    "score": 0-100 的整数（50=中性，>50 偏多，<50 偏空）,
    "label": "Bullish" 或 "Bearish" 或 "Neutral",
    "reason": "一句话说明市场情绪判断依据"
  }},
  "must_reads": [
    {{
      "title": "新闻标题",
      "summary": "一句话摘要（不超过50字）",
      "url": "原始链接",
      "sentiment": "positive/negative/neutral",
      "impact_on_portfolio": "对用户持仓的具体影响（一句话）",
      "related_symbol": "相关标的代码（如 600519），无则留空",
      "priority": "high/medium/low"
    }}
  ],
  "portfolio_moves": [
    {{
      "symbol": "标的代码",
      "name": "标的名称",
      "event_summary": "该标的今日关键事件（一句话）",
      "sentiment": "positive/negative/neutral",
      "action_hint": "建议关注方向（如：关注渠道价格变化、留意油价走势）"
    }}
  ],
  "one_liner": "今日持仓整体信息面的一句话总结"
}}

要求：
- must_reads 选 5 条最值得关注的（从所有新闻中挑选，不限于持仓相关）
- portfolio_moves 为每个有新闻的持仓标的生成一条
- 使用中文
- 只输出 JSON，不要 markdown 代码块

排版规范（必须遵守）：
- reason、summary、impact_on_portfolio、event_summary、action_hint 等文本字段中，段落之间用 \\n\\n 分隔
- 多要点时用 Markdown 列表格式（- 或 1.）
- 异动标的用列表形式呈现，便于阅读"""


def build_analysis_prompt(holdings_desc: str, news_json: str) -> str:
    return BRIEFING_PROMPT.format(holdings_desc=holdings_desc, news_json=news_json)


def _sanitize_for_json(text: str) -> str:
    """修复截断的 Unicode 字符，确保 JSON 可解析。"""
    if not text:
        return text
    # 1. 若为 bytes 则按 UTF-8 解码（忽略无效字节）
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="ignore")
    # 2. 移除 U+FFFD（替换字符），常由截断的多字节序列产生
    text = text.replace("\uFFFD", "")
    # 3. 移除其他可能破坏 JSON 的控制字符（保留 \n \t）
    text = "".join(c for c in text if c in "\n\t\r" or (ord(c) >= 32 and ord(c) != 127))
    return text


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
            "title": (n.get("title", "") or "")[:80],
            "date": n.get("published_at", ""),
            "snippet": (n.get("content_snippet", "") or "")[:150],
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

    # Parse structured JSON from LLM response
    briefing = None
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        clean = "\n".join(lines)

    # 修复截断的 Unicode：移除 U+FFFD 及无效 UTF-8，避免 json.loads 失败
    clean = _sanitize_for_json(clean)

    # 多种尝试解析 JSON
    try:
        briefing = json.loads(clean)
    except json.JSONDecodeError as e:
        # 尝试提取 JSON 对象（处理可能的尾部垃圾字符）
        import re
        json_match = re.search(r'\{.*\}', clean, re.DOTALL)
        if json_match:
            extracted = _sanitize_for_json(json_match.group())
            try:
                briefing = json.loads(extracted)
            except json.JSONDecodeError:
                # 尝试修复常见问题：截断的 JSON
                partial = extracted
                # 计算括号平衡，尝试补全
                open_braces = partial.count('{') - partial.count('}')
                open_brackets = partial.count('[') - partial.count(']')
                if open_braces > 0 or open_brackets > 0:
                    # 截断的 JSON，尝试补全
                    fix = partial.rstrip(',\n ')
                    fix += ']' * open_brackets + '}' * open_braces
                    try:
                        briefing = json.loads(fix)
                    except json.JSONDecodeError:
                        print(f"[Analyst] JSON 解析失败，尝试修复后仍失败: {str(e)[:100]}")

    result = {
        "analysis_time": datetime.now(CST).isoformat(),
        "model": DASHSCOPE_MODEL,
        "holdings_analyzed": holdings_desc,
        "news_count_input": len(news_for_prompt),
        "token_usage": usage,
        "analysis": text,
        "briefing": briefing,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_for_store = text
    if briefing:
        analysis_for_store = json.dumps(briefing, ensure_ascii=False, indent=2)
    rec = AnalysisRecord(
        id=ts, analysis_time=result["analysis_time"],
        model=result["model"], holdings_analyzed=holdings_desc,
        news_count_input=len(news_for_prompt),
        analysis=analysis_for_store, token_usage=usage,
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
