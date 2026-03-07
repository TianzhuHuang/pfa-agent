"""
新加坡市场 (SGX) 实时行情 — Yahoo Finance API

免费 API，无需 key。TradingView 的 SGX:T14 对应 Yahoo 的 T14.SI。
生产环境可通过 HTTP_PROXY/HTTPS_PROXY 配置代理。
"""

from __future__ import annotations

import logging
import os
import requests
from typing import Dict, List

from pfa.proxy_fetch import get as proxy_get, use_proxy

logger = logging.getLogger("pfa.sgx_quote")


def _get_proxies() -> Dict[str, str | None]:
    """HTTP 代理：生产环境在国内时可配置（PFA_PROXY_BASE 未设置时）。"""
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if proxy:
        return {"http": proxy, "https": proxy}
    return {"http": None, "https": None}

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def _to_yahoo_sgx_symbol(symbol: str) -> str:
    """Convert PFA symbol to Yahoo SGX format. T14 -> T14.SI"""
    sym = str(symbol).strip().upper()
    if not sym:
        return ""
    if sym.endswith(".SI"):
        return sym
    return f"{sym}.SI"


def get_sgx_quotes(holdings: List[Dict]) -> Dict[str, Dict]:
    """
    获取 SGX 标的实时价格。

    Args:
        holdings: 持仓列表，market="SGX" 或 exchange="SGX" 或 OT 中疑似 SGX 的标的

    Returns:
        {symbol: {current, percent, name}} 字典
    """
    results = {}
    for h in holdings:
        sym = h.get("symbol", "")
        if not sym:
            continue
        yahoo_sym = _to_yahoo_sgx_symbol(sym)
        if not yahoo_sym:
            continue
        try:
            url = YAHOO_CHART_URL.format(symbol=yahoo_sym)
            params = {"interval": "1d", "range": "1d"}
            headers = {"User-Agent": "Mozilla/5.0"}
            if use_proxy():
                resp = proxy_get(url, params=params, headers=headers, timeout=8)
            else:
                resp = requests.get(url, params=params, headers=headers, timeout=8, proxies=_get_proxies())
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.debug(f"Yahoo SGX {yahoo_sym} error: {e}")
            continue
        try:
            result = data.get("chart", {}).get("result", [])
            if not result:
                continue
            meta = result[0].get("meta", {})
            current = meta.get("regularMarketPrice") or meta.get("previousClose")
            if current is None:
                continue
            prev = meta.get("previousClose") or current
            pct = ((float(current) - float(prev)) / float(prev) * 100) if prev else 0
            results[sym] = {
                "current": float(current),
                "percent": round(pct, 2),
                "name": meta.get("shortName") or h.get("name", sym),
            }
        except (KeyError, TypeError, ValueError):
            continue
    if results:
        logger.info(f"Yahoo SGX: fetched {len(results)} prices")
    return results
