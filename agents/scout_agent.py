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


# ---------------------------------------------------------------------------
# 华尔街见闻 macro feed
# ---------------------------------------------------------------------------

WALLSTREETCN_URL = "https://api-one.wallstcn.com/apiv1/content/lives"


def _fetch_wallstreetcn(limit: int = 20) -> List[FeedItem]:
    """Fetch macro flash news from wallstreetcn."""
    now_iso = datetime.now(CST).isoformat()
    try:
        resp = requests.get(
            WALLSTREETCN_URL,
            params={"channel": "global-channel", "limit": limit},
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    items: List[FeedItem] = []
    for raw in data.get("data", {}).get("items", []):
        content = raw.get("content_text", "")[:300]
        title = raw.get("title", "") or content[:60]
        uri = raw.get("uri", "")
        url = f"https://wallstreetcn.com/live/{uri}" if uri else ""
        display_time = raw.get("display_time", 0)
        pub_str = ""
        if display_time:
            from datetime import datetime as _dt
            pub_str = _dt.fromtimestamp(display_time, tz=CST).strftime("%Y-%m-%d %H:%M:%S")
        fid = hashlib.md5((url or title).encode()).hexdigest()[:12]
        items.append(FeedItem(
            id=fid, title=title, url=url,
            published_at=pub_str, content_snippet=content,
            source="wallstreetcn", source_id=str(raw.get("id", "")),
            symbol="", symbol_name="", market="",
            fetched_at=now_iso, tags=["macro"],
        ))
    return items


# ---------------------------------------------------------------------------
# RSS feed fetcher
# ---------------------------------------------------------------------------

def _fetch_rss(url: str, feed_name: str, holdings: List[Dict]) -> List[FeedItem]:
    """Fetch and parse an RSS feed, matching entries to holdings."""
    import feedparser as fp
    now_iso = datetime.now(CST).isoformat()
    try:
        feed = fp.parse(url)
    except Exception:
        return []
    if feed.bozo and not feed.entries:
        return []

    items: List[FeedItem] = []
    for entry in feed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))
        import re as _re
        summary_clean = _re.sub(r"<[^>]+>", "", summary)[:300]
        link = entry.get("link", "")
        pub_time = ""
        for key in ("published_parsed", "updated_parsed"):
            tp = entry.get(key)
            if tp:
                try:
                    pub_time = datetime(*tp[:6], tzinfo=CST).isoformat()
                except Exception:
                    pass
                break
        if not pub_time:
            pub_time = entry.get("published", entry.get("updated", ""))

        search_text = f"{title} {summary_clean}".lower()
        matched_sym, matched_name, matched_mkt = "", "", ""
        for h in holdings:
            name = h.get("name", "")
            for kw in _get_keywords(h["symbol"], name):
                if kw.lower() in search_text:
                    matched_sym = h["symbol"]
                    matched_name = name
                    matched_mkt = h.get("market", "")
                    break
            if matched_sym:
                break

        fid = hashlib.md5((link or title).encode()).hexdigest()[:12]
        items.append(FeedItem(
            id=fid, title=title, url=link,
            published_at=pub_time, content_snippet=summary_clean,
            source="rss", source_id=feed_name,
            symbol=matched_sym, symbol_name=matched_name,
            market=matched_mkt, fetched_at=now_iso,
        ))
    return items


# ---------------------------------------------------------------------------
# Xueqiu user timeline fetcher
# ---------------------------------------------------------------------------

