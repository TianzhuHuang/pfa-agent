"""
PFA 统一数据层 — 新闻 / 分析的存储与查询

所有数据源（东方财富、RSS、雪球等）抓取后统一写入此层；
Streamlit 面板、Phase 3 知识库均从此层读取，不再直接碰 raw JSON。

存储后端：本地 JSON 文件（data/users/{user_id}/store/）
多账号预留：所有函数接受 user_id 参数，默认 "admin"。
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent

CST = timezone(timedelta(hours=8))

DEFAULT_USER = "admin"


def _user_store_dir(user_id: str = DEFAULT_USER) -> Path:
    """Get the store directory for a specific user."""
    return ROOT / "data" / "users" / user_id / "store"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class FeedItem:
    """一条新闻 / 信息条目。"""
    id: str
    title: str
    url: str
    published_at: str
    content_snippet: str
    source: str
    source_id: str
    symbol: str
    symbol_name: str
    market: str
    fetched_at: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FeedItem":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AnalysisRecord:
    """一次深度分析记录。"""
    id: str
    analysis_time: str
    model: str
    holdings_analyzed: str
    news_count_input: int
    analysis: str
    token_usage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AnalysisRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _ensure_dir(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)


def _feeds_dir(user_id: str = DEFAULT_USER) -> Path:
    d = _user_store_dir(user_id) / "feeds"
    _ensure_dir(d)
    return d


def _analysis_dir(user_id: str = DEFAULT_USER) -> Path:
    d = _user_store_dir(user_id) / "analyses"
    _ensure_dir(d)
    return d


# Legacy path (for backward compatibility / migration)
_LEGACY_STORE = ROOT / "data" / "store"


def _legacy_feeds_dir() -> Path:
    d = _LEGACY_STORE / "feeds"
    return d if d.exists() else Path()


def _legacy_analysis_dir() -> Path:
    d = _LEGACY_STORE / "analyses"
    return d if d.exists() else Path()


# ---------------------------------------------------------------------------
# Feed items: save / query
# ---------------------------------------------------------------------------

def save_feed_items(
    items: List[FeedItem],
    source_label: str = "",
    user_id: str = DEFAULT_USER,
) -> Path:
    """Persist a batch of FeedItem."""
    if not items:
        return Path()
    now = datetime.now(CST)
    ts = now.strftime("%Y%m%d_%H%M%S")
    label = f"_{source_label}" if source_label else ""
    path = _feeds_dir(user_id) / f"feeds{label}_{ts}.json"
    data = {
        "saved_at": now.isoformat(),
        "count": len(items),
        "items": [it.to_dict() for it in items],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_all_feed_items(
    symbol: Optional[str] = None,
    source: Optional[str] = None,
    since_hours: Optional[int] = None,
    date_str: Optional[str] = None,
    user_id: str = DEFAULT_USER,
) -> List[FeedItem]:
    """Load feed items with optional filters."""
    # Collect from both user dir and legacy dir
    dirs = [_feeds_dir(user_id)]
    legacy = _legacy_feeds_dir()
    if legacy.exists():
        dirs.append(legacy)

    items: List[FeedItem] = []
    seen_ids: set = set()
    cutoff = None
    if since_hours:
        cutoff = datetime.now(CST) - timedelta(hours=since_hours)

    date_filter = (date_str or "").replace("-", "")

    for feeds_dir in dirs:
        if not feeds_dir.exists():
            continue
        for fp in sorted(feeds_dir.glob("feeds_*.json"), reverse=True):
            if date_filter and date_filter not in fp.stem:
                continue
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            for raw in data.get("items", []):
                item = FeedItem.from_dict(raw)
                if item.id in seen_ids:
                    continue
                seen_ids.add(item.id)
                if symbol and item.symbol != symbol:
                    continue
                if source and item.source != source:
                    continue
                if cutoff and item.published_at:
                    try:
                        pub = datetime.fromisoformat(
                            item.published_at.replace(" ", "T")
                        )
                        if pub.tzinfo is None:
                            pub = pub.replace(tzinfo=CST)
                        if pub < cutoff:
                            continue
                    except ValueError:
                        pass
                items.append(item)
    return items


# ---------------------------------------------------------------------------
# Analysis records: save / query
# ---------------------------------------------------------------------------

def save_analysis(
    record: AnalysisRecord,
    user_id: str = DEFAULT_USER,
) -> Path:
    """Persist an analysis record."""
    path = _analysis_dir(user_id) / f"analysis_{record.id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def load_all_analyses(user_id: str = DEFAULT_USER) -> List[AnalysisRecord]:
    """Load all analysis records, newest first."""
    dirs = [_analysis_dir(user_id)]
    legacy = _legacy_analysis_dir()
    if legacy.exists():
        dirs.append(legacy)

    records: List[AnalysisRecord] = []
    seen_ids: set = set()
    for d in dirs:
        if not d.exists():
            continue
        for fp in sorted(d.glob("analysis_*.json"), reverse=True):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                rec = AnalysisRecord.from_dict(data)
                if rec.id not in seen_ids:
                    seen_ids.add(rec.id)
                    records.append(rec)
            except (json.JSONDecodeError, OSError, TypeError):
                continue
    records.sort(key=lambda r: r.analysis_time, reverse=True)
    return records


def load_analysis_by_date(
    date_str: str,
    user_id: str = DEFAULT_USER,
) -> List[AnalysisRecord]:
    """Load analyses matching a date string (YYYY-MM-DD)."""
    return [a for a in load_all_analyses(user_id) if date_str in a.analysis_time]


# ---------------------------------------------------------------------------
# Migration: import legacy data/raw/ and data/store/ into user store
# ---------------------------------------------------------------------------

def migrate_legacy_to_user(user_id: str = DEFAULT_USER) -> int:
    """One-time migration of legacy data into user-scoped store."""
    count = 0

    # Migrate data/raw/ fetch files
    raw_dir = ROOT / "data" / "raw"
    if raw_dir.exists():
        for fp in sorted(raw_dir.glob("fetch_*.json")):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            fetched_at = data.get("fetch_time", "")
            items: List[FeedItem] = []
            for result in data.get("results", []):
                sym = result.get("symbol", "")
                name = result.get("name", "")
                market = result.get("market", "")
                for n in result.get("news", []):
                    items.append(FeedItem(
                        id=n.get("id", ""), title=n.get("title", ""),
                        url=n.get("url", ""), published_at=n.get("published_at", ""),
                        content_snippet=n.get("content_snippet", ""),
                        source=n.get("source", "eastmoney"),
                        source_id=n.get("source_id", ""),
                        symbol=sym, symbol_name=name, market=market,
                        fetched_at=fetched_at,
                    ))
            if items:
                save_feed_items(items, source_label="migrated", user_id=user_id)
                count += len(items)

    # Migrate data/raw/ analysis files
    if raw_dir.exists():
        for fp in sorted(raw_dir.glob("analysis_*.json")):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            ts = data.get("analysis_time", fp.stem)
            rec = AnalysisRecord(
                id=ts.replace(":", "").replace("-", "").replace("T", "_")[:15],
                analysis_time=data.get("analysis_time", ""),
                model=data.get("model", ""),
                holdings_analyzed=data.get("holdings_analyzed", ""),
                news_count_input=data.get("news_count_input", 0),
                analysis=data.get("analysis", ""),
                token_usage=data.get("token_usage", {}),
            )
            save_analysis(rec, user_id=user_id)
            count += 1

    return count
