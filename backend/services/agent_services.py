"""
Agent 服务层 — 将 Scout, Analyst, Auditor 封装为 FastAPI 可调用的 Service
"""

from typing import Any, Dict, List, Generator
import uuid

from agents.protocol import make_request
from agents import scout_agent, analyst_agent, auditor_agent


class ScoutService:
    """Scout Agent 服务：抓取新闻。"""

    @staticmethod
    def fetch_all(holdings: List[Dict], hours: int = 72) -> Dict[str, Any]:
        req = make_request("backend", "scout", "fetch_all", holdings=holdings, hours=hours)
        resp = scout_agent.handle(req)
        if resp.status != "ok":
            return {"status": "error", "error": resp.error}
        return {"status": "ok", **resp.payload}

    @staticmethod
    def fetch_news(symbol: str, name: str, market: str, hours: int = 72) -> Dict[str, Any]:
        req = make_request("backend", "scout", "fetch_news", symbol=symbol, name=name, market=market, hours=hours)
        resp = scout_agent.handle(req)
        if resp.status != "ok":
            return {"status": "error", "error": resp.error}
        return {"status": "ok", **resp.payload}


class AnalystService:
    """Analyst Agent 服务：深度分析。"""

    @staticmethod
    def analyze(items: List[Dict], holdings: List[Dict]) -> Dict[str, Any]:
        req = make_request("backend", "analyst", "analyze", items=items, holdings=holdings)
        resp = analyst_agent.handle(req)
        if resp.status != "ok":
            return {"status": "error", "error": resp.error, "payload": resp.payload}
        return {"status": "ok", **resp.payload}


class AuditorService:
    """Auditor Agent 服务：交叉验证。"""

    @staticmethod
    def audit(analysis: str, items: List[Dict], holdings: List[Dict]) -> Dict[str, Any]:
        req = make_request("backend", "auditor", "audit", analysis=analysis, items=items, holdings=holdings)
        resp = auditor_agent.handle(req)
        if resp.status != "ok":
            return {"status": "error", "error": resp.error}
        return {"status": "ok", **resp.payload}


class BriefingService:
    """晨报流水线：Scout → Analyst → Auditor。"""

    @staticmethod
    def run_streaming(holdings: List[Dict], hours: int = 72, do_audit: bool = False) -> Generator[Dict, None, None]:
        """流式执行，yield 状态与结果。"""
        from agents.secretary_agent import run_full_pipeline_streaming
        task_id = str(uuid.uuid4())[:8]
        yield {"type": "task_id", "task_id": task_id}
        for evt in run_full_pipeline_streaming(holdings, hours=hours, do_audit=do_audit):
            evt["task_id"] = task_id
            yield evt
