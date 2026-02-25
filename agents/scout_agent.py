"""
数据搜集员 (The Scout)

职责：只负责找数据。监控 RSS、东方财富等渠道，
      把 HTML 转化为干净的结构化数据。
技术重点：API 调用、反爬策略、数据去重。

支持的 action:
  - fetch_news:   抓取指定标的的新闻 (payload: symbol, name, market, hours)
  - fetch_rss:    抓取 RSS 源          (payload: rss_urls, holdings)
  - fetch_all:    抓取全部持仓新闻     (payload: holdings, hours)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.protocol import AgentMessage, make_response, make_error
from pfa.data.store import FeedItem, save_feed_items

CST = timezone(timedelta(hours=8))

EASTMONEY_SEARCH_URL = "https://search-api-web.eastmoney.com/search/jsonp"
EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://so.eastmoney.com/",
}

SEARCH_ALIASES = {
    "00883": ["中海油", "中国海洋石油", "CNOOC"],
    "600519": ["贵州茅台", "茅台", "Moutai"],
    "600436": ["片仔癀", "Pien Tze Huang"],
}


# ---------------------------------------------------------------------------
# Core fetching logic (reused from scripts/)
# ---------------------------------------------------------------------------

def _get_keywords(symbol: str, name: str) -> List[str]:
    kws = []
    if name:
        kws.append(name)
    for alias in SEARCH_ALIASES.get(symbol, []):
        if alias not in kws:
            kws.append(alias)
    if not kws:
        kws.append(symbol)
    return kws


def _fetch_eastmoney(keyword: str, page_size: int = 20) -> List[Dict]:
    param_payload = {
        "uid": "", "keyword": keyword,
        "type": ["cmsArticleWebOld"],
        "client": "web", "clientType": "web", "clientVersion": "curr",
        "param": {"cmsArticleWebOld": {
            "searchScope": "default", "sort": "default",
            "pageIndex": 1, "pageSize": page_size,
            "preTag": "", "postTag": "",
        }},
    }
    params = {"cb": "jQuery", "param": json.dumps(param_payload, ensure_ascii=False)}
    try:
        resp = requests.get(EASTMONEY_SEARCH_URL, params=params,
                            headers=EASTMONEY_HEADERS, timeout=15)
        resp.raise_for_status()
        text = resp.text
        data = json.loads(text[text.index("(") + 1 : text.rindex(")")])
        raw = data.get("result", {}).get("cmsArticleWebOld", [])
        return raw if isinstance(raw, list) else raw.get("list", [])
    except Exception:
        return []


def _normalize(raw: Dict, symbol: str, name: str, market: str) -> FeedItem:
    title = re.sub(r"<[^>]+>", "", raw.get("title", ""))
    snippet = re.sub(r"<[^>]+>", "", raw.get("content", ""))[:300]
    return FeedItem(
        id=hashlib.md5(raw.get("url", title).encode()).hexdigest()[:12],
        title=title, url=raw.get("url", ""),
        published_at=raw.get("date", ""),
        content_snippet=snippet,
        source="eastmoney", source_id=raw.get("code", ""),
        symbol=symbol, symbol_name=name, market=market,
        fetched_at=datetime.now(CST).isoformat(),
    )


def _filter_by_time(items: List[FeedItem], hours: int) -> List[FeedItem]:
    cutoff = datetime.now(CST) - timedelta(hours=hours)
    result = []
    for it in items:
        try:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(it.published_at, fmt).replace(tzinfo=CST)
                    break
                except ValueError:
                    dt = None
            if dt and dt >= cutoff:
                result.append(it)
            elif dt is None:
                result.append(it)
        except Exception:
            result.append(it)
    return result


def _dedup(items: List[FeedItem]) -> List[FeedItem]:
    seen, out = set(), []
    for it in items:
        if it.id not in seen:
            seen.add(it.id)
            out.append(it)
    return out


# ---------------------------------------------------------------------------
# Public API — called by other agents
# ---------------------------------------------------------------------------

def fetch_news_for_symbol(
    symbol: str, name: str, market: str, hours: int = 72
) -> List[FeedItem]:
    """Fetch news for a single holding. Returns deduplicated, time-filtered items."""
    keywords = _get_keywords(symbol, name)
    all_items: List[FeedItem] = []
    for kw in keywords:
        raws = _fetch_eastmoney(kw)
        all_items.extend(_normalize(r, symbol, name, market) for r in raws)
        time.sleep(0.3)
    all_items = _dedup(all_items)
    in_window = _filter_by_time(all_items, hours)
    return in_window


def fetch_news_for_all(
    holdings: List[Dict], hours: int = 72
) -> List[FeedItem]:
    """Fetch news for all holdings."""
    all_items: List[FeedItem] = []
    for h in holdings:
        items = fetch_news_for_symbol(
            h["symbol"], h.get("name", h["symbol"]),
            h.get("market", "?"), hours,
        )
        all_items.extend(items)
    if all_items:
        save_feed_items(all_items, source_label="eastmoney")
    return all_items


# ---------------------------------------------------------------------------
# Agent message handler
# ---------------------------------------------------------------------------

def handle(msg: AgentMessage) -> AgentMessage:
    """Process an incoming AgentMessage and return a response."""
    action = msg.action
    p = msg.payload

    try:
        if action == "fetch_news":
            items = fetch_news_for_symbol(
                p["symbol"], p.get("name", p["symbol"]),
                p.get("market", "?"), p.get("hours", 72),
            )
            if items:
                save_feed_items(items, source_label="eastmoney")
            return make_response(
                msg, "scout",
                symbol=p["symbol"],
                count=len(items),
                items=[it.to_dict() for it in items],
            )

        elif action == "fetch_all":
            items = fetch_news_for_all(
                p.get("holdings", []), p.get("hours", 72),
            )
            by_symbol: Dict[str, int] = {}
            for it in items:
                by_symbol[it.symbol] = by_symbol.get(it.symbol, 0) + 1
            return make_response(
                msg, "scout",
                total=len(items),
                by_symbol=by_symbol,
                items=[it.to_dict() for it in items],
            )

        else:
            return make_error(msg, "scout", f"未知 action: {action}")

    except Exception as e:
        return make_error(msg, "scout", str(e))
