"""
合规与监督员 (The Auditor)

职责：负责"挑刺"。监督分析师的结论是否有事实错误（幻觉），
      核对数据来源是否真实，检查逻辑是否自相矛盾。
技术重点：Cross-check（交叉验证）、事实核查逻辑。

支持的 action:
  - audit:  审核 Analyst 产出的分析报告
            (payload: analysis, items, holdings)

使用模型：OpenAI GPT (OPENAI_API_KEY)，与 Analyst 使用的 Qwen 形成
          模型差异化交叉验证。若 OPENAI_API_KEY 不可用，fallback 到
          DashScope qwen-max（不同于 Analyst 的 qwen-plus）。
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.protocol import AgentMessage, make_response, make_error

CST = timezone(timedelta(hours=8))

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def _call_openai(prompt: str, api_key: str) -> Tuple[str, Dict]:
    resp = requests.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={"model": "gpt-4o-mini",
              "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.2, "max_tokens": 1500},
        timeout=120,
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    body = resp.json()
    return body["choices"][0]["message"]["content"], body.get("usage", {})


def _call_dashscope(prompt: str, api_key: str) -> Tuple[str, Dict]:
    resp = requests.post(
        DASHSCOPE_URL,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={"model": "qwen-max",
              "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.2, "max_tokens": 1500},
        timeout=120,
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    body = resp.json()
    return body["choices"][0]["message"]["content"], body.get("usage", {})


def _pick_backend() -> Tuple[str, str]:
    """Choose the best available model backend. Returns (backend_name, api_key)."""
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        return "openai/gpt-4o-mini", openai_key
    dash_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if dash_key:
        return "dashscope/qwen-max", dash_key
    raise RuntimeError("Auditor 需要 OPENAI_API_KEY 或 DASHSCOPE_API_KEY")


def build_audit_prompt(analysis: str, news_json: str, holdings_desc: str) -> str:
    return (
        f"你是一位严格的投研合规审核员（\"杠精分析师\"）。\n"
        f"你的职责是审查以下投研分析报告，找出其中可能存在的：\n"
        f"1. **事实错误**：数据、数字、日期是否与原始新闻一致？\n"
        f"2. **逻辑漏洞**：推理链条是否自洽？结论是否由证据支撑？\n"
        f"3. **过度推断**：是否存在 AI 幻觉——即在原始新闻中找不到的信息？\n"
        f"4. **遗漏风险**：是否忽略了原始新闻中的重大负面信息？\n\n"
        f"--- 用户持仓 ---\n{holdings_desc}\n\n"
        f"--- 原始新闻（JSON） ---\n{news_json}\n\n"
        f"--- 待审核的分析报告 ---\n{analysis}\n\n"
        f"请输出审核意见，格式：\n"
        f"1. 对每个发现的问题，指出具体位置和性质。\n"
        f"2. 给出修正建议。\n"
        f"3. 最后用一句话给出**审核结论**：通过 / 需修正 / 存在重大问题。\n"
        f"使用中文回答。如果分析报告质量良好无明显问题，也请明确说明。"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def audit(
    analysis_text: str,
    items: List[Dict],
    holdings: List[Dict],
) -> Dict[str, Any]:
    """Audit an analyst report. Returns audit result dict.

    If the preferred backend fails, automatically falls back to the next
    available one so the audit pipeline is resilient.
    """
    backend, api_key = _pick_backend()

    holdings_desc = "、".join(
        f"{h.get('name', h['symbol'])}({h['symbol']}.{h.get('market', '?')})"
        for h in holdings
    )
    news_json = json.dumps(
        [{"title": n.get("title", ""), "date": n.get("published_at", ""),
          "snippet": n.get("content_snippet", "")[:150], "url": n.get("url", "")}
         for n in items[:20]],
        ensure_ascii=False, indent=2,
    )

    prompt = build_audit_prompt(analysis_text, news_json, holdings_desc)

    text, usage = None, {}
    if backend.startswith("openai"):
        try:
            text, usage = _call_openai(prompt, api_key)
        except Exception as e:
            dash_key = os.environ.get("DASHSCOPE_API_KEY", "")
            if dash_key:
                backend = "dashscope/qwen-max(fallback)"
                text, usage = _call_dashscope(prompt, dash_key)
            else:
                raise
    else:
        text, usage = _call_dashscope(prompt, api_key)

    return {
        "audit_time": datetime.now(CST).isoformat(),
        "backend": backend,
        "audit_result": text,
        "token_usage": usage,
    }


# ---------------------------------------------------------------------------
# Agent message handler
# ---------------------------------------------------------------------------

def handle(msg: AgentMessage) -> AgentMessage:
    try:
        if msg.action == "audit":
            result = audit(
                msg.payload.get("analysis", ""),
                msg.payload.get("items", []),
                msg.payload.get("holdings", []),
            )
            return make_response(msg, "auditor", **result)
        else:
            return make_error(msg, "auditor", f"未知 action: {msg.action}")
    except Exception as e:
        return make_error(msg, "auditor", str(e))
