"""
浏览器抓取器 — 使用 Playwright 绕过 WAF / 渲染 SPA

支持的数据源:
  - 雪球行情 + 热股（通过 xq_a_token 认证 API）
  - Twitter/X（需登录，当前返回元信息）
  - 任意 URL 页面内容提取
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import requests as http_requests

CST = timezone(timedelta(hours=8))
CHROME_PATH = "/usr/bin/google-chrome-stable"
LAUNCH_ARGS = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]


def _get_xq_token() -> str:
    """Use Playwright to visit xueqiu.com and extract xq_a_token cookie."""
    from playwright.sync_api import sync_playwright
    token = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH, headless=True, args=LAUNCH_ARGS)
        page = browser.new_page()
        page.goto("https://xueqiu.com/", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)
        for c in page.context.cookies():
            if c["name"] == "xq_a_token":
                token = c["value"]
                break
        browser.close()
    return token


# ===================================================================
# 雪球
# ===================================================================

def fetch_xueqiu_quote(symbols: List[str]) -> List[Dict]:
    """Fetch real-time stock quotes from Xueqiu.

    symbols: list of Xueqiu-format symbols, e.g. ["SH600519", "HK00883"]
    """
    token = _get_xq_token()
    if not token:
        return []
    headers = {"User-Agent": "Mozilla/5.0", "Cookie": f"xq_a_token={token}"}
    results = []
    for sym in symbols:
        try:
            resp = http_requests.get(
                "https://stock.xueqiu.com/v5/stock/quote.json",
                params={"symbol": sym, "extend": "detail"},
                headers=headers, timeout=10,
            )
            if resp.status_code == 200:
                q = resp.json().get("data", {}).get("quote", {})
                results.append({
                    "symbol": sym, "name": q.get("name", ""),
                    "current": q.get("current"), "percent": q.get("percent"),
                    "volume": q.get("volume"), "amount": q.get("amount"),
                    "high": q.get("high"), "low": q.get("low"),
                    "open": q.get("open"), "last_close": q.get("last_close"),
                    "market_capital": q.get("market_capital"),
                    "source": "xueqiu",
                })
        except Exception:
            continue
    return results


def fetch_xueqiu_hot(count: int = 10) -> List[Dict]:
    """Fetch Xueqiu hot stock list."""
    token = _get_xq_token()
    if not token:
        return []
    headers = {"User-Agent": "Mozilla/5.0", "Cookie": f"xq_a_token={token}"}
    try:
        resp = http_requests.get(
            "https://stock.xueqiu.com/v5/stock/hot_stock/list.json",
            params={"size": count, "_type": 10, "type": 10},
            headers=headers, timeout=10,
        )
        if resp.status_code == 200:
            items = resp.json().get("data", {}).get("items", [])
            return [
                {"symbol": it.get("code", ""), "name": it.get("name", ""),
                 "current": it.get("current"), "percent": it.get("percent"),
                 "source": "xueqiu"}
                for it in items
            ]
    except Exception:
        pass
    return []


# ===================================================================
# Twitter
# ===================================================================

def fetch_twitter_profile(handle: str) -> Dict[str, Any]:
    """Fetch Twitter/X profile info. Full tweet scraping needs login."""
    from playwright.sync_api import sync_playwright
    result = {"handle": handle, "status": "error", "tweets": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH, headless=True, args=LAUNCH_ARGS)
        page = browser.new_page()
        try:
            page.goto(f"https://x.com/{handle}",
                       wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)
            result["title"] = page.title()
            result["needs_login"] = True
            result["status"] = "partial"
            result["note"] = "Twitter/X 需要登录才能抓取推文。可通过 Desktop 面板登录后重试。"
        except Exception as e:
            result["error"] = str(e)
        browser.close()
    return result


# ===================================================================
# 通用 URL 监控
# ===================================================================

def fetch_monitor_url(url: str) -> Dict[str, Any]:
    """Fetch and extract content from any URL using browser rendering."""
    from playwright.sync_api import sync_playwright
    result = {"url": url, "title": "", "items": [], "status": "error"}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH, headless=True, args=LAUNCH_ARGS)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            result["title"] = page.title()
            body = page.inner_text("body")
            lines = [l.strip() for l in body.split("\n")
                     if l.strip() and len(l.strip()) > 10]
            result["content_lines"] = len(lines)
            result["items"] = [
                {"text": l[:100], "source": "monitor_url"}
                for l in lines[:30]
                if len(l) > 15 and not any(k in l for k in ["登录", "注册", "下载", "cookie"])
            ]
            result["status"] = "ok"
        except Exception as e:
            result["error"] = str(e)
        browser.close()
    return result
