#!/usr/bin/env python3
"""
网络连通性诊断 — 阿里云等机房环境下的多链路压力测试与评估

测试轨道：
1. 数字货币直连 (OKX)
2. 全球金融数据 (Finnhub 美股)
3. 中继代理 (Cloudflare Worker) → Yahoo / Binance

用法: python3 scripts/network_diagnostic.py
建议: PYTHONPATH=/opt/pfa python3 scripts/network_diagnostic.py  (若从 scripts 运行)
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path
from urllib.parse import quote

# 保证从 scripts/ 运行时能找到项目根
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import requests

TIMEOUT = 10
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def _random_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}


def _classify_error(exc: Exception) -> str:
    """区分 DNS 解析失败、连接超时、其他."""
    msg = (getattr(exc, "message", "") or str(exc)).lower()
    if "name or service not known" in msg or "nodename nor servname provided" in msg:
        return "DNS 解析失败"
    if "getaddrinfo failed" in msg or "gaierror" in type(exc).__name__.lower():
        return "DNS 解析失败"
    if "timeout" in msg or "timed out" in msg or "timedout" in msg:
        return "连接/读取超时"
    if isinstance(exc, (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout)):
        return "连接/读取超时"
    if "network is unreachable" in msg or "network unreachable" in msg:
        return "网络不可达 (Network unreachable)"
    if "connection" in msg and ("refused" in msg or "error" in msg):
        return "连接被拒绝或失败"
    return f"其他: {type(exc).__name__}"


def probe(
    name: str,
    url: str,
    *,
    headers: dict | None = None,
) -> dict:
    """单次请求：记录状态码、响应时间(ms)、错误类型。"""
    h = _random_headers()
    if headers:
        h.update(headers)
    start = time.perf_counter()
    try:
        r = requests.get(url, headers=h, timeout=TIMEOUT)
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "name": name,
            "status": r.status_code,
            "latency_ms": round(latency_ms, 0),
            "error": None,
            "ok": r.status_code == 200,
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "name": name,
            "status": None,
            "latency_ms": round(latency_ms, 0),
            "error": _classify_error(e),
            "ok": False,
        }


def main() -> int:
    proxy_base = "https://pfa-proxy.huangtianzhu5746.workers.dev"
    results: list[dict] = []

    print("=== PFA 网络连通性诊断（阿里云环境）===\n")
    print("超时设置: %d 秒 | User-Agent: 随机\n" % TIMEOUT)

    # 1. OKX 直连
    print("[1/4] 数字货币直连 (OKX)...")
    r1 = probe(
        "OKX (BTC-USDT)",
        "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT",
    )
    results.append(r1)

    # 2. Finnhub
    print("[2/4] 全球金融 (Finnhub AAPL)...")
    r2 = probe(
        "Finnhub (美股 AAPL)",
        "https://finnhub.io/api/v1/quote?symbol=AAPL&token=d6me301r01qi0ajlt2kgd6me301r01qi0ajlt2l0",
    )
    results.append(r2)

    # 3a. Worker → Yahoo
    print("[3/4] 中继代理 → Yahoo (0700.HK)...")
    yahoo_url = "https://query1.finance.yahoo.com/v8/finance/chart/0700.HK"
    proxy_url_yahoo = f"{proxy_base}/?url={quote(yahoo_url)}"
    r3a = probe("Worker → Yahoo 港股", proxy_url_yahoo)
    results.append(r3a)

    # 3b. Worker → Binance
    print("[4/4] 中继代理 → Binance (BTCUSDT)...")
    binance_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    proxy_url_binance = f"{proxy_base}/?url={quote(binance_url)}"
    r3b = probe("Worker → Binance", proxy_url_binance)
    results.append(r3b)

    # 输出表格
    print("\n" + "=" * 80)
    print("诊断结果汇总")
    print("=" * 80)
    print(f"{'链路':<28} {'状态码':<10} {'延迟(ms)':<12} {'错误':<28} {'判定':<10}")
    print("-" * 80)

    for r in results:
        status_str = str(r["status"]) if r["status"] is not None else "—"
        err_str = (r["error"] or "—")[:26]
        verdict = "Green (稳定)" if r["ok"] else "Red (不可达)"
        print(f"{r['name']:<28} {status_str:<10} {r['latency_ms']:<12.0f} {err_str:<28} {verdict:<10}")

    print("=" * 80)
    green_count = sum(1 for r in results if r["ok"])
    print(f"\n可用链路: {green_count}/{len(results)}")
    if green_count == 0:
        print("建议: 检查本机出网策略；若 Worker 不可达，可考虑 OKX 直连 + Finnhub 美股，或为 Worker 绑定自定义域名。")
    return 0 if green_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
