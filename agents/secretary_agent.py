"""
私人秘书 (The Secretary)

职责：
  1. 编排 Scout → Analyst → Auditor 流水线
  2. 管理持仓配置（增删改 + CSV/JSON 批量导入）
  3. 管理数据源配置（RSS / Twitter / 监控 URL）
  4. 通过 Streamlit 提供 Web 控制中心

所有配置修改通过 Secretary 统一处理，保证数据一致性。
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.protocol import AgentMessage, make_request
from agents import scout_agent, analyst_agent, auditor_agent

CST = timezone(timedelta(hours=8))
PORTFOLIO_PATH = ROOT / "config" / "my-portfolio.json"
DATA_SOURCES_PATH = ROOT / "config" / "data-sources.json"


def _log(role: str, action: str, detail: str = ""):
    ts = datetime.now(CST).strftime("%H:%M:%S")
    print(f"[{ts}] {role:>10s} | {action} {detail}")


# ===================================================================
# Portfolio Management
# ===================================================================

def load_portfolio() -> dict:
    if PORTFOLIO_PATH.exists():
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "holdings": [],
            "channels": {"rss_urls": [], "xueqiu_user_ids": [], "twitter_handles": []},
            "preferences": {}}


def save_portfolio(data: dict) -> None:
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def validate_portfolio() -> Tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_portfolio.py"),
         str(PORTFOLIO_PATH)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return result.returncode == 0, result.stdout + result.stderr


def add_holding(symbol: str, name: str, market: str,
                cost_price: float = 0, quantity: int = 0,
                position_pct: float = 0, source: str = "manual") -> dict:
    """Add a single holding and return the updated portfolio."""
    portfolio = load_portfolio()
    now = datetime.now(CST).isoformat()
    h: Dict[str, Any] = {
        "symbol": symbol.strip(), "name": name.strip(),
        "market": market, "source": source, "updated_at": now,
    }
    if cost_price > 0:
        h["cost_price"] = cost_price
    if quantity > 0:
        h["quantity"] = quantity
    if position_pct > 0:
        h["position_pct"] = position_pct
    portfolio.setdefault("holdings", []).append(h)
    save_portfolio(portfolio)
    return portfolio


def remove_holding(symbol: str) -> dict:
    portfolio = load_portfolio()
    portfolio["holdings"] = [
        h for h in portfolio.get("holdings", []) if h.get("symbol") != symbol
    ]
    save_portfolio(portfolio)
    return portfolio


def update_holdings_bulk(holdings: List[Dict]) -> dict:
    """Replace all holdings with a new list."""
    portfolio = load_portfolio()
    now = datetime.now(CST).isoformat()
    clean = []
    for h in holdings:
        sym = str(h.get("symbol", "")).strip()
        if not sym:
            continue
        entry: Dict[str, Any] = {
            "symbol": sym,
            "name": str(h.get("name", "")).strip(),
            "market": h.get("market", "A"),
            "source": h.get("source", "manual"),
            "updated_at": now,
        }
        for num_key in ("cost_price", "quantity", "position_pct"):
            val = h.get(num_key)
            if val and float(val) > 0:
                entry[num_key] = float(val)
        clean.append(entry)
    portfolio["holdings"] = clean
    save_portfolio(portfolio)
    return portfolio


def parse_csv_holdings(csv_text: str) -> List[Dict]:
    """Parse CSV text into holdings list. Expects headers: symbol,name,market,cost_price,quantity"""
    reader = csv.DictReader(io.StringIO(csv_text))
    holdings = []
    for row in reader:
        h: Dict[str, Any] = {
            "symbol": row.get("symbol", row.get("代码", "")).strip(),
            "name": row.get("name", row.get("名称", "")).strip(),
            "market": row.get("market", row.get("市场", "A")).strip(),
            "source": "csv",
        }
        for key, cn in [("cost_price", "成本价"), ("quantity", "数量"),
                        ("position_pct", "仓位")]:
            val = row.get(key, row.get(cn, ""))
            if val:
                try:
                    h[key] = float(val)
                except ValueError:
                    pass
        if h["symbol"]:
            holdings.append(h)
    return holdings


def parse_json_holdings(json_text: str) -> List[Dict]:
    """Parse JSON text into holdings list. Accepts array or {holdings:[...]}"""
    data = json.loads(json_text)
    if isinstance(data, list):
        return data
    return data.get("holdings", [])


# ===================================================================
# Data Source Management
# ===================================================================

def _default_sources() -> dict:
    return {
        "rss_urls": [],
        "twitter_handles": [],
        "monitor_urls": [],
        "xueqiu_user_ids": [],
    }


def load_data_sources() -> dict:
    """Load from data-sources.json, falling back to portfolio channels."""
    if DATA_SOURCES_PATH.exists():
        with open(DATA_SOURCES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    portfolio = load_portfolio()
    channels = portfolio.get("channels", {})
    sources = _default_sources()
    sources["rss_urls"] = channels.get("rss_urls", [])
    sources["twitter_handles"] = channels.get("twitter_handles", [])
    sources["xueqiu_user_ids"] = channels.get("xueqiu_user_ids", [])
    return sources


def save_data_sources(sources: dict) -> None:
    with open(DATA_SOURCES_PATH, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    portfolio = load_portfolio()
    portfolio.setdefault("channels", {})
    portfolio["channels"]["rss_urls"] = sources.get("rss_urls", [])
    portfolio["channels"]["twitter_handles"] = sources.get("twitter_handles", [])
    portfolio["channels"]["xueqiu_user_ids"] = sources.get("xueqiu_user_ids", [])
    save_portfolio(portfolio)


def add_source(source_type: str, value: str) -> dict:
    sources = load_data_sources()
    key = source_type if source_type in sources else f"{source_type}s"
    if key not in sources:
        sources[key] = []
    value = value.strip()
    if value and value not in sources[key]:
        sources[key].append(value)
    save_data_sources(sources)
    return sources


def remove_source(source_type: str, value: str) -> dict:
    sources = load_data_sources()
    key = source_type if source_type in sources else f"{source_type}s"
    if key in sources:
        sources[key] = [v for v in sources[key] if v != value]
    save_data_sources(sources)
    return sources


# ===================================================================
# Pipeline Orchestration
# ===================================================================

def run_full_pipeline(
    holdings: List[Dict],
    hours: int = 72,
    do_audit: bool = True,
) -> Dict[str, Any]:
    """Run Scout → Analyst → Auditor pipeline."""
    result: Dict[str, Any] = {
        "status": "ok", "scout_result": None,
        "analyst_result": None, "auditor_result": None,
        "pipeline_log": [],
    }

    def log(msg: str):
        result["pipeline_log"].append(msg)
        _log("Secretary", msg)

    log("Scout → 开始抓取新闻...")
    scout_req = make_request("secretary", "scout", "fetch_all",
                             holdings=holdings, hours=hours)
    scout_resp = scout_agent.handle(scout_req)

    if scout_resp.status != "ok":
        log(f"Scout 失败: {scout_resp.error}")
        result["status"] = "error"
        result["error"] = scout_resp.error
        return result

    total = scout_resp.payload.get("total", 0)
    log(f"Scout ← 完成，共 {total} 条新闻")
    result["scout_result"] = scout_resp.payload

    if total == 0:
        log("无新闻，流程结束")
        return result

    log("Analyst → 开始深度分析...")
    analyst_req = make_request("secretary", "analyst", "analyze",
                               items=scout_resp.payload["items"],
                               holdings=holdings)
    analyst_resp = analyst_agent.handle(analyst_req)

    if analyst_resp.status != "ok":
        log(f"Analyst 失败: {analyst_resp.error}")
        result["status"] = "partial"
        result["error"] = analyst_resp.error
        return result

    log(f"Analyst ← 完成 (model={analyst_resp.payload.get('model', '?')})")
    result["analyst_result"] = analyst_resp.payload

    if do_audit:
        log("Auditor → 开始交叉验证...")
        auditor_req = make_request("secretary", "auditor", "audit",
                                    analysis=analyst_resp.payload.get("analysis", ""),
                                    items=scout_resp.payload["items"],
                                    holdings=holdings)
        auditor_resp = auditor_agent.handle(auditor_req)

        if auditor_resp.status != "ok":
            log(f"Auditor 失败: {auditor_resp.error}（分析仍有效，未经审核）")
            result["status"] = "partial"
        else:
            log(f"Auditor ← 完成 (backend={auditor_resp.payload.get('backend', '?')})")
            result["auditor_result"] = auditor_resp.payload
    else:
        log("Auditor 跳过")

    log("流程完成")
    return result


def fetch_single_symbol(
    symbol: str, name: str, market: str, hours: int = 72
) -> Dict[str, Any]:
    req = make_request("secretary", "scout", "fetch_news",
                       symbol=symbol, name=name, market=market, hours=hours)
    resp = scout_agent.handle(req)
    if resp.status != "ok":
        return {"status": "error", "error": resp.error}
    return {"status": "ok", **resp.payload}
