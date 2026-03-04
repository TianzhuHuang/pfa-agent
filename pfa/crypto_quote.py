"""
数字货币实时行情 — Binance 优先，CoinGecko 回退

免费 API，无需 key，支持 BTC/ETH/USDT 等主流币种。
Binance 在国内可能被墙，失败时自动回退 CoinGecko。
生产环境可通过 HTTP_PROXY/HTTPS_PROXY 配置代理。
"""

from __future__ import annotations

import logging
import os
import requests
from typing import Dict, List

logger = logging.getLogger("pfa.crypto_quote")


def _get_proxies() -> Dict[str, str | None]:
    """HTTP 代理：生产环境在国内时可配置 HTTP_PROXY/HTTPS_PROXY。"""
    http = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    proxy = https or http
    if proxy:
        return {"http": proxy, "https": proxy}
    return {"http": None, "https": None}

BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

# Binance 支持的 USDT 交易对（主流币）
BINANCE_USDT_SYMBOLS = {"BTC", "ETH", "USDT", "USDC", "BNB", "XRP", "ADA", "DOGE", "SOL", "DOT", "MATIC", "LTC", "SHIB", "TRX", "AVAX", "LINK", "UNI", "ATOM", "XMR", "ETC"}

# 常见数字货币 symbol -> CoinGecko ID 映射（非 Binance 或 Binance 失败时用）
SYMBOL_TO_COINGECKO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "USDC": "usd-coin",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "SOL": "solana",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LTC": "litecoin",
    "SHIB": "shiba-inu",
    "TRX": "tron",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "XMR": "monero",
    "ETC": "ethereum-classic",
}


def _get_crypto_holdings_symbols(holdings: List[Dict]) -> List[str]:
    """筛选数字货币持仓的 symbol 列表。"""
    crypto_symbols = []
    for h in holdings:
        market = str(h.get("market", "")).upper()
        account = str(h.get("account", "")).strip()
        if market in ("OT", "CRYPTO") or account == "数字货币":
            sym = str(h.get("symbol", "")).upper()
            if sym and (sym in BINANCE_USDT_SYMBOLS or sym in SYMBOL_TO_COINGECKO_ID):
                crypto_symbols.append(sym)
    return list(dict.fromkeys(crypto_symbols))  # 去重保序


def get_crypto_quotes_binance(holdings: List[Dict]) -> Dict[str, Dict]:
    """
    从 Binance 获取数字货币价格。国内可能被墙，失败返回空。
    Returns {symbol: {current, percent, name}}
    """
    symbols = _get_crypto_holdings_symbols(holdings)
    symbols = [s for s in symbols if s in BINANCE_USDT_SYMBOLS]
    if not symbols:
        return {}
    try:
        resp = requests.get(
            BINANCE_TICKER_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
            proxies=_get_proxies(),
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Binance API error: {e}")
        return {}
    # data 可能是单对象或数组；/ticker/price 无 symbol 时返回数组
    items = data if isinstance(data, list) else [data]
    results = {}
    for item in items:
        sym_raw = item.get("symbol", "")
        if sym_raw.endswith("USDT"):
            base = sym_raw[:-4]
            if base in symbols:
                try:
                    price = float(item.get("price", 0))
                    results[base] = {"current": price, "percent": 0, "name": base}
                except (ValueError, TypeError):
                    pass
    if results:
        logger.info(f"Binance: fetched {len(results)} crypto prices")
    return results


def get_crypto_quotes(holdings: List[Dict]) -> Dict[str, Dict]:
    """
    获取数字货币实时价格。Binance 优先，失败时回退 CoinGecko。

    Args:
        holdings: 持仓列表，筛选 market="OT" 或 market="CRYPTO" 或 account="数字货币" 的项

    Returns:
        {symbol: {current, percent, name}} 字典
    """
    symbols = _get_crypto_holdings_symbols(holdings)
    if not symbols:
        return {}

    # 先试 Binance
    results = get_crypto_quotes_binance(holdings)
    missing = [s for s in symbols if s not in results and s in SYMBOL_TO_COINGECKO_ID]
    if not missing:
        return results

    # 回退 CoinGecko（补全 Binance 未覆盖的币种）
    coin_ids = [SYMBOL_TO_COINGECKO_ID[s] for s in missing]
    if not coin_ids:
        return results

    try:
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        }
        resp = requests.get(
            COINGECKO_API,
            params=params,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=10,
            proxies=_get_proxies(),
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        logger.warning("CoinGecko API timeout")
        return {}
    except Exception as e:
        logger.error(f"CoinGecko API error: {e}")
        return {}

    # 解析 CoinGecko 结果并合并
    id_to_symbol = {v: k for k, v in SYMBOL_TO_COINGECKO_ID.items()}
    for coin_id, prices in data.items():
        symbol = id_to_symbol.get(coin_id)
        if not symbol or symbol not in missing:
            continue
        current = prices.get("usd")
        if current is None:
            continue
        pct_24h = prices.get("usd_24h_change", 0) or 0
        results[symbol] = {
            "current": float(current),
            "percent": round(float(pct_24h), 2),
            "name": coin_id.replace("-", " ").title(),
            "source": "coingecko",
        }
    cg_added = sum(1 for s in missing if s in results)
    if cg_added:
        logger.info(f"CoinGecko: fetched {cg_added} crypto prices (fallback)")

    return results