def _fetch_xueqiu_user_timeline(uid: str, hours: int, holdings: List[Dict]) -> List[FeedItem]:
    """Fetch Xueqiu user posts, convert to FeedItem, filter by time and optionally by content quality."""
    try:
        from backend.services.social_service import fetch_xueqiu_user_timeline as _fetch
        statuses = _fetch(uid, count=20)
    except Exception:
        return []

    now_iso = datetime.now(CST).isoformat()
    cutoff = datetime.now(CST) - timedelta(hours=hours)
    items: List[FeedItem] = []
    for s in statuses:
        text = (s.get("description") or s.get("text") or "").strip()
        text_clean = re.sub(r"<[^>]+>", "", text)
        title = (s.get("title") or text_clean[:60] or "").strip()
        user = s.get("user") or {}
        screen_name = user.get("screen_name", "")
        target = s.get("target", "")
        url = f"https://xueqiu.com{target}" if target else ""
        created_at = s.get("created_at")
        pub_str = ""
        if created_at is not None:
            try:
                if isinstance(created_at, (int, float)):
                    ts = int(created_at) / 1000 if created_at > 1e12 else int(created_at)
                    pub_str = datetime.fromtimestamp(ts, tz=CST).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    pub_str = str(created_at)
            except (ValueError, OSError):
                pub_str = str(created_at)
        if pub_str:
            try:
                dt = datetime.strptime(pub_str[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST)
                if dt < cutoff:
                    continue
            except ValueError:
                pass
        # Filter: keep substantial content (>300 chars or 研报/深度)
        if len(text_clean) < 300 and "研报" not in text_clean and "深度" not in text_clean:
            continue
        fid = hashlib.md5((url or title or text_clean[:50]).encode()).hexdigest()[:12]
        search_text = f"{title} {text_clean}".lower()
        matched_sym, matched_name, matched_mkt = "", "", ""
        for h in holdings:
            name = h.get("name", "")
            for kw in _get_keywords(h["symbol"], name):
                if kw.lower() in search_text:
                    matched_sym = h["symbol"]
                    matched_name = name
                    matched_mkt = h.get("market", "")
                    break
            if matched_sym:
                break
        items.append(FeedItem(
            id=fid,
            title=title or text_clean[:60],
            url=url,
            published_at=pub_str,
            content_snippet=text_clean[:300],
            source="xueqiu_user",
            source_id=screen_name or uid,
            symbol=matched_sym,
            symbol_name=matched_name,
            market=matched_mkt,
            fetched_at=now_iso,
        ))
    return items


# ---------------------------------------------------------------------------
# Multi-source fetch orchestration
# ---------------------------------------------------------------------------

def _load_data_sources() -> Dict:
    ds_path = ROOT / "config" / "data-sources.json"
    if ds_path.exists():
        with open(ds_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def fetch_news_for_all(
    holdings: List[Dict], hours: int = 72
) -> List[FeedItem]:
    """Fetch from ALL enabled sources: East Money per-stock + macro APIs + RSS."""
    all_items: List[FeedItem] = []
    ds = _load_data_sources()

    # 1) East Money per-stock news
    for h in holdings:
        items = fetch_news_for_symbol(
            h["symbol"], h.get("name", h["symbol"]),
            h.get("market", "?"), hours,
        )
        all_items.extend(items)

    # 2) 华尔街见闻 macro
    api_sources = ds.get("api_sources", [])
    for src in api_sources:
        if not src.get("enabled", True):
            continue
        if src.get("type") == "wallstreetcn":
            macro_items = _fetch_wallstreetcn(20)
            all_items.extend(macro_items)
            time.sleep(0.3)

    # 3) RSS feeds
    rss_list = ds.get("rss_urls", [])
    for rss in rss_list:
        if isinstance(rss, str):
            url, name = rss, rss
        else:
            if not rss.get("enabled", True):
                continue
            url = rss["url"]
            name = rss.get("name", url)
        rss_items = _fetch_rss(url, name, holdings)
        all_items.extend(rss_items)
        time.sleep(0.3)

    # 4) Self-hosted RSSHub sources
    rsshub_base = ds.get("self_hosted_rsshub", "")
    if rsshub_base:
        for unavail in ds.get("unavailable_sources", []):
            route = unavail.get("rsshub_route", "")
            if route:
                rsshub_url = f"{rsshub_base.rstrip('/')}{route}"
                rss_items = _fetch_rss(rsshub_url, unavail.get("name", route), holdings)
                all_items.extend(rss_items)
                time.sleep(0.3)

    # 5) Xueqiu user timelines (requires Cookie from extension sync)
    try:
        from backend.services.social_service import has_xueqiu_auth
        xueqiu_ids = ds.get("xueqiu_user_ids", []) or []
        if has_xueqiu_auth() and xueqiu_ids:
            for uid in xueqiu_ids:
                uid_str = str(uid).strip()
                if not uid_str:
                    continue
                xq_items = _fetch_xueqiu_user_timeline(uid_str, hours, holdings)
                all_items.extend(xq_items)
                time.sleep(0.5)
    except Exception:
        pass

    all_items = _dedup(all_items)
    if all_items:
        save_feed_items(all_items, source_label="multi")
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
            symbol = p["symbol"]
            name = p.get("name", symbol)
            market = p.get("market", "?")
            hours = p.get("hours", 72)

            # 1) East Money per-stock
            em_items = fetch_news_for_symbol(symbol, name, market, hours)

            # 2) RSS + RSSHub + 华尔街见闻: fetch and filter for this symbol
            holding = [{"symbol": symbol, "name": name, "market": market}]
            ds = _load_data_sources()

            rss_items: List[FeedItem] = []
            for rss in ds.get("rss_urls", []):
                if isinstance(rss, str):
                    url, rname = rss, rss
                else:
                    if not rss.get("enabled", True):
                        continue
                    url, rname = rss["url"], rss.get("name", rss["url"])
                fetched = _fetch_rss(url, rname, holding)
                rss_items.extend(it for it in fetched if it.symbol == symbol)
                time.sleep(0.2)

            rsshub_base = ds.get("self_hosted_rsshub", "")
            if rsshub_base:
                for unavail in ds.get("unavailable_sources", []):
                    route = unavail.get("rsshub_route", "")
                    if route:
                        rurl = f"{rsshub_base.rstrip('/')}{route}"
                        fetched = _fetch_rss(rurl, unavail.get("name", route), holding)
                        rss_items.extend(it for it in fetched if it.symbol == symbol)
                        time.sleep(0.2)

            all_items = _dedup(em_items + rss_items)
            if all_items:
                save_feed_items(all_items, source_label="eastmoney")

            by_source: Dict[str, int] = {}
            for it in all_items:
                by_source[it.source] = by_source.get(it.source, 0) + 1

            return make_response(
                msg, "scout",
                symbol=symbol,
                count=len(all_items),
                by_source=by_source,
                items=[it.to_dict() for it in all_items],
            )

        elif action == "fetch_all":
            items = fetch_news_for_all(
                p.get("holdings", []), p.get("hours", 72),
            )
            by_source: Dict[str, int] = {}
            by_symbol: Dict[str, int] = {}
            for it in items:
                by_source[it.source] = by_source.get(it.source, 0) + 1
                if it.symbol:
                    by_symbol[it.symbol] = by_symbol.get(it.symbol, 0) + 1
            return make_response(
                msg, "scout",
                total=len(items),
                by_source=by_source,
                by_symbol=by_symbol,
                items=[it.to_dict() for it in items],
            )

        else:
            return make_error(msg, "scout", f"未知 action: {action}")

    except Exception as e:
        return make_error(msg, "scout", str(e))
