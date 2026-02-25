#!/usr/bin/env python3
"""
PFA RSS 抓取器 — 从用户配置的 RSS 源拉取信息，关联持仓标的

用法:
    python scripts/fetch_rss.py                             # 抓取全部 RSS
    python scripts/fetch_rss.py --portfolio config/x.json   # 指定持仓文件

数据存储: data/store/feeds/ (统一数据层)
"""

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import feedparser

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pfa.data.store import FeedItem, save_feed_items

DEFAULT_PORTFOLIO = ROOT / "config" / "my-portfolio.json"
CST = timezone(timedelta(hours=8))

SEARCH_ALIASES = {
    "00883": ["中海油", "中国海洋石油", "CNOOC"],
    "600519": ["贵州茅台", "茅台", "Moutai", "Kweichow"],
    "600436": ["片仔癀", "Pien Tze Huang"],
}


def load_portfolio(path: Path) -> dict:
    if not path.exists():
        print(f"[ERROR] 持仓文件不存在: {path}", file=sys.stderr)
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    holdings = data.get("holdings", [])
    markets = sorted(set(h.get("market", "?") for h in holdings))
    print(f"[INFO] 已加载持仓：共 {len(holdings)} 个标的，市场：{'/'.join(markets)}")
    return data


def get_keywords_for_holding(holding: dict) -> List[str]:
    """All keywords that identify this holding (name + aliases)."""
    kws = []
    name = holding.get("name", "")
    if name:
        kws.append(name)
    symbol = holding.get("symbol", "")
    for alias in SEARCH_ALIASES.get(symbol, []):
        if alias not in kws:
            kws.append(alias)
    if symbol and symbol not in kws:
        kws.append(symbol)
    return kws


def match_holding(text: str, holdings: List[dict]) -> Optional[dict]:
    """Return the first holding whose keywords appear in the text."""
    text_lower = text.lower()
    for h in holdings:
        for kw in get_keywords_for_holding(h):
            if kw.lower() in text_lower:
                return h
    return None


def parse_entry_time(entry: dict) -> str:
    """Extract published time as ISO string."""
    for key in ("published_parsed", "updated_parsed"):
        tp = entry.get(key)
        if tp:
            try:
                dt = datetime(*tp[:6], tzinfo=CST)
                return dt.isoformat()
            except Exception:
                pass
    for key in ("published", "updated"):
        val = entry.get(key, "")
        if val:
            return val
    return ""


def fetch_one_rss(url: str, holdings: List[dict]) -> List[FeedItem]:
    """Fetch and parse a single RSS feed, matching entries to holdings."""
    print(f"\n[RSS] {url}")
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"  [WARN] 解析失败: {e}", file=sys.stderr)
        return []

    if feed.bozo and not feed.entries:
        print(f"  [WARN] Feed 异常: {feed.bozo_exception}", file=sys.stderr)
        return []

    feed_title = feed.feed.get("title", url)
    print(f"  Feed: {feed_title} ({len(feed.entries)} entries)")

    items: List[FeedItem] = []
    now_iso = datetime.now(CST).isoformat()

    for entry in feed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))
        summary_clean = re.sub(r"<[^>]+>", "", summary)[:300]
        link = entry.get("link", "")
        pub_time = parse_entry_time(entry)
        search_text = f"{title} {summary_clean}"

        matched = match_holding(search_text, holdings)
        symbol = matched.get("symbol", "") if matched else ""
        symbol_name = matched.get("name", "") if matched else ""
        market = matched.get("market", "") if matched else ""

        entry_id = hashlib.md5((link or title).encode()).hexdigest()[:12]

        items.append(FeedItem(
            id=entry_id,
            title=title,
            url=link,
            published_at=pub_time,
            content_snippet=summary_clean,
            source="rss",
            source_id=feed_title,
            symbol=symbol,
            symbol_name=symbol_name,
            market=market,
            fetched_at=now_iso,
        ))

    matched_count = sum(1 for it in items if it.symbol)
    print(f"  → {len(items)} 条目，{matched_count} 条匹配持仓标的")
    return items


def main():
    parser = argparse.ArgumentParser(description="PFA RSS 抓取器")
    parser.add_argument(
        "--portfolio", type=Path, default=DEFAULT_PORTFOLIO,
        help="持仓配置文件路径 (默认: config/my-portfolio.json)",
    )
    args = parser.parse_args()

    portfolio = load_portfolio(args.portfolio)
    holdings = portfolio.get("holdings", [])
    rss_urls = portfolio.get("channels", {}).get("rss_urls", [])

    if not rss_urls:
        print("[INFO] 未配置 RSS 源 (channels.rss_urls 为空)")
        print("  请在 config/my-portfolio.json 中添加 RSS URL")
        sys.exit(0)

    print(f"[INFO] 共 {len(rss_urls)} 个 RSS 源")

    all_items: List[FeedItem] = []
    for url in rss_urls:
        items = fetch_one_rss(url, holdings)
        all_items.extend(items)
        time.sleep(0.5)

    if all_items:
        path = save_feed_items(all_items, source_label="rss")
        print(f"\n[STORE] {len(all_items)} 条 RSS 条目写入统一数据层 → {path}")
    else:
        print("\n[INFO] 未获取到任何 RSS 条目")

    matched = [it for it in all_items if it.symbol]
    print(f"\n[SUMMARY] 共 {len(all_items)} 条 RSS 条目，{len(matched)} 条匹配持仓标的")
    print("[DONE] RSS 抓取完毕")


if __name__ == "__main__":
    main()
