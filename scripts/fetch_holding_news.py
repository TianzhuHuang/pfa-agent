#!/usr/bin/env python3
"""
PFA 持仓感知器 — 根据持仓标的抓取相关新闻

用法:
    python scripts/fetch_holding_news.py                             # 仅抓取
    python scripts/fetch_holding_news.py --analyze                   # 抓取 + Claude 深度分析
    python scripts/fetch_holding_news.py --portfolio config/x.json   # 指定持仓文件
    python scripts/fetch_holding_news.py --hours 48                  # 指定时间窗口

数据存储: data/raw/fetch_<timestamp>.json
分析存储: data/raw/analysis_<timestamp>.json
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORTFOLIO = ROOT / "config" / "my-portfolio.json"
RAW_DIR = ROOT / "data" / "raw"

EASTMONEY_SEARCH_URL = "https://search-api-web.eastmoney.com/search/jsonp"
EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://so.eastmoney.com/",
}

SEARCH_ALIASES = {
    "00883": ["中海油", "中国海洋石油"],
    "600519": ["贵州茅台", "茅台"],
    "600436": ["片仔癀"],
}


# ---------------------------------------------------------------------------
# Portfolio loading (security: masked summary only)
# ---------------------------------------------------------------------------

def load_portfolio(path: Path) -> dict:
    """Load portfolio; log only masked summary per security-architecture.md."""
    if not path.exists():
        print(f"[ERROR] 持仓文件不存在: {path}", file=sys.stderr)
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    holdings = data.get("holdings", [])
    markets = sorted(set(h.get("market", "?") for h in holdings))
    print(f"[INFO] 已加载持仓：共 {len(holdings)} 个标的，市场：{'/'.join(markets)}")
    return data


# ---------------------------------------------------------------------------
# Search keyword generation
# ---------------------------------------------------------------------------

def get_search_keywords(holding: dict) -> List[str]:
    """Generate search keywords from a holding entry."""
    keywords = []
    name = holding.get("name", "")
    symbol = holding.get("symbol", "")
    if name:
        keywords.append(name)
    aliases = SEARCH_ALIASES.get(symbol, [])
    for alias in aliases:
        if alias not in keywords:
            keywords.append(alias)
    if not keywords:
        keywords.append(symbol)
    return keywords


# ---------------------------------------------------------------------------
# East Money fetcher
# ---------------------------------------------------------------------------

def fetch_eastmoney(keyword: str, page_size: int = 20) -> List[Dict[str, Any]]:
    """Fetch news articles from East Money search API."""
    param_payload = {
        "uid": "",
        "keyword": keyword,
        "type": ["cmsArticleWebOld"],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {
            "cmsArticleWebOld": {
                "searchScope": "default",
                "sort": "default",
                "pageIndex": 1,
                "pageSize": page_size,
                "preTag": "",
                "postTag": "",
            }
        },
    }
    params = {"cb": "jQuery", "param": json.dumps(param_payload, ensure_ascii=False)}
    try:
        resp = requests.get(
            EASTMONEY_SEARCH_URL,
            params=params,
            headers=EASTMONEY_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        text = resp.text
        jsonp_start = text.index("(") + 1
        jsonp_end = text.rindex(")")
        data = json.loads(text[jsonp_start:jsonp_end])
        raw_items = data.get("result", {}).get("cmsArticleWebOld", [])
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("list", [])
        return raw_items
    except Exception as e:
        print(f"  [WARN] 东方财富抓取失败 ({keyword}): {e}", file=sys.stderr)
        return []


def normalize_eastmoney(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize an East Money article to a standard schema."""
    title = re.sub(r"<[^>]+>", "", raw.get("title", ""))
    content_snippet = re.sub(r"<[^>]+>", "", raw.get("content", ""))[:300]
    return {
        "id": hashlib.md5(raw.get("url", title).encode()).hexdigest()[:12],
        "title": title,
        "url": raw.get("url", ""),
        "published_at": raw.get("date", ""),
        "content_snippet": content_snippet,
        "source": "eastmoney",
        "source_id": raw.get("code", ""),
    }


# ---------------------------------------------------------------------------
# Time filtering
# ---------------------------------------------------------------------------

def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse various datetime string formats."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str, fmt).replace(
                tzinfo=timezone(timedelta(hours=8))
            )
        except ValueError:
            continue
    return None


