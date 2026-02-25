"""
持仓截图 OCR — 通义千问 VL 多模态模型

上传券商持仓截图，qwen-vl-plus 直接提取结构化持仓数据。
比传统 OCR 准确率高，因为模型理解表格语义。
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

DASHSCOPE_VL_URL = (
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
)
VL_MODEL = "qwen-vl-plus"

EXTRACT_PROMPT = """请从这张券商持仓截图中提取所有股票/基金的持仓信息。

请严格按以下 JSON 数组格式返回，不要包含任何其他文字：
[
  {
    "symbol": "股票代码（如 600519、00700、AAPL）",
    "name": "股票名称",
    "market": "市场（A/HK/US/OTHER）",
    "quantity": 持仓数量（整数，没有则填0）,
    "cost_price": 成本价（浮点数，没有则填0）,
    "current_price": 现价（浮点数，没有则填0）,
    "position_pct": 仓位占比百分比（浮点数，没有则填0）
  }
]

注意：
- 代码只保留数字/字母部分，去掉交易所前缀（如 SH、SZ）
- 如果是 A 股（沪深），market 填 "A"
- 如果是港股，market 填 "HK"
- 如果是美股，market 填 "US"
- 只返回 JSON 数组，不要返回 markdown 代码块或其他说明文字"""


def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).hexdigest() if False else base64.b64encode(image_bytes).decode("utf-8")


def extract_holdings_from_image(
    image_bytes: bytes,
    mime_type: str = "image/png",
) -> Dict[str, Any]:
    """Send a screenshot to qwen-vl-plus and extract holdings.

    Returns: {"status": "ok"/"error", "holdings": [...], "raw_response": "..."}
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        return {"status": "error", "error": "DASHSCOPE_API_KEY 未设置", "holdings": []}

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64}"

    try:
        resp = requests.post(
            DASHSCOPE_VL_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": VL_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": data_url}},
                            {"type": "text", "text": EXTRACT_PROMPT},
                        ],
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        body = resp.json()
    except requests.exceptions.HTTPError as e:
        err = e.response.text[:300] if e.response else str(e)
        return {"status": "error", "error": f"API 请求失败: {err}", "holdings": []}
    except Exception as e:
        return {"status": "error", "error": str(e), "holdings": []}

    choices = body.get("choices", [])
    if not choices:
        return {"status": "error", "error": "模型返回空结果", "holdings": []}

    raw_text = choices[0].get("message", {}).get("content", "")

    # Parse JSON from response (strip markdown fences if present)
    json_text = raw_text.strip()
    if json_text.startswith("```"):
        lines = json_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        json_text = "\n".join(lines)

    try:
        holdings = json.loads(json_text)
        if isinstance(holdings, dict):
            holdings = holdings.get("holdings", [holdings])
        if not isinstance(holdings, list):
            holdings = [holdings]
    except json.JSONDecodeError:
        return {
            "status": "partial",
            "error": "模型返回的 JSON 解析失败，请查看原始输出",
            "holdings": [],
            "raw_response": raw_text,
        }

    return {
        "status": "ok",
        "holdings": holdings,
        "raw_response": raw_text,
        "usage": body.get("usage", {}),
    }
