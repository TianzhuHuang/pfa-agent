"""
私人秘书 (The Secretary)

职责：负责交互。编排 Scout → Analyst → Auditor 流水线，
      整理最终简报并渲染到 Streamlit UI。
技术重点：UI/UX、消息格式化、流程编排。

核心流程:
  1. Secretary 向 Scout 发送 fetch 指令
  2. Scout 返回结构化新闻数据
  3. Secretary 将数据转交 Analyst 进行深度分析
  4. Secretary 将分析报告交给 Auditor 做交叉验证
  5. Secretary 整合所有结果，渲染到界面
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.protocol import AgentMessage, make_request
from agents import scout_agent, analyst_agent, auditor_agent

CST = timezone(timedelta(hours=8))


def _log(role: str, action: str, detail: str = ""):
    ts = datetime.now(CST).strftime("%H:%M:%S")
    print(f"[{ts}] {role:>10s} | {action} {detail}")


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------

def run_full_pipeline(
    holdings: List[Dict],
    hours: int = 72,
    do_audit: bool = True,
) -> Dict[str, Any]:
    """Run the full Scout → Analyst → Auditor pipeline.

    Returns a dict with keys: scout_result, analyst_result, auditor_result, status.
    """
    result: Dict[str, Any] = {
        "status": "ok",
        "scout_result": None,
        "analyst_result": None,
        "auditor_result": None,
        "pipeline_log": [],
    }

    def log(msg: str):
        result["pipeline_log"].append(msg)
        _log("Secretary", msg)

    # --- Step 1: Scout fetches news ---
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

    # --- Step 2: Analyst produces analysis ---
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

    # --- Step 3: Auditor cross-checks ---
    if do_audit:
        log("Auditor → 开始交叉验证...")
        auditor_req = make_request("secretary", "auditor", "audit",
                                    analysis=analyst_resp.payload.get("analysis", ""),
                                    items=scout_resp.payload["items"],
                                    holdings=holdings)
        auditor_resp = auditor_agent.handle(auditor_req)

        if auditor_resp.status != "ok":
            log(f"Auditor 失败: {auditor_resp.error}（分析结果仍然有效，但未经审核）")
            result["status"] = "partial"
        else:
            backend = auditor_resp.payload.get("backend", "?")
            log(f"Auditor ← 完成 (backend={backend})")
            result["auditor_result"] = auditor_resp.payload
    else:
        log("Auditor 跳过（do_audit=False）")

    log("流程完成")
    return result


def fetch_single_symbol(
    symbol: str, name: str, market: str, hours: int = 72
) -> Dict[str, Any]:
    """Fetch news for a single symbol via Scout."""
    req = make_request("secretary", "scout", "fetch_news",
                       symbol=symbol, name=name, market=market, hours=hours)
    resp = scout_agent.handle(req)
    if resp.status != "ok":
        return {"status": "error", "error": resp.error}
    return {"status": "ok", **resp.payload}
