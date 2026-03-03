"""
AI 记账助理 — 自然语言解析持仓操作

支持: "平安证券加仓 500 股中海油，价格 21.5"
      "卖出 100 股茅台"
      "添加 AAPL 200股 成本 185.5 到盈透账户"
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import requests

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

PARSE_PROMPT = """你是一个持仓管理助理。用户会用自然语言描述持仓变动，请解析为结构化 JSON。

严格输出以下 JSON 格式（不要输出其他文字）：
{{
  "action": "add" 或 "remove" 或 "update",
  "symbol": "股票代码（如 600519、00883、AAPL）",
  "name": "股票名称",
  "market": "A 或 HK 或 US",
  "quantity": 数量（整数）,
  "price": 价格（浮点数，没提到则为0）,
  "account": "账户名称（没提到则为空字符串）",
  "confidence": 0-100 的置信度
}}

规则：
- "加仓"、"买入"、"添加" = action: "add"
- "卖出"、"减仓"、"清仓" = action: "remove"
- "修改"、"更新成本"、"数量改为"、"数量为" = action: "update"
- "数量为0"、"清仓" = action: "update" (quantity=0)
- "记录"、"备忘"、"笔记"、"因为"、"理由"、"看好"、"看空" = action: "memo"
  (此时 quantity 和 price 可为0, 把用户说的原因写入 text)
- memo 时 action 字段里的子类型用 memo_action 字段: buy/sell/hold/watch/note
- 腾讯 / 腾讯控股 = 00700, 市场 HK
- 中海油 / 中国海洋石油 = 00883, 市场 HK
- 茅台 = 600519, 市场 A
- 片仔癀 = 600436, 市场 A
- 五粮液 = 000858, 市场 A
- 如果用户没明确说代码，根据名称推断
- 只输出 JSON

用户输入: {user_input}"""


def parse_portfolio_command(user_input: str) -> Dict[str, Any]:
    """Parse natural language portfolio command into structured action."""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        return {"error": "DASHSCOPE_API_KEY 未设置"}

    prompt = PARSE_PROMPT.format(user_input=user_input)

    try:
        resp = requests.post(
            DASHSCOPE_URL,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"model": "qwen-plus",
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.1, "max_tokens": 500},
            timeout=30,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        result = json.loads(text)
        return result
    except json.JSONDecodeError:
        return {"error": f"解析失败: {text[:200]}"}
    except Exception as e:
        return {"error": str(e)}
