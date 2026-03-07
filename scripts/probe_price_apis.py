#!/usr/bin/env python3
"""
价格接口探测脚本 — 在阿里云等机房环境测试各数据源可用性与速度

用法: python3 scripts/probe_price_apis.py

测试接口:
- 腾讯财经 qt.gtimg.cn (A股/港股，需 Referer: http://gu.qq.com)
- 网易财经 api.money.126.net (A股，JSON)
- 新浪财经 hq.sinajs.cn (A股/港股/美股，需 Referer)
- 东方财富 push2.eastmoney.com (A股)
- Yahoo Finance (港股/美股/SGX)
- Binance (数字货币)
- CoinGecko (数字货币)
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

# 配置 PFA_PROXY_BASE 时，除腾讯外所有探测经 Worker 代理
try:
    from pfa.proxy_fetch import get as proxy_get, use_proxy
except ImportError:
    def use_proxy() -> bool:
        return False
    def proxy_get(*args, **kwargs) -> requests.Response:
        raise RuntimeError("pfa.proxy_fetch not available")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


@dataclass
class ProbeResult:
    name: str
    ok: bool
    ms: float
    sample_price: Optional[float] = None
    error: Optional[str] = None
    raw: Optional[str] = None


def _probe(
    name: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    parse: Optional[Callable[[requests.Response], Optional[float]]] = None,
    timeout: float = 10,
    direct_only: bool = False,
) -> ProbeResult:
    """通用探测：请求 URL，解析现价。PFA_PROXY_BASE 存在且 direct_only=False 时经代理；腾讯直连(direct_only=True)。"""
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    start = time.perf_counter()
    try:
        if direct_only or not use_proxy():
            r = requests.get(url, headers=h, params=params, timeout=timeout)
        else:
            full_url = url + ("&" if "?" in url else "?") + urlencode(params) if params else url
            r = proxy_get(full_url, headers=h, timeout=timeout)
        ms = (time.perf_counter() - start) * 1000
        if r.status_code != 200:
            return ProbeResult(name=name, ok=False, ms=ms, error=f"HTTP {r.status_code}", raw=r.text[:150])
        price = None
        if parse:
            price = parse(r)
        return ProbeResult(name=name, ok=price is not None, ms=ms, sample_price=price, raw=r.text[:200] if not price else None)
    except Exception as e:
        ms = (time.perf_counter() - start) * 1000
        return ProbeResult(name=name, ok=False, ms=ms, error=str(e))


# --- 腾讯财经 ---
def _parse_tencent(r: requests.Response) -> Optional[float]:
    # 返回格式: v_s_sh600519="1~贵州茅台~600519~1401.18~..." 或 v_hk00883="100~中国海洋石油~00883~27.45~..."
    # 现价为第 4 个字段 (index 3)
    text = r.text
    m = re.search(r'="([^"]+)"', text)
    if m:
        parts = m.group(1).split("~")
        if len(parts) >= 4:
            try:
                return float(parts[3])
            except (ValueError, TypeError):
                pass
    return None


def probe_tencent_ashare() -> ProbeResult:
    return _probe(
        "腾讯-A股",
        "http://qt.gtimg.cn/q=s_sh600519",
        headers={"Referer": "http://gu.qq.com/"},
        parse=_parse_tencent,
        direct_only=True,
    )


def probe_tencent_hk() -> ProbeResult:
    return _probe(
        "腾讯-港股",
        "http://qt.gtimg.cn/q=hk00883",
        headers={"Referer": "http://gu.qq.com/"},
        parse=_parse_tencent,
        direct_only=True,
    )


# --- 网易财经 ---
def _parse_netease(r: requests.Response) -> Optional[float]:
    # 返回: _ntes_quote_callback({"0600519":{"name":"贵州茅台","price":1401.18,...}})
    text = r.text
    m = re.search(r'_ntes_quote_callback\((.*)\)', text)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
        for k, v in data.items():
            if isinstance(v, dict) and "price" in v:
                return float(v["price"])
    except (json.JSONDecodeError, (ValueError, TypeError)):
        pass
    return None


def probe_netease_ashare() -> ProbeResult:
    return _probe(
        "网易-A股",
        "http://api.money.126.net/data/feed/0600519,money.api",
        parse=_parse_netease,
    )


# --- 新浪财经 ---
def _parse_sina(r: requests.Response) -> Optional[float]:
    # A股: var hq_str_sh600519="贵州茅台,今开,昨收,现价,..." 现价=第4字段
    # 港股: 字段顺序不同，现价约第7字段
    text = r.text
    m = re.search(r'="([^"]+)"', text)
    if m:
        parts = m.group(1).split(",")
        if len(parts) >= 4:
            try:
                # A股现价第4字段(index 3)
                p = float(parts[3])
                if p > 0:
                    return p
            except (ValueError, TypeError):
                pass
        if len(parts) >= 7:
            try:
                # 港股现价第7字段(index 6)
                p = float(parts[6])
                if p > 0:
                    return p
            except (ValueError, TypeError):
                pass
    return None


def probe_sina_ashare() -> ProbeResult:
    return _probe(
        "新浪-A股",
        "https://hq.sinajs.cn/list=sh600519",
        headers={"Referer": "https://finance.sina.com.cn/"},
        parse=_parse_sina,
    )


def probe_sina_hk() -> ProbeResult:
    return _probe(
        "新浪-港股",
        "https://hq.sinajs.cn/list=hk00883",
        headers={"Referer": "https://finance.sina.com.cn/"},
        parse=_parse_sina,
    )


# --- 东方财富 ---
def _parse_eastmoney(r: requests.Response) -> Optional[float]:
    j = r.json()
    d = j.get("data")
    if d and isinstance(d, dict):
        f43 = d.get("f43")
        if f43 is not None:
            return float(f43) / 100
    return None


def probe_eastmoney_ashare() -> ProbeResult:
    return _probe(
        "东方财富-A股",
        "https://push2.eastmoney.com/api/qt/stock/get",
        params={"secid": "1.600519"},
        headers={"Referer": "https://quote.eastmoney.com/"},
        parse=_parse_eastmoney,
    )


# --- Yahoo Finance ---
def _parse_yahoo(r: requests.Response) -> Optional[float]:
    j = r.json()
    r0 = j.get("chart", {}).get("result", [])
    if r0:
        meta = r0[0].get("meta", {})
        p = meta.get("regularMarketPrice") or meta.get("previousClose")
        if p is not None:
            return float(p)
    return None


def probe_yahoo_hk() -> ProbeResult:
    return _probe(
        "Yahoo-港股",
        "https://query1.finance.yahoo.com/v8/finance/chart/00883.HK",
        params={"interval": "1d", "range": "1d"},
        parse=_parse_yahoo,
    )


def probe_yahoo_us() -> ProbeResult:
    return _probe(
        "Yahoo-美股",
        "https://query1.finance.yahoo.com/v8/finance/chart/NIO",
        params={"interval": "1d", "range": "1d"},
        parse=_parse_yahoo,
    )


def probe_yahoo_sgx() -> ProbeResult:
    return _probe(
        "Yahoo-SGX",
        "https://query1.finance.yahoo.com/v8/finance/chart/T14.SI",
        params={"interval": "1d", "range": "1d"},
        parse=_parse_yahoo,
    )


# --- Binance ---
def _parse_binance(r: requests.Response) -> Optional[float]:
    j = r.json()
    p = j.get("price")
    if p:
        return float(p)
    return None


def probe_binance() -> ProbeResult:
    return _probe(
        "Binance-BTC",
        "https://api.binance.com/api/v3/ticker/price",
        params={"symbol": "BTCUSDT"},
        parse=_parse_binance,
    )


# --- CoinGecko ---
def _parse_coingecko(r: requests.Response) -> Optional[float]:
    j = r.json()
    btc = j.get("bitcoin")
    if btc and "usd" in btc:
        return float(btc["usd"])
    return None


def probe_coingecko() -> ProbeResult:
    return _probe(
        "CoinGecko-BTC",
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": "bitcoin", "vs_currencies": "usd"},
        parse=_parse_coingecko,
    )


def main() -> int:
    probes: List[Tuple[str, Callable[[], ProbeResult]]] = [
        ("国内市场", probe_tencent_ashare),
        ("国内市场", probe_tencent_hk),
        ("国内市场", probe_netease_ashare),
        ("国内市场", probe_sina_ashare),
        ("国内市场", probe_sina_hk),
        ("国内市场", probe_eastmoney_ashare),
        ("国际市场", probe_yahoo_hk),
        ("国际市场", probe_yahoo_us),
        ("国际市场", probe_yahoo_sgx),
        ("数字货币", probe_binance),
        ("数字货币", probe_coingecko),
    ]

    proxy_note = " (经 PFA_PROXY_BASE 代理)" if use_proxy() else ""
    print("=== 价格接口探测（阿里云等机房环境）===" + proxy_note + "\n")
    results: List[ProbeResult] = []
    last_cat = None
    for cat, fn in probes:
        if cat != last_cat:
            print(f"【{cat}】")
            last_cat = cat
        r = fn()
        results.append(r)
        status = "✓" if r.ok else "✗"
        price_str = f" 现价 {r.sample_price}" if r.sample_price is not None else ""
        err_str = f" ({r.error})" if r.error else ""
        print(f"  {status} {r.name}: {r.ms:.0f}ms{price_str}{err_str}")

    # 按速度排序（仅成功的）
    ok_results = [r for r in results if r.ok]
    ok_results.sort(key=lambda x: x.ms)

    print("\n--- 按速度排序（成功接口）---")
    for i, r in enumerate(ok_results, 1):
        print(f"  {i}. {r.name}: {r.ms:.0f}ms (现价 {r.sample_price})")

    if not ok_results:
        print("\n⚠ 所有接口均不可用，请检查网络或代理配置。")
        return 1

    print(f"\n✓ 共 {len(ok_results)}/{len(results)} 个接口可用")
    return 0


if __name__ == "__main__":
    sys.exit(main())
