"""
对话服务 — 基于 SQLite 的持久化存储

替代 pfa.data.store 的 JSON 方案，支持多终端同步。
"""

from typing import List, Dict, Any

from backend.database.session import get_session, init_db
from backend.database.models import ChatMessage


def load_chat_history(user_id: str = "admin") -> List[Dict[str, Any]]:
    """从数据库加载首页对话历史（symbol/session_id 为 null），按时间正序。"""
    init_db()
    db = get_session()
    try:
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == (user_id or "admin"))
            .filter(ChatMessage.symbol.is_(None))
            .filter(ChatMessage.session_id.is_(None))
            .order_by(ChatMessage.created_at.asc())
            .limit(200)
            .all()
        )
        return [{"role": r.role, "content": r.content} for r in rows]
    finally:
        db.close()


def save_chat_history(messages: List[Dict[str, Any]], user_id: str = "admin") -> None:
    """将首页对话写入数据库。仅操作 symbol/session_id 为 null 的记录。"""
    init_db()
    db = get_session()
    try:
        uid = user_id or "admin"
        db.query(ChatMessage).filter(ChatMessage.user_id == uid).filter(
            ChatMessage.symbol.is_(None)
        ).filter(ChatMessage.session_id.is_(None)).delete()
        for m in messages[-200:]:
            role = m.get("role", "assistant")
            content = m.get("content", "")
            if isinstance(content, str):
                content = content.replace("\r\n", "\n").replace("\r", "\n")
            else:
                content = str(content)
            db.add(ChatMessage(user_id=uid, role=role, content=content, symbol=None, session_id=None))
        db.commit()
    finally:
        db.close()


def get_global_session_meta(user_id: str = "admin") -> dict | None:
    """获取首页全局会话的元信息（首条提问、更新时间），用于统一历史列表。"""
    init_db()
    db = get_session()
    try:
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == (user_id or "admin"))
            .filter(ChatMessage.symbol.is_(None))
            .filter(ChatMessage.session_id.is_(None))
            .order_by(ChatMessage.created_at.asc())
            .limit(200)
            .all()
        )
        if not rows:
            return None
        first_q = ""
        for r in rows:
            if r.role == "user":
                first_q = (r.content or "")[:30]
                break
        last = rows[-1]
        return {
            "type": "global",
            "session_id": "global",
            "first_question": first_q or "首页对话",
            "updated_at": last.created_at.isoformat() if last.created_at else "",
        }
    finally:
        db.close()


def append_message(role: str, content: str, user_id: str = "admin") -> None:
    """追加单条消息（用于流式完成后写入）。"""
    init_db()
    db = get_session()
    try:
        content = (content or "").replace("\r\n", "\n").replace("\r", "\n")
        db.add(ChatMessage(user_id=user_id or "admin", role=role, content=content))
        db.commit()
    finally:
        db.close()
