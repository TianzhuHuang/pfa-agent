"""
个股对话服务 — symbol + session_id 维度的持久化

支持 DB 与 JSON 回退。与 chat_service 分离：首页对话 symbol=null，个股对话 symbol+session_id。
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
_USE_DB = os.environ.get("PFA_USE_DB", "1") == "1"


def _ticker_chat_dir(user_id: str, symbol: str) -> Path:
    return ROOT / "data" / "users" / (user_id or "admin") / "ticker_chat" / (symbol or "")


def _list_sessions_json(user_id: str, symbol: str) -> List[Dict[str, Any]]:
    """JSON 回退：列出该标的的会话。"""
    d = _ticker_chat_dir(user_id, symbol)
    if not d.exists():
        return []
    out = []
    for f in d.glob("*.json"):
        sid = f.stem
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            msgs = data.get("messages", [])
            first_q = ""
            for m in msgs:
                if m.get("role") == "user":
                    first_q = (m.get("content", "") or "")[:30]
                    break
            mtime = f.stat().st_mtime if f.exists() else 0
            updated = datetime.utcfromtimestamp(mtime).isoformat() if mtime else ""
            out.append({"session_id": sid, "first_question": first_q, "updated_at": updated})
        except (OSError, json.JSONDecodeError):
            continue
    out.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return out[:50]


def _load_session_json(user_id: str, symbol: str, session_id: str) -> List[Dict[str, Any]]:
    """JSON 回退：加载指定会话消息。"""
    p = _ticker_chat_dir(user_id, symbol) / f"{session_id}.json"
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", [])
    except (OSError, json.JSONDecodeError):
        return []


def _save_session_json(
    user_id: str, symbol: str, session_id: str, messages: List[Dict[str, Any]]
) -> None:
    """JSON 回退：保存会话消息。"""
    d = _ticker_chat_dir(user_id, symbol)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{session_id}.json"
    out = messages[-200:] if len(messages) > 200 else messages
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"messages": out}, f, ensure_ascii=False, indent=2)


def list_sessions(user_id: str = "admin", symbol: str = "") -> List[Dict[str, Any]]:
    """该标的的会话列表，按 updated_at 倒序。每项含 session_id、first_question（≤30 字）、updated_at。"""
    if _USE_DB:
        try:
            return _list_sessions_db(user_id or "admin", (symbol or "").strip())
        except Exception:
            pass
    return _list_sessions_json(user_id or "admin", (symbol or "").strip())


def _list_sessions_db(user_id: str, symbol: str) -> List[Dict[str, Any]]:
    from sqlalchemy import func
    from backend.database.session import get_session, init_db
    from backend.database.models import ChatMessage

    init_db()
    db = get_session()
    try:
        rows = (
            db.query(
                ChatMessage.session_id,
                func.max(ChatMessage.created_at).label("updated_at"),
            )
            .filter(ChatMessage.user_id == user_id)
            .filter(ChatMessage.symbol == symbol)
            .filter(ChatMessage.session_id.isnot(None))
            .group_by(ChatMessage.session_id)
            .order_by(func.max(ChatMessage.created_at).desc())
            .limit(50)
            .all()
        )
        out = []
        for sid, updated in rows:
            if not sid:
                continue
            first_q = ""
            first_row = (
                db.query(ChatMessage.content)
                .filter(
                    ChatMessage.user_id == user_id,
                    ChatMessage.symbol == symbol,
                    ChatMessage.session_id == sid,
                    ChatMessage.role == "user",
                )
                .order_by(ChatMessage.created_at.asc())
                .first()
            )
            if first_row:
                first_q = (first_row[0] or "")[:30]
            out.append(
                {
                    "session_id": sid,
                    "first_question": first_q,
                    "updated_at": updated.isoformat() if updated else "",
                }
            )
        return out
    finally:
        db.close()


def load_session(
    user_id: str = "admin", symbol: str = "", session_id: str = ""
) -> List[Dict[str, Any]]:
    """加载指定会话的消息。"""
    if _USE_DB:
        try:
            return _load_session_db(user_id or "admin", (symbol or "").strip(), (session_id or "").strip())
        except Exception:
            pass
    return _load_session_json(user_id or "admin", (symbol or "").strip(), (session_id or "").strip())


def _load_session_db(user_id: str, symbol: str, session_id: str) -> List[Dict[str, Any]]:
    from backend.database.session import get_session, init_db
    from backend.database.models import ChatMessage

    init_db()
    db = get_session()
    try:
        rows = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.user_id == user_id,
                ChatMessage.symbol == symbol,
                ChatMessage.session_id == session_id,
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(200)
            .all()
        )
        return [{"role": r.role, "content": r.content} for r in rows]
    finally:
        db.close()


def save_session(
    user_id: str,
    symbol: str,
    session_id: str,
    messages: List[Dict[str, Any]],
) -> None:
    """覆盖保存该会话的消息。"""
    if _USE_DB:
        try:
            _save_session_db(user_id or "admin", (symbol or "").strip(), (session_id or "").strip(), messages)
            return
        except Exception:
            pass
    _save_session_json(user_id or "admin", (symbol or "").strip(), (session_id or "").strip(), messages)


def _save_session_db(user_id: str, symbol: str, session_id: str, messages: List[Dict[str, Any]]) -> None:
    from backend.database.session import get_session, init_db
    from backend.database.models import ChatMessage

    init_db()
    db = get_session()
    try:
        db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id,
            ChatMessage.symbol == symbol,
            ChatMessage.session_id == session_id,
        ).delete()
        for m in messages[-200:]:
            role = m.get("role", "assistant")
            content = m.get("content", "")
            if isinstance(content, str):
                content = content.replace("\r\n", "\n").replace("\r", "\n")
            else:
                content = str(content)
            db.add(
                ChatMessage(
                    user_id=user_id,
                    role=role,
                    content=content,
                    symbol=symbol,
                    session_id=session_id,
                )
            )
        db.commit()
    finally:
        db.close()


def list_all_ticker_sessions(user_id: str = "admin") -> List[Dict[str, Any]]:
    """列出所有标的的会话，合并后按 updated_at 倒序。每项含 type, symbol, symbol_name, session_id, first_question, updated_at。"""
    if _USE_DB:
        try:
            return _list_all_ticker_sessions_db(user_id or "admin")
        except Exception:
            pass
    return _list_all_ticker_sessions_json(user_id or "admin")


def _list_all_ticker_sessions_json(user_id: str) -> List[Dict[str, Any]]:
    base = ROOT / "data" / "users" / (user_id or "admin") / "ticker_chat"
    if not base.exists():
        return []
    out = []
    for sym_dir in base.iterdir():
        if not sym_dir.is_dir():
            continue
        symbol = sym_dir.name
        for f in sym_dir.glob("*.json"):
            sid = f.stem
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                msgs = data.get("messages", [])
                first_q = ""
                for m in msgs:
                    if m.get("role") == "user":
                        first_q = (m.get("content", "") or "")[:30]
                        break
                mtime = f.stat().st_mtime if f.exists() else 0
                updated = datetime.utcfromtimestamp(mtime).isoformat() if mtime else ""
                out.append({
                    "type": "ticker",
                    "symbol": symbol,
                    "symbol_name": symbol,
                    "session_id": sid,
                    "first_question": first_q,
                    "updated_at": updated,
                })
            except (OSError, json.JSONDecodeError):
                continue
    out.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return out[:80]


def _list_all_ticker_sessions_db(user_id: str) -> List[Dict[str, Any]]:
    from sqlalchemy import func
    from backend.database.session import get_session, init_db
    from backend.database.models import ChatMessage
    from agents.secretary_agent import load_portfolio

    init_db()
    db = get_session()
    holdings = load_portfolio().get("holdings", [])
    symbol_names = {str(h.get("symbol", "")): str(h.get("name", "")) or str(h.get("symbol", "")) for h in holdings}

    try:
        rows = (
            db.query(
                ChatMessage.symbol,
                ChatMessage.session_id,
                func.max(ChatMessage.created_at).label("updated_at"),
            )
            .filter(ChatMessage.user_id == user_id)
            .filter(ChatMessage.symbol.isnot(None))
            .filter(ChatMessage.session_id.isnot(None))
            .group_by(ChatMessage.symbol, ChatMessage.session_id)
            .order_by(func.max(ChatMessage.created_at).desc())
            .limit(80)
            .all()
        )
        out = []
        for symbol, sid, updated in rows:
            if not symbol or not sid:
                continue
            first_q = ""
            first_row = (
                db.query(ChatMessage.content)
                .filter(
                    ChatMessage.user_id == user_id,
                    ChatMessage.symbol == symbol,
                    ChatMessage.session_id == sid,
                    ChatMessage.role == "user",
                )
                .order_by(ChatMessage.created_at.asc())
                .first()
            )
            if first_row:
                first_q = (first_row[0] or "")[:30]
            out.append({
                "type": "ticker",
                "symbol": symbol,
                "symbol_name": symbol_names.get(symbol, symbol),
                "session_id": sid,
                "first_question": first_q,
                "updated_at": updated.isoformat() if updated else "",
            })
        return out
    finally:
        db.close()


def get_or_create_last_session(user_id: str = "admin", symbol: str = "") -> Optional[str]:
    """返回该标的最后活跃的 session_id；若无则返回 None（前端将新建）。"""
    sessions = list_sessions(user_id, symbol)
    if sessions:
        return sessions[0].get("session_id")
    return None
