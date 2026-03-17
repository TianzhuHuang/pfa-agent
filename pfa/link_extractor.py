"""
Link extractor — fetch web pages and extract main content for chat context.

Uses trafilatura when available, with a simple HTML fallback otherwise.
"""

from __future__ import annotations

import html
import os
import re
import time
from typing import Any, Dict, List

import requests


def _simple_clean_html(text: str) -> str:
    """Very small fallback extractor: strip tags and collapse whitespace."""
    # Remove script/style blocks
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    # Strip remaining tags
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    # Unescape entities
    text = html.unescape(text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_with_trafilatura(url: str, html_text: str) -> Dict[str, Any]:
    try:
        import trafilatura  # type: ignore
    except Exception:
        return {}

    try:
        downloaded = trafilatura.extract(
            html_text,
            include_comments=False,
            include_tables=False,
            no_fallback=True,
        )
    except Exception:
        downloaded = None
    if not downloaded:
        return {}
    return {"text": downloaded}


def fetch_link(url: str) -> Dict[str, Any]:
    """Fetch a single URL and extract main content with timing info."""
    out: Dict[str, Any] = {"url": url, "status": "error", "title": "", "text": ""}
    timings: Dict[str, float] = {}

    start_total = time.monotonic()
    try:
        fetch_start = time.monotonic()
        resp = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "PFA-LinkFetcher/1.0 (+https://example.com)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            allow_redirects=True,
        )
        timings["http_fetch_ms"] = (time.monotonic() - fetch_start) * 1000.0
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type and "xml" not in content_type:
            out["error"] = f"不支持的内容类型: {content_type[:60]}"
            return out
        html_text = resp.text or ""
    except Exception as e:
        timings["http_fetch_ms"] = timings.get("http_fetch_ms", 0.0)
        out["error"] = str(e)[:200]
        out["debug_timings"] = _finalize_timings(timings, start_total)
        return out

    # Extract title
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html_text)
    if m:
        out["title"] = html.unescape(m.group(1)).strip()

    # Try trafilatura first
    extract_start = time.monotonic()
    extracted: Dict[str, Any] = _extract_with_trafilatura(url, html_text)
    if not extracted:
        # Fallback: simple HTML stripping
        cleaned = _simple_clean_html(html_text)
        extracted = {"text": cleaned}
    timings["extract_main_ms"] = (time.monotonic() - extract_start) * 1000.0

    out["text"] = (extracted.get("text") or "").strip()
    if not out["text"]:
        out["error"] = "未能抽取正文内容"
        out["status"] = "error"
    else:
        out["status"] = "ok"

    if _debug_enabled():
        out["debug_timings"] = _finalize_timings(timings, start_total)
    return out


def fetch_links(urls: List[str]) -> Dict[str, Any]:
    """Fetch multiple URLs and return a batch result with optional timings."""
    results: List[Dict[str, Any]] = []
    batch_start = time.monotonic()
    for url in urls:
        url = (url or "").strip()
        if not url:
            continue
        results.append(fetch_link(url))
    batch_timings: Dict[str, float] = {}
    if _debug_enabled():
        batch_timings["total_ms"] = (time.monotonic() - batch_start) * 1000.0
    out: Dict[str, Any] = {"results": results}
    if batch_timings:
        out["debug_timings"] = batch_timings
    return out


def _debug_enabled() -> bool:
    return bool(os.environ.get("PFA_DEBUG_TIMING"))


def _finalize_timings(timings: Dict[str, float], start_total: float) -> Dict[str, float]:
    timings = {k: round(v, 1) for k, v in timings.items()}
    total_ms = (time.monotonic() - start_total) * 1000.0
    timings.setdefault("total_ms", round(total_ms, 1))
    return timings

