"""
股票搜索服务 — 东方财富 Suggest API

支持 A 股、港股、美股，按代码 / 名称 / 拼音模糊搜索。
无需 API Key。
"""

from __future__ import annotations

import requests
from typing import Any, Dict, List

SUGGEST_URL = "https://searchapi.eastmoney.com/api/suggest/get"
SUGGEST_TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"

MARKET_MAP = {
    "沪A": "A", "深A": "A", "北A": "A",
    "港股": "HK", "美股": "US",
}


def search_stock(keyword: str, count: int = 8) -> List[Dict[str, str]]:
    """Search stocks by code, name, or pinyin abbreviation.

    Returns list of dicts with keys: code, name, market, market_raw, type.
    """
    if not keyword or not keyword.strip():
        return []
    try:
        resp = requests.get(
            SUGGEST_URL,
            params={"input": keyword.strip(), "type": 14,
                    "token": SUGGEST_TOKEN, "count": count},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    results = []
    for item in data.get("QuotationCodeTable", {}).get("Data", []):
        market_raw = item.get("SecurityTypeName", "")
        market = MARKET_MAP.get(market_raw, "OTHER")
        results.append({
            "code": item.get("Code", ""),
            "name": item.get("Name", ""),
            "market": market,
            "market_raw": market_raw,
            "type": item.get("Type", ""),
        })
    return results
