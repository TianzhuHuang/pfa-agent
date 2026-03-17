"""
组合存储统一入口 — Supabase 优先，SQLite/JSON 仅本地开发

当 Supabase 已配置时，完全禁用本地 JSON；admin 返回空，禁止 migrate_json_to_db。
user_id 未传时尝试从 backend.context.current_user_id 读取（API 请求内有效）。
"""

import logging
import os
from typing import Any, Dict, List, Optional

_USE_DB = os.environ.get("PFA_USE_DB", "1") == "1"
_log = logging.getLogger("pfa.portfolio_store")


def _deduplicate_holdings(holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """合并同标的同账户的重复持仓（存量数据去重）。symbol 归一化：600900/600900.SH -> 600900。"""
    from pfa.symbol_utils import symbol_for_compare
    if not holdings:
        return []
    groups: Dict[tuple, List[Dict]] = {}
    for h in holdings:
        sym = str(h.get("symbol", "")).strip()
        acc = str(h.get("account", "默认")).strip() or "默认"
        mkt = str(h.get("market", "A"))[:2] or "A"
        key = (symbol_for_compare(sym, mkt), acc)
        groups.setdefault(key, []).append(h)
    out: List[Dict[str, Any]] = []
    for (canon_sym, acc), items in groups.items():
        if len(items) == 1:
            h = dict(items[0])
            h["symbol"] = canon_sym
            out.append(h)
            continue
        # 合并：数量累加，成本加权平均
        merged = dict(items[0])
        merged["symbol"] = canon_sym
        total_q = sum(float(x.get("quantity", 0) or 0) for x in items)
        total_cost_val = sum(
            float(x.get("quantity", 0) or 0) * float(x.get("cost_price", 0) or 0)
            for x in items
        )
        merged["quantity"] = total_q
        merged["cost_price"] = round(total_cost_val / total_q, 4) if total_q > 0 else 0
        merged["updated_at"] = max(str(x.get("updated_at", "") or "") for x in items)
        if any(x.get("name") for x in items):
            merged["name"] = next((x.get("name") for x in items if x.get("name")), merged.get("name", ""))
        out.append(merged)
    return out


def _resolve_user_id(user_id: Optional[str] = None) -> str:
    if user_id is not None and user_id != "":
        return user_id
    try:
        from backend.context import get_current_user_id
        return get_current_user_id()
    except ImportError:
        return "admin"


def _empty_portfolio() -> Dict[str, Any]:
    """新用户空组合结构。"""
    return {
        "version": "1.0",
        "holdings": [],
        "accounts": [],
        "channels": {"rss_urls": [], "xueqiu_user_ids": [], "twitter_handles": []},
        "preferences": {},
    }


def _is_force_local_storage() -> bool:
    """本地模式（X-PFA-Local-Mode: 1）时使用本地 JSON/SQLite，不要求登录。"""
    try:
        from backend.context import get_force_local_storage
        return get_force_local_storage()
    except ImportError:
        return False


def load_portfolio(user_id: Optional[str] = None) -> Dict[str, Any]:
    uid = _resolve_user_id(user_id)
    try:
        from backend.database.supabase_store import use_supabase, load_portfolio_db, save_portfolio_db
        if use_supabase() and not _is_force_local_storage():
            # Supabase 已配置且非本地模式：完全禁用 JSON 路径
            if uid in ("admin", ""):
                return _empty_portfolio()
            try:
                data = load_portfolio_db(uid)
                holdings = data.get("holdings", [])
                deduped = _deduplicate_holdings(holdings)
                if len(deduped) < len(holdings):
                    data = dict(data)
                    data["holdings"] = deduped
                    try:
                        save_portfolio_db(data, uid)
                        _log.info("load_portfolio: 合并重复持仓 %d -> %d 条", len(holdings), len(deduped))
                    except Exception as se:
                        _log.warning("load_portfolio: 合并后保存失败，仅返回合并结果: %s", se)
                return data
            except Exception as e:
                _log.warning("Supabase load_portfolio failed user_id=%s: %s", uid, e)
                return _empty_portfolio()
    except (ImportError, ValueError):
        pass
    # 未配置 Supabase：SQLite + JSON（仅本地开发）
    if _USE_DB:
        try:
            from backend.services.portfolio_service import load_portfolio_db, migrate_json_to_db, save_portfolio_db
            data = load_portfolio_db(uid)
            if uid in ("admin", "") and not data.get("holdings") and not data.get("accounts"):
                if migrate_json_to_db(uid):
                    data = load_portfolio_db(uid)
            holdings = data.get("holdings", [])
            deduped = _deduplicate_holdings(holdings)
            if len(deduped) < len(holdings):
                data = dict(data)
                data["holdings"] = deduped
                try:
                    save_portfolio_db(data, uid)
                    _log.info("load_portfolio: 合并重复持仓 %d -> %d 条", len(holdings), len(deduped))
                except Exception as se:
                    _log.warning("load_portfolio: 合并后保存失败，仅返回合并结果: %s", se)
            return data
        except Exception:
            pass
    if uid not in ("admin", ""):
        return _empty_portfolio()
    from pfa.portfolio_json import load_portfolio_json, save_portfolio_json
    data = load_portfolio_json()
    holdings = data.get("holdings", [])
    deduped = _deduplicate_holdings(holdings)
    if len(deduped) < len(holdings):
        data = dict(data)
        data["holdings"] = deduped
        try:
            save_portfolio_json(data)
            _log.info("load_portfolio: 合并重复持仓 %d -> %d 条", len(holdings), len(deduped))
        except Exception as se:
            _log.warning("load_portfolio: 合并后保存失败，仅返回合并结果: %s", se)
    return data


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


class AuthRequiredError(Exception):
    """Supabase 已配置但 user_id 为 admin，需用户登录后再操作。"""
    pass


def save_portfolio(data: Dict[str, Any], user_id: Optional[str] = None) -> None:
    uid = _resolve_user_id(user_id)
    try:
        from backend.database.supabase_store import use_supabase, save_portfolio_db
        if use_supabase() and not _is_force_local_storage():
            if uid in ("admin", ""):
                _log.warning("save_portfolio: Supabase 已配置但 user_id=admin，拒绝静默 no-op，需用户登录")
                raise AuthRequiredError("请重新登录后再操作")
            save_portfolio_db(data, uid)
            return
    except (ImportError, ValueError):
        pass
    except Exception as e:
        _log.warning("Supabase save_portfolio failed user_id=%s: %s", uid, e)
        raise
    # 未配置 Supabase：SQLite + JSON（仅本地开发）
    if _USE_DB:
        try:
            from backend.services.portfolio_service import save_portfolio_db
            save_portfolio_db(data, uid)
            from pfa.portfolio_json import save_portfolio_json
            save_portfolio_json(data)
            return
        except Exception:
            pass
    from pfa.portfolio_json import save_portfolio_json
    save_portfolio_json(data)
