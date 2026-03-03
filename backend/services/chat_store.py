"""
对话存储统一入口 — DB 优先，JSON 回退

环境变量 PFA_USE_DB=1 时使用 SQLite；否则使用原有 JSON。
支持从 JSON 迁移到 DB。
user_id 未传时从 backend.context 读取（API 请求内有效）。
"""

import os
from typing import List, Dict, Any, Optional

_USE_DB = os.environ.get("PFA_USE_DB", "1") == "1"


def _resolve_user_id(user_id: Optional[str] = None) -> str:
    if user_id is not None and user_id != "":
        return user_id
    try:
        from backend.context import get_current_user_id
        return get_current_user_id()
    except ImportError:
        return "admin"


def load_chat_history(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    uid = _resolve_user_id(user_id)
    try:
        from backend.database.supabase_store import use_supabase, load_chat_history as _load_sb
        if use_supabase():
            return _load_sb(uid)
    except (ImportError, ValueError):
        pass
    if _USE_DB:
        try:
            from backend.services.chat_service import load_chat_history as _load_db
            return _load_db(uid)
        except Exception:
            pass
    from pfa.data.store import load_chat_history as _load_json
    return _load_json(uid)


def save_chat_history(messages: List[Dict[str, Any]], user_id: Optional[str] = None) -> None:
    uid = _resolve_user_id(user_id)
    try:
        from backend.database.supabase_store import use_supabase, save_chat_history as _save_sb
        if use_supabase():
            _save_sb(messages, uid)
            return
    except (ImportError, ValueError):
        pass
    if _USE_DB:
        try:
            from backend.services.chat_service import save_chat_history as _save_db
            _save_db(messages, uid)
            return
        except Exception:
            pass
    from pfa.data.store import save_chat_history as _save_json
    _save_json(messages, uid)


def migrate_json_to_db(user_id: Optional[str] = None) -> int:
    """从 JSON 迁移到 DB，返回迁移条数。"""
    uid = _resolve_user_id(user_id)
    from pfa.data.store import load_chat_history as _load_json
    msgs = _load_json(uid)
    if not msgs:
        return 0
    try:
        from backend.services.chat_service import save_chat_history as _save_db
        _save_db(msgs, uid)
        return len(msgs)
    except Exception:
        return 0