def filter_by_time(
    articles: List[Dict[str, Any]], hours: int
) -> List[Dict[str, Any]]:
    """Keep only articles within the given time window."""
    cutoff = datetime.now(timezone(timedelta(hours=8))) - timedelta(hours=hours)
    filtered = []
    for a in articles:
        dt = parse_datetime(a.get("published_at", ""))
        if dt and dt >= cutoff:
            filtered.append(a)
        elif dt is None:
            filtered.append(a)
    return filtered


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate by article id."""
    seen = set()
    result = []
    for a in articles:
        aid = a.get("id", "")
        if aid and aid in seen:
            continue
        seen.add(aid)
        result.append(a)
    return result


# ---------------------------------------------------------------------------
# Main fetch pipeline
# ---------------------------------------------------------------------------

def fetch_all_news(
    holdings: List[Dict[str, Any]], hours: int = 24
) -> Dict[str, Any]:
    """Fetch news for all holdings and return structured results."""
    now = datetime.now(timezone(timedelta(hours=8)))
    results = []

    for h in holdings:
        symbol = h.get("symbol", "?")
        name = h.get("name", symbol)
        market = h.get("market", "?")
        print(f"\n[FETCH] {name} ({symbol}.{market})")
        keywords = get_search_keywords(h)

        all_articles: List[Dict[str, Any]] = []
        for kw in keywords:
            print(f"  关键词: {kw}")
            raw_items = fetch_eastmoney(kw, page_size=20)
            articles = [normalize_eastmoney(r) for r in raw_items]
            print(f"    → 获取 {len(articles)} 条")
            all_articles.extend(articles)
            time.sleep(0.5)

        all_articles = deduplicate(all_articles)
        in_window = filter_by_time(all_articles, hours)
        print(f"  去重后 {len(all_articles)} 条，{hours}h 内 {len(in_window)} 条")

        results.append(
            {
                "symbol": symbol,
                "name": name,
                "market": market,
                "keywords_used": keywords,
                "total_fetched": len(all_articles),
                "in_time_window": len(in_window),
                "news": in_window,
            }
        )

    total_news = sum(r["in_time_window"] for r in results)
    output = {
        "fetch_time": now.isoformat(),
        "time_window_hours": hours,
        "portfolio_summary": {
            "count": len(holdings),
            "markets": sorted(set(h.get("market", "?") for h in holdings)),
        },
        "total_news_count": total_news,
        "results": results,
    }
    return output


# ---------------------------------------------------------------------------
# Raw data storage
# ---------------------------------------------------------------------------

def save_raw(data: Dict[str, Any], prefix: str = "fetch") -> Path:
    """Save raw fetch results to data/raw/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RAW_DIR / f"{prefix}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVED] {path}")
    return path


# ---------------------------------------------------------------------------
# Claude deep analysis
# ---------------------------------------------------------------------------

def analyze_with_claude(
    fetch_data: Dict[str, Any], holdings: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Call Claude to pick the top-3 most noteworthy news items."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[WARN] ANTHROPIC_API_KEY 未设置，跳过深度分析", file=sys.stderr)
        return None

    try:
        import anthropic
    except ImportError:
        print("[WARN] anthropic SDK 未安装，跳过深度分析", file=sys.stderr)
        return None

    all_news = []
    for result in fetch_data.get("results", []):
        symbol = result["symbol"]
        name = result["name"]
        for n in result.get("news", []):
            all_news.append(
                {
                    "holding": f"{name}({symbol})",
                    "title": n["title"],
                    "date": n["published_at"],
                    "snippet": n["content_snippet"][:200],
                    "url": n["url"],
                }
            )

    if not all_news:
        print("[INFO] 无新闻可供分析")
        return None

    holdings_desc = "、".join(
        f"{h.get('name', h['symbol'])}({h['symbol']}.{h['market']})"
        for h in holdings
    )
    news_text = json.dumps(all_news, ensure_ascii=False, indent=2)

    prompt = f"""你是一位专业的基金经理助理。以下是用户当前持仓标的：
{holdings_desc}

以下是最近抓取到的与这些持仓相关的新闻列表（JSON 格式）：
{news_text}

请完成以下任务：
1. 从上述新闻中筛选出**最值得关注的 3 条信息**。
2. 对每条信息，说明：
   - 涉及哪个持仓标的
   - 为什么值得关注（对持仓可能产生什么影响）
   - 建议的关注等级（高/中/低）

输出要求：
- 使用中文回答
- 结构清晰，编号列出
- 每条附上原始新闻标题和链接
- 最后给出一句话总结：今天持仓整体的信息面情况"""

    print("\n[ANALYZE] 正在调用 Claude 进行深度分析...")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    analysis_text = message.content[0].text
    analysis_result = {
        "analysis_time": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "model": "claude-sonnet-4-20250514",
        "holdings_analyzed": holdings_desc,
        "news_count_input": len(all_news),
        "analysis": analysis_text,
    }

    print("\n" + "=" * 60)
    print("📊 深度分析结果")
    print("=" * 60)
    print(analysis_text)
    print("=" * 60)

    return analysis_result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PFA 持仓感知器 — 抓取持仓相关新闻"
    )
    parser.add_argument(
        "--portfolio",
        type=Path,
        default=DEFAULT_PORTFOLIO,
        help="持仓配置文件路径 (默认: config/my-portfolio.json)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=72,
        help="抓取时间窗口，单位小时 (默认: 72)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="抓取后调用 Claude 进行深度分析",
    )
    args = parser.parse_args()

    portfolio = load_portfolio(args.portfolio)
    holdings = portfolio.get("holdings", [])
    if not holdings:
        print("[ERROR] 持仓列表为空", file=sys.stderr)
        sys.exit(1)

    fetch_data = fetch_all_news(holdings, hours=args.hours)
    fetch_path = save_raw(fetch_data, prefix="fetch")

    print(f"\n[SUMMARY] 共抓取 {fetch_data['total_news_count']} 条新闻")
    for r in fetch_data["results"]:
        print(f"  {r['name']}({r['symbol']}): {r['in_time_window']} 条")

    if args.analyze:
        analysis = analyze_with_claude(fetch_data, holdings)
        if analysis:
            save_raw(analysis, prefix="analysis")

    print("\n[DONE] 持仓感知器执行完毕")


if __name__ == "__main__":
    main()
