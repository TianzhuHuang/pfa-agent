"""
组合存储统一入口 — DB 优先，JSON 回退

环境变量 PFA_USE_DB=1 时使用 SQLite；否则使用 JSON。
user_id 未传时尝试从 backend.context.current_user_id 读取（API 请求内有效）。
"""

import os
from typing import Any, Dict, Optional

_USE_DB = os.environ.get("PFA_USE_DB", "1") == "1"


def _resolve_user_id(user_id: Optional[str] = None) -> str:
    if user_id is not None and user_id != "":
        return user_id
    try:
        from backend.context import get_current_user_id
        return get_current_user_id()
    except ImportError:
        return "admin"


def load_portfolio(user_id: Optional[str] = None) -> Dict[str, Any]:
    uid = _resolve_user_id(user_id)
    try:
        from backend.database.supabase_store import use_supabase, load_portfolio_db
        if use_supabase() and uid not in ("admin", ""):
            # Supabase user_id 需为 UUID，admin 回退到 JSON
            # 新用户无数据时直接返回空，禁止将本地 JSON 迁移到新用户（避免生产环境泄露测试数据）
            data = load_portfolio_db(uid)
            return data
    except (ImportError, ValueError, Exception):
        pass
    if _USE_DB:
        try:
            from backend.services.portfolio_service import load_portfolio_db, migrate_json_to_db
            data = load_portfolio_db(uid)
            # 仅 admin 空数据时从 JSON 迁移，避免其他 user_id 误加载测试数据
            if uid in ("admin", "") and not data.get("holdings") and not data.get("accounts"):
                if migrate_json_to_db(uid):
                    data = load_portfolio_db(uid)
            return data
        except Exception:
            pass
    from pfa.portfolio_json import load_portfolio_json
    return load_portfolio_json()


def _migrate_json_to_supabase(user_id: str) -> bool:
    """从 JSON 迁移到 Supabase。"""
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    path = ROOT / "config" / "my-portfolio.json"
    if not path.exists():
        return False
    try:
        import json
        from backend.database.supabase_store import save_portfolio_db
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        save_portfolio_db(data, user_id)
        return True
    except Exception:
        return False


def save_portfolio(data: Dict[str, Any], user_id: Optional[str] = None) -> None:
    uid = _resolve_user_id(user_id)
    try:
        from backend.database.supabase_store import use_supabase, save_portfolio_db
        if use_supabase() and uid not in ("admin", ""):
            save_portfolio_db(data, uid)
            from pfa.portfolio_json import save_portfolio_json
            save_portfolio_json(data)
            return
    except (ImportError, ValueError):
        pass
    if _USE_DB:
        try:
            from backend.services.portfolio_service import save_portfolio_db
            save_portfolio_db(data, uid)
            from pfa.portfolio_json import save_portfolio_json
            save_portfolio_json(data)  # 双写，保持 JSON 与 validate 等脚本兼容
            return
        except Exception:
            pass
    from pfa.portfolio_json import save_portfolio_json
    save_portfolio_json(data)
