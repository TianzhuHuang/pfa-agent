"""
持仓截图 OCR — 通义千问 VL 多模态模型

上传券商持仓截图，qwen-vl-plus 直接提取结构化持仓数据。
比传统 OCR 准确率高，因为模型理解表格语义。

可选扩展：新闻/文章类截图可接入本地 OCR（如 PaddleOCR）做快速正文提取，
再由 qwen-plus 做摘要，以降低延迟；持仓表仍建议使用 qwen-vl-plus。
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

In addition to stocks, please look for cryptocurrency tickers like BTC, ETH, SOL, USDT. If found, extract them as asset type 'CRYPTO'.

请严格按以下 JSON 格式返回，不要包含任何其他文字。若截图中存在「可用」「可取」「可用保证金」等字样及对应金额，在根对象中增加 "available_balance" 字段（浮点数）。

返回格式一（仅有持仓）：直接返回 JSON 数组
[
  {
    "symbol": "股票代码（如 600519、00883、AAPL）或数字货币代码（如 BTC、ETH、USDT）",
    "name": "股票名称",
    "market": "市场（A/HK/US/CRYPTO/OTHER）",
    "currency": "原始币种（CNY/HKD/USD）",
    "quantity": 持仓数量（整数，没有则填0）,
    "cost_price": 成本价（浮点数，没有则填0）,
    "current_price": 现价（浮点数，没有则填0）,
    "position_pct": 仓位占比百分比（浮点数，没有则填0）
  }
]

返回格式二（有可用余额时）：返回 JSON 对象
{"holdings": [上述数组], "available_balance": 可用余额数值}

注意：
- 代码只保留数字/字母部分，去掉交易所前缀（如 SH、SZ）
- 港股代码统一 5 位：如 883 填 00883
- 若截图为交易所/币安等数字货币持仓，symbol 填 BTC、ETH、USDT 等，market 填 "CRYPTO"
- 若截图中有「沪港」「港股通」或「HK$」标识，该行 market 填 "HK"，currency 填 "HKD"
- 如果是 A 股（沪深），market 填 "A"，currency 填 "CNY"
- 如果是港股，market 填 "HK"，currency 填 "HKD"
- 如果是美股，market 填 "US"，currency 填 "USD"
- 只返回 JSON，不要返回 markdown 代码块或其他说明文字"""

EXTRACT_NEWS_PROMPT = """请摘录图片中的主要文字内容（如新闻标题、正文要点、关键数据），用于对话上下文。
要求：用中文、连贯的段落或要点列表；只返回文字内容，不要 JSON 或 markdown 标记。若图中无有效文字则返回「图中无文字内容」。"""


def extract_text_from_image(
    image_bytes: bytes,
    mime_type: str = "image/png",
) -> Dict[str, Any]:
    """从图片中提取文字（新闻/文章截图），用于对话上下文。"""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        return {"status": "error", "error": "DASHSCOPE_API_KEY 未设置", "text": ""}
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64}"
    try:
        resp = requests.post(
            DASHSCOPE_VL_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": VL_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": data_url}},
                            {"type": "text", "text": EXTRACT_NEWS_PROMPT},
                        ],
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 2000,
            },
            timeout=40,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        body = resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e), "text": ""}
    choices = body.get("choices", [])
    if not choices:
        return {"status": "error", "error": "模型返回空结果", "text": ""}
    text = (choices[0].get("message", {}).get("content", "") or "").strip()
    return {"status": "ok", "text": text}


def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).hexdigest() if False else base64.b64encode(image_bytes).decode("utf-8")


def _normalize_ocr_holdings(holdings: List[Dict]) -> List[Dict]:
    """后处理：港股 currency 补全、symbol 5 位标准化、CRYPTO 保留、去除后缀。"""
    from pfa.symbol_utils import normalize_hk_symbol
    out = []
    for h in holdings:
        h = dict(h)
        raw_market = (h.get("market") or "A").strip().upper()
        if raw_market in ("CRYPTO", "OT"):
            market = raw_market
        else:
            market = raw_market[:2] or "A"
        h["market"] = market
        if market == "HK":
            h["currency"] = "HKD"
            h["symbol"] = normalize_hk_symbol(h.get("symbol", ""))
        elif market in ("CRYPTO", "OT"):
            h["currency"] = (h.get("currency") or "USD").strip().upper() or "USD"
            h["symbol"] = (h.get("symbol") or "").strip().upper()
        else:
            cur = (h.get("currency") or "").strip().upper()
            if cur not in ("CNY", "USD", "HKD"):
                h["currency"] = "CNY" if market == "A" else "USD" if market == "US" else "CNY"
            sym = (h.get("symbol") or "").strip()
            for suffix in (".HK", ".hk", ".SH", ".sh", ".SZ", ".sz"):
                sym = sym.rstrip(suffix)
            h["symbol"] = sym
        out.append(h)
    return out


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
            timeout=40,
            proxies={"http": None, "https": None},  # 绕过系统代理，避免 ProxyError
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

    available_balance: Optional[float] = None
    try:
        parsed = json.loads(json_text)
        if isinstance(parsed, dict):
            available_balance = parsed.get("available_balance")
            if available_balance is not None:
                try:
                    available_balance = float(available_balance)
                except (TypeError, ValueError):
                    available_balance = None
            holdings = parsed.get("holdings", [parsed])
        else:
            holdings = parsed
        if not isinstance(holdings, list):
            holdings = [holdings]
    except json.JSONDecodeError:
        return {
            "status": "partial",
            "error": "模型返回的 JSON 解析失败，请查看原始输出",
            "holdings": [],
            "raw_response": raw_text,
        }

    holdings = _normalize_ocr_holdings(holdings)
    from pfa.ocr_correction import validate_and_correct_ocr_holdings
    holdings = validate_and_correct_ocr_holdings(holdings)
    out: Dict[str, Any] = {
        "status": "ok",
        "holdings": holdings,
        "raw_response": raw_text,
        "usage": body.get("usage", {}),
    }
    if available_balance is not None and available_balance > 0:
        out["available_balance"] = round(available_balance, 2)
    return out
