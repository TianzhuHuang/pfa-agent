"""
实时行情 API — 新浪财经（毫秒级，无需浏览器）

替代 Playwright + 雪球方案，速度从 10s → 0.5s。
支持 A 股、港股。
"""

from __future__ import annotations

import re
import requests
from typing import Dict, List, Optional

SINA_HQ_URL = "https://hq.sinajs.cn/list="
SINA_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://finance.sina.com.cn/",
}


def _to_sina_code(symbol: str, market: str) -> str:
    """Convert PFA symbol to Sina format."""
    if market == "A":
        if symbol.startswith("6"):
            return f"sh{symbol}"
        else:
            return f"sz{symbol}"
    elif market == "HK":
        return f"hk{symbol}"
    elif market == "US":
        return f"gb_{symbol.lower()}"
    return ""


def get_realtime_quotes(holdings: List[Dict]) -> Dict[str, Dict]:
    """Get real-time quotes for all holdings via Sina Finance API.

    Returns {symbol: {current, percent, name, high, low, open, last_close}}.
    ~0.5s for any number of stocks (single HTTP call).
    """
    code_map = {}
    for h in holdings:
        sym = h["symbol"]
        mkt = h.get("market", "A")
        sina_code = _to_sina_code(sym, mkt)
        if sina_code:
            code_map[sina_code] = sym

    if not code_map:
        return {}

    try:
        url = SINA_HQ_URL + ",".join(code_map.keys())
        resp = requests.get(url, headers=SINA_HEADERS, timeout=5)
        resp.encoding = "gbk"
    except Exception:
        return {}

    results = {}
    for line in resp.text.strip().split("\n"):
        if not line or "=" not in line:
            continue
        # Parse: var hq_str_sh600519="name,open,last_close,current,..."
        match = re.match(r'var hq_str_(\w+)="(.+)"', line.strip())
        if not match:
            continue
        sina_code = match.group(1)
        fields = match.group(2).split(",")
        pfa_symbol = code_map.get(sina_code, "")
        if not pfa_symbol:
            continue

        try:
            if sina_code.startswith(("sh", "sz")):
                # A-share: name,open,last_close,current,high,low,...
                current = float(fields[3])
                last_close = float(fields[2])
                pct = ((current - last_close) / last_close * 100) if last_close > 0 else 0
                results[pfa_symbol] = {
                    "current": current,
                    "percent": round(pct, 2),
                    "name": fields[0],
                    "open": float(fields[1]),
                    "high": float(fields[4]),
                    "low": float(fields[5]),
                    "last_close": last_close,
                }
            elif sina_code.startswith("hk"):
                # HK: eng_name,cn_name,open,last_close,high,low,current,change,pct,...
                current = float(fields[6])
                pct = float(fields[8])
                results[pfa_symbol] = {
                    "current": current,
                    "percent": round(pct, 2),
                    "name": fields[1],
                    "open": float(fields[2]),
                    "high": float(fields[4]),
                    "low": float(fields[5]),
                    "last_close": float(fields[3]),
                }
            elif sina_code.startswith("gb_"):
                # US: name,current,...
                if len(fields) > 1:
                    current = float(fields[1])
                    last_close = float(fields[26]) if len(fields) > 26 else 0
                    pct = ((current - last_close) / last_close * 100) if last_close > 0 else 0
                    results[pfa_symbol] = {
                        "current": current,
                        "percent": round(pct, 2),
                        "name": fields[0],
                    }
        except (ValueError, IndexError):
            continue

    return results
