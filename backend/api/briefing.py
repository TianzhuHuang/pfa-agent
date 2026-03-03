"""
Briefing & Analysis API — 晨报生成、分析记录

流式 SSE 接口，防止长时间请求超时。
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


def _extract_briefing(result: dict) -> dict | None:
    ar = result.get("analyst_result", {})
    briefing = ar.get("briefing")
    if not briefing and ar.get("analysis"):
        try:
            briefing = json.loads(ar.get("analysis", "{}"))
        except (json.JSONDecodeError, TypeError):
            pass
    return briefing


@router.get("/briefing/history")
def get_briefing_history(
    limit: int = 30,
    offset: int = 0,
    from_date: str | None = None,
    to_date: str | None = None,
    include_content: bool = False,
):
    """按日期倒序返回晨报历史，支持分页与日期范围。include_content=true 时返回完整内容。"""
    from backend.services.briefing_store import list_briefing_reports
    items = list_briefing_reports(
        limit=limit, offset=offset, from_date=from_date, to_date=to_date, include_content=include_content
    )
    return {"reports": items}


@router.get("/briefing/test-llm")
def test_llm_connection():
    """测试 DashScope API 是否可用，用于排查晨报卡住问题。"""
    import os
    import requests
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        return {"ok": False, "error": "DASHSCOPE_API_KEY 未设置"}
    try:
        r = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "qwen-plus", "messages": [{"role": "user", "content": "回复：ok"}], "max_tokens": 10},
            timeout=15,
            proxies={"http": None, "https": None},
        )
        r.raise_for_status()
        return {"ok": True, "message": "DashScope API 连接正常"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/briefing/{report_id}")
def get_briefing_by_id(report_id: int):
    """获取单条晨报完整内容（用于懒加载展开）。"""
    from backend.context import get_current_user_id
    uid = get_current_user_id()
    try:
        from backend.database.supabase_store import use_supabase, get_briefing_by_id as _get_sb
        if use_supabase():
            r = _get_sb(report_id, uid)
            if not r:
                return {"status": "error", "error": "未找到"}
            return r
    except (ImportError, ValueError):
        pass
    from backend.database.session import get_session
    from backend.database.models import BriefingReport
    db = get_session()
    try:
        r = db.query(BriefingReport).filter(
            BriefingReport.id == report_id,
            BriefingReport.user_id == uid,
        ).first()
        if not r:
            return {"status": "error", "error": "未找到"}
        return r.to_dict()
    finally:
        db.close()


@router.post("/briefing/generate")
def generate_briefing(hours: int = 24):
    """生成今日晨报：Scout → Analyst 流水线。流式返回状态与结果，防止超时。"""
    from agents.secretary_agent import load_portfolio

    p = load_portfolio()
    holdings = p.get("holdings", [])

    def generate():
        if not holdings:
            yield f"data: {json.dumps({'type': 'error', 'error': '请先添加持仓'}, ensure_ascii=False)}\n\n"
            return
        try:
            from backend.services.agent_services import BriefingService
            from backend.services.briefing_store import save_briefing_report
            for evt in BriefingService.run_streaming(holdings, hours=hours, do_audit=False):
                if evt.get("type") == "done" and evt.get("result"):
                    try:
                        save_briefing_report(evt["result"])
                    except Exception:
                        pass
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)[:500]}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/briefing/generate-sync")
def generate_briefing_sync(hours: int = 24):
    """同步版本（兼容旧调用，可能超时）。"""
    from agents.secretary_agent import load_portfolio, run_full_pipeline

    p = load_portfolio()
    holdings = p.get("holdings", [])
    if not holdings:
        return {"status": "error", "error": "请先添加持仓"}
    try:
        result = run_full_pipeline(holdings, hours=hours, do_audit=False)
        if result.get("status") not in ("ok", "partial"):
            return {"status": "error", "error": result.get("error", "生成失败")}
        briefing = _extract_briefing(result)
        return {
            "status": "ok",
            "briefing": briefing,
            "analysis_raw": result.get("analyst_result", {}).get("analysis"),
            "news_count": result.get("scout_result", {}).get("count", 0),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/analysis/list")
def list_analyses(limit: int = 20):
    """获取分析记录列表，按时间倒序。"""
    from pfa.data.store import load_all_analyses
    records = load_all_analyses()[:limit]
    return {
        "analyses": [
            {
                "id": r.id,
                "analysis_time": r.analysis_time,
                "model": r.model,
                "holdings_analyzed": r.holdings_analyzed,
                "news_count_input": r.news_count_input,
                "token_usage": r.token_usage,
            }
            for r in records
        ],
    }


@router.get("/analysis/{analysis_id}")
def get_analysis(analysis_id: str):
    """获取单条分析详情。"""
    from pfa.data.store import load_all_analyses
    records = load_all_analyses()
    for r in records:
        if r.id == analysis_id:
            return {
                "id": r.id,
                "analysis_time": r.analysis_time,
                "model": r.model,
                "holdings_analyzed": r.holdings_analyzed,
                "news_count_input": r.news_count_input,
                "analysis": r.analysis,
                "token_usage": r.token_usage,
            }
    return {"status": "error", "error": "未找到"}
