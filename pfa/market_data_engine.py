"""
PFAIntelEngine — 多轨行情引擎：Finnhub（美股/加密货币优先）、OKX/Gate.io 兜底、Yahoo 经代理（港/SGX）

统一输出格式：{ "symbol": str, "price": float, "source": str }。
代理基准地址由环境变量 PFA_PROXY_BASE 控制；若 workers.dev 持续不可达，请在 Cloudflare 绑定自定义域名并填入该变量。
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional

import requests

from pfa.proxy_fetch import get as proxy_get, use_proxy

_log = logging.getLogger("pfa.market_data_engine")

# Finnhub：美股与加密货币均可用 quote API；Token 优先环境变量
FINNHUB_API_KEY = "d6me301r01qi0ajlt2kgd6me301r01qi0ajlt2l0"
FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
OKX_TICKER_URL = "https://www.okx.com/api/v5/market/ticker"
GATEIO_TICKER_URL = "https://data.gateapi.io/api2/1/ticker/{pair}"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

RETRY_ATTEMPTS = 3
RETRY_MIN_SEC = 2
RETRY_MAX_SEC = 3
REQUEST_TIMEOUT = 10


def _finnhub_token() -> str:
    import os
    return (os.environ.get("FINNHUB_API_KEY") or os.environ.get("FINNHUB_TOKEN") or FINNHUB_API_KEY).strip()


def _get_with_retry(
    fn: Callable[[], Optional[Dict[str, Any]]],
    label: str = "",
) -> Optional[Dict[str, Any]]:
    """失败时随机等待 2–3 秒后重试，最多 3 次。"""
    last_err: Optional[Exception] = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            out = fn()
            if out is not None:
                return out
        except Exception as e:
            last_err = e
            _log.debug("%s attempt %d: %s", label or "request", attempt, e)
        if attempt < RETRY_ATTEMPTS:
            wait = random.uniform(RETRY_MIN_SEC, RETRY_MAX_SEC)
            time.sleep(wait)
    if last_err:
        _log.debug("%s failed after %d attempts: %s", label or "request", RETRY_ATTEMPTS, last_err)
    return None


def _norm(symbol: str) -> str:
    return str(symbol or "").strip().upper()


def _fetch_finnhub_quote(symbol: str, finnhub_symbol: str) -> Optional[Dict[str, Any]]:
    """Finnhub quote API。返回 { symbol, price, source } 或 None。"""
    try:
        r = requests.get(
            FINNHUB_QUOTE_URL,
            params={"symbol": finnhub_symbol, "token": _finnhub_token()},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        c = data.get("c")  # current price
        if c is None:
            return None
        return {"symbol": _norm(symbol), "price": float(c), "source": "finnhub"}
    except Exception as e:
        _log.debug("Finnhub %s (%s): %s", symbol, finnhub_symbol, e)
        return None


def _fetch_okx_price(symbol: str) -> Optional[Dict[str, Any]]:
    """OKX 直连。返回 { symbol, price, source } 或 None。"""
    try:
        inst_id = f"{_norm(symbol)}-USDT"
        r = requests.get(
            OKX_TICKER_URL,
            params={"instId": inst_id},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        tickers = data.get("data") or []
        if not tickers:
            return None
        last = tickers[0].get("last")
        if last is None:
            return None
        return {"symbol": _norm(symbol), "price": float(last), "source": "okx"}
    except Exception as e:
        _log.debug("OKX %s: %s", symbol, e)
        return None


def _fetch_gateio_price(symbol: str) -> Optional[Dict[str, Any]]:
    """Gate.io 公开接口，国内机房通常更稳。pair 格式 btc_usdt。"""
    try:
        pair = f"{_norm(symbol).lower()}_usdt"
        url = GATEIO_TICKER_URL.format(pair=pair)
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        last = data.get("last")
        if last is None:
            return None
        return {"symbol": _norm(symbol), "price": float(last), "source": "gateio"}
    except Exception as e:
        _log.debug("Gate.io %s: %s", symbol, e)
        return None


def _fetch_crypto_price(symbol: str) -> Optional[Dict[str, Any]]:
    """加密货币：Finnhub → OKX → Gate.io（超时/失败时切换）。"""
    sym = _norm(symbol)
    # 1) Finnhub（BINANCE:XXXUSDT）
    out = _get_with_retry(
        lambda: _fetch_finnhub_quote(symbol, f"BINANCE:{sym}USDT"),
        label=f"crypto-finnhub-{sym}",
    )
    if out:
        return out
    # 2) OKX
    out = _get_with_retry(lambda: _fetch_okx_price(symbol), label=f"crypto-okx-{sym}")
    if out:
        return out
    # 3) Gate.io 兜底
    out = _get_with_retry(lambda: _fetch_gateio_price(symbol), label=f"crypto-gateio-{sym}")
    return out


def _yahoo_symbol(symbol: str, market: str) -> Optional[str]:
    if market == "HK":
        return f"{_norm(symbol)}.HK"
    if market == "US":
        return _norm(symbol)
    if market == "SGX":
        s = _norm(symbol)
        return s if s.endswith(".SI") else f"{s}.SI"
    return None


def _fetch_yahoo_price(symbol: str, market: str) -> Optional[Dict[str, Any]]:
    """港/SGX 经 PFA_PROXY_BASE 代理访问 Yahoo（若已配置）。"""
    yahoo_sym = _yahoo_symbol(symbol, market)
    if not yahoo_sym:
        return None
    url = YAHOO_CHART_URL.format(symbol=yahoo_sym)
    params = {"interval": "1d", "range": "1d"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        if use_proxy():
            r = proxy_get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        else:
            r = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None
        meta = result[0].get("meta", {})
        current = meta.get("regularMarketPrice") or meta.get("previousClose")
        if current is None:
            return None
        return {"symbol": symbol, "price": float(current), "source": "yahoo"}
    except Exception as e:
        _log.debug("Yahoo %s (%s): %s", symbol, yahoo_sym, e)
        return None


def _fetch_us_price(symbol: str) -> Optional[Dict[str, Any]]:
    """美股：Finnhub 优先，失败再走 Yahoo（经代理）。"""
    sym = _norm(symbol)
    out = _fetch_finnhub_quote(symbol, sym)
    if out:
        return out
    return _fetch_yahoo_price(symbol, "US")


class PFAIntelEngine:
    """
    多轨行情：美股 Finnhub 优先；加密货币 Finnhub → OKX → Gate.io；港/SGX 走 Yahoo（经代理）。
    统一输出：{ symbol, price, source }。
    """

    def get_price(self, symbol: str, market: str) -> Optional[Dict[str, Any]]:
        """单标的价格。market: CRYPTO/OT(数字货币), HK, US, SGX."""
        market = str(market or "").upper()
        if market in ("OT", "CRYPTO"):
            return _fetch_crypto_price(symbol)
        if market == "US":
            return _fetch_us_price(symbol)
        if market in ("HK", "SGX"):
            return _fetch_yahoo_price(symbol, market)
        return None

    def get_multiple_prices(
        self,
        symbols_list: List[Dict[str, str]],
    ) -> List[Optional[Dict[str, Any]]]:
        """批量价格。返回与输入同序的列表，失败项为 None。每项为 { symbol, price, source }。"""
        results: List[Optional[Dict[str, Any]]] = []
        for item in symbols_list:
            sym = (item.get("symbol") or "").strip()
            mkt = (item.get("market") or "").upper()
            if not sym:
                results.append(None)
                continue
            results.append(self.get_price(sym, mkt))
        return results


def get_multiple_prices(symbols_list: List[Dict[str, str]]) -> List[Optional[Dict[str, Any]]]:
    """Convenience: PFAIntelEngine().get_multiple_prices(symbols_list)."""
    return PFAIntelEngine().get_multiple_prices(symbols_list)
