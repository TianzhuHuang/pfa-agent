"""
组合 JSON 读写 — 与 secretary_agent 解耦，供 portfolio_store 使用
"""

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_PATH = ROOT / "config" / "my-portfolio.json"


def load_portfolio_json() -> Dict[str, Any]:
    if PORTFOLIO_PATH.exists():
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "version": "1.0",
            "holdings": [],
            "channels": {"rss_urls": [], "xueqiu_user_ids": [], "twitter_handles": []},
            "preferences": {},
            "accounts": [],
        }
    data.setdefault("holdings", [])
    data.setdefault("channels", {})
    data.setdefault("preferences", {})
    data.setdefault("accounts", [])
    return data


def save_portfolio_json(data: Dict[str, Any]) -> None:
    data.setdefault("holdings", [])
    data.setdefault("channels", {})
    data.setdefault("preferences", {})
    data.setdefault("accounts", [])
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
