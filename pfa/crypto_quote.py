"""
数字货币实时行情 — Finnhub / OKX / Gate.io / Binance / CoinGecko 多链路

国内机房：Finnhub 与 Gate.io 通常可达；OKX/Binance/CoinGecko 可能超时或被墙，按顺序尝试。
"""

from __future__ import annotations

import logging
import os
import requests
from typing import Dict, List

from pfa.proxy_fetch import get as proxy_get, use_proxy

logger = logging.getLogger("pfa.crypto_quote")

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
FINNHUB_TOKEN_DEFAULT = "d6me301r01qi0ajlt2kgd6me301r01qi0ajlt2l0"
GATEIO_TICKER_URL = "https://data.gateapi.io/api2/1/ticker/{pair}"


def _get_proxies() -> Dict[str, str | None]:
    """HTTP 代理：生产环境在国内时可配置（PFA_PROXY_BASE 未设置时）。"""
    http = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    proxy = https or http
    if proxy:
        return {"http": proxy, "https": proxy}
    return {"http": None, "https": None}

OKX_TICKER_URL = "https://www.okx.com/api/v5/market/ticker"
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


def _finnhub_token() -> str:
    return (os.environ.get("FINNHUB_API_KEY") or os.environ.get("FINNHUB_TOKEN") or FINNHUB_TOKEN_DEFAULT).strip()


def get_crypto_quotes_finnhub(holdings: List[Dict]) -> Dict[str, Dict]:
    """数字货币：Finnhub BINANCE:XXXUSDT，国内机房通常可达。"""
    symbols = _get_crypto_holdings_symbols(holdings)
    if not symbols:
        return {}
    results = {}
    token = _finnhub_token()
    for sym in symbols:
        try:
            r = requests.get(
                FINNHUB_QUOTE_URL,
                params={"symbol": f"BINANCE:{sym}USDT", "token": token},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            c = data.get("c")
            if c is None:
                continue
            results[sym] = {"current": float(c), "percent": 0, "name": sym, "source": "finnhub"}
        except Exception as e:
            logger.debug("Finnhub crypto %s: %s", sym, e)
    if results:
        logger.info("Finnhub: fetched %d crypto prices", len(results))
    return results


def get_crypto_quotes_gateio(holdings: List[Dict]) -> Dict[str, Dict]:
    """数字货币：Gate.io 公开接口，国内机房通常较稳。"""
    symbols = _get_crypto_holdings_symbols(holdings)
    if not symbols:
        return {}
    results = {}
    for sym in symbols:
        try:
            url = GATEIO_TICKER_URL.format(pair=f"{sym.lower()}_usdt")
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            r.raise_for_status()
            data = r.json()
            last = data.get("last")
            if last is None:
                continue
            results[sym] = {"current": float(last), "percent": 0, "name": sym, "source": "gateio"}
        except Exception as e:
            logger.debug("Gate.io %s: %s", sym, e)
    if results:
        logger.info("Gate.io: fetched %d crypto prices", len(results))
    return results


def get_crypto_quotes_okx(holdings: List[Dict]) -> Dict[str, Dict]:
    """
    从 OKX 获取数字货币价格。直连；机房不可达时可依赖后续 Binance/CoinGecko 经代理。
    Returns {symbol: {current, percent, name}}
    """
    symbols = _get_crypto_holdings_symbols(holdings)
    if not symbols:
        return {}
    results = {}
    for sym in symbols:
        try:
            inst_id = f"{sym}-USDT"
            resp = requests.get(
                OKX_TICKER_URL,
                params={"instId": inst_id},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            tickers = data.get("data") or []
            if not tickers:
                continue
            last = tickers[0].get("last")
            if last is None:
                continue
            results[sym] = {"current": float(last), "percent": 0, "name": sym, "source": "okx"}
        except Exception as e:
            logger.debug("OKX %s error: %s", sym, e)
    if results:
        logger.info("OKX: fetched %d crypto prices", len(results))
    return results


def get_crypto_quotes_binance(holdings: List[Dict]) -> Dict[str, Dict]:
    """
    从 Binance 获取数字货币价格。机房易被墙，配置 PFA_PROXY_BASE 时经代理。
    Returns {symbol: {current, percent, name}}
    """
    symbols = _get_crypto_holdings_symbols(holdings)
    symbols = [s for s in symbols if s in BINANCE_USDT_SYMBOLS]
    if not symbols:
        return {}
    try:
        if use_proxy():
            resp = proxy_get(BINANCE_TICKER_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        else:
            resp = requests.get(
                BINANCE_TICKER_URL,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=8,
                proxies=_get_proxies(),
            )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Binance API error: %s", e)
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
    获取数字货币实时价格。Finnhub → OKX → Gate.io → Binance → CoinGecko，按可联通链路依次尝试。

    Args:
        holdings: 持仓列表，筛选 market="OT" 或 market="CRYPTO" 或 account="数字货币" 的项

    Returns:
        {symbol: {current, percent, name}} 字典
    """
    symbols = _get_crypto_holdings_symbols(holdings)
    if not symbols:
        return {}

    # Finnhub → OKX → Gate.io → Binance → CoinGecko，只补缺失
    results = get_crypto_quotes_finnhub(holdings)
    missing = [s for s in symbols if s not in results]
    if missing:
        for s, v in get_crypto_quotes_okx(holdings).items():
            if s in missing:
                results[s] = v
    missing = [s for s in symbols if s not in results]
    if missing:
        for s, v in get_crypto_quotes_gateio(holdings).items():
            if s in missing:
                results[s] = v
    missing = [s for s in symbols if s not in results]
    if missing:
        for s, v in get_crypto_quotes_binance(holdings).items():
            if s in missing:
                results[s] = v
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
        if use_proxy():
            resp = proxy_get(COINGECKO_API, params=params, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, timeout=10)
        else:
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
