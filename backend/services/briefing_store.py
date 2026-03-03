"""
晨报持久化 — 保存与查询 BriefingReport

user_id 未传时从 backend.context 读取（API 请求内有效）。
"""

import json
from datetime import datetime, date, timedelta, time
from typing import List, Optional

from sqlalchemy import desc

from backend.database.session import get_session
from backend.database.models import BriefingReport


def _resolve_user_id(user_id: Optional[str] = None) -> str:
    if user_id is not None and user_id != "":
        return user_id
    try:
        from backend.context import get_current_user_id
        return get_current_user_id()
    except ImportError:
        return "admin"


def _extract_briefing(result: dict) -> Optional[dict]:
    ar = result.get("analyst_result", {})
    briefing = ar.get("briefing")
    if not briefing and ar.get("analysis"):
        try:
            briefing = json.loads(ar.get("analysis", "{}"))
        except (json.JSONDecodeError, TypeError):
            pass
    return briefing


def _make_summary(briefing: dict) -> str:
    """生成 20 字以内摘要。"""
    one_liner = (briefing.get("one_liner") or "").strip()
    if one_liner:
        return one_liner[:20] + ("..." if len(one_liner) > 20 else "")
    moves = briefing.get("portfolio_moves") or []
    if moves:
        first = moves[0]
        name = first.get("name") or first.get("symbol") or ""
        event = (first.get("event_summary") or "")[:15]
        return f"{name} {event}".strip()[:20]
    reads = briefing.get("must_reads") or []
    if reads:
        title = (reads[0].get("title") or "")[:20]
        return title
    return "投研晨报"


def save_briefing_report(result: dict, user_id: Optional[str] = None) -> Optional[BriefingReport]:
    """Analyst 完成后保存晨报到数据库。同一天覆盖旧记录。"""
    uid = _resolve_user_id(user_id)
    try:
        from backend.database.supabase_store import use_supabase, save_briefing_report as _save_sb
        if use_supabase():
            _save_sb(result, uid)
            return None
    except (ImportError, ValueError):
        pass
    briefing = _extract_briefing(result)
    if not briefing:
        return None
    summary = _make_summary(briefing)
    content = json.dumps(briefing, ensure_ascii=False)
    today = date.today()
    report_dt = datetime.combine(today, time.min)
    end_dt = report_dt + timedelta(days=1)

    db = get_session()
    try:
        # 同一天只保留最新一条
        existing = db.query(BriefingReport).filter(
            BriefingReport.user_id == uid,
            BriefingReport.report_date >= report_dt,
            BriefingReport.report_date < end_dt,
        ).first()
        if existing:
            existing.content = content
            existing.summary = summary
            existing.created_at = datetime.utcnow()
            db.commit()
            return existing
        report = BriefingReport(
            user_id=uid,
            report_date=report_dt,
            content=content,
            summary=summary,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_briefing_reports(
    user_id: Optional[str] = None,
    limit: int = 30,
    offset: int = 0,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    include_content: bool = False,
) -> List[dict]:
    """按日期倒序返回晨报列表，支持分页与日期范围。include_content=False 时仅返回摘要，用于懒加载。"""
    uid = _resolve_user_id(user_id)
    try:
        from backend.database.supabase_store import use_supabase, list_briefing_reports as _list_sb
        if use_supabase():
            return _list_sb(uid, limit, offset, from_date, to_date, include_content)
    except (ImportError, ValueError):
        pass
    db = get_session()
    try:
        q = db.query(BriefingReport).filter(BriefingReport.user_id == uid)
        if from_date:
            try:
                fd = datetime.strptime(from_date, "%Y-%m-%d")
                q = q.filter(BriefingReport.report_date >= fd)
            except ValueError:
                pass
        if to_date:
            try:
                td = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
                q = q.filter(BriefingReport.report_date < td)
            except ValueError:
                pass
        rows = q.order_by(desc(BriefingReport.report_date)).offset(offset).limit(limit).all()
        out = []
        for r in rows:
            d = r.to_dict()
            if not include_content:
                d.pop("content", None)
            out.append(d)
        return out
    finally:
        db.close()


def get_briefing_by_date(report_date: str, user_id: Optional[str] = None) -> Optional[dict]:
    """按日期获取单条晨报。"""
    uid = _resolve_user_id(user_id)
    db = get_session()
    try:
        rd = datetime.strptime(report_date, "%Y-%m-%d")
        end = rd + timedelta(days=1)
        r = db.query(BriefingReport).filter(
            BriefingReport.user_id == uid,
            BriefingReport.report_date >= rd,
            BriefingReport.report_date < end,
        ).first()
        return r.to_dict() if r else None
    except ValueError:
        return None
    finally:
        db.close()
