"""
PFAIntelEngine — 双轨制行情引擎：OKX（数字货币）+ Yahoo 经代理（港/美/SGX）

提供标准化价格接口 { symbol, price, source, updated_at }，便于仪表盘「高净值资产追踪」等扩展。
港/美/SGX 一律经 PFA_PROXY_BASE 代理访问 Yahoo；未配置代理时 Yahoo 请求会失败。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from pfa.proxy_fetch import get as proxy_get, use_proxy

_log = logging.getLogger("pfa.market_data_engine")

OKX_TICKER_URL = "https://www.okx.com/api/v5/market/ticker"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def _yahoo_symbol(symbol: str, market: str) -> Optional[str]:
    if market == "HK":
        return f"{str(symbol).strip().upper()}.HK"
    if market == "US":
        return str(symbol).strip().upper()
    if market == "SGX":
        s = str(symbol).strip().upper()
        return s if s.endswith(".SI") else f"{s}.SI"
    return None


def _fetch_okx_price(symbol: str) -> Optional[Dict[str, Any]]:
    """Single crypto via OKX. Returns { symbol, price, source, updated_at } or None."""
    try:
        inst_id = f"{symbol.upper()}-USDT"
        r = requests.get(OKX_TICKER_URL, params={"instId": inst_id}, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        r.raise_for_status()
        data = r.json()
        tickers = data.get("data") or []
        if not tickers:
            return None
        last = tickers[0].get("last")
        if last is None:
            return None
        return {
            "symbol": symbol.upper(),
            "price": float(last),
            "source": "okx",
            "updated_at": time.time(),
        }
    except Exception as e:
        _log.debug("OKX %s: %s", symbol, e)
        return None


def _fetch_yahoo_price(symbol: str, market: str) -> Optional[Dict[str, Any]]:
    """HK/US/SGX via Yahoo, always through proxy when PFA_PROXY_BASE is set."""
    yahoo_sym = _yahoo_symbol(symbol, market)
    if not yahoo_sym:
        return None
    url = YAHOO_CHART_URL.format(symbol=yahoo_sym)
    params = {"interval": "1d", "range": "1d"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        if use_proxy():
            r = proxy_get(url, params=params, headers=headers, timeout=10)
        else:
            r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None
        meta = result[0].get("meta", {})
        current = meta.get("regularMarketPrice") or meta.get("previousClose")
        if current is None:
            return None
        return {
            "symbol": symbol,
            "price": float(current),
            "source": "yahoo",
            "updated_at": time.time(),
        }
    except Exception as e:
        _log.debug("Yahoo %s (%s): %s", symbol, yahoo_sym, e)
        return None


class PFAIntelEngine:
    """
    双轨制行情：数字货币走 OKX，港/美/SGX 走 Yahoo（经代理）。
    返回结构统一：{ symbol, price, source, updated_at }。
    """

    def get_price(self, symbol: str, market: str) -> Optional[Dict[str, Any]]:
        """单标的价格。market: CRYPTO/OT(当数字货币), HK, US, SGX."""
        market = str(market or "").upper()
        if market in ("OT", "CRYPTO"):
            return _fetch_okx_price(symbol)
        if market in ("HK", "US", "SGX"):
            return _fetch_yahoo_price(symbol, market)
        return None

    def get_multiple_prices(
        self,
        symbols_list: List[Dict[str, str]],
    ) -> List[Optional[Dict[str, Any]]]:
        """
        批量价格。symbols_list 每项需含 symbol 与 market。
        返回与输入同序的列表，失败项为 None。
        """
        results: List[Optional[Dict[str, Any]]] = []
        for item in symbols_list:
            sym = (item.get("symbol") or "").strip()
            mkt = (item.get("market") or "").upper()
            if not sym:
                results.append(None)
                continue
            out = self.get_price(sym, mkt)
            results.append(out)
        return results


def get_multiple_prices(symbols_list: List[Dict[str, str]]) -> List[Optional[Dict[str, Any]]]:
    """Convenience: PFAIntelEngine().get_multiple_prices(symbols_list)."""
    return PFAIntelEngine().get_multiple_prices(symbols_list)
